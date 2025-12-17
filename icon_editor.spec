# -*- mode: python ; coding: utf-8 -*-
# ONE-FILE EXE BUILD
# Build with: pyinstaller --clean --noconfirm icon_editor.spec
# Output: dist/IconCreator.exe (single ~60MB file)

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path.cwd().resolve()
app_icon = None  # Set to icon path if you have one

block_cipher = None

hidden = collect_submodules('PIL')
hidden += [
    'tkinter',
    'tkinter.filedialog',
    'tkinter.colorchooser',
    'tkinter.simpledialog',
    'tkinter.messagebox',
]

a = Analysis(
    ['icon_editor/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ONE-FILE MODE: Include everything in the EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,       # ← INCLUDE BINARIES
    a.zipfiles,       # ← INCLUDE ZIPFILES  
    a.datas,          # ← INCLUDE DATA
    [],
    name='IconCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,    # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon
)

# NO COLLECT SECTION FOR ONE-FILE BUILD
