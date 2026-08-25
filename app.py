# -*- coding: utf-8 -*-
"""app.py - Photo Watermark (PWM) - Tkinter 桌面版"""
import os
import sys
import json
import queue
import threading
import importlib.util
import shutil
import subprocess
import urllib.request
import zipfile

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

from PIL import Image, ImageTk, ImageOps
import photo
from lang import tr, LANGS, set_lang, get_lang

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)   # 打包后：exe 所在目录（插件/配置都放这里）
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, 'config.json')
PLUGINS_DIR = os.path.join(APP_DIR, 'plugins')
FONTS_DIR = os.path.join(APP_DIR, 'fonts')
APP_VERSION = '1.1.0'

# ==================== 插件系统 ====================
class PluginAPI:
    def __init__(self):
        self.tokens = {}          # name -> func(meta, settings) -> str
        self.formats = {}         # name -> {ext,label,save}
        self.camera_names = []    # [(make, model, friendly)]
        self.presets = {}         # name -> template（模板预设）
        self.styles = {}          # name -> (label, renderer)（自定义水印样式）
        self.export_hooks = []    # [func(img, meta, settings) -> img|None]（导出前处理）

    def add_token(self, name, func):
        if isinstance(name, str) and callable(func):
            self.tokens[name] = func

    def add_format(self, name, ext, label, save_func):
        self.formats[name] = {'ext': ext, 'label': label, 'save': save_func}

    def add_camera_name(self, make, model, friendly):
        self.camera_names.append((make, model, friendly))

    def add_template_preset(self, name, template):
        """新增模板预设（显示在「模板预设」下拉框）"""
        if name and isinstance(template, str):
            self.presets[name] = template

    def add_watermark_style(self, name, label, renderer):
        """新增水印样式。renderer(img, settings, values) 返回绘制后的 PIL 图像。"""
        if name and callable(renderer):
            self.styles[name] = (label, renderer)

    def on_export(self, func):
        """导出钩子：水印绘制后、保存前调用 func(img, meta, settings)，可返回修改后的图像。"""
        if callable(func):
            self.export_hooks.append(func)


def load_plugins():
    api = PluginAPI()
    loaded = []
    errors = []
    if not os.path.isdir(PLUGINS_DIR):
        return api, loaded, errors
    for name in sorted(os.listdir(PLUGINS_DIR)):
        d = os.path.join(PLUGINS_DIR, name)
        if not os.path.isdir(d) or name.startswith('_') or name.startswith('.'):
            continue
        main_py = os.path.join(d, 'plugin.py')
        if not os.path.isfile(main_py):
            continue
        try:
            spec = importlib.util.spec_from_file_location('cwm_plugin_' + name, main_py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, 'register'):
                mod.register(api)
                loaded.append(name)
        except Exception as e:
            errors.append((name, str(e)))
            print(tr('插件加载失败 [%s]: %s') % (name, e))
    return api, loaded, errors


def reload_plugins():
    """重新扫描并加载插件（插件管理窗口用），返回 (api, names, errors)。"""
    global PLUGIN_API, PLUGIN_NAMES, PLUGIN_ERRORS, FORMAT_CHOICES
    for m in list(sys.modules):
        if m.startswith('cwm_plugin_'):
            del sys.modules[m]
    PLUGIN_API, PLUGIN_NAMES, PLUGIN_ERRORS = load_plugins()
    FORMAT_CHOICES = [('jpg', 'JPG（可保留EXIF）'), ('png', 'PNG（无损）'), ('webp', 'WebP'), ('bmp', 'BMP')]
    for fname, fspec in PLUGIN_API.formats.items():
        FORMAT_CHOICES.append((fname, fspec['label']))
    _rebuild_presets()
    return PLUGIN_API, PLUGIN_NAMES, PLUGIN_ERRORS


# ==================== 全局 ====================
PLUGIN_API, PLUGIN_NAMES, PLUGIN_ERRORS = load_plugins()

FORMAT_CHOICES = [('jpg', 'JPG（可保留EXIF）'), ('png', 'PNG（无损）'), ('webp', 'WebP'), ('bmp', 'BMP')]
for fname, fspec in PLUGIN_API.formats.items():
    FORMAT_CHOICES.append((fname, fspec['label']))

BASE_TEMPLATE_PRESETS = {
    '相机 + 参数（默认）': '{make}  {model}   {focal}  {shutter}  {aperture}  {iso}',
    '相机 + 参数 + 日期': '{make}  {model}   {focal}  {shutter}  {aperture}  {iso}\n{date} {time}',
    '仅相机': '{make}  {model}',
    '仅参数': '{shutter}  {aperture}  {iso}',
    '完整信息': '{make} {model}\n{lens}\n{focal}  {shutter}  {aperture}  {iso}\n{date} {time}',
    '自定义（可保存）': None,  # 特殊：恢复 config 里保存的自定义模板
}

def _rebuild_presets():
    global TEMPLATE_PRESETS
    TEMPLATE_PRESETS = dict(BASE_TEMPLATE_PRESETS)
    TEMPLATE_PRESETS.update(PLUGIN_API.presets)

TEMPLATE_PRESETS = dict(BASE_TEMPLATE_PRESETS)
_rebuild_presets()


_NUM_KEYS = ('font_size_pct', 'line_spacing', 'text_opacity', 'offset_x_pct', 'offset_y_pct',
              'margin_pct', 'bg_opacity', 'bg_padding', 'outline_width', 'shadow_blur', 'jpeg_quality')

def load_config():
    cfg = dict(photo.DEFAULT_SETTINGS)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            for k, v in saved.items():
                if k not in cfg:
                    continue
                if k == 'update_url' and not v:
                    continue  # 空值用默认更新地址
                if k in _NUM_KEYS:
                    try:
                        v = float(v)
                        if k == 'jpeg_quality':
                            v = int(v)
                        if v <= 0:
                            continue
                    except Exception:
                        continue
                cfg[k] = v
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def camera_name_for(meta):
    """插件可覆盖相机名，其次自动识别。"""
    if not meta:
        return ''
    for make, model, friendly in PLUGIN_API.camera_names:
        if meta.get('make') == make and meta.get('model') == model:
            return friendly
    return meta.get('camera_text', '')


def build_values(meta, settings):
    values = photo.values_for(meta, settings)
    values['camera'] = (settings.get('camera_override') or '').strip() or camera_name_for(meta)
    for name, func in PLUGIN_API.tokens.items():
        try:
            v = func(meta, settings)
            if v is not None:
                values[name] = str(v)
        except Exception as e:
            print(tr('插件 token 出错 [%s]: %s') % (name, e))
    return values


def _version_newer(a, b):
    """比较版本号，a > b 返回 True。"""
    def parse(v):
        out = []
        for part in str(v).replace('-', '.').split('.'):
            try:
                out.append(int(part))
            except ValueError:
                out.append(0)
        return out
    return parse(a) > parse(b)


# ==================== 插件管理窗口 ====================
class PluginManagerWindow:
    def __init__(self, parent):
        self.parent = parent
        self.win = tk.Toplevel(parent.root)
        self.win.title(tr('插件管理'))
        self.win.geometry('640x360')
        self.win.transient(parent.root)
        self.win.grab_set()
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self.win, padding=6)
        top.pack(fill='x')
        ttk.Button(top, text=tr('打开插件文件夹'), command=self.open_dir).pack(side='left')
        ttk.Button(top, text=tr('添加插件(.zip/.py)'), command=self.add_plugin).pack(side='left', padx=6)
        ttk.Button(top, text=tr('刷新'), command=self.refresh).pack(side='left', padx=6)
        ttk.Label(top, text=tr('插件 = plugins 里的一个文件夹，内含 plugin.py'),
                  foreground='#888').pack(side='left', padx=10)

        cols = ('name', 'status', 'error')
        self.tree = ttk.Treeview(self.win, columns=cols, show='headings')
        self.tree.heading('name', text=tr('插件名'))
        self.tree.heading('status', text=tr('状态'))
        self.tree.heading('error', text=tr('错误信息'))
        self.tree.column('name', width=180)
        self.tree.column('status', width=80)
        self.tree.column('error', width=320)
        sb = ttk.Scrollbar(self.win, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=(6, 0), pady=(0, 6))
        sb.pack(side='left', fill='y', pady=(0, 6))

        bottom = ttk.Frame(self.win, padding=6)
        bottom.pack(fill='x')
        ttk.Button(bottom, text=tr('关闭'), command=self.win.destroy).pack(side='right')

    def refresh(self):
        _api, names, errors = reload_plugins()
        self.parent._refresh_format_choices()
        self.tree.delete(*self.tree.get_children())
        for name in names:
            self.tree.insert('', 'end', values=(name, tr('已加载'), ''))
        for name, err in errors:
            self.tree.insert('', 'end', values=(name, tr('加载失败'), err))
        if not names and not errors:
            self.tree.insert('', 'end', values=(tr('（无插件）'), '-', ''))

    def open_dir(self):
        try:
            os.makedirs(PLUGINS_DIR, exist_ok=True)
            os.startfile(PLUGINS_DIR)
        except Exception as e:
            messagebox.showerror(tr('无法打开'), str(e))

    def add_plugin(self):
        path = filedialog.askopenfilename(title=tr('选择插件（.zip 或 .py）'),
                                          filetypes=[(tr('插件'), '*.zip *.py'), (tr('所有文件'), '*.*')])
        if not path:
            return
        try:
            os.makedirs(PLUGINS_DIR, exist_ok=True)
            if path.lower().endswith('.zip'):
                with zipfile.ZipFile(path) as z:
                    tmp = os.path.join(PLUGINS_DIR, '__tmp_import__')
                    if os.path.isdir(tmp):
                        shutil.rmtree(tmp)
                    os.makedirs(tmp, exist_ok=True)
                    z.extractall(tmp)
                    plugin_py = None
                    for root, dirs, files in os.walk(tmp):
                        if 'plugin.py' in files:
                            plugin_py = os.path.join(root, 'plugin.py')
                            break
                    if not plugin_py:
                        shutil.rmtree(tmp, ignore_errors=True)
                        messagebox.showerror(tr('添加失败'), tr('压缩包里找不到 plugin.py'))
                        return
                    folder_name = os.path.basename(os.path.dirname(plugin_py))
                    target = os.path.join(PLUGINS_DIR, folder_name)
                    if os.path.isdir(target):
                        shutil.rmtree(tmp, ignore_errors=True)
                        messagebox.showinfo(tr('提示'), tr('插件已存在：') + folder_name)
                        return
                    shutil.copytree(os.path.dirname(plugin_py), target)
                    shutil.rmtree(tmp, ignore_errors=True)
            else:
                stem = os.path.splitext(os.path.basename(path))[0]
                target = os.path.join(PLUGINS_DIR, stem)
                os.makedirs(target, exist_ok=True)
                shutil.copy(path, os.path.join(target, 'plugin.py'))
            self.refresh()
            self.parent.status_var.set('插件已添加')
        except Exception as e:
            messagebox.showerror(tr('添加插件失败'), str(e))


# ==================== 主界面 ====================
class App:
    def __init__(self, root):
        self.root = root
        self.settings = load_config()
        set_lang(self.settings.get('language', 'zh'))
        self.photos = []            # [{path,name,raw,checked,meta}]
        self.current_index = None
        self.preview_img = None     # PhotoImage 引用
        self.busy = False
        self.cancel = False
        self.msg_q = queue.Queue()
        self.preview_timer = None
        try:
            os.makedirs(FONTS_DIR, exist_ok=True)
        except Exception:
            pass
        self.fonts = photo.available_fonts(FONTS_DIR)

        root.title('Photo Watermark v' + APP_VERSION)
        root.geometry('1380x860')
        root.minsize(1100, 700)
        self._build_ui()
        self._bind_settings()
        self._loading = True          # 初始化控件值时不触发保存/重绘
        self._apply_settings_to_widgets()
        self._loading = False
        self._on_change()
        self.root.after(100, self._poll_queue)

    # ---------- UI 构建 ----------
    def _build_ui(self):
        root = self.root
        top = ttk.Frame(root, padding=(8, 6))
        top.pack(fill='x')
        ttk.Button(top, text=tr('选择照片文件夹'), command=self.choose_input).pack(side='left')
        self.folder_var = tk.StringVar(value=tr('未选择文件夹'))
        ttk.Label(top, textvariable=self.folder_var, foreground='#666').pack(side='left', padx=8)
        ttk.Button(top, text=tr('选择输出文件夹'), command=self.choose_output).pack(side='left', padx=(16, 2))
        self.output_var = tk.StringVar(value='')
        ttk.Label(top, textvariable=self.output_var, foreground='#666').pack(side='left', padx=6)
        ttk.Button(top, text=tr('打开输出文件夹'), command=self.open_output).pack(side='left')

        paned = ttk.Panedwindow(root, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=8, pady=(0, 4))

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        bar = ttk.Frame(left)
        bar.pack(fill='x')
        self.count_var = tk.StringVar(value=tr('0 张'))
        ttk.Label(bar, textvariable=self.count_var).pack(side='left')
        ttk.Button(bar, text=tr('全选'), command=lambda: self.set_all_checked(True)).pack(side='right', padx=2)
        ttk.Button(bar, text=tr('全不选'), command=lambda: self.set_all_checked(False)).pack(side='right', padx=2)

        cols = ('check', 'name', 'camera', 'shutter', 'aperture', 'iso', 'size')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse')
        heads = {'check': '✓', 'name': '文件名', 'camera': '相机', 'shutter': '快门',
                 'aperture': '光圈', 'iso': 'ISO', 'size': '尺寸'}
        widths = {'check': 34, 'name': 150, 'camera': 130, 'shutter': 70, 'aperture': 60, 'iso': 70, 'size': 90}
        for c in cols:
            self.tree.heading(c, text=tr(heads[c]))
            self.tree.column(c, width=widths[c], anchor='w', stretch=(c in ('name', 'camera')))
        sb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Button-1>', self._on_tree_click)

        right = ttk.Frame(paned)
        paned.add(right, weight=3)
        self.canvas = tk.Canvas(right, bg='#111', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.meta_var = tk.StringVar(value='')
        ttk.Label(right, textvariable=self.meta_var, foreground='#555').pack(fill='x')

        nb = ttk.Notebook(right)
        nb.pack(fill='x', pady=(4, 0))
        self._build_text_tab(nb)
        self._build_style_tab(nb)
        self._build_position_tab(nb)
        self._build_bg_tab(nb)
        self._build_export_tab(nb)

        bottom = ttk.Frame(root, padding=(8, 4))
        bottom.pack(fill='x')
        self.btn_export = ttk.Button(bottom, text=tr('导出水印照片'), command=self.do_export)
        self.btn_export.pack(side='left')
        self.btn_cancel = ttk.Button(bottom, text=tr('取消'), command=self.request_cancel, state='disabled')
        self.btn_cancel.pack(side='left', padx=6)
        self.progress = ttk.Progressbar(bottom, mode='determinate')
        self.progress.pack(side='left', fill='x', expand=True, padx=8)
        self.status_var = tk.StringVar(value=tr('就绪'))
        ttk.Label(bottom, textvariable=self.status_var).pack(side='left')


    def _build_text_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=tr('水印文字'))
        ttk.Label(f, text=tr('模板预设')).pack(anchor='w')
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(f, textvariable=self.preset_var, values=[tr(k) for k in TEMPLATE_PRESETS.keys()], state='readonly')
        self.preset_combo.pack(fill='x', pady=(2, 2))
        crow = ttk.Frame(f)
        crow.pack(fill='x', pady=(0, 6))
        self.save_custom_btn = ttk.Button(crow, text=tr('保存为自定义模板'), command=self.save_custom_template)
        self.save_custom_btn.pack(side='left')
        ttk.Label(crow, text=tr('保存后可在预设里选“自定义（可保存）”恢复'), foreground='#888').pack(side='left', padx=6)
        ttk.Label(f, text=tr('模板（可编辑，换行=多行）')).pack(anchor='w')
        self.template_text = tk.Text(f, height=4, font=('Microsoft YaHei', 10))
        self.template_text.pack(fill='x', pady=(2, 4))
        hint = tr('可用变量：{make} {model} {camera} {shutter} {aperture} {iso} {focal} {lens} {date} {time}')
        extra = ''
        if PLUGIN_API.tokens:
            extra = tr('   插件变量: ') + ' '.join('{%s}' % k for k in PLUGIN_API.tokens)
        ttk.Label(f, text=hint + extra, foreground='#888', wraplength=620).pack(anchor='w')
        ttk.Label(f, text=tr('相机名覆盖（留空=自动识别品牌型号）')).pack(anchor='w', pady=(6, 2))
        self.override_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.override_var).pack(fill='x')

    def _build_style_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=tr('样式'))
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('字体')).pack(side='left')
        self.font_var = tk.StringVar()
        names = [n for n, _ in self.fonts]
        if self.settings.get('font_family') not in names and names:
            self.settings['font_family'] = names[0]
        self.font_combo = ttk.Combobox(row, textvariable=self.font_var, values=names, state='readonly')
        self.font_combo.pack(side='left', fill='x', expand=True, padx=6)
        frow = ttk.Frame(f)
        frow.pack(fill='x', pady=(2, 2))
        ttk.Button(frow, text=tr('添加字体文件'), command=self.add_font).pack(side='left')
        ttk.Button(frow, text=tr('打开字体文件夹'), command=self.open_fonts_dir).pack(side='left', padx=6)
        ttk.Label(frow, text=tr('把自己的 .ttf/.otf 字体放进去即可'), foreground='#888').pack(side='left')
        self.bold_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('加粗'), variable=self.bold_var).pack(anchor='w', pady=4)

        srow = ttk.Frame(f); srow.pack(fill='x', pady=(2, 0))
        ttk.Label(srow, text=tr('水印样式')).pack(side='left')
        self.style_var = tk.StringVar()
        self.style_combo = ttk.Combobox(srow, textvariable=self.style_var, state='readonly')
        self.style_combo.pack(side='left', fill='x', expand=True, padx=6)
        self._refresh_style_choices()

        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('字号(%宽)')).pack(side='left')
        self.size_var = tk.DoubleVar()
        ttk.Scale(row, from_=0.5, to=8, variable=self.size_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.size_label = ttk.Label(row, text='', width=5)
        self.size_label.pack(side='left')

        row = ttk.Frame(f); row.pack(fill='x', pady=2)
        ttk.Label(row, text=tr('行距')).pack(side='left')
        self.spacing_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=1, variable=self.spacing_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.spacing_label = ttk.Label(row, text='', width=5)
        self.spacing_label.pack(side='left')

        row = ttk.Frame(f); row.pack(fill='x', pady=4)
        ttk.Label(row, text=tr('文字颜色')).pack(side='left')
        self.text_color_btn = ttk.Button(row, text=tr('选择颜色'), command=self.pick_text_color)
        self.text_color_btn.pack(side='left', padx=6)
        self.text_color_sw = tk.Canvas(row, width=24, height=18, highlightthickness=1, highlightbackground='#999')
        self.text_color_sw.pack(side='left')
        ttk.Label(row, text=tr('透明度')).pack(side='left', padx=(12, 4))
        self.text_opacity_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=1, variable=self.text_opacity_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.opacity_label = ttk.Label(row, text='', width=5)
        self.opacity_label.pack(side='left')

    def _build_position_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=tr('位置'))
        self.anchor_var = tk.IntVar()
        grid = ttk.Frame(f)
        grid.pack(pady=4)
        syms = ['↖', '↑', '↗', '←', '＋', '→', '↙', '↓', '↘']
        self.anchor_btns = []
        for i, s in enumerate(syms):
            b = ttk.Button(grid, text=s, width=4, command=lambda idx=i: self._set_anchor(idx))
            b.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self.anchor_btns.append(b)

        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('横向偏移%')).pack(side='left')
        self.ox_var = tk.DoubleVar()
        ttk.Scale(row, from_=-20, to=20, variable=self.ox_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.ox_label = ttk.Label(row, text='', width=6)
        self.ox_label.pack(side='left')
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('纵向偏移%')).pack(side='left')
        self.oy_var = tk.DoubleVar()
        ttk.Scale(row, from_=-20, to=20, variable=self.oy_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.oy_label = ttk.Label(row, text='', width=6)
        self.oy_label.pack(side='left')
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('边距%')).pack(side='left')
        self.margin_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=15, variable=self.margin_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.margin_label = ttk.Label(row, text='', width=6)
        self.margin_label.pack(side='left')

        ttk.Label(f, text=tr('提示：边距=0 时贴底；纵向偏移为正值可把水印推向/超出底边'),
                  foreground='#888').pack(anchor='w', pady=(4, 0))


    def _build_bg_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=tr('背景/描边'))
        self.bg_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('半透明背景条'), variable=self.bg_enabled_var, command=self._on_change).pack(anchor='w')
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('背景颜色')).pack(side='left')
        ttk.Button(row, text=tr('选择'), command=self.pick_bg_color).pack(side='left', padx=6)
        self.bg_color_sw = tk.Canvas(row, width=24, height=18, highlightthickness=1, highlightbackground='#999')
        self.bg_color_sw.pack(side='left')
        ttk.Label(row, text=tr('不透明度')).pack(side='left', padx=(12, 4))
        self.bg_opacity_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=1, variable=self.bg_opacity_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.bg_opacity_label = ttk.Label(row, text='', width=5)
        self.bg_opacity_label.pack(side='left')
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('内边距(×字号)')).pack(side='left')
        self.bg_padding_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=2, variable=self.bg_padding_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.bg_padding_label = ttk.Label(row, text='', width=5)
        self.bg_padding_label.pack(side='left')

        self.outline_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('文字描边'), variable=self.outline_var, command=self._on_change).pack(anchor='w', pady=(8, 0))
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('描边颜色')).pack(side='left')
        ttk.Button(row, text=tr('选择'), command=self.pick_outline_color).pack(side='left', padx=6)
        self.outline_color_sw = tk.Canvas(row, width=24, height=18, highlightthickness=1, highlightbackground='#999')
        self.outline_color_sw.pack(side='left')
        ttk.Label(row, text=tr('粗细')).pack(side='left', padx=(12, 4))
        self.outline_width_var = tk.DoubleVar()
        ttk.Scale(row, from_=0.02, to=0.3, variable=self.outline_width_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.outline_width_label = ttk.Label(row, text='', width=5)
        self.outline_width_label.pack(side='left')

        self.shadow_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('文字阴影'), variable=self.shadow_var, command=self._on_change).pack(anchor='w', pady=(8, 0))
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('阴影强度')).pack(side='left')
        self.shadow_blur_var = tk.DoubleVar()
        ttk.Scale(row, from_=0, to=0.5, variable=self.shadow_blur_var, command=lambda v: self._on_change()).pack(side='left', fill='x', expand=True, padx=6)
        self.shadow_blur_label = ttk.Label(row, text='', width=5)
        self.shadow_blur_label.pack(side='left')

    def _build_export_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=tr('导出'))
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('输出格式')).pack(side='left')
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(row, textvariable=self.format_var, values=[tr(v) for _, v in FORMAT_CHOICES], state='readonly')
        self.format_combo.pack(side='left', fill='x', expand=True, padx=6)
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('JPG质量')).pack(side='left')
        self.quality_var = tk.IntVar()
        ttk.Scale(row, from_=50, to=100, variable=self.quality_var, command=lambda v: None).pack(side='left', fill='x', expand=True, padx=6)
        self.quality_label = ttk.Label(row, text='', width=5)
        self.quality_label.pack(side='left')
        self.preserve_exif_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('导出 JPG 时保留 EXIF 信息'), variable=self.preserve_exif_var).pack(anchor='w', pady=4)
        row = ttk.Frame(f); row.pack(fill='x')
        ttk.Label(row, text=tr('文件名后缀')).pack(side='left')
        self.suffix_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.suffix_var, width=12).pack(side='left', padx=6)
        self.overwrite_var = tk.BooleanVar()
        ttk.Checkbutton(f, text=tr('覆盖已存在的输出文件（否则自动加 (1)(2)）'), variable=self.overwrite_var).pack(anchor='w', pady=4)
        ttk.Label(f, text=tr('插件已加载: %s') % (', '.join(PLUGIN_NAMES) if PLUGIN_NAMES else '无'),
                  foreground='#888').pack(anchor='w', pady=2)
        row2 = ttk.Frame(f)
        row2.pack(fill='x', pady=2)
        ttk.Button(row2, text=tr('插件管理'), command=self.open_plugin_manager).pack(side='left')
        ttk.Button(row2, text=tr('检查更新'), command=self.check_update).pack(side='left', padx=6)
        ttk.Label(row2, text=tr('当前版本 v') + APP_VERSION, foreground='#888').pack(side='left', padx=6)
        ttk.Label(f, text=tr('作者：Shiraijikuu　·　AI 协助：OpenAI Codex　·　MIT 开源'),
                  foreground='#aaa').pack(anchor='w', pady=(2, 4))
        langrow = ttk.Frame(f)
        langrow.pack(fill='x', pady=(2, 4))
        ttk.Label(langrow, text=tr('语言')).pack(side='left')
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(langrow, textvariable=self.lang_var,
                                       values=list(LANGS.values()), state='readonly', width=14)
        self.lang_combo.pack(side='left', padx=6)
        self.lang_combo.set(LANGS[get_lang()])
        self.lang_combo.bind('<<ComboboxSelected>>', self._on_language_change)


    # ---------- 设置绑定 ----------
    def _apply_settings_to_widgets(self):
        s = self.settings
        self.template_text.delete('1.0', 'end')
        self.template_text.insert('1.0', s.get('template', ''))
        self.preset_combo.set('')
        self.override_var.set(s.get('camera_override', ''))
        self.font_var.set(s.get('font_family', '微软雅黑'))
        self.bold_var.set(bool(s.get('bold')))
        self.size_var.set(s.get('font_size_pct', 2.2))
        self.spacing_var.set(s.get('line_spacing', 0.35))
        self.text_opacity_var.set(s.get('text_opacity', 1.0))
        self.anchor_var.set(s.get('anchor', 7))
        self.ox_var.set(s.get('offset_x_pct', 0))
        self.oy_var.set(s.get('offset_y_pct', 0))
        self.margin_var.set(s.get('margin_pct', 3))
        self.bg_enabled_var.set(bool(s.get('bg_enabled')))
        self.bg_opacity_var.set(s.get('bg_opacity', 0.45))
        self.bg_padding_var.set(s.get('bg_padding', 0.6))
        self.outline_var.set(bool(s.get('outline_enabled')))
        self.outline_width_var.set(s.get('outline_width', 0.06))
        self.shadow_var.set(bool(s.get('shadow_enabled')))
        self.shadow_blur_var.set(s.get('shadow_blur', 0.15))
        fmt = s.get('format', 'jpg')
        labels = dict((tr(v), k) for k, v in FORMAT_CHOICES)
        self.format_var.set(labels.get(fmt, labels.get('jpg', tr('JPG（可保留EXIF）'))))
        self.style_var.set(self._style_labels().get(s.get('style', 'default'), tr('默认')))
        self.quality_var.set(s.get('jpeg_quality', 95))
        self.preserve_exif_var.set(bool(s.get('preserve_exif')))
        self.suffix_var.set(s.get('suffix', '_wm'))
        self.overwrite_var.set(bool(s.get('overwrite')))
        self._update_labels()
        self._update_anchor_buttons()

    def _bind_settings(self):
        self.preset_combo.bind('<<ComboboxSelected>>', self._on_preset)
        self.template_text.bind('<<Modified>>', self._on_template_modified)
        self.override_var.trace_add('write', lambda *a: self._on_change())
        self.font_var.trace_add('write', lambda *a: self._on_change())
        self.bold_var.trace_add('write', lambda *a: self._on_change())
        self.size_var.trace_add('write', lambda *a: self._on_change())
        self.spacing_var.trace_add('write', lambda *a: self._on_change())
        self.text_opacity_var.trace_add('write', lambda *a: self._on_change())
        self.ox_var.trace_add('write', lambda *a: self._on_change())
        self.oy_var.trace_add('write', lambda *a: self._on_change())
        self.margin_var.trace_add('write', lambda *a: self._on_change())
        self.bg_enabled_var.trace_add('write', lambda *a: self._on_change())
        self.bg_opacity_var.trace_add('write', lambda *a: self._on_change())
        self.bg_padding_var.trace_add('write', lambda *a: self._on_change())
        self.outline_var.trace_add('write', lambda *a: self._on_change())
        self.outline_width_var.trace_add('write', lambda *a: self._on_change())
        self.shadow_var.trace_add('write', lambda *a: self._on_change())
        self.shadow_blur_var.trace_add('write', lambda *a: self._on_change())
        self.format_var.trace_add('write', lambda *a: self._on_change())
        self.quality_var.trace_add('write', lambda *a: self._on_change())
        self.preserve_exif_var.trace_add('write', lambda *a: self._on_change())
        self.suffix_var.trace_add('write', lambda *a: self._on_change())
        self.overwrite_var.trace_add('write', lambda *a: self._on_change())

    def _on_preset(self, _evt=None):
        disp = self.preset_var.get()
        name = disp
        for k in TEMPLATE_PRESETS:
            if tr(k) == disp:
                name = k
                break
        t = TEMPLATE_PRESETS.get(name)
        if name == '自定义（可保存）':
            t = self.settings.get('custom_template', '')
            if not t:
                self.status_var.set('还没有保存过自定义模板：先编辑模板，再点“保存为自定义模板”')
                return
        if t:
            self.template_text.delete('1.0', 'end')
            self.template_text.insert('1.0', t)
            self._on_change()

    def save_custom_template(self):
        t = self.template_text.get('1.0', 'end').strip()
        if not t:
            messagebox.showwarning(tr('提示'), tr('模板不能为空'))
            return
        self.settings['custom_template'] = t
        save_config(self.settings)
        self.status_var.set('已保存自定义模板（可在预设里选“自定义（可保存）”恢复）')

    def _on_template_modified(self, _evt=None):
        if self.template_text.edit_modified():
            self.template_text.edit_modified(False)
            self._on_change()

    def _on_change(self, *_):
        if getattr(self, '_loading', False):
            return
        self._update_labels()
        self._collect_settings()
        save_config(self.settings)
        self._schedule_preview()

    def _collect_settings(self):
        s = self.settings
        s['template'] = self.template_text.get('1.0', 'end').strip()
        s['camera_override'] = self.override_var.get().strip()
        s['font_family'] = self.font_var.get()
        s['bold'] = bool(self.bold_var.get())
        s['font_size_pct'] = float(self.size_var.get())
        s['line_spacing'] = float(self.spacing_var.get())
        s['text_opacity'] = float(self.text_opacity_var.get())
        s['anchor'] = int(self.anchor_var.get())
        s['offset_x_pct'] = float(self.ox_var.get())
        s['offset_y_pct'] = float(self.oy_var.get())
        s['margin_pct'] = float(self.margin_var.get())
        s['bg_enabled'] = bool(self.bg_enabled_var.get())
        s['bg_opacity'] = float(self.bg_opacity_var.get())
        s['bg_padding'] = float(self.bg_padding_var.get())
        s['outline_enabled'] = bool(self.outline_var.get())
        s['outline_width'] = float(self.outline_width_var.get())
        s['shadow_enabled'] = bool(self.shadow_var.get())
        s['shadow_blur'] = float(self.shadow_blur_var.get())
        style_labels = self._style_labels()
        s['style'] = style_labels.get(self.style_var.get(), 'default')
        labels = dict((tr(v), k) for k, v in FORMAT_CHOICES)
        s['format'] = labels.get(self.format_var.get(), 'jpg')
        s['jpeg_quality'] = int(self.quality_var.get())
        s['preserve_exif'] = bool(self.preserve_exif_var.get())
        s['suffix'] = self.suffix_var.get().strip()
        s['overwrite'] = bool(self.overwrite_var.get())


    def _update_labels(self):
        self.size_label.config(text='%.1f' % float(self.size_var.get()))
        self.spacing_label.config(text='%.2f' % float(self.spacing_var.get()))
        self.opacity_label.config(text='%.2f' % float(self.text_opacity_var.get()))
        self.ox_label.config(text='%+.1f' % float(self.ox_var.get()))
        self.oy_label.config(text='%+.1f' % float(self.oy_var.get()))
        self.margin_label.config(text='%.1f' % float(self.margin_var.get()))
        self.bg_opacity_label.config(text='%.2f' % float(self.bg_opacity_var.get()))
        self.bg_padding_label.config(text='%.1f' % float(self.bg_padding_var.get()))
        self.outline_width_label.config(text='%.2f' % float(self.outline_width_var.get()))
        self.shadow_blur_label.config(text='%.2f' % float(self.shadow_blur_var.get()))
        self.quality_label.config(text='%d' % int(self.quality_var.get()))
        self.text_color_sw.config(bg=self.settings.get('text_color', '#ffffff'))
        self.bg_color_sw.config(bg=self.settings.get('bg_color', '#000000'))
        self.outline_color_sw.config(bg=self.settings.get('outline_color', '#000000'))

    def _update_anchor_buttons(self):
        a = int(self.anchor_var.get())
        for i, b in enumerate(self.anchor_btns):
            b.state(['pressed'] if i == a else ['!pressed'])

    def _set_anchor(self, idx):
        self.anchor_var.set(idx)
        self._on_change()

    def pick_text_color(self):
        c = colorchooser.askcolor(self.settings.get('text_color', '#ffffff'), title=tr('文字颜色'))
        if c and c[1]:
            self.settings['text_color'] = c[1]
            self._update_labels()
            self._schedule_preview()

    def pick_bg_color(self):
        c = colorchooser.askcolor(self.settings.get('bg_color', '#000000'), title=tr('背景颜色'))
        if c and c[1]:
            self.settings['bg_color'] = c[1]
            self._update_labels()
            self._schedule_preview()

    def pick_outline_color(self):
        c = colorchooser.askcolor(self.settings.get('outline_color', '#000000'), title=tr('描边颜色'))
        if c and c[1]:
            self.settings['outline_color'] = c[1]
            self._update_labels()
            self._schedule_preview()

    # ---------- 字体 ----------
    def add_font(self):
        path = filedialog.askopenfilename(
            title=tr('选择字体文件'), filetypes=[(tr('字体文件'), '*.ttf *.otf *.ttc'), (tr('所有文件'), '*.*')])
        if not path:
            return
        try:
            os.makedirs(FONTS_DIR, exist_ok=True)
            shutil.copy(path, os.path.join(FONTS_DIR, os.path.basename(path)))
            self.fonts = photo.available_fonts(FONTS_DIR)
            self.font_combo['values'] = [n for n, _ in self.fonts]
            self.font_var.set([n for n, _ in self.fonts][-1])
            self.status_var.set('已添加字体：' + os.path.basename(path))
            self._on_change()
        except Exception as e:
            messagebox.showerror(tr('添加字体失败'), str(e))

    def open_fonts_dir(self):
        try:
            os.makedirs(FONTS_DIR, exist_ok=True)
            os.startfile(FONTS_DIR)
        except Exception as e:
            messagebox.showerror(tr('无法打开'), str(e))

    # ---------- 插件管理 ----------
    def open_plugin_manager(self):
        PluginManagerWindow(self)

    def _style_labels(self):
        """返回 {显示名: 样式键}"""
        d = {tr('默认'): 'default'}
        for name, (label, _r) in PLUGIN_API.styles.items():
            d[label] = name
        return d

    def _refresh_style_choices(self):
        opts = [tr('默认')] + [label for _n, (label, _r) in PLUGIN_API.styles.items()]
        self.style_combo['values'] = opts
        self.style_var.set(self._style_labels().get(self.settings.get('style', 'default'), tr('默认')))

    def _render_with_style(self, img, settings, values):
        style = settings.get('style', 'default')
        if style != 'default' and style in PLUGIN_API.styles:
            _label, renderer = PLUGIN_API.styles[style]
            out = renderer(img, settings, values)
            if out is None:
                out = img
            return out
        return photo.render_watermark(img, settings, values, fonts_dir=FONTS_DIR)

    def _apply_export_hooks(self, img, meta, settings):
        for hook in PLUGIN_API.export_hooks:
            try:
                res = hook(img, meta, settings)
                if res is not None:
                    img = res
            except Exception as e:
                print('插件导出钩子出错: %s' % e)
        return img

    def _refresh_format_choices(self):
        self.format_combo['values'] = [v for _, v in FORMAT_CHOICES]
        cur = self.settings.get('format', 'jpg')
        labels = dict((tr(v), k) for k, v in FORMAT_CHOICES)
        self.format_var.set(labels.get(cur, labels.get('jpg', tr('JPG（可保留EXIF）'))))

    # ---------- 语言切换 ----------
    def _on_language_change(self, _evt=None):
        disp = self.lang_var.get()
        code = None
        for c, d in LANGS.items():
            if d == disp:
                code = c
                break
        if code is None or code == get_lang():
            return
        self.settings['language'] = code
        save_config(self.settings)
        self._relaunch()

    def _relaunch(self):
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable, os.path.abspath(__file__)])
        except Exception:
            pass
        self.root.destroy()

    # ---------- 热更新 ----------
    def check_update(self):
        url = (self.settings.get('update_url') or '').strip()
        if not url:
            messagebox.showinfo(tr('检查更新'),
                                tr('未配置更新地址。\n\n'
                                   '在 config.json 中设置 update_url，例如：\n'
                                   'https://example.com/update.json\n\n'
                                   '清单格式（JSON）：\n'
                                   '{"version":"1.1.0","url":"https://example.com/app.exe","note":"更新说明"}'))
            return
        self.status_var.set('正在检查更新…')
        threading.Thread(target=self._check_update_worker, args=(url,), daemon=True).start()

    def _check_update_worker(self, url):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.loads(r.read().decode('utf-8'))
            latest = str(data.get('version', ''))
            dl_url = data.get('url', '')
            note = data.get('note', '')
            self.msg_q.put(('update_result', (latest, dl_url, note)))
        except Exception as e:
            self.msg_q.put(('update_result', (None, None, str(e))))

    def _download_update(self, dl_url, version):
        try:
            upd_dir = os.path.join(APP_DIR, 'updates')
            os.makedirs(upd_dir, exist_ok=True)
            target = os.path.join(upd_dir, 'new_version.exe')
            with urllib.request.urlopen(dl_url, timeout=180) as r, open(target, 'wb') as f:
                shutil.copyfileobj(r, f)
            self.msg_q.put(('update_downloaded', (version, target)))
        except Exception as e:
            self.msg_q.put(('update_downloaded', (None, str(e))))

    def _apply_update(self, new_exe):
        if not getattr(sys, 'frozen', False):
            messagebox.showinfo(tr('更新'), tr('源码模式：请用新版本文件替换 app.py / photo.py'))
            return
        exe = os.path.join(APP_DIR, os.path.basename(sys.executable))
        if not os.path.exists(exe):
            messagebox.showerror(tr('更新'), tr('找不到当前程序文件：') + exe)
            return
        updater = os.path.join(APP_DIR, 'update.cmd')
        name = os.path.basename(exe)
        script = ('@echo off\r\n'
                  'ping 127.0.0.1 -n 3 > nul\r\n'
                  'taskkill /IM "' + name + '" /F > nul 2>&1\r\n'
                  'copy /Y "' + new_exe + '" "' + exe + '" > nul\r\n'
                  'del /Q "' + new_exe + '"\r\n'
                  'start "" "' + exe + '"\r\n'
                  'del "%~f0"\r\n')
        try:
            with open(updater, 'w', encoding='gbk') as f:
                f.write(script)
        except Exception as e:
            messagebox.showerror(tr('更新失败'), str(e))
            return
        try:
            subprocess.Popen(['cmd', '/c', updater],
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except Exception:
            os.startfile(updater)
        self.root.destroy()

    # ---------- 照片列表 ----------
    def choose_input(self):
        if self.busy:
            return
        folder = filedialog.askdirectory(title=tr('选择包含相机照片的文件夹'))
        if folder:
            self._start_scan(folder)

    def _start_scan(self, folder):
        self.folder_var.set(folder)
        self.photos = []
        self.tree.delete(*self.tree.get_children())
        self.count_var.set('0 张')
        self.busy = True
        self.btn_export.config(state='disabled')
        threading.Thread(target=self._scan_worker, args=(folder,), daemon=True).start()

    def _scan_worker(self, folder):
        found = []
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('$RECYCLE.BIN', 'System Volume Information')]
            for fn in files:
                if photo.is_supported_name(fn):
                    found.append(os.path.join(root, fn))
        found.sort()
        for i, p in enumerate(found):
            meta = photo.read_meta(p)
            self.msg_q.put(('scan_item', (p, meta)))
            if i % 5 == 0:
                self.msg_q.put(('scan_progress', (i + 1, len(found))))
        self.msg_q.put(('scan_done', len(found)))

    def _on_scan_item(self, item):
        path, meta = item
        idx = len(self.photos)
        self.photos.append({'path': path, 'name': os.path.basename(path),
                            'raw': meta.get('raw', False), 'checked': True, 'meta': meta})
        check = '☑'
        size = '%dx%d' % (meta.get('width', 0), meta.get('height', 0)) if meta.get('width') else ''
        name = ('[RAW] ' if meta.get('raw') else '') + os.path.basename(path)
        self.tree.insert('', 'end', iid=str(idx), values=(
            check, name, meta.get('camera_text', ''), meta.get('shutter_text', ''),
            meta.get('aperture_text', ''), meta.get('iso_text', ''), size))

    def _on_scan_done(self, total):
        self.busy = False
        self.btn_export.config(state='normal')
        self.count_var.set('%d 张' % len(self.photos))
        self.status_var.set('扫描完成，共 %d 张照片' % total)
        if self.photos:
            self.tree.selection_set('0')
            self._on_select()

    def _on_tree_click(self, evt):
        region = self.tree.identify('region', evt.x, evt.y)
        if region == 'cell':
            col = self.tree.identify_column(evt.x)
            if col == '#1':
                iid = self.tree.identify_row(evt.y)
                if iid:
                    idx = int(iid)
                    self.photos[idx]['checked'] = not self.photos[idx]['checked']
                    self.tree.set(iid, 'check', '☑' if self.photos[idx]['checked'] else '☐')

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.current_index = idx
        self._load_preview(idx)

    def set_all_checked(self, val):
        for i, ph in enumerate(self.photos):
            ph['checked'] = val
            self.tree.set(str(i), 'check', '☑' if val else '☐')


    # ---------- 预览 ----------
    def _load_preview(self, idx):
        ph = self.photos[idx]
        try:
            img = self._open_oriented(ph['path'], (ph.get('meta') or {}).get('orientation'))
        except Exception as e:
            self.status_var.set('无法打开: %s' % e)
            return
        self._current_preview_full = img
        self.meta_var.set(self._meta_text(ph['meta']))
        self._render_preview()

    def _meta_text(self, m):
        parts = []
        if m.get('raw'):
            parts.append(tr('RAW 内嵌预览'))
        if m.get('width'):
            parts.append('%dx%d' % (m['width'], m['height']))
        for k in ('camera_text', 'lens_text', 'focal_text', 'shutter_text', 'aperture_text', 'iso_text'):
            if m.get(k):
                parts.append(m[k])
        if m.get('date_text'):
            parts.append(m['date_text'] + (' ' + m['time_text'] if m.get('time_text') else ''))
        return '  ·  '.join(parts)

    def _open_oriented(self, path, orientation=None):
        if photo.is_raw_name(path):
            with open(path, 'rb') as f:
                jpg = photo.extract_embedded_jpeg(f.read())
            if not jpg:
                raise ValueError(tr('RAW 内没有可用的内嵌预览'))
            img = Image.open(__import__('io').BytesIO(jpg)).convert('RGB')
            # RAW 内嵌预览通常不带方向信息，需按 RAW 自身 EXIF 的方向手动转正
            return photo.apply_orientation(img, orientation)
        img = Image.open(path).convert('RGB')
        return ImageOps.exif_transpose(img)

    def _schedule_preview(self):
        if self.preview_timer:
            self.root.after_cancel(self.preview_timer)
        self.preview_timer = self.root.after(80, self._render_preview)

    def _render_preview(self):
        img = getattr(self, '_current_preview_full', None)
        if img is None:
            return
        self._collect_settings()
        try:
            meta = self.photos[self.current_index]['meta']
            out = self._render_with_style(img, self.settings, build_values(meta, self.settings))
        except Exception as e:
            self.status_var.set('预览渲染失败: %s' % e)
            return
        cw = max(120, self.canvas.winfo_width() - 10)
        ch = max(120, self.canvas.winfo_height() - 10)
        scale = min(cw / out.width, ch / out.height, 2.0)
        disp = out.resize((max(1, int(out.width * scale)), max(1, int(out.height * scale))), Image.LANCZOS)
        self.preview_img = ImageTk.PhotoImage(disp)
        self.canvas.delete('all')
        self.canvas.create_image(cw // 2, ch // 2, image=self.preview_img)

    # ---------- 输出 ----------
    def choose_output(self):
        d = filedialog.askdirectory(title=tr('选择水印输出文件夹'))
        if d:
            self.output_var.set(d)
            self.settings['output_folder'] = d
            save_config(self.settings)

    def open_output(self):
        d = self.output_var.get()
        if not d:
            d = self.settings.get('output_folder', '')
        if d and os.path.isdir(d):
            os.startfile(d)

    def request_cancel(self):
        self.cancel = True

    def do_export(self):
        if self.busy:
            return
        self._collect_settings()
        targets = [ph for ph in self.photos if ph.get('checked') and ph.get('meta')]
        if not targets:
            messagebox.showwarning(tr('提示'), tr('没有可导出的照片（请先选择文件夹并等待扫描完成）'))
            return
        outdir = self.output_var.get() or self.settings.get('output_folder', '')
        if not outdir:
            messagebox.showwarning(tr('提示'), tr('请先选择输出文件夹'))
            return
        fmt = self.settings.get('format', 'jpg')
        os.makedirs(outdir, exist_ok=True)
        self.busy = True
        self.cancel = False
        self.btn_export.config(state='disabled')
        self.btn_cancel.config(state='normal')
        self.progress.config(value=0)
        threading.Thread(target=self._export_worker, args=(targets, outdir, fmt), daemon=True).start()

    def _export_worker(self, targets, outdir, fmt):
        s = self.settings
        try:
            for i, ph in enumerate(targets):
                if self.cancel:
                    break
                self.msg_q.put(('export_progress', (i, len(targets), ph['name'])))
                try:
                    img = self._open_oriented(ph['path'], (ph.get('meta') or {}).get('orientation'))
                    values = build_values(ph['meta'], s)
                    out = self._render_with_style(img, s, values)
                    out = self._apply_export_hooks(out, ph['meta'], s)
                    base = os.path.splitext(ph['name'])[0]
                    suffix = s.get('suffix', '_wm').replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
                    if fmt in PLUGIN_API.formats:
                        spec = PLUGIN_API.formats[fmt]
                        target = self._unique_path(os.path.join(outdir, base + suffix + spec['ext']))
                        spec['save'](out, target, s.get('jpeg_quality', 95), ph['meta'], ph['path'])
                    else:
                        fmts = {'jpg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP', 'bmp': 'BMP'}
                        target = self._unique_path(os.path.join(outdir, base + suffix + '.' + fmt))
                        photo.save_watermarked(ph['path'], target, out, fmt,
                                               s.get('jpeg_quality', 95), ph['meta'],
                                               preserve_exif=s.get('preserve_exif', True))
                except Exception as e:
                    self.msg_q.put(('export_error', (ph['name'], str(e))))
            self.msg_q.put(('export_done', None))
        except Exception as e:
            self.msg_q.put(('export_done', str(e)))

    def _unique_path(self, target):
        if self.settings.get('overwrite') or not os.path.exists(target):
            return target
        base, ext = os.path.splitext(target)
        i = 1
        while os.path.exists('%s (%d)%s' % (base, i, ext)):
            i += 1
        return '%s (%d)%s' % (base, i, ext)

    # ---------- 消息队列 ----------
    def _poll_queue(self):
        try:
            while True:
                kind, data = self.msg_q.get_nowait()
                if kind == 'scan_item':
                    self._on_scan_item(data)
                elif kind == 'scan_progress':
                    self.count_var.set('%d/%d 张' % (data[0], data[1]))
                elif kind == 'scan_done':
                    self._on_scan_done(data)
                elif kind == 'export_progress':
                    i, n, name = data
                    self.progress.config(value=0 if n == 0 else i * 100 / n)
                    self.status_var.set('正在处理 (%d/%d)：%s' % (i, n, name))
                elif kind == 'export_error':
                    self.status_var.set('导出失败：%s' % data[1])
                    print(tr('导出失败 %s: %s') % data)
                elif kind == 'update_result':
                    latest, dl_url, note = data
                    if not latest:
                        self.status_var.set('检查更新失败')
                        messagebox.showerror(tr('检查更新失败'), str(note))
                    elif not _version_newer(latest, APP_VERSION):
                        self.status_var.set('已是最新版本 v' + APP_VERSION)
                        messagebox.showinfo(tr('检查更新'), tr('当前已是最新版本 v') + APP_VERSION)
                    else:
                        self.status_var.set('发现新版本 v' + latest)
                        if messagebox.askyesno(tr('发现新版本'), tr('发现新版本 v%s\n%s\n\n是否立即下载更新？') % (latest, note or '')):
                            threading.Thread(target=self._download_update, args=(dl_url, latest), daemon=True).start()
                elif kind == 'update_downloaded':
                    version, target = data
                    if not version:
                        self.status_var.set('下载更新失败')
                        messagebox.showerror(tr('下载更新失败'), str(target))
                    else:
                        self.status_var.set('更新已下载')
                        if messagebox.askyesno(tr('更新下载完成'), tr('新版本 v%s 已下载，是否现在重启完成更新？') % version):
                            self._apply_update(target)
                elif kind == 'export_done':
                    self.busy = False
                    self.btn_export.config(state='normal')
                    self.btn_cancel.config(state='disabled')
                    if data:
                        self.status_var.set('导出出错：%s' % data)
                        messagebox.showerror(tr('导出出错'), str(data))
                    else:
                        self.status_var.set('导出完成')
                        messagebox.showinfo(tr('导出完成'), tr('水印照片已导出到：\n') + self.output_var.get())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        style.theme_use('vista')
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
