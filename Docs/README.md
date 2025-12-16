# Icon Creator & Editor

A full-featured, cross-platform icon creator and editor written in Python. Create, edit, and export multi-resolution Windows .ico files with full alpha transparency. Includes drawing tools, shapes, text, selection and move/transform, layers, zoom/pan, quick actions, and a robust CLI for automation and batch conversion.

- License: MIT (see LICENSE)
- OS: Windows, macOS, Linux
- Python: 3.8+ (3.10+ recommended)

---

## Features

- File formats
  - Input: PNG, JPG, JPEG, BMP, GIF, TIFF, WebP, ICO
  - Output: ICO (multi-resolution), PNG (composite or per-size set)
  - Transparency: Full 8-bit alpha support
- Icon sizes
  - Standard: 16, 24, 32, 48, 64, 128, 256 (customizable)
  - Multiple sizes stored in a single ICO file
- Editing tools
  - Brush/Pencil with variable size
  - Eraser (transparent)
  - Fill bucket with tolerance
  - Eyedropper (RGBA)
  - Magic Eraser (fills to transparency with tolerance)
  - Selection rectangle
  - Move/Transform (move selected region; commit or deselect)
  - Text tool (draw text at point; configurable pixel size)
  - Shapes: Line, Rectangle, Ellipse (with live preview, commit on mouse-up)
- Layers
  - Add/Delete, Reorder (Up/Down), Toggle visibility, Active layer management
  - Quick actions operate on the active layer (except Trim which affects all)
- Quick actions
  - Invert colors
  - Grayscale
  - Flip Horizontal/Vertical
  - Trim Transparent (crop to bounding box of visible content across layers)
  - Make Background Transparent (remove most common corner color)
- Viewing and navigation
  - Zoom 1x–16x (Ctrl+Mouse Wheel)
  - Panning (Middle-mouse drag or Space + Left-drag)
  - Pixel grid (toggle)
  - Fit to Window and Reset Scroll
- Export
  - Live preview Export dialog for ICO
  - Optional export of PNG set alongside ICO (one PNG per size)
- Undo/Redo
  - Layer-aware stack (50 steps by default)
- Recent files and Theme
  - “Open Recent” (remembers last 5 files)
  - Light/Dark/System theme toggle
  - Persistent config (~/.icon_editor_config.json)
- CLI (Command Line Interface)
  - Single-file and batch folder modes
  - Optional PNG set export
  - Custom sizes and resampling algorithm

---

## Screenshots (description)

- Main Window: Top toolbar with tools and sliders; left editor canvas with checkerboard transparency; right side panel with zoom controls, sizes, export settings, quick actions, and layer list.
- Export Dialog: Live previews for each selected icon size with checkerboard background; option to export PNG set.

---

## Installation

1) Ensure Python 3.8+ is installed.

2) Install dependencies:
```
pip install Pillow
```

On Linux, if tkinter is not available, install it via your package manager (examples):
- Debian/Ubuntu:
  - sudo apt-get update
  - sudo apt-get install python3-tk
- Fedora:
  - sudo dnf install python3-tkinter
- Arch:
  - sudo pacman -S tk

No additional GUI toolkit is required beyond tkinter.

---

## Project Structure

```
icon_editor/
  main.py                  # Application entry / CLI
  gui/
    __init__.py
    main_window.py         # Main window, menus, side panel, status bar
    canvas_editor.py       # Canvas with tools, layers, selection, drawing
    toolbar.py             # Tool and parameter controls
    dialogs.py             # Reserved for future custom dialogs
  core/
    __init__.py
    image_handler.py       # Load/save with transparency
    icon_generator.py      # ICO export and preview dialog
    editor_tools.py        # Tool enums, flood fill, brush line, undo/redo stack
    transparency.py        # Checkerboard background
  utils/
    __init__.py
    helpers.py             # Utility functions
    validators.py          # Size validators
    config.py              # Persistent config (recent files, theme)
LICENSE
NOTICE
README.md
```

---

## Running

GUI mode:
```
python icon_editor/main.py
```

The first run creates a config file:
- Windows/macOS/Linux: ~/.icon_editor_config.json

---

## Usage (GUI)

- File > New: create a blank canvas (default 256x256)
- File > Open: load an image (PNG/JPG/GIF/TIFF/WebP/ICO). Large images are auto-downscaled for smoother editing (configurable in CLI; GUI defaults to 3072 px max dimension for loading).
- Tools:
  - Brush/Eraser: click-drag to draw; adjust Size and Alpha in toolbar
  - Fill/Magic Eraser: click to fill; adjust Fill tolerance
  - Eyedropper: click to set RGBA color
  - Selection: drag rectangle; Esc to clear
  - Move: select, then Move to drag floating selection; switch tool or Esc to commit
  - Text: click where to place text, enter string and optional size
  - Shapes: choose shape, drag from start to end; stroke committed on release
- Layers panel:
  - Add, Delete, move Up/Down, Toggle Visibility
  - Click a layer to make it active (drawing affects only that layer)
- Quick actions: operate on active layer unless noted (Trim affects all)
- Export:
  - Side panel “Export ICO…” -> Select sizes and algorithm in preview dialog
  - Optionally export PNG set (one PNG for each size)

---

## Keyboard Shortcuts

- General:
  - Ctrl+O: Open
  - Ctrl+S: Save PNG (composite)
  - Ctrl+E: Export ICO
  - Ctrl+N: New
  - Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z): Undo/Redo
  - F: Fit to Window
  - Esc: Deselect selection
- Tools:
  - B: Brush
  - E: Eraser
  - G: Fill
  - I: Eyedropper
  - M: Magic Eraser
  - S: Selection
  - V: Move
  - T: Text
  - L: Line
  - R: Rectangle
  - C: Ellipse
- View:
  - Ctrl + Mouse Wheel: Zoom
  - Middle Button Drag: Pan
  - Space + Left Drag: Pan

---

## Export Details

- ICO export:
  - Select sizes and resampling algorithm (Nearest, Bilinear, Bicubic, Lanczos).
  - Maintain aspect ratio: fits into a square canvas with transparent padding.
  - Optional PNG set export to a sibling folder (e.g., icon_png/).
- ICO is saved with frames sorted from largest to smallest.

---

## CLI (Command Line)

Run the program in CLI mode for automation or batch conversion.

Single export:
```
python icon_editor/main.py --cli --input path/to/image.png --output out/icon.ico --sizes 16,24,32,48,64,128,256 --resample lanczos --export-pngs
```

Batch export (directory):
```
python icon_editor/main.py --cli --input-dir ./images --pattern "*.png" --out-dir ./out --sizes 16,32,48,256 --resample lanczos --export-pngs
```

Options:
- --cli: run in command line mode
- Single mode:
  - --input: input image file
  - --output: target .ico path
- Batch mode:
  - --input-dir: input directory
  - --pattern: file glob (default: "*.png")
  - --out-dir: output directory (default: input_dir/ico_output)
- Common:
  - --sizes: comma-separated list (e.g., 16,32,48,256). If omitted, defaults to standard sizes.
  - --resample: nearest | bilinear | bicubic | lanczos (default: lanczos)
  - --no-aspect: disables aspect preservation (stretches to square)
  - --export-pngs: also export a PNG set for each size
  - --max-dim: downscale large input images for editing (default 3072)

---

## Performance & Safety

- Large images: Automatic downscale on open for editing responsiveness (GUI load path uses 3072 px cap; changeable in CLI).
- Fill operations: flood_fill includes a safety cap (MAX_PIXELS ~1.2M) to prevent UI blocking on extremely large fills. If a fill stops early, repeat on the remainder with a higher tolerance or smaller selection.
- Rendering: only the composite and changed regions are updated; grid overlay enabled at higher zoom.

---

## Known Limitations

- Text tool font: uses DejaVuSans.ttf when available, otherwise falls back to PIL’s default bitmap font. Install additional fonts or modify code to pick a custom font path.
- No advanced transforms (rotate/scale arbitrary) for selections beyond move; future enhancement.
- Floating selection must be committed (switch tool or Esc) before export to ensure it is baked into layers.

---

## Troubleshooting

- “Module tkinter not found” on Linux:
  - Install tk: e.g., Debian/Ubuntu: `sudo apt-get install python3-tk`
- Pillow errors opening some images:
  - Update Pillow: `pip install --upgrade Pillow`
  - Convert image to PNG first if it’s an uncommon format variant.
- ICO not showing all sizes:
  - Ensure sizes are selected and check the exported file with a viewer that supports multi-size ICO.

---

## Development

Recommended environment:

```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install Pillow
```

Run:
```
python icon_editor/main.py
```

Code style:
- Python 3.8+ typing where practical
- Modular architecture (gui/core/utils)
- Clear separation of GUI, image handling, and export logic

---

## Extending

Some ideas for enhancement:
- Advanced transforms: rotate, scale selection
- Layer blend modes and opacity
- Shape fill options and stroke styles
- Smart background removal (chroma or ML-based)
- Plugin system for effects
- ICNS export (macOS), SVG import

---

## License

This project is released under the MIT License (see LICENSE). Third-party dependencies retain their own licenses:
- Python (tkinter): PSF / BSD-style (Tcl/Tk)
- Pillow: HPND

Copyright (c) 2025

---

## Credits

- Built with Python, tkinter, and Pillow
- Thanks to contributors and testers
