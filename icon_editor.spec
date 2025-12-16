# Build with:
#   pyinstaller --clean --noconfirm icon_editor.spec
#
# Output:
#   dist/IconCreator/IconCreator.exe  (Windows)
#   dist/IconCreator/IconCreator      (macOS/Linux)

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# IMPORTANT: __file__ is not defined in PyInstaller spec context.
# Use the current working directory as the project root.
project_root = Path.cwd().resolve()

# Optional .ico for Windows. Set to a valid path or leave as None.
app_icon = None  # str(project_root / "assets" / "app.ico")

block_cipher = None

# Ensure Pillow submodules (plugins) are bundled
hidden = collect_submodules('PIL')

# You can add any tkinter submodules explicitly if needed (usually auto-detected)
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
    datas=[
        ('LICENSE', '.'),   # optional: ship license
        ('NOTICE', '.'),    # optional: ship notice
        # Example: bundle assets or fonts
        # ('icon_editor/assets', 'icon_editor/assets'),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IconCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # set True to see console logs for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IconCreator'
)
