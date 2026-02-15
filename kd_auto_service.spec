# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=['D:\\PythonProject\\kd_auto'],
    binaries=[('chromedriver.exe', '.')],
    datas=[
        ('config', 'config'),
        ('templates', 'templates'),
        ('reports', 'reports'),
    ],
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
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    onefile=True,  # 启用单文件模式，将资源嵌入exe
)
