from pathlib import Path
from tempfile import TemporaryDirectory
import random
import unittest

from player.library import Playlist, SEEK_SECONDS, seek_target, time_label, read_playlist, write_playlist, read_srt, caption_text


class LibraryTests(unittest.TestCase):
    def test_all_requested_seek_steps_and_bounds(self):
        self.assertEqual(SEEK_SECONDS, (5, 10, 30, 60, 300, 600))
        for seconds in SEEK_SECONDS:
            self.assertEqual(seek_target(700000, seconds*1000, 2000000), 700000+seconds*1000)
            self.assertEqual(seek_target(700000, -seconds*1000, 2000000), 700000-seconds*1000)
        self.assertEqual(seek_target(100, -600000, 1000), 0)
        self.assertEqual(seek_target(100, 600000, 1000), 1000)
        self.assertEqual(time_label(3661000), '01:01:01')

    def test_playlist_navigation_repeat_remove_and_reorder(self):
        p = Playlist()
        p.add(['one.mp3', 'two.mp4', 'three.mkv', 'one.mp3'])
        self.assertEqual(len(p.items), 3)
        p.select(2)
        self.assertIsNone(p.advance(automatic=True))
        self.assertEqual(p.advance(), p.items[0])
        self.assertEqual(p.advance(-1), p.items[2])
        self.assertEqual(p.advance(automatic=True, repeat='one'), p.items[2])
        current = p.current
        p.reorder(list(reversed(p.items)))
        self.assertEqual(p.current, current)
        self.assertFalse(p.remove([1]))
        self.assertEqual(p.current, current)
        self.assertTrue(p.remove([p.index]))

    def test_shuffle_visits_each_track_then_stops_and_previous_uses_history(self):
        p = Playlist()
        p.add(['1.wav', '2.wav', '3.wav', '4.wav'])
        p.select(0)
        visited = [p.current]
        for _ in range(3):
            visited.append(p.advance(automatic=True, shuffle=True, rng=random.Random(9)))
        self.assertEqual(len(set(visited)), 4)
        self.assertIsNone(p.advance(automatic=True, shuffle=True))
        self.assertEqual(p.advance(-1, shuffle=True), visited[-2])
        self.assertIsNotNone(p.advance(automatic=True, shuffle=True, repeat='all'))

    def test_unicode_playlist_relative_paths_and_srt_overlap(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / 'nhạc.m3u8'
            p.write_text('#EXTM3U\n#EXTINF:10,Test\nBài hát.mp3\nhttps://example.com/test.mp4\n', encoding='utf-8-sig')
            entries = read_playlist(p)
            self.assertEqual(entries[0], (root/'Bài hát.mp3').as_uri())
            out = root/'saved.m3u8'
            write_playlist(out, entries)
            self.assertEqual(read_playlist(out), entries)
            srt = root/'phụ đề.srt'
            srt.write_text('1\n00:00:01,000 --> 00:00:03,000\nXin chào\n\n2\n00:00:02,000 --> 00:00:04,000\nViệt Nam\n', encoding='utf-8')
            cues = read_srt(srt)
            self.assertEqual(caption_text(cues, 2500), 'Xin chào\nViệt Nam')
            self.assertEqual(caption_text(cues, 4000), '')
