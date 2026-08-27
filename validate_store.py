# -*- coding: utf-8 -*-
"""validate_store.py — 校验插件商店清单（plugins.json）结构与 checksum 一致性。

用法：python validate_store.py
CI 每次 push 自动运行：清单与实际 Release 一旦失配立即变红提醒。
仅用标准库；会下载各插件 Release zip 做 SHA-256 比对。
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED = ('id', 'name', 'version', 'author', 'repo', 'license', 'install_url', 'checksum', 'updated_at')
VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')
ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-_]*$')


def validate_plugin(p):
    errors = []
    for k in REQUIRED:
        if not str(p.get(k, '') or '').strip():
            errors.append('缺少字段 %s' % k)
    pid = str(p.get('id', ''))
    if pid and not ID_RE.match(pid):
        errors.append('id 格式非法: %r' % pid)
    ver = str(p.get('version', '') or '')
    if ver and not VERSION_RE.match(ver):
        errors.append('version 不是 x.y.z: %r' % ver)
    url = str(p.get('install_url', '') or '')
    if url and not url.startswith('https://'):
        errors.append('install_url 必须为 HTTPS: %r' % url)
    if errors:
        return errors
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
    except Exception as e:
        return ['下载 install_url 失败: %s (%s)' % (url, e)]
    actual = hashlib.sha256(data).hexdigest()
    expected = str(p.get('checksum', '') or '').strip().lower()
    if actual != expected:
        return ['checksum 不匹配: 清单 %s... vs 实际 %s...' % (expected[:16], actual[:16])]
    return []


def main():
    path = os.path.join(HERE, 'plugins.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    plugins = data.get('plugins', []) if isinstance(data, dict) else []
    if data.get('schema_version') != 1:
        print('警告：schema_version 不是 1')
    ok = True
    print('== 校验插件商店清单 plugins.json ==')
    for p in plugins:
        errs = validate_plugin(p)
        name = p.get('name') or p.get('id')
        if errs:
            ok = False
            print('[FAIL] %s (%s):' % (name, p.get('id')))
            for e in errs:
                print('   -', e)
        else:
            print('[ OK ] %s v%s  checksum 匹配' % (name, p.get('version')))
    if not plugins:
        print('[FAIL] plugins.json 里没有插件')
        ok = False

    upath = os.path.join(HERE, 'update.json')
    if os.path.exists(upath):
        try:
            with open(upath, encoding='utf-8') as f:
                u = json.load(f)
            miss = [k for k in ('version', 'url', 'note') if not str(u.get(k, '') or '').strip()]
            ver = str(u.get('version', ''))
            if miss or not VERSION_RE.match(ver):
                print('[FAIL] update.json 字段缺失或版本非法: %s' % (miss or ver))
                ok = False
            elif not str(u.get('url', '')).startswith('https://'):
                print('[FAIL] update.json url 必须为 HTTPS')
                ok = False
            else:
                print('[ OK ] update.json 结构正常 (v%s)' % ver)
        except Exception as e:
            print('[FAIL] update.json 解析失败: %s' % e)
            ok = False

    print()
    print('结果：', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
