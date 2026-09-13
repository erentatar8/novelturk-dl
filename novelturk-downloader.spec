# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

from PyInstaller.utils.hooks import collect_all

datas = [
    ('src/web', 'src/web'),
    ('assets', 'assets')
]
binaries = []
hiddenimports = [
    'webview',
    'xhtml2pdf',
    'ebooklib',
    'bs4',
    'PIL',
    'reportlab',
    'reportlab.graphics.barcode.code128',
    'reportlab.graphics.barcode.code39',
    'reportlab.graphics.barcode.code93',
    'reportlab.graphics.barcode.usps',
    'reportlab.graphics.barcode.qr'
]

for pkg in ['reportlab', 'xhtml2pdf', 'webview']:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='novelturk-dl',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.icns'
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='novelturk-dl'
    )
    app = BUNDLE(
        coll,
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
else:
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
        icon='assets/icon.ico'
    )
