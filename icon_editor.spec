# icon_editor.spec
# Build with: pyinstaller --clean --noconfirm icon_editor.spec
# Produces a single-file executable in ./dist (IconCreator[.exe] on Windows)

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(__file__).parent.resolve()

# Optional: include a custom app icon (uncomment and set a valid .ico path on Windows)
app_icon = None  # str(project_root / "assets" / "app.ico")

block_cipher = None

hidden = collect_submodules('PIL')  # ensure Pillow submodules are bundled

a = Analysis(
    ['icon_editor/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('LICENSE', '.'),            # optional: ship license
        ('NOTICE', '.'),             # optional: ship notice
        # ('icon_editor/assets', 'icon_editor/assets'),  # optional: bundle assets/fonts if you add them
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
    console=False,          # set True if you prefer a console window
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
