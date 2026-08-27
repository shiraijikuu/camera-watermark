# -*- coding: utf-8 -*-
"""test_scale_entry.py — 滑块+手动输入框辅助（_add_scale_entry）：回显/钳制/非法回退。

运行：python -m unittest test_scale_entry -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
import tkinter as tk


class TestScaleEntry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.geometry('200x80+0+0')
            cls.root.update()
        except Exception:
            raise unittest.SkipTest('no display for Tk')

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def _make(self, lo=0.5, hi=8, fmt='%.1f'):
        var = tk.DoubleVar(value=2.5)
        calls = []
        ent = app._add_scale_entry(self.root, var, lo, hi,
                                   lambda v: calls.append(v), fmt=fmt)
        ent.pack()
        self.root.update()
        return var, ent, calls

    def test_init_syncs_entry(self):
        _, ent, _ = self._make()
        self.assertEqual(ent.get(), '2.5')

    def test_var_change_syncs_entry(self):
        var, ent, _ = self._make()
        var.set(3.25)
        self.root.update()
        self.assertIn(ent.get(), ('3.2', '3.25'))

    def test_commit_clamps_to_hi(self):
        var, ent, calls = self._make()
        ent.delete(0, 'end'); ent.insert(0, '9')
        ent.focus_force(); self.root.update()
        ent.event_generate('<Return>'); self.root.update()
        self.assertAlmostEqual(var.get(), 8.0)
        self.assertIn(8.0, calls)

    def test_commit_clamps_to_lo(self):
        var, ent, calls = self._make()
        ent.delete(0, 'end'); ent.insert(0, '0')
        ent.focus_force(); self.root.update()
        ent.event_generate('<Return>'); self.root.update()
        self.assertAlmostEqual(var.get(), 0.5)

    def test_invalid_input_keeps_value(self):
        var, ent, _ = self._make()
        ent.delete(0, 'end'); ent.insert(0, 'abc')
        ent.focus_force(); self.root.update()
        ent.event_generate('<Return>'); self.root.update()
        self.assertAlmostEqual(var.get(), 2.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
