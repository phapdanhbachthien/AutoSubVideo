"""Real PCM gain before QAudioSink; QAudioOutput alone clamps volume to 100%."""
from array import array
import math
import threading

from PySide6.QtCore import QObject, Signal, QIODevice
from PySide6.QtMultimedia import QAudioBufferOutput, QAudioFormat, QAudioOutput, QAudioSink, QMediaDevices, QMediaPlayer


class GainProcessor:
    def __init__(self):
        self.gain = .7
        self.muted = False
        self.rate = 1.0
        self.reset()

    def reset(self):
        self._tail = []
        self._phase = 0.0

    @staticmethod
    def limit(value):
        # Preserve quiet material exactly; smoothly compress peaks instead of
        # wrapping integer samples or hard-clipping at boosts up to 5x.
        if not math.isfinite(value):
            return 0.0
        magnitude = abs(value)
        if magnitude <= .9:
            return value
        return math.copysign(.9 + .1 * (1 - math.exp(-min(100, (magnitude - .9) / .1))), value)

    def process(self, data, audio_format):
        spec = {QAudioFormat.Float: ('f', 1.0, 0), QAudioFormat.Int16: ('h', 32768.0, 0),
                QAudioFormat.Int32: ('i', 2147483648.0, 0), QAudioFormat.UInt8: ('B', 128.0, 128)}
        kind, scale, offset = spec[audio_format.sampleFormat()]
        samples = array(kind)
        channels = max(1, audio_format.channelCount())
        frame_size = samples.itemsize * channels
        samples.frombytes(data[:len(data)//frame_size*frame_size])
        values = [(value-offset)/scale for value in samples]
        if not math.isclose(self.rate, 1.0):
            values = self._tail + values
            frames = len(values)//channels
            result = []
            phase = self._phase
            while phase < frames-1:
                index = int(phase)
                fraction = phase-index
                for channel in range(channels):
                    first = values[index*channels+channel]
                    second = values[(index+1)*channels+channel]
                    result.append(first+(second-first)*fraction)
                phase += self.rate
            self._phase = phase-max(0,frames-1)
            self._tail = values[-channels:] if frames else []
            values = result
        gain = 0.0 if self.muted else self.gain
        boosted = [0.0]*len(values) if gain==0 else [self.limit(value*gain) for value in values]
        if kind == 'f':
            return array('f', boosted).tobytes()
        low, high = (-int(scale), int(scale)-1) if not offset else (0, 255)
        return array(kind, (max(low,min(high,round(value*scale+offset))) for value in boosted)).tobytes()


class AudioRing(QIODevice):
    def __init__(self,parent=None):
        super().__init__(parent)
        self._data = bytearray()
        self._lock = threading.Lock()
        self.open(QIODevice.ReadOnly | QIODevice.Unbuffered)

    def isSequential(self):
        return True

    def atEnd(self):
        return False

    def reset(self):
        # A pull audio stream has no file position. Clearing queued PCM is an
        # explicit operation in SoftwareAudioOutput.reset(), not a rewind.
        return True

    def bytesAvailable(self):
        with self._lock:
            length = len(self._data)
        return length + super().bytesAvailable()

    def push(self,data):
        with self._lock:
            self._data.extend(data)
        self.readyRead.emit()

    def clear(self):
        with self._lock:
            self._data.clear()

    def readData(self,maximum):
        with self._lock:
            result = bytes(self._data[:maximum])
            del self._data[:len(result)]
        return result


class SoftwareAudioOutput(QObject):
    """One silent Qt clock output + a PCM output with gain 0..5 before the sink.

    The clock output keeps Qt's playback scheduling, track selection and rate
    control. Its volume stays zero to prevent two audible copies. Decoded PCM
    goes through our processor and then the real output device at unity gain.
    """
    processedBuffer = Signal(bytes)
    outputError = Signal(str)

    def __init__(self,player,parent=None):
        super().__init__(parent)
        self.player = player
        self.processor = GainProcessor()
        self.clock_output = QAudioOutput(self)
        self.clock_output.setVolume(0.0)
        player.setAudioOutput(self.clock_output)
        device = QMediaDevices.defaultAudioOutput()
        self.format = device.preferredFormat() if not device.isNull() else QAudioFormat()
        if not self.format.isValid():
            self.format.setSampleRate(48000)
            self.format.setChannelCount(2)
            self.format.setSampleFormat(QAudioFormat.Float)
        self.buffer_output = QAudioBufferOutput(self.format,self)
        player.setAudioBufferOutput(self.buffer_output)
        self.buffer_output.audioBufferReceived.connect(self.receive)
        self.ring = AudioRing(self)
        self.sink = None if device.isNull() else QAudioSink(device,self.format,self)
        if self.sink:
            self.sink.setVolume(1.0)
            self.sink.setBufferSize(self.format.bytesForDuration(150000))
        self._started = False
        self._minimum_time = 0
        player.sourceChanged.connect(lambda _:self.reset())
        player.playbackStateChanged.connect(self.playback_state)

    def setVolume(self,volume):
        self.processor.gain = max(0.0,min(5.0,float(volume)))

    def volume(self):
        return self.processor.gain

    def setMuted(self,muted):
        self.processor.muted = bool(muted)

    def isMuted(self):
        return self.processor.muted

    def setRate(self,rate):
        self.reset(self.player.position())
        self.processor.rate = max(.25,min(4.0,float(rate)))

    def reset(self,position=0):
        if self.sink:
            # reset() discards pending device data immediately. stop() may wait
            # for a suspended stream to drain and freeze a seek/pause action.
            self.sink.reset()
        self._started = False
        self.ring.clear()
        self.processor.reset()
        self._minimum_time = max(0,int(position)*1000)

    def playback_state(self,state):
        if not self.sink:
            return
        if state == QMediaPlayer.PausedState and self._started:
            self.sink.suspend()
        elif state == QMediaPlayer.PlayingState:
            if self._started:
                self.sink.resume()
            elif self.ring.bytesAvailable():
                self.sink.start(self.ring)
                self._started = True
        elif state == QMediaPlayer.StoppedState and self.player.mediaStatus() != QMediaPlayer.EndOfMedia:
            self.reset()

    def receive(self,buffer):
        if not buffer.isValid():
            return
        start, end = buffer.startTime(), buffer.startTime()+buffer.duration()
        if end <= self._minimum_time:
            return
        raw = bytes(buffer.constData())
        if start < self._minimum_time:
            frames = round((self._minimum_time-start)*self.format.sampleRate()/1000000)
            raw = raw[frames*self.format.bytesPerFrame():]
        data = self.processor.process(raw,self.format)
        self.processedBuffer.emit(data)
        if not self.sink:
            return
        if self.ring.bytesAvailable() > self.format.bytesForDuration(2000000):
            # Recover sync after an exceptional UI/device stall, without growing
            # an unbounded audio queue or replaying seconds of stale sound.
            self.sink.reset()
            self._started = False
            self.ring.clear()
        self.ring.push(data)
        if not self._started and self.player.playbackState()==QMediaPlayer.PlayingState:
            self.sink.start(self.ring)
            self._started = True

    def pending_milliseconds(self):
        if not self.sink or not self._started:
            return 0
        buffered = max(0,self.sink.bufferSize()-self.sink.bytesFree())+self.ring.bytesAvailable()
        return round(self.format.durationForBytes(buffered)/1000)
