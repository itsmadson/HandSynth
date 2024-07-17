# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Gather all necessary data for mediapipe
mediapipe_datas = collect_all('mediapipe')[0]

a = Analysis(
    ['hand_synth_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
        ('green space.jpg', '.'),
        ('icon.ico', '.')
    ] + mediapipe_datas,
    hiddenimports=[
        'cv2',
        'mediapipe',
        'mido',
        'mido.backends.rtmidi',
        'rtmidi',
        'numpy',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Exclude binaries that might cause conflicts
excluded_binaries = [
    'vcruntime140.dll',
    'msvcp140.dll',
    'qwindows.dll',
    'qwindowsvistastyle.dll',
]
a.binaries = [x for x in a.binaries if x[0] not in excluded_binaries]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MadHand',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, change to False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)