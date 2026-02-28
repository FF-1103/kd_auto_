# -*- mode: python ; coding: utf-8 -*-

import os

def collect_templates():
    templates_dir = 'templates'
    result = []
    for f in os.listdir(templates_dir):
        if f != 'register.html':
            result.append((os.path.join(templates_dir, f), 'templates'))
    return result

a = Analysis(
    ['main.py'],
    pathex=['D:\\PythonProject\\kd_auto'],
    binaries=[('chromedriver.exe', '.')],
    datas=[
        ('config', 'config'),
        ('reports', 'reports'),
    ] + collect_templates(),
    hiddenimports=[
        'selenium',
        'pandas',
        'openpyxl',
        'sqlalchemy',
        'fastapi',
        'uvicorn',
        'jinja2',
        'python_multipart',
        'pydantic',
        'starlette',
        'pymysql',
        'passlib.handlers.bcrypt',
        'bcrypt',
        'itsdangerous',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='运单号自动化服务',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,  # 使用系统默认临时目录
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    onefile=True,
)
