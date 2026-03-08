# Icon Creator & Editor

A full-featured, cross-platform icon creator and editor written in Python. Create, edit, and export multi-resolution Windows .ico files with full alpha transparency. Includes a compact ribbon-style toolbar, drawing tools, shapes, text, zoom/pan, quick actions, and a robust CLI for automation and batch conversion.

- **License**: MIT
- **OS**: Windows, macOS, Linux
- **Python**: 3.8+ (Note: The included Windows build script requires exactly Python 3.13.12).

---

## GUI Overview & Controls
<br>
<img width="1402" height="952" alt="image" src="https://github.com/user-attachments/assets/a8648f4c-360a-48b9-8bc4-1ddb9ece98fa" />
<br>
The application features a streamlined, single-row ribbon toolbar at the top of the window, divided into logical groups from left to right:

### 1. File Operations
- **Open**: Load an existing image (PNG, JPG, BMP, GIF, TIFF, WebP, ICO). Large images are auto-downscaled for performance.
- **Save**: Saves the current composite canvas as a flat PNG file.
- **Export**: Opens the multi-resolution `.ico` preview dialog.

### 2. Drawing Tools
Select a tool to interact with the main canvas. The active tool button appears depressed.
- **Selection (S)**: Drag a rectangle to select an area. Press `Esc` to clear.
- **Move (V)**: Drag a selected area to a new location. Switch tools or press `Esc` to commit the move to the canvas.
- **Brush (B)**: Freehand drawing.
- **Eraser (E)**: Erases pixels to full transparency.
- **Fill (G)**: Flood-fills an area based on color similarity.
- **Eyedropper (I)**: Click the canvas to pick an RGBA color.
- **Magic Eraser (M)**: Flood-fills an area with transparency.
- **Text (T)**: Click on the canvas, enter text, and set the font size to stamp text.
- **Shapes**: **Line (L)**, **Rectangle (R)**, and **Ellipse (C)**. Click and drag to draw; the shape is committed to the canvas when you release the mouse.

### 3. Tool Settings & Sliders
- **Size**: Adjusts the stroke width (1–64) for the Brush, Eraser, and Shape tools.
- **Color Box**: Click the solid colored square to open the system color picker.
- **Alpha**: Sets the opacity (0–255) of your selected color.
- **Tol (Tolerance)**: Adjusts how aggressively the Fill and Magic Eraser tools spread across similar colors (0–100).

### 4. View Controls
- **Grid**: Toggles a 1px overlay grid (only visible at 4x zoom or higher).
- **Fit**: Fits the canvas to the current window size.
- **Reset**: Resets the scrollbars to the center of the image.
- **Zoom Slider**: Manually set the zoom level from 1x to 16x.

### Top Menu Bar
- **File**: New Canvas, Open Recent, Save, Export, Exit.
- **Edit**: Undo/Redo, **Quick Actions** (Invert Colors, Grayscale, Flip Horizontal/Vertical, Trim Transparent boundaries).
- **View**: Theme toggle (Light, Dark, System).

---

## Navigation Shortcuts
- **Zoom**: `Ctrl + Mouse Wheel`
- **Pan**: `Middle Mouse Button Drag` OR hold `Space + Left Drag`
- **Undo / Redo**: `Ctrl+Z` / `Ctrl+Y`

---

## Export Details
- **Live Preview**: Clicking Export opens a dialog showing exactly how your icon will look at standard Windows sizes (256, 128, 64, 48, 32, 24, 16).
- **Resampling**: Choose between Nearest, Bilinear, Bicubic, or Lanczos algorithms.
- **PNG Set**: Includes a checkbox to optionally save a folder containing individual `.png` files for every resolution alongside your final `.ico`.

---

## CLI (Command Line)
Run the program in CLI mode for automation or batch conversion.

**Single export:**
```bash
python icon_editor/main.py --cli --input path/to/image.png --output out/icon.ico --sizes 16,24,32,48,64,128,256 --resample lanczos --export-pngs
```

**Batch export (directory):**
```bash
python icon_editor/main.py --cli --input-dir ./images --pattern "*.png" --out-dir ./out --sizes 16,32,48,256 --resample lanczos --export-pngs
```

---

## Building a Single-File Executable

This project is configured to build as a single, standalone executable (`.exe` on Windows) containing all dependencies.

### Windows (Automated)
Run the included batch script. This script automatically creates a virtual environment, installs dependencies, and runs PyInstaller. 
*Note: This script strictly requires Python 3.13.12 to be installed on your system.*

1. Double click `BUILD_EXE.bat`.
2. Wait for the process to complete.
3. The final executable will be located in `dist/IconCreator.exe`.

### Manual / macOS / Linux
If you are not using the batch script or are on a different OS, you can build manually using the provided spec file:

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```
3. Run PyInstaller with the spec file:
   ```bash
   pyinstaller --clean --noconfirm icon_editor.spec
   ```
4. The standalone executable will be generated in the `dist/` folder.
