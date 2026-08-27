# -*- coding: utf-8 -*-
"""test_empty_ui.py — 空状态引导文案三语齐全（不依赖 GUI）。

运行：python -m unittest test_empty_ui -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang


GUIDE = '把照片文件夹拖进来 / 点上方「选择照片文件夹」'


class TestEmptyStateGuide(unittest.TestCase):
    def test_guide_registered_in_all_langs(self):
        self.assertIn(GUIDE, lang.EN)
        self.assertIn(GUIDE, lang.ZH_TW)
        self.assertTrue(lang.EN[GUIDE].strip())
        self.assertTrue(lang.ZH_TW[GUIDE].strip())

    def test_tr_returns_nonempty(self):
        from lang import tr, set_lang, get_lang
        orig = get_lang()
        try:
            for code in ('zh', 'en', 'zh_tw'):
                set_lang(code)
                self.assertTrue(tr(GUIDE).strip())
        finally:
            set_lang(orig)


if __name__ == "__main__":
    unittest.main(verbosity=2)
