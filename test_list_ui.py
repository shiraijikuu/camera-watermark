# -*- coding: utf-8 -*-
"""test_list_ui.py — 照片列表 搜索/排序/筛选 纯逻辑测试（不依赖 GUI）。

运行：python -m unittest test_list_ui -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


def make_photos():
    return [
        {'name': 'DSC0001.JPG', 'raw': False, 'meta': {'date_text': '2026-01-02', 'time_text': '10:00:00', 'camera_text': 'Sony A7C II'}},
        {'name': 'DSC0002.ARW', 'raw': True, 'meta': {'date_text': '2026-01-01', 'time_text': '09:00:00', 'camera_text': 'Sony A7C II'}},
        {'name': 'IMG_0003.JPG', 'raw': False, 'meta': {'date_text': '2026-01-03', 'time_text': '11:00:00', 'camera_text': 'Canon R5'}},
    ]


class FakeApp:
    def __init__(self, photos):
        self.photos = photos


class TestMatchesFilters(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp(make_photos())

    def test_empty_search_all(self):
        self.assertTrue(app.App._matches_filters(self.app, 0, '', '全部'))
        self.assertTrue(app.App._matches_filters(self.app, 1, '', '全部'))
        self.assertTrue(app.App._matches_filters(self.app, 2, '', '全部'))

    def test_search_substring_case_insensitive(self):
        self.assertTrue(app.App._matches_filters(self.app, 0, 'dsc', '全部'))
        self.assertTrue(app.App._matches_filters(self.app, 0, 'dsc0001', '全部'))
        self.assertTrue(app.App._matches_filters(self.app, 2, 'img', '全部'))

    def test_search_no_match(self):
        self.assertFalse(app.App._matches_filters(self.app, 0, 'xyz', '全部'))

    def test_filter_raw(self):
        self.assertTrue(app.App._matches_filters(self.app, 1, '', 'RAW'))
        self.assertFalse(app.App._matches_filters(self.app, 0, '', 'RAW'))
        self.assertFalse(app.App._matches_filters(self.app, 2, '', 'RAW'))

    def test_filter_jpg(self):
        self.assertTrue(app.App._matches_filters(self.app, 0, '', 'JPG'))
        self.assertTrue(app.App._matches_filters(self.app, 2, '', 'JPG'))
        self.assertFalse(app.App._matches_filters(self.app, 1, '', 'JPG'))

    def test_search_and_filter_combined(self):
        self.assertTrue(app.App._matches_filters(self.app, 0, 'dsc', 'JPG'))
        self.assertFalse(app.App._matches_filters(self.app, 1, 'dsc', 'JPG'))  # RAW excluded


class TestSortedIndexes(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp(make_photos())

    def test_sort_by_filename(self):
        got = app.App._sorted_indexes(self.app, [2, 0, 1], '文件名')
        self.assertEqual(got, [0, 1, 2])  # DSC0001 < DSC0002 < IMG_0003 (name.lower)

    def test_sort_by_capture_time(self):
        got = app.App._sorted_indexes(self.app, [0, 1, 2], '拍摄时间')
        self.assertEqual(got, [1, 0, 2])  # 01-01, 01-02, 01-03

    def test_sort_by_camera(self):
        got = app.App._sorted_indexes(self.app, [0, 1, 2], '相机')
        self.assertEqual(got, [2, 0, 1])  # Canon R5 first, then Sony

    def test_default_filename(self):
        got = app.App._sorted_indexes(self.app, [2, 0, 1], '未知键')
        self.assertEqual(got, [0, 1, 2])  # 未知键回退到文件名排序


if __name__ == "__main__":
    unittest.main(verbosity=2)
