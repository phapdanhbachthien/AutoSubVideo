from array import array
import math
import unittest

from PySide6.QtMultimedia import QAudioFormat

from player.audio import GainProcessor, AudioRing


def format_for(sample_format=QAudioFormat.Float,channels=2):
    fmt=QAudioFormat();fmt.setSampleRate(48000);fmt.setChannelCount(channels);fmt.setSampleFormat(sample_format)
    return fmt


class AudioTests(unittest.TestCase):
    def test_true_five_times_pcm_amplitude(self):
        processor=GainProcessor();processor.gain=5.0
        samples=array('f',[.01,-.02,.03,-.04]*100)
        result=array('f');result.frombytes(processor.process(samples.tobytes(),format_for()))
        for before,after in zip(samples,result):
            self.assertAlmostEqual(after,before*5,places=6)
        before_rms=math.sqrt(sum(x*x for x in samples)/len(samples))
        after_rms=math.sqrt(sum(x*x for x in result)/len(result))
        self.assertAlmostEqual(after_rms/before_rms,5.0,places=5)

    def test_limiter_prevents_overflow_and_preserves_sign(self):
        processor=GainProcessor();processor.gain=5
        samples=array('h',[32760,-32760,1000,-1000])
        result=array('h');result.frombytes(processor.process(samples.tobytes(),format_for(QAudioFormat.Int16)))
        self.assertGreater(result[0],0);self.assertLess(result[1],0)
        self.assertTrue(all(-32768<=x<=32767 for x in result))
        self.assertEqual(result[2],5000);self.assertEqual(result[3],-5000)

    def test_mute_and_unsigned_silence(self):
        processor=GainProcessor();processor.muted=True
        self.assertEqual(processor.process(array('f',[.2,-.2]).tobytes(),format_for()),b'\0'*8)
        self.assertEqual(processor.process(bytes([255,0,200,50]),format_for(QAudioFormat.UInt8)),bytes([128]*4))

    def test_rate_processing_preserves_duration_ratio_and_channel_alignment(self):
        data=array('f',[.1,-.1]*4800).tobytes()
        for rate in [.25,.5,2,4]:
            processor=GainProcessor();processor.rate=rate
            output=processor.process(data,format_for())
            frames=len(output)//8
            self.assertAlmostEqual(frames,4800/rate,delta=5)
            self.assertEqual(len(output)%8,0)

    def test_ring_seek_flush_does_not_replay_old_audio(self):
        ring=AudioRing()
        ring.push(b'old-audio')
        self.assertEqual(bytes(ring.read(3)),b'old')
        ring.clear();ring.push(b'new-audio')
        self.assertEqual(bytes(ring.read(20)),b'new-audio')
        self.assertEqual(ring.bytesAvailable(),0)
