from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, unquote
import random
import re

MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.m4v', '.mpeg', '.mpg',
                    '.ts', '.m2ts', '.flv', '.vob', '.mp3', '.flac', '.wav', '.ogg', '.opus',
                    '.m4a', '.aac', '.wma', '.aiff', '.ape', '.alac', '.3gp'}
SEEK_SECONDS = (5, 10, 30, 60, 300, 600)


def seek_target(position, delta, duration):
    return max(0, min(max(0, int(duration)), int(position) + int(delta)))


def time_label(milliseconds):
    seconds = max(0, int(milliseconds)) // 1000
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'


def normalize_source(value):
    value = str(value).strip()
    if value.startswith(('https://', 'http://', 'file://')):
        return value
    return Path(value).expanduser().resolve().as_uri()


def source_title(uri):
    return unquote(urlparse(uri).path.rstrip('/').rsplit('/', 1)[-1]) or uri


class Playlist:
    def __init__(self):
        self.items = []
        self.index = -1
        self.history = []
        self.visited = set()

    @property
    def current(self):
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def add(self, values):
        for value in values:
            uri = normalize_source(value)
            if uri not in self.items:
                self.items.append(uri)
                self.visited.clear()

    def select(self, index):
        if not 0 <= index < len(self.items):
            return None
        self.index = index
        return self.current

    def advance(self, direction=1, *, automatic=False, shuffle=False, repeat='off', rng=None):
        if not self.items:
            return None
        if automatic and repeat == 'one' and self.current:
            return self.current
        if shuffle and direction < 0 and self.history:
            return self.select(self.history.pop())
        if shuffle and direction > 0:
            if self.index >= 0:
                self.visited.add(self.index)
            choices = [i for i in range(len(self.items)) if i not in self.visited]
            if not choices:
                if automatic and repeat == 'off':
                    return None
                self.visited = {self.index}
                choices = [i for i in range(len(self.items)) if i != self.index] or [0]
            if self.index >= 0:
                self.history.append(self.index)
            selected = (rng or random).choice(choices)
            self.visited.add(selected)
            return self.select(selected)
        next_index = self.index + direction
        if automatic and repeat == 'off' and next_index >= len(self.items):
            return None
        return self.select(next_index % len(self.items))

    def remove(self, rows):
        previous, old = self.current, self.index
        self.items = [value for i, value in enumerate(self.items) if i not in set(rows)]
        self.index = self.items.index(previous) if previous in self.items else min(old, len(self.items)-1)
        self.history.clear()
        self.visited.clear()
        return previous != self.current

    def reorder(self, values):
        current = self.current
        self.items = list(values)
        self.index = self.items.index(current) if current in self.items else -1
        self.history.clear()
        self.visited.clear()


def read_playlist(path):
    path = Path(path)
    entries = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            entries.append(normalize_source(line if line.startswith(('https://', 'http://', 'file://')) else path.parent / line))
    return entries


def write_playlist(path, entries):
    Path(path).write_text('#EXTM3U\n' + '\n'.join(entries) + '\n', encoding='utf-8')


@dataclass(frozen=True)
class Caption:
    start: int
    end: int
    text: str


def read_srt(path):
    text = Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n').strip()
    cues = []
    stamp = r'(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})'
    for block in re.split(r'\n[ \t]*\n', text):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            raise ValueError('SRT không hợp lệ; hãy dùng tệp UTF-8 có số thứ tự và mốc thời gian.')
        match = re.fullmatch(stamp + r'\s*-->\s*' + stamp, lines[1].strip())
        if not match:
            raise ValueError('Mốc thời gian SRT không hợp lệ.')
        a = list(map(int, match.groups()))
        milliseconds = lambda v: ((v[0]*60+v[1])*60+v[2])*1000+v[3]
        start, end = milliseconds(a[:4]), milliseconds(a[4:])
        if end <= start:
            raise ValueError('Thời gian kết thúc phụ đề phải lớn hơn thời gian bắt đầu.')
        cues.append(Caption(start, end, '\n'.join(lines[2:])))
    return sorted(cues, key=lambda cue: cue.start)


def caption_text(cues, position):
    return '\n'.join(c.text for c in cues if c.start <= position < c.end)
