# PyIcon Creator & Editor

A full-featured, cross-platform icon creator and editor written in Python. Create, edit, and export multi-resolution Windows `.ico` files and Apple `.icns` files with full alpha transparency. Includes a compact ribbon-style toolbar, drawing tools, shapes, text, zoom/pan, quick actions, selection and move tools, and a robust CLI for automation and batch conversion.

- **License**: MIT
- **OS**: Windows, macOS, Linux
- **Python**: 3.8+ for source use; the included Windows build script requires exactly **Python 3.13.12**

---

## GUI Overview & Controls
   The application features a streamlined, single-row ribbon toolbar at the top of the window, divided into logical groups from left to right.
<br>
<br>
<img width="1562" height="964" alt="image" src="https://github.com/user-attachments/assets/1d6a34fb-f635-43a1-8063-a9e876581415" />
<br>
<br>
### 1. File Operations
- **Open**: Load an existing image (`PNG`, `JPG`, `BMP`, `GIF`, `TIFF`, `WebP`, `ICO`)
- **Save**: Save the current composite canvas as a flat `PNG`
- **Export ICO**: Export a multi-resolution Windows icon with preview
- **Export ICNS**: Export a macOS icon using Pillow-based `.icns` export

### 2. Drawing Tools
Select a tool to interact with the main canvas. The active tool button appears depressed.

- **Selection (S)**: Drag a rectangle to select an area. Press `Esc` to clear
- **Move (V)**: Drag a selected area to a new location. The floating selection preview and selection box move together, and switching tools or pressing `Esc` commits the move to the canvas
- **Brush (B)**: Freehand drawing
- **Eraser (E)**: Erase pixels to full transparency
- **Fill (G)**: Flood-fill an area based on color similarity
- **Eyedropper (I)**: Click the canvas to pick an RGBA color
- **Magic Eraser (M)**: Flood-fill an area with transparency
- **Text (T)**: Click on the canvas, enter text, and stamp it using a chosen font size
- **Shapes**:
  - **Line (L)**
  - **Rectangle (R)** — supports outline or filled mode
  - **Ellipse (C)** — supports outline or filled mode

### 3. Tool Settings & Sliders
- **Filled**: Toggle filled mode for Rectangle and Ellipse tools
- **Size**: Adjust stroke width for Brush, Eraser, and Shape tools
- **Color Box**: Open the system color picker
- **Alpha**: Set opacity from `0–255`
- **Tol (Tolerance)**: Adjust how aggressively Fill and Magic Eraser spread across similar colors

### 4. View Controls
- **Grid**: Toggle a 1px overlay grid, visible at `4x` zoom or higher
- **Fit**: Fit the canvas to the current window size
- **Reset**: Reset scrollbars to the image center
- **Zoom Slider**: Set zoom level from `1x` to `16x`

### Top Menu Bar
- **File**: New Canvas, Open Recent, Save, Export ICO, Export ICNS, Exit
- **Edit**: Undo/Redo, Deselect, Quick Actions
- **View**: Grid toggle, Light/Dark/System theme
- **Help**: About

---

## Navigation & Shortcuts

### View / Navigation
- **Zoom**: `Ctrl + Mouse Wheel`
- **Pan**: `Middle Mouse Button Drag` or hold `Space + Left Drag`
- **Fit to Window**: `F`

### Edit
- **Undo**: `Ctrl+Z`
- **Redo**: `Ctrl+Y`
- **Clear Selection / Deselect / Commit Move**: `Esc`
- **Delete Selected Area**: `Delete`

### Tool Shortcuts
- **Selection**: `S`
- **Move**: `V`
- **Brush**: `B`
- **Eraser**: `E`
- **Fill**: `G`
- **Eyedropper**: `I`
- **Magic Eraser**: `M`
- **Text**: `T`
- **Line**: `L`
- **Rectangle**: `R`
- **Ellipse**: `C`

---

## Selection and Move Behavior

The editor supports rectangular selection and moving selected pixels as a floating selection.

- Draw a selection using the **Selection** tool
- Switch to the **Move** tool and drag inside the selected region to reposition it
- The moved selection preview and the visible selection box stay aligned while dragging
- Press `Esc` or switch to another tool to commit the moved selection back onto the active layer
- Press `Delete` to clear the selected area to transparency

---

## Export Details

### ICO Export
- Live preview of generated sizes before saving
- Standard Windows icon sizes such as `256, 128, 64, 48, 32, 24, 16`
- Resampling options supported internally through Pillow helpers
- Optional export of a companion PNG set in a sibling folder

### ICNS Export
- Live preview of generated sizes before saving
- Standard macOS export sizes such as `1024, 512, 256, 128, 64, 32, 16`
- `.icns` export is handled through Pillow by saving from the largest prepared square RGBA image
- No `icnsutil` dependency is required; current runtime dependencies are `Pillow` and `pyinstaller` only

---

## Supported Input Formats

The editor can open the following formats:

- `.png`
- `.jpg`
- `.jpeg`
- `.bmp`
- `.gif`
- `.tif`
- `.tiff`
- `.webp`
- `.ico`

Loaded images are converted to RGBA automatically, and very large images may be downscaled for more responsive editing.

---

## CLI (Command Line)

Run the program in CLI mode for automation or batch conversion.

### Single Export
```bash
python icon_editor/main.py --cli --input path/to/image.png --output out/icon.ico --sizes 16,24,32,48,64,128,256 --resample lanczos --export-pngs
```

### Batch Export
```bash
python icon_editor/main.py --cli --input-dir ./images --pattern "*.png" --out-dir ./out --sizes 16,32,48,256 --resample lanczos --export-pngs
```

### CLI Notes
- `--cli` enables command-line mode
- Use `--input` and `--output` for a single export
- Use `--input-dir` for batch export
- `--sizes` accepts comma-separated icon sizes
- `--resample` accepts:
  - `nearest`
  - `bilinear`
  - `bicubic`
  - `lanczos`
- `--no-aspect` disables aspect-ratio preservation
- `--export-pngs` also writes a PNG set for each generated size
- `--max-dim` controls automatic downscaling for large source images in CLI mode

---

## Building the Application

This project can be packaged as a standalone desktop application using PyInstaller.

### Windows (Automated)

Use the included batch script:

```bat
BUILD_EXE.bat
```

What the script does:

1. Checks for **exactly Python 3.13.12**
2. Creates a fresh virtual environment in `.venv`
3. Activates the virtual environment
4. Upgrades `pip`, `setuptools`, and `wheel`
5. Installs dependencies from `requirements.txt`
6. Installs PyInstaller
7. Builds the application using `icon_editor.spec`

Important notes:

- The script requires **Python 3.13.12**
- If the wrong version is installed, it opens the official Python download page for that required version
- The build output is written to the `dist/` folder

### macOS / Linux (Manual)

On macOS and Linux, build from a terminal:

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Activate it:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

4. Build with PyInstaller:

```bash
pyinstaller --clean --noconfirm icon_editor.spec
```

5. Check the output in the `dist/` folder

### Build Output by Platform

PyInstaller output depends on the operating system:

- **Windows**: standalone `.exe`
- **macOS**: `.app` bundle
- **Linux**: native executable/build output appropriate to the platform

### Spec File Notes

The application is built from `icon_editor.spec`. The spec file:

- uses `icon_editor/main.py` as the entry point
- includes `icon.ico` as bundled data
- collects Pillow submodules automatically
- includes hidden imports for several `tkinter` modules
- sets the packaged application name to **Pyicon Editor**

### Example Manual Build Workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
pyinstaller --clean --noconfirm icon_editor.spec
```

---

## Requirements

Current dependencies are:

```txt
Pillow>=10.0,<11
pyinstaller>=6.0
```

---

## Project Notes

- The app uses `tkinter` for the GUI and Pillow for image processing
- Theme preference and recent files are stored in a user config file
- The project is licensed under the MIT License
- Third-party notices for Python/tkinter and Pillow are included in `NOTICE`

---
