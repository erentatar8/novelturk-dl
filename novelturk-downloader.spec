# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

added_files = [
    ('src/web', 'src/web'),
    ('assets', 'assets')
]

hidden_imports = [
    'webview',
    'xhtml2pdf',
    'ebooklib',
    'bs4',
    'PIL',
    'reportlab'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='novelturk-dl',
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
    icon='assets/icon.icns' if sys.platform == 'darwin' else 'assets/icon.ico'
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='novelturk-dl.app',
        icon='assets/icon.icns',
        bundle_identifier='com.novelturk.dl',
        info_plist={
            'CFBundleName': 'novelturk-dl',
            'CFBundleDisplayName': 'novelturk-dl',
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False'
        }
    )
