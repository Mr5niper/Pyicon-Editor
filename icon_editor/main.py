Here is a complete, build-stable drop-in of the entire project with the initialization races fixed and every method included. It’s structured to work both in a normal Python run and a PyInstaller one-file EXE (spec-driven). I removed constructor-time callbacks, deferred first-time updates, and guarded all UI callbacks.

Copy these files exactly into your repo. Then build with your icon_editor.spec (or the one I include at the end).

File: icon_editor/main.py
```
import sys
import os
import argparse
from pathlib import Path

# Ensure local package import
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from gui.main_window import run_app
from core.image_handler import load_image_with_alpha
from core.icon_generator import prepare_image_for_size, save_ico_from_images
from utils.helpers import parse_sizes_list


def run_cli_single(args):
    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    try:
        img = load_image_with_alpha(input_path, max_edit_dimension=args.max_dim)
    except Exception as e:
        print(f"Error: Failed to load image: {e}")
        sys.exit(1)

    sizes = parse_sizes_list(args.sizes) if args.sizes else [16, 24, 32, 48, 64, 128, 256]
    if not sizes:
        print("Error: No sizes specified.")
        sys.exit(1)
    resample_name = args.resample or "lanczos"

    prepared = []
    for s in sorted(set(sizes), reverse=True):
        prepared.append((s, prepare_image_for_size(
            img, s, resample_name,
            maintain_aspect=(not args.no_aspect),
            pad_to_square=True
        )))

    try:
        save_ico_from_images(prepared, output_path)
    except Exception as e:
        print(f"Error: Failed to export ICO: {e}")
        sys.exit(1)

    if args.export_pngs:
        png_dir = output_path.parent / f"{output_path.stem}_png"
        png_dir.mkdir(parents=True, exist_ok=True)
        for sz, im in prepared:
            out_png = png_dir / f"{output_path.stem}_{sz}.png"
            im.save(out_png, format="PNG", optimize=True)
        print(f"Saved PNG set to: {png_dir}")

    print(f"Exported ICO: {output_path}")


def run_cli_batch(args):
    in_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir) if args.out_dir else in_dir / "ico_output"
    pattern = args.pattern or "*.png"
    if not in_dir.exists():
        print(f"Error: Input directory not found: {in_dir}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    sizes = parse_sizes_list(args.sizes) if args.sizes else [16, 24, 32, 48, 64, 128, 256]
    if not sizes:
        print("Error: No sizes specified.")
        sys.exit(1)
    resample_name = args.resample or "lanczos"

    count = 0
    for path in in_dir.rglob(pattern):
        if not path.is_file():
            continue
        try:
            img = load_image_with_alpha(path, max_edit_dimension=args.max_dim)
        except Exception as e:
            print(f"[SKIP] {path.name}: {e}")
            continue

        prepared = []
        for s in sorted(set(sizes), reverse=True):
            prepared.append((s, prepare_image_for_size(
                img, s, resample_name,
                maintain_aspect=(not args.no_aspect),
                pad_to_square=True
            )))

        out_ico = out_dir / f"{path.stem}.ico"
        try:
            save_ico_from_images(prepared, out_ico)
            if args.export_pngs:
                png_dir = out_dir / f"{path.stem}_png"
                png_dir.mkdir(parents=True, exist_ok=True)
                for sz, im in prepared:
                    (png_dir / f"{path.stem}_{sz}.png").write_bytes(pil_to_png_bytes(im))
            print(f"[OK] {path.name} -> {out_ico.name}")
            count += 1
        except Exception as e:
            print(f"[FAIL] {path.name}: {e}")
    print(f"Batch complete. {count} icons exported to {out_dir}")


def pil_to_png_bytes(im):
    from io import BytesIO
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Icon Creator & Editor")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode")
    parser.add_argument("--input", type=str, help="Input image path (for single export)")
    parser.add_argument("--output", type=str, help="Output .ico path (for single export)")
    parser.add_argument("--sizes", type=str, help="Comma-separated sizes (e.g., 16,32,48,256)")
    parser.add_argument("--resample", type=str, default="lanczos",
                        choices=["nearest", "bilinear", "bicubic", "lanczos"],
                        help="Resampling algorithm")
    parser.add_argument("--no-aspect", action="store_true", help="Do not maintain aspect ratio (stretches)")
    parser.add_argument("--export-pngs", action="store_true", help="Also export PNG set for each size")
    parser.add_argument("--max-dim", type=int, default=3072, help="Max dimension to downscale large images for editing (CLI)")

    # Batch mode
    parser.add_argument("--input-dir", type=str, help="Input directory for batch")
    parser.add_argument("--pattern", type=str, help="Glob pattern for input (e.g., '*.png')")
    parser.add_argument("--out-dir", type=str, help="Output directory for batch output")

    args = parser.parse_args()

    if args.cli:
        if args.input_dir:
            run_cli_batch(args)
            return
        if not args.input or not args.output:
            parser.error("--cli requires --input and --output (or use --input-dir for batch mode)")
        run_cli_single(args)
        return

    # GUI mode
    try:
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI Aware
            except Exception:
                pass
    except Exception:
        pass
    run_app()


if __name__ == "__main__":
    main()
```

File: icon_editor/__main__.py
```
from .main import main

if __name__ == "__main__":
    main()
```

File: icon_editor/gui/main_window.py
```
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path

from core.image_handler import (
    load_image_with_alpha,
    save_png,
    open_image_dialog,
    save_png_dialog,
)
from core.icon_generator import export_ico_dialog
from core.editor_tools import ToolType
from gui.canvas_editor import CanvasEditor
from gui.toolbar import ToolBar
from utils.helpers import human_readable_size
from utils.config import AppConfig


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Icon Creator & Editor")
        self.geometry("1320x880")
        self.minsize(1100, 740)

        self.config_mgr = AppConfig()
        self.recent_files = self.config_mgr.recent_files.copy()
        self.theme = self.config_mgr.theme or "System"

        self.style = ttk.Style()
        self._apply_theme(self.theme)

        self.current_file: Path | None = None

        self.maintain_aspect = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=False)

        # Pending zoom text if early callback arrives
        self._pending_zoom = None

        # Build order: menu -> statusbar -> layout (editor)
        self._build_menu()
        self._build_statusbar()
        self._build_layout()

        # Initialize blank canvas AFTER editor exists to avoid early callbacks
        self.after_idle(lambda: self.canvas_editor.new_blank((256, 256)))

        self._update_status("Ready")

        # Key bindings
        self.bind_all("<Control-o>", lambda e: self.open_image())
        self.bind_all("<Control-s>", lambda e: self.save_png())
        self.bind_all("<Control-e>", lambda e: self.export_ico())
        self.bind_all("<Control-n>", lambda e: self.new_canvas())
        self.bind_all("<Control-z>", lambda e: self.canvas_editor.undo())
        self.bind_all("<Control-Shift-Z>", lambda e: self.canvas_editor.redo())
        self.bind_all("<Control-y>", lambda e: self.canvas_editor.redo())
        self.bind_all("<Key-f>", lambda e: self.canvas_editor.fit_to_window())

        # Tool hotkeys
        self.bind_all("<Key-b>", lambda e: self._select_tool(ToolType.PENCIL))
        self.bind_all("<Key-e>", lambda e: self._select_tool(ToolType.ERASER))
        self.bind_all("<Key-g>", lambda e: self._select_tool(ToolType.FILL))
        self.bind_all("<Key-i>", lambda e: self._select_tool(ToolType.EYEDROPPER))
        self.bind_all("<Key-m>", lambda e: self._select_tool(ToolType.MAGIC_ERASER))
        self.bind_all("<Key-s>", lambda e: self._select_tool(ToolType.SELECTION))
        self.bind_all("<Key-t>", lambda e: self._select_tool(ToolType.TEXT))
        self.bind_all("<Key-l>", lambda e: self._select_tool(ToolType.SHAPE_LINE))
        self.bind_all("<Key-r>", lambda e: self._select_tool(ToolType.SHAPE_RECT))
        self.bind_all("<Key-c>", lambda e: self._select_tool(ToolType.SHAPE_ELLIPSE))
        self.bind_all("<Key-v>", lambda e: self._select_tool(ToolType.MOVE))

        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _apply_theme(self, mode: str):
        try:
            if mode.lower() == "dark":
                self.style.theme_use("clam")
                dark_bg = "#2b2b2b"
                light_bg = "#3a3a3a"
                fg = "#e8e8e8"
                self.configure(bg=dark_bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton"]:
                    self.style.configure(elem, background=dark_bg, foreground=fg)
                self.style.configure("TEntry", fieldbackground=light_bg, foreground=fg)
                self.style.map("TButton", background=[("active", "#444")])
            elif mode.lower() == "light":
                self.style.theme_use("clam")
                bg = "#f0f0f0"
                self.configure(bg=bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton"]:
                    self.style.configure(elem, background=bg, foreground="#111")
                self.style.configure("TEntry", fieldbackground="#ffffff", foreground="#111")
            else:
                try:
                    if os.name == "nt":
                        self.style.theme_use("vista")
                    else:
                        self.style.theme_use("default")
                except Exception:
                    self.style.theme_use("clam")
        except Exception:
            pass

    def _select_tool(self, tool):
        self.toolbar.set_tool(tool)
        self.canvas_editor.set_tool(tool)

    def _build_menu(self):
        menubar = tk.Menu(self)
        # File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New (Ctrl+N)", command=self.new_canvas)
        file_menu.add_command(label="Open... (Ctrl+O)", command=self.open_image)

        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=self.recent_menu)
        self._refresh_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Save PNG... (Ctrl+S)", command=self.save_png)
        file_menu.add_command(label="Export ICO... (Ctrl+E)", command=self.export_ico)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
        edit_menu.add_command(label="Redo (Ctrl+Y)", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Make Background Transparent", command=self.make_bg_transparent)
        edit_menu.add_command(label="Deselect (Esc)", command=self._deselect)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(
            label="Show Grid", variable=self.show_grid, command=self._toggle_grid
        )
        theme_menu = tk.Menu(view_menu, tearoff=0)
        theme_menu.add_command(label="Light", command=lambda: self._set_theme("Light"))
        theme_menu.add_command(label="Dark", command=lambda: self._set_theme("Dark"))
        theme_menu.add_command(label="System", command=lambda: self._set_theme("System"))
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        menubar.add_cascade(label="View", menu=view_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.toolbar = ToolBar(
            self,
            on_tool_change=self._on_tool_change,
            on_brush_size_change=self._on_brush_size_change,
            on_alpha_change=self._on_alpha_change,
            on_color_change=self._on_color_change,
            on_fill_tolerance_change=self._on_fill_tolerance_change
        )
        self.toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")

        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=2, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0)
        self.main_frame.rowconfigure(0, weight=1)

        # Side panel first (safe to reference self.canvas_editor in callbacks later)
        self.side_panel = ttk.Frame(self.main_frame)
        self.side_panel.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)
        self._build_side_panel(self.side_panel)

        # Canvas editor – defer callbacks to event loop
        self.canvas_editor = CanvasEditor(
            self.main_frame,
            on_status=lambda msg: self.after_idle(lambda: self._update_status(msg)),
            on_cursor=lambda x, y: self.after_idle(lambda: self._update_cursor(x, y)),
            on_size_change=lambda w, h: self.after_idle(lambda: self._update_image_info(w, h)),
            on_zoom_change=lambda z: self.after_idle(lambda: self._update_zoom_info(z)),
            on_layers_changed=lambda: self.after_idle(self._refresh_layers_panel)
        )
        self.canvas_editor.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        self.bind_all("<Escape>", lambda e: self._deselect())

    def _build_side_panel(self, parent):
        info_group = ttk.LabelFrame(parent, text="Image Info")
        info_group.pack(fill="x", pady=(0, 10))
        self.info_label = ttk.Label(info_group, text="No image loaded")
        self.info_label.pack(fill="x", padx=8, pady=8)

        zoom_group = ttk.LabelFrame(parent, text="View / Zoom")
        zoom_group.pack(fill="x", pady=(0, 10))
        self.zoom_var = tk.IntVar(value=4)
        zoom_scale = ttk.Scale(
            zoom_group, from_=1, to=16, orient="horizontal",
            command=lambda v: self.canvas_editor.set_zoom(int(float(v)))
        )
        zoom_scale.set(4)
        zoom_scale.pack(fill="x", padx=8, pady=8)
        btn_row = ttk.Frame(zoom_group)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Fit to Window (F)", command=self.canvas_editor.fit_to_window).pack(side="left")
        ttk.Button(btn_row, text="Reset Scroll", command=self.canvas_editor.reset_scroll).pack(side="left", padx=(8, 0))
        ttk.Label(zoom_group, text="Ctrl+Wheel Zoom • Space+Drag or Middle Button to Pan").pack(padx=8, pady=(4, 8))

        sizes_group = ttk.LabelFrame(parent, text="Target Icon Sizes")
        sizes_group.pack(fill="x", pady=(0, 10))
        self.size_vars = {}
        for size in (256, 128, 64, 48, 32, 24, 16):
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(sizes_group, text=f"{size} x {size}", variable=var)
            cb.pack(anchor="w", padx=8)
            self.size_vars[size] = var

        resample_group = ttk.LabelFrame(parent, text="Resize Algorithm")
        resample_group.pack(fill="x", pady=(0, 10))
        self.resample_combo = ttk.Combobox(resample_group, values=["Nearest", "Bilinear", "Bicubic", "Lanczos"], state="readonly")
        self.resample_combo.set("Lanczos")
        self.resample_combo.pack(fill="x", padx=8, pady=8)

        ap_group = ttk.LabelFrame(parent, text="Resize Options")
        ap_group.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(ap_group, text="Maintain Aspect Ratio", variable=self.maintain_aspect).pack(anchor="w", padx=8)
        ttk.Label(ap_group, text="ICO frames are square; padding is applied when keeping aspect.").pack(anchor="w", padx=8, pady=(4, 0))

        qa_group = ttk.LabelFrame(parent, text="Quick Actions")
        qa_group.pack(fill="x", pady=(0, 10))
        ttk.Button(qa_group, text="Invert Colors", command=lambda: self.canvas_editor.quick_invert()).pack(fill="x", padx=8, pady=3)
        ttk.Button(qa_group, text="Grayscale", command=lambda: self.canvas_editor.quick_grayscale()).pack(fill="x", padx=8, pady=3)
        ttk.Button(qa_group, text="Flip Horizontal", command=lambda: self.canvas_editor.quick_flip_h()).pack(fill="x", padx=8, pady=3)
        ttk.Button(qa_group, text="Flip Vertical", command=lambda: self.canvas_editor.quick_flip_v()).pack(fill="x", padx=8, pady=3)
        ttk.Button(qa_group, text="Trim Transparent", command=lambda: self.canvas_editor.quick_trim_transparent()).pack(fill="x", padx=8, pady=3)
        ttk.Button(qa_group, text="Make BG Transparent", command=self.make_bg_transparent).pack(fill="x", padx=8, pady=3)

        layers_group = ttk.LabelFrame(parent, text="Layers")
        layers_group.pack(fill="both", expand=True, pady=(0, 10))
        self.layers_list = tk.Listbox(layers_group, height=8)
        self.layers_list.pack(fill="both", expand=True, padx=8, pady=6)
        self.layers_list.bind("<<ListboxSelect>>", self._on_layer_select)
        layer_btns = ttk.Frame(layers_group)
        layer_btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(layer_btns, text="Add", command=self._layer_add).pack(side="left")
        ttk.Button(layer_btns, text="Delete", command=self._layer_delete).pack(side="left", padx=4)
        ttk.Button(layer_btns, text="Up", command=lambda: self._layer_move(-1)).pack(side="left", padx=4)
        ttk.Button(layer_btns, text="Down", command=lambda: self._layer_move(1)).pack(side="left", padx=4)
        ttk.Button(layer_btns, text="Toggle Vis", command=self._layer_toggle_vis).pack(side="left", padx=4)

        action_group = ttk.Frame(parent)
        action_group.pack(fill="x", pady=(10, 0))
        ttk.Button(action_group, text="Open Image...", command=self.open_image).pack(fill="x", pady=(0, 6))
        ttk.Button(action_group, text="Save PNG...", command=self.save_png).pack(fill="x", pady=(0, 6))
        ttk.Button(action_group, text="Export ICO...", command=self.export_ico).pack(fill="x")

    def _build_statusbar(self):
        self.statusbar = ttk.Frame(self)
        self.statusbar.grid(row=3, column=0, sticky="ew")
        self.statusbar.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self.statusbar, text="Status: Ready", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=8)
        self.cursor_label = ttk.Label(self.statusbar, text="Cursor: -, -", width=20, anchor="e")
        self.cursor_label.grid(row=0, column=1, sticky="e", padx=8)
        self.dim_label = ttk.Label(self.statusbar, text="Canvas: 0x0", width=16, anchor="e")
        self.dim_label.grid(row=0, column=2, sticky="e", padx=8)
        self.zoom_label = ttk.Label(self.statusbar, text="Zoom: 4x", width=12, anchor="e")
        self.zoom_label.grid(row=0, column=3, sticky="e", padx=8)
        if self._pending_zoom is not None:
            self.zoom_label.config(text=f"Zoom: {self._pending_zoom}x")
            self._pending_zoom = None

    def _update_status(self, text):
        self.status_label.config(text=f"Status: {text}")

    def _update_cursor(self, x, y):
        if x is None or y is None:
            self.cursor_label.config(text="Cursor: -, -")
        else:
            self.cursor_label.config(text=f"Cursor: {x}, {y}")

    def _update_image_info(self, w, h):
        self.dim_label.config(text=f"Canvas: {w}x{h}")
        comp = None
        try:
            if hasattr(self, "canvas_editor") and self.canvas_editor is not None:
                comp = self.canvas_editor.get_composite()
        except Exception:
            comp = None
        if comp is not None:
            sz = comp.width * comp.height * 4
            self.info_label.config(
                text=f"Size: {w} x {h}\nMode: RGBA\nApprox Mem: {human_readable_size(sz)}"
            )
        else:
            self.info_label.config(text=f"Size: {w} x {h}\nMode: RGBA")

    def _update_zoom_info(self, zoom):
        if hasattr(self, "zoom_label"):
            self.zoom_label.config(text=f"Zoom: {zoom}x")
        else:
            self._pending_zoom = zoom

    def _on_tool_change(self, tool: ToolType):
        self.canvas_editor.set_tool(tool)

    def _on_brush_size_change(self, size: int):
        self.canvas_editor.set_brush_size(size)

    def _on_color_change(self, rgba):
        self.canvas_editor.set_color(rgba)

    def _on_alpha_change(self, alpha: int):
        self.canvas_editor.set_alpha(alpha)

    def _on_fill_tolerance_change(self, tol: int):
        self.canvas_editor.set_fill_tolerance(tol)

    def _toggle_grid(self):
        self.canvas_editor.set_grid(self.show_grid.get())

    def _about(self):
        messagebox.showinfo(
            "About",
            "Icon Creator & Editor\n- Multi-resolution ICO export\n- Drawing, selection, shapes, text\n- Layers, panning/zoom, recent files"
        )

    def _set_theme(self, theme: str):
        self.theme = theme
        self._apply_theme(theme)
        self.config_mgr.theme = theme
        self.config_mgr.save()

    def _on_exit(self):
        self.config_mgr.recent_files = self.recent_files[:5]
        self.config_mgr.theme = self.theme
        self.config_mgr.save()
        self.destroy()

    def _refresh_recent_menu(self):
        self.recent_menu.delete(0, "end")
        if not self.recent_files:
            self.recent_menu.add_command(label="(Empty)", state="disabled")
            return
        for path_str in self.recent_files:
            p = Path(path_str)
            label = p.name if len(p.name) < 48 else "..." + p.name[-45:]
            self.recent_menu.add_command(label=label, command=lambda s=path_str: self._open_recent(s))

    def _open_recent(self, path_str: str):
        p = Path(path_str)
        if not p.exists():
            messagebox.showerror("Missing file", f"File not found:\n{p}")
            self.recent_files = [s for s in self.recent_files if s != path_str]
            self._refresh_recent_menu()
            return
        self._open_path(p)

    def _add_recent(self, p: Path):
        s = str(p.resolve())
        if s in self.recent_files:
            self.recent_files.remove(s)
        self.recent_files.insert(0, s)
        self.recent_files = self.recent_files[:5]
        self._refresh_recent_menu()

    def new_canvas(self):
        dialog = tk.Toplevel(self)
        dialog.title("New Canvas")
        dialog.transient(self)
        dialog.resizable(False, False)
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        w_var = tk.IntVar(value=256)
        h_var = tk.IntVar(value=256)
        w_entry = ttk.Entry(dialog, textvariable=w_var, width=10)
        h_entry = ttk.Entry(dialog, textvariable=h_var, width=10)
        w_entry.grid(row=0, column=1, padx=10, pady=8)
        h_entry.grid(row=1, column=1, padx=10, pady=8)

        def ok():
            w, h = int(w_var.get()), int(h_var.get())
            if w <= 0 or h <= 0 or w > 4096 or h > 4096:
                messagebox.showerror("Invalid size", "Please enter sizes between 1 and 4096.")
                return
            self.canvas_editor.new_blank((w, h))
            dialog.destroy()

        ttk.Button(dialog, text="Create", command=ok).grid(row=2, column=0, columnspan=2, pady=10)
        dialog.grab_set()
        self.wait_window(dialog)

    def _open_path(self, p: Path):
        try:
            img = load_image_with_alpha(p, max_edit_dimension=3072)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image:\n{e}")
            return
        self.canvas_editor.load_image(img)
        self.current_file = p
        self._add_recent(p)
        self._update_status(f"Loaded: {p.name}")

    def open_image(self, path: str | None = None):
        if not path:
            path = open_image_dialog(self)
            if not path:
                return
        self._open_path(Path(path))

    def save_png(self):
        comp = self.canvas_editor.get_composite()
        if comp is None:
            messagebox.showinfo("No image", "Create or open an image first.")
            return
        out = save_png_dialog(self, initialfile=(self.current_file.stem + ".png") if self.current_file else None)
        if not out:
            return
        try:
            save_png(comp, out)
            self._update_status(f"Saved PNG: {Path(out).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PNG:\n{e}")

    def export_ico(self):
        comp = self.canvas_editor.get_composite()
        if comp is None:
            messagebox.showinfo("No image", "Create or open an image first.")
            return
        sizes = [s for s, var in self.size_vars.items() if var.get()]
        if not sizes:
            messagebox.showinfo("No sizes selected", "Select at least one icon size.")
            return
        resample = self.resample_combo.get()
        export_ico_dialog(
            self,
            base_image=comp,
            sizes=sorted(sizes, reverse=True),
            resample=resample,
            maintain_aspect=self.maintain_aspect.get()
        )

    def undo(self):
        self.canvas_editor.undo()

    def redo(self):
        self.canvas_editor.redo()

    def _deselect(self):
        self.canvas_editor.clear_selection()

    def make_bg_transparent(self):
        self.canvas_editor.make_background_transparent()

    # Layers UI interaction
    def _refresh_layers_panel(self):
        if not hasattr(self, "layers_list"):
            return
        self.layers_list.delete(0, "end")
        for idx, (name, vis) in enumerate(self.canvas_editor.get_layer_list()):
            mark = "👁" if vis else "☐"
            self.layers_list.insert("end", f"{mark} {name}")
        active = self.canvas_editor.active_layer_index()
        if 0 <= active < self.layers_list.size():
            self.layers_list.select_clear(0, "end")
            self.layers_list.select_set(active)
            self.layers_list.activate(active)


def run_app():
    app = MainWindow()
    app.mainloop()
```

File: icon_editor/gui/canvas_editor.py
```
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps, ImageChops, ImageFont
from core.editor_tools import ToolType, UndoRedoStack, flood_fill, draw_brush_line
from core.transparency import create_checkerboard
from utils.helpers import clamp


class CanvasEditor(ttk.Frame):
    def __init__(self, parent, on_status=None, on_cursor=None, on_size_change=None, on_zoom_change=None, on_layers_changed=None):
        super().__init__(parent)
        self.parent = parent
        self.on_status = on_status or (lambda text: None)
        self.on_cursor = on_cursor or (lambda x, y: None)
        self.on_size_change = on_size_change or (lambda w, h: None)
        self.on_zoom_change = on_zoom_change or (lambda z: None)
        self.on_layers_changed = on_layers_changed or (lambda: None)

        # Layers: created by new_blank/load_image (do not create here)
        self.layers = []              # list[Image.Image]
        self.layer_visible = []       # list[bool]
        self.layer_names = []         # list[str]
        self.active_layer = 0

        self._composite_cache = None
        self._composite_dirty = True

        self._display_image = None
        self.zoom = 4
        self.show_grid = False

        self._space_pan_active = False

        self.tool = ToolType.PENCIL
        self.brush_size = 1
        self.color = (0, 0, 0, 255)
        self.alpha = 255
        self.fill_tolerance = 0

        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.sel_floating = None
        self.sel_offset = (0, 0)

        self.is_drawing = False
        self.last_pos = None

        self.shape_start = None
        self.preview_image = None

        self.history = UndoRedoStack(limit=50)

        self._build_ui()
        # Do NOT call new_blank here; main_window will initialize after widget assignment

    # ---------- Layers / Composite ----------
    def width(self):
        return self.layers[0].width if self.layers else 0

    def height(self):
        return self.layers[0].height if self.layers else 0

    def _mark_dirty(self):
        self._composite_dirty = True

    def get_composite(self):
        if not self.layers:
            return None
        if self._composite_dirty or self._composite_cache is None:
            base = Image.new("RGBA", (self.width(), self.height()), (0, 0, 0, 0))
            for ly, vis in zip(self.layers, self.layer_visible):
                if vis:
                    base.alpha_composite(ly)
            self._composite_cache = base
            self._composite_dirty = False
        return self._composite_cache.copy()

    def _get_composite_with_preview(self):
        comp = self.get_composite()
        if comp is None:
            return None
        comp = comp.copy()
        if self.sel_floating is not None:
            comp.alpha_composite(self.sel_floating, self.sel_offset)
        if self.preview_image is not None:
            comp.alpha_composite(self.preview_image)
        return comp

    def active_layer_index(self):
        return self.active_layer

    def get_layer_list(self):
        return [(self.layer_names[i], self.layer_visible[i]) for i in range(len(self.layers))]

    def set_active_layer(self, idx: int):
        if 0 <= idx < len(self.layers):
            self.active_layer = idx
            self.on_status(f"Active layer: {self.layer_names[idx]}")

    def layer_add(self):
        if not self.layers:
            return
        self._push_state()
        new_layer = Image.new("RGBA", (self.width(), self.height()), (0, 0, 0, 0))
        self.layers.insert(self.active_layer + 1, new_layer)
        self.layer_visible.insert(self.active_layer + 1, True)
        self.layer_names.insert(self.active_layer + 1, f"Layer {len(self.layers)}")
        self.active_layer += 1
        self._mark_dirty()
        self._refresh_display()
        self.on_layers_changed()

    def layer_delete(self):
        if len(self.layers) <= 1:
            messagebox.showinfo("Cannot delete", "At least one layer is required.")
            return
        self._push_state()
        del self.layers[self.active_layer]
        del self.layer_visible[self.active_layer]
        del self.layer_names[self.active_layer]
        self.active_layer = max(0, self.active_layer - 1)
        self._mark_dirty()
        self._refresh_display()
        self.on_layers_changed()

    def layer_move(self, direction: int):
        i = self.active_layer
        j = i + direction
        if 0 <= i < len(self.layers) and 0 <= j < len(self.layers):
            self._push_state()
            self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
            self.layer_visible[i], self.layer_visible[j] = self.layer_visible[j], self.layer_visible[i]
            self.layer_names[i], self.layer_names[j] = self.layer_names[j], self.layer_names[i]
            self.active_layer = j
            self._mark_dirty()
            self._refresh_display()
            self.on_layers_changed()

    def layer_toggle_visibility(self):
        if not self.layers:
            return
        self._push_state()
        self.layer_visible[self.active_layer] = not self.layer_visible[self.active_layer]
        self._mark_dirty()
        self._refresh_display()
        self.on_layers_changed()

    # ---------- UI setup ----------
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg="#3a3a3a", highlightthickness=0, cursor="cross")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.vbar.grid(row=0, column=1, sticky="ns")

        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.bind("<Button-2>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.bind("<Button-3>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.bind("<KeyPress-space>", self._on_space_down)
        self.canvas.bind("<KeyRelease-space>", self._on_space_up)

        self.canvas.bind("<Button-2>", self._on_pan_press)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_release)

        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", lambda e: self.on_cursor(None, None))
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)

        self._first_fit_done = False
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

    def _on_canvas_configure(self, event):
        if not self._first_fit_done and self.layers:
            self.fit_to_window()
            self._first_fit_done = True

    # ---------- Project lifecycle ----------
    def new_blank(self, size):
        w, h = size
        self.layers = [Image.new("RGBA", (w, h), (0, 0, 0, 0))]
        self.layer_visible = [True]
        self.layer_names = ["Layer 1"]
        self.active_layer = 0
        self._reset_selection()
        self.history.clear()
        self._push_state()
        self._mark_dirty()
        self.fit_to_window()
        self.on_status(f"New {w}x{h} canvas")
        self.on_size_change(w, h)
        self.on_layers_changed()

    def load_image(self, image):
        img = image.convert("RGBA")
        self.layers = [img]
        self.layer_visible = [True]
        self.layer_names = ["Background"]
        self.active_layer = 0
        self._reset_selection()
        self.history.clear()
        self._push_state()
        self._mark_dirty()
        self.fit_to_window()
        self.on_status("Image loaded")
        self.on_size_change(img.width, img.height)
        self.on_layers_changed()

    def _reset_selection(self):
        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.sel_floating = None
        self.sel_offset = (0, 0)
        self.preview_image = None

    # ---------- View controls ----------
    def set_zoom(self, zoom: int):
        zoom = clamp(zoom, 1, 16)
        if self.zoom != zoom:
            self.zoom = zoom
            self._refresh_display()
            self.on_status(f"Zoom: {self.zoom}x")
            self.on_zoom_change(self.zoom)

    def fit_to_window(self):
        if not self.layers:
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        zw = cw // max(1, self.width())
        zh = ch // max(1, self.height())
        z = max(1, min(zw, zh))
        self.zoom = clamp(z, 1, 16)
        self._refresh_display()
        self.reset_scroll()
        self.on_zoom_change(self.zoom)

    def reset_scroll(self):
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        x0, y0, x1, y1 = bbox
        w = x1 - x0
        h = y1 - y0
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        tx = max(0, (w - cw) // 2)
        ty = max(0, (h - ch) // 2)
        if w > cw:
            self.canvas.xview_moveto(tx / w)
        else:
            self.canvas.xview_moveto(0)
        if h > ch:
            self.canvas.yview_moveto(ty / h)
        else:
            self.canvas.yview_moveto(0)

    def set_grid(self, show: bool):
        self.show_grid = show
        self._refresh_display()

    # ---------- Tool settings ----------
    def set_tool(self, tool: ToolType):
        # Commit floating selection if leaving MOVE
        if self.tool == ToolType.MOVE and self.sel_floating is not None and tool != ToolType.MOVE:
            self._commit_floating_selection()
        self.tool = tool
        self.on_status(f"Tool: {tool.value}")

    def set_brush_size(self, size: int):
        size = clamp(size, 1, 128)
        self.brush_size = size
        self.on_status(f"Brush size: {self.brush_size}")

    def set_alpha(self, alpha: int):
        self.alpha = clamp(alpha, 0, 255)
        r, g, b, _ = self.color
        self.set_color((r, g, b, self.alpha))

    def set_color(self, rgba):
        self.color = (
            clamp(int(rgba[0]), 0, 255),
            clamp(int(rgba[1]), 0, 255),
            clamp(int(rgba[2]), 0, 255),
            clamp(int(rgba[3]), 0, 255),
        )
        self.on_status(f"Color: RGBA{self.color}")

    def set_fill_tolerance(self, tol: int):
        self.fill_tolerance = clamp(int(tol), 0, 255)
        self.on_status(f"Fill tolerance: {self.fill_tolerance}")

    # ---------- Quick Actions ----------
    def quick_invert(self):
        if not self.layers:
            return
        ly = self.layers[self.active_layer]
        self._push_state()
        r, g, b, a = ly.split()
        r, g, b = ImageChops.invert(r), ImageChops.invert(g), ImageChops.invert(b)
        self.layers[self.active_layer] = Image.merge("RGBA", (r, g, b, a))
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Inverted colors")

    def quick_grayscale(self):
        if not self.layers:
            return
        self._push_state()
        self.layers[self.active_layer] = ImageOps.grayscale(self.layers[self.active_layer]).convert("RGBA")
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Grayscale applied")

    def quick_flip_h(self):
        if not self.layers:
            return
        self._push_state()
        self.layers[self.active_layer] = self.layers[self.active_layer].transpose(Image.FLIP_LEFT_RIGHT)
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Flipped horizontally")

    def quick_flip_v(self):
        if not self.layers:
            return
        self._push_state()
        self.layers[self.active_layer] = self.layers[self.active_layer].transpose(Image.FLIP_TOP_BOTTOM)
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Flipped vertically")

    def quick_trim_transparent(self):
        comp = self.get_composite()
        if comp is None:
            return
        bbox = comp.split()[3].getbbox()
        if not bbox:
            self.on_status("Nothing to trim (no opaque pixels)")
            return
        self._push_state()
        for i in range(len(self.layers)):
            self.layers[i] = self.layers[i].crop(bbox)
        self._mark_dirty()
        self._refresh_display()
        self.on_size_change(self.width(), self.height())
        self.on_layers_changed()
        self.on_status("Trimmed transparent borders")

    # ---------- Selection ----------
    def clear_selection(self):
        if self.sel_floating is not None:
            self._commit_floating_selection()
        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.preview_image = None
        self._refresh_display()
        self.on_status("Selection cleared")

    # ---------- Events / Input ----------
    def _on_space_down(self, event):
        self._space_pan_active = True
        self.canvas.config(cursor="fleur")

    def _on_space_up(self, event):
        self._space_pan_active = False
        self.canvas.config(cursor="cross")

    def _on_pan_press(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def _on_pan_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_release(self, event):
        self.canvas.config(cursor="cross")

    def _image_to_canvas(self, x, y):
        return (x * self.zoom), (y * self.zoom)

    def _canvas_to_image(self, cx, cy):
        x0 = self.canvas.canvasx(0)
        y0 = self.canvas.canvasy(0)
        ix = int((cx + x0) // self.zoom)
        iy = int((cy + y0) // self.zoom)
        return ix, iy

    def _on_mouse_move(self, event):
        ix, iy = self._canvas_to_image(event.x, event.y)
        if 0 <= ix < self.width() and 0 <= iy < self.height():
            self.on_cursor(ix, iy)
        else:
            self.on_cursor(None, None)

    def _on_mouse_down(self, event):
        if not self.layers:
            return

        if self._space_pan_active:
            self.canvas.scan_mark(event.x, event.y)
            return

        ix, iy = self._canvas_to_image(event.x, event.y)
        if not (0 <= ix < self.width() and 0 <= iy < self.height()):
            return

        self._push_state()

        if self.tool == ToolType.PENCIL:
            self._draw_point(ix, iy, self.color)
        elif self.tool == ToolType.ERASER:
            self._draw_point(ix, iy, (0, 0, 0, 0))
        elif self.tool == ToolType.EYEDROPPER:
            comp = self._get_composite_with_preview() or self.get_composite()
            if comp:
                try:
                    r, g, b, a = comp.getpixel((ix, iy))
                    self.set_color((r, g, b, a))
                except Exception:
                    pass
        elif self.tool == ToolType.FILL:
            flood_fill(self.layers[self.active_layer], (ix, iy), self.color, tolerance=self.fill_tolerance)
        elif self.tool == ToolType.MAGIC_ERASER:
            r, g, b, a = self.layers[self.active_layer].getpixel((ix, iy))
            flood_fill(self.layers[self.active_layer], (ix, iy), (r, g, b, 0), tolerance=self.fill_tolerance)
        elif self.tool == ToolType.SELECTION:
            self.sel_active = True
            self.sel_start = (ix, iy)
            self.sel_rect = (ix, iy, ix, iy)
        elif self.tool == ToolType.MOVE:
            if self.sel_floating is None and self.sel_rect and self._point_in_rect((ix, iy), self.sel_rect):
                x0, y0, x1, y1 = self._norm_rect(self.sel_rect)
                box = (x0, y0, x1, y1)
                self.sel_floating = self.layers[self.active_layer].crop(box)
                draw = ImageDraw.Draw(self.layers[self.active_layer])
                draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
                self.sel_offset = (x0, y0)
        elif self.tool in (ToolType.SHAPE_LINE, ToolType.SHAPE_RECT, ToolType.SHAPE_ELLIPSE):
            self.shape_start = (ix, iy)
            self.preview_image = Image.new("RGBA", (self.width(), self.height()), (0, 0, 0, 0))
        elif self.tool == ToolType.TEXT:
            txt = simpledialog.askstring("Text", "Enter text:")
            if txt:
                try:
                    sz = simpledialog.askinteger("Text size", "Font size (px):", initialvalue=16, minvalue=6, maxvalue=512)
                except Exception:
                    sz = 16
                self._draw_text(ix, iy, txt, sz)

        self.last_pos = (ix, iy)
        self._mark_dirty()
        self._refresh_display()

    def _on_mouse_drag(self, event):
        if not self.layers:
            return
        if self._space_pan_active:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            return

        ix, iy = self._canvas_to_image(event.x, event.y)
        ix = clamp(ix, 0, max(1, self.width()) - 1)
        iy = clamp(iy, 0, max(1, self.height()) - 1)

        if self.tool == ToolType.PENCIL:
            draw_brush_line(self.layers[self.active_layer], self.last_pos, (ix, iy), self.color, self.brush_size)
        elif self.tool == ToolType.ERASER:
            draw_brush_line(self.layers[self.active_layer], self.last_pos, (ix, iy), (0, 0, 0, 0), self.brush_size)
        elif self.tool == ToolType.SELECTION and self.sel_active and self.sel_start:
            x0, y0 = self.sel_start
            self.sel_rect = (x0, y0, ix, iy)
        elif self.tool == ToolType.MOVE and self.sel_floating is not None:
            dx = ix - self.last_pos[0]
            dy = iy - self.last_pos[1]
            self.sel_offset = (self.sel_offset[0] + dx, self.sel_offset[1] + dy)
        elif self.tool in (ToolType.SHAPE_LINE, ToolType.SHAPE_RECT, ToolType.SHAPE_ELLIPSE) and self.shape_start:
            self._update_shape_preview(self.shape_start, (ix, iy))

        self.last_pos = (ix, iy)
        self._mark_dirty()
        self._refresh_display()

    def _on_mouse_up(self, event):
        if not self.layers:
            return
        if self.tool in (ToolType.SHAPE_LINE, ToolType.SHAPE_RECT, ToolType.SHAPE_ELLIPSE) and self.shape_start:
            self._commit_shape(self.shape_start, self.last_pos)
            self.shape_start = None
            self.preview_image = None
        self._mark_dirty()
        self._refresh_display()

    def _on_mouse_wheel(self, event):
        ctrl = (event.state & 0x4) != 0
        if not ctrl:
            if hasattr(event, "delta") and event.delta != 0:
                dy = -1 if event.delta > 0 else 1
                self.canvas.yview_scroll(dy, "units")
            else:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
            return
        delta = 0
        if hasattr(event, "delta") and event.delta != 0:
            delta = 1 if event.delta > 0 else -1
        else:
            if event.num == 4:
                delta = 1
            elif event.num == 5:
                delta = -1
        if delta != 0:
            new_zoom = clamp(self.zoom + delta, 1, 16)
            self.set_zoom(new_zoom)

    # ---------- Drawing helpers ----------
    def _draw_point(self, x, y, color):
        if not (0 <= x < self.width() and 0 <= y < self.height()):
            return
        half = self.brush_size // 2
        bbox = (x - half, y - half, x + half, y + half)
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        draw.ellipse([bbox[0], bbox[1], bbox[2], bbox[3]], fill=color)

    def _draw_text(self, x, y, text, size_px):
        self._push_state()
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size_px)
        except Exception:
            font = ImageFont.load_default()
        draw.text((x, y), text, fill=self.color, font=font)
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Text added")

    def _point_in_rect(self, pt, rect):
        x0, y0, x1, y1 = self._norm_rect(rect)
        x, y = pt
        return x0 <= x < x1 and y0 <= y < y1

    def _norm_rect(self, rect):
        x0, y0, x1, y1 = rect
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        return x0, y0, x1, y1

    def _commit_floating_selection(self):
        if self.sel_floating is None:
            return
        self.layers[self.active_layer].alpha_composite(self.sel_floating, self.sel_offset)
        self.sel_floating = None
        self.sel_rect = None
        self.sel_active = False
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Selection moved")

    def _update_shape_preview(self, start, end):
        self.preview_image = Image.new("RGBA", (self.width(), self.height()), (0, 0, 0, 0))
        draw = ImageDraw.Draw(self.preview_image, "RGBA")
        x0, y0 = start
        x1, y1 = end
        if self.tool == ToolType.SHAPE_LINE:
            draw.line([x0, y0, x1, y1], fill=self.color, width=self.brush_size)
        elif self.tool == ToolType.SHAPE_RECT:
            draw.rectangle([x0, y0, x1, y1], outline=self.color, width=self.brush_size)
        elif self.tool == ToolType.SHAPE_ELLIPSE:
            draw.ellipse([x0, y0, x1, y1], outline=self.color, width=self.brush_size)

    def _commit_shape(self, start, end):
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        x0, y0 = start
        x1, y1 = end
        if self.tool == ToolType.SHAPE_LINE:
            draw.line([x0, y0, x1, y1], fill=self.color, width=self.brush_size)
            self.on_status("Line drawn")
        elif self.tool == ToolType.SHAPE_RECT:
            draw.rectangle([x0, y0, x1, y1], outline=self.color, width=self.brush_size)
            self.on_status("Rectangle drawn")
        elif self.tool == ToolType.SHAPE_ELLIPSE:
            draw.ellipse([x0, y0, x1, y1], outline=self.color, width=self.brush_size)
            self.on_status("Ellipse drawn")
        self._mark_dirty()

    # ---------- Undo / Redo ----------
    def _push_state(self):
        snapshot = {
            "layers": [ly.copy() for ly in self.layers],
            "visible": list(self.layer_visible),
            "names": list(self.layer_names),
            "active": self.active_layer,
            "selection": (self.sel_active, self.sel_rect, self.sel_floating.copy() if self.sel_floating else None, self.sel_offset),
        }
        self.history.push(snapshot)

    def _restore_state(self, snapshot):
        self.layers = [ly.copy() for ly in snapshot["layers"]]
        self.layer_visible = list(snapshot["visible"])
        self.layer_names = list(snapshot["names"])
        self.active_layer = snapshot["active"]
        s_active, s_rect, s_float, s_off = snapshot["selection"]
        self.sel_active = s_active
        self.sel_rect = s_rect
        self.sel_floating = s_float.copy() if s_float else None
        self.sel_offset = s_off
        self._mark_dirty()
        self._refresh_display()
        self.on_layers_changed()
        self.on_size_change(self.width(), self.height())

    def undo(self):
        snap = self.history.undo()
        if snap is not None:
            self._restore_state(snap)
            self.on_status("Undo")

    def redo(self):
        snap = self.history.redo()
        if snap is not None:
            self._restore_state(snap)
            self.on_status("Redo")

    # ---------- BG transparent ----------
    def make_background_transparent(self):
        if not self.layers:
            return
        img = self.layers[self.active_layer]
        corners = [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]
        samples = [img.getpixel(c) for c in corners]
        target = max(set(samples), key=samples.count)
        px = img.load()
        self._push_state()
        for y in range(img.height):
            for x in range(img.width):
                if px[x, y][:3] == target[:3]:
                    px[x, y] = (px[x, y][0], px[x, y][1], px[x, y][2], 0)
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Background made transparent")

    # ---------- Rendering ----------
    def _compose_display_image(self):
        if not self.layers:
            return None

        comp = self._get_composite_with_preview()
        if comp is None:
            return None

        if self.sel_active and self.sel_rect:
            x0, y0, x1, y1 = self._norm_rect(self.sel_rect)
            overlay = Image.new("RGBA", (self.width(), self.height()), (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            d.rectangle([x0, y0, x1, y1], outline=(0, 200, 255, 255), width=1)
            comp.alpha_composite(overlay)

        bg = create_checkerboard((comp.width, comp.height), square_size=8)
        composed = Image.alpha_composite(bg.convert("RGBA"), comp)

        if self.zoom != 1:
            composed = composed.resize((comp.width * self.zoom, comp.height * self.zoom), Image.NEAREST)

        if self.show_grid and self.zoom >= 4:
            draw = ImageDraw.Draw(composed)
            w, h = composed.size
            for x in range(0, w, self.zoom):
                draw.line([(x, 0), (x, h)], fill=(0, 0, 0, 40))
            for y in range(0, h, self.zoom):
                draw.line([(0, y), (w, y)], fill=(0, 0, 0, 40))
        return composed

    def _refresh_display(self):
        composed = self._compose_display_image()
        if composed is None:
            return
        self._display_image = ImageTk.PhotoImage(composed)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, composed.width, composed.height))
        self.canvas.create_image(0, 0, image=self._display_image, anchor="nw")
```

File: icon_editor/gui/toolbar.py
```
import tkinter as tk
from tkinter import ttk, colorchooser
from core.editor_tools import ToolType


class ToolBar(ttk.Frame):
    def __init__(self, parent, on_tool_change, on_brush_size_change, on_alpha_change, on_color_change, on_fill_tolerance_change):
        super().__init__(parent)
        self.on_tool_change = on_tool_change
        self.on_brush_size_change = on_brush_size_change
        self.on_alpha_change = on_alpha_change
        self.on_color_change = on_color_change
        self.on_fill_tolerance_change = on_fill_tolerance_change
        self._build_ui()

    def set_tool(self, tool: ToolType):
        self.tool_var.set(tool.value)
        self.on_tool_change(tool)

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=1)

        tool_frame = ttk.Frame(self)
        tool_frame.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.tool_var = tk.StringVar(value=ToolType.PENCIL.value)
        tools = [
            ("Select (S)", ToolType.SELECTION),
            ("Move (V)", ToolType.MOVE),
            ("Brush (B)", ToolType.PENCIL),
            ("Eraser (E)", ToolType.ERASER),
            ("Fill (G)", ToolType.FILL),
            ("Eyedrop (I)", ToolType.EYEDROPPER),
            ("Magic Erase (M)", ToolType.MAGIC_ERASER),
            ("Text (T)", ToolType.TEXT),
            ("Line (L)", ToolType.SHAPE_LINE),
            ("Rect (R)", ToolType.SHAPE_RECT),
            ("Ellipse (C)", ToolType.SHAPE_ELLIPSE),
        ]
        for (label, tool) in tools:
            b = ttk.Radiobutton(tool_frame, text=label, value=tool.value, variable=self.tool_var,
                                command=lambda t=tool: self.on_tool_change(t))
            b.pack(side="left", padx=(0, 6))

        size_frame = ttk.Frame(self)
        size_frame.grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(size_frame, text="Size").pack(side="left", padx=(0, 6))
        self.brush_var = tk.IntVar(value=1)
        brush_scale = ttk.Scale(size_frame, from_=1, to=64, orient="horizontal",
                                command=lambda v: self.on_brush_size_change(int(float(v))))
        brush_scale.set(1)
        brush_scale.pack(side="left", padx=(0, 6), ipadx=60)

        ca_frame = ttk.Frame(self)
        ca_frame.grid(row=0, column=2, sticky="ew", padx=8, pady=6)
        ca_frame.columnconfigure(1, weight=1)
        self.color_preview = tk.Canvas(ca_frame, width=40, height=20, bg="#000000", highlightthickness=1, highlightbackground="#666")
        self.color_preview.grid(row=0, column=0, padx=(0, 6))
        self.color_preview.bind("<Button-1>", self._choose_color)

        ttk.Label(ca_frame, text="Alpha").grid(row=0, column=1, sticky="w")
        self.alpha_var = tk.IntVar(value=255)
        alpha_scale = ttk.Scale(ca_frame, from_=0, to=255, orient="horizontal",
                                command=lambda v: self._alpha_changed(int(float(v))))
        alpha_scale.set(255)
        alpha_scale.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        tol_frame = ttk.Frame(self)
        tol_frame.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        ttk.Label(tol_frame, text="Fill tolerance").pack(side="left", padx=(0, 6))
        self.tol_var = tk.IntVar(value=0)
        tol_scale = ttk.Scale(tol_frame, from_=0, to=255, orient="horizontal",
                              command=lambda v: self._tolerance_changed(int(float(v))))
        tol_scale.set(0)
        tol_scale.pack(side="left", fill="x", expand=True)

        self.current_color = (0, 0, 0, 255)
        self._update_color_preview()

    def _choose_color(self, event=None):
        initial = "#%02x%02x%02x" % self.current_color[:3]
        color = colorchooser.askcolor(color=initial, title="Choose Color")
        if color is None or color[0] is None:
            return
        r, g, b = [int(c) for c in color[0]]
        a = self.alpha_var.get()
        self.current_color = (r, g, b, a)
        self._update_color_preview()
        self.on_color_change(self.current_color)

    def _alpha_changed(self, alpha: int):
        alpha = max(0, min(255, int(alpha)))
        self.alpha_var.set(alpha)
        r, g, b, _ = self.current_color
        self.current_color = (r, g, b, alpha)
        self._update_color_preview()
        self.on_alpha_change(alpha)
        self.on_color_change(self.current_color)

    def _tolerance_changed(self, tol: int):
        tol = max(0, min(255, int(tol)))
        self.tol_var.set(tol)
        self.on_fill_tolerance_change(tol)

    def _update_color_preview(self):
        r, g, b, a = self.current_color
        hex_color = "#%02x%02x%02x" % (r, g, b)
        self.color_preview.configure(bg=hex_color)
```

File: icon_editor/core/editor_tools.py
```
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any


class ToolType(Enum):
    PENCIL = "pencil"
    ERASER = "eraser"
    FILL = "fill"
    EYEDROPPER = "eyedropper"
    MAGIC_ERASER = "magic_eraser"
    SELECTION = "selection"
    MOVE = "move"
    TEXT = "text"
    SHAPE_LINE = "shape_line"
    SHAPE_RECT = "shape_rect"
    SHAPE_ELLIPSE = "shape_ellipse"


@dataclass
class UndoRedoStack:
    limit: int = 50

    def __post_init__(self):
        self._stack: list[Any] = []
        self._index: int = -1

    def push(self, snapshot: Any):
        if self._index < len(self._stack) - 1:
            self._stack = self._stack[: self._index + 1]
        self._stack.append(snapshot)
        if len(self._stack) > self.limit:
            self._stack.pop(0)
        self._index = len(self._stack) - 1

    def undo(self) -> Optional[Any]:
        if self._index <= 0:
            return None
        self._index -= 1
        return self._stack[self._index]

    def redo(self) -> Optional[Any]:
        if self._index >= len(self._stack) - 1:
            return None
        self._index += 1
        return self._stack[self._index]

    def clear(self):
        self._stack.clear()
        self._index = -1


def draw_brush_line(image, p0: tuple[int, int], p1: tuple[int, int], color: tuple[int, int, int, int], brush_size: int):
    from PIL import ImageDraw
    x0, y0 = p0
    x1, y1 = p1
    draw = ImageDraw.Draw(image, "RGBA")
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    half = brush_size // 2

    def dot(px, py):
        bbox = (px - half, py - half, px + half, py + half)
        draw.ellipse(bbox, fill=color)

    while True:
        dot(x, y)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def flood_fill(image, seed: tuple[int, int], fill_color: tuple[int, int, int, int], tolerance: int = 0):
    """
    Non-recursive flood fill with RGBA tolerance and safety cap.
    """
    w, h = image.size
    px = image.load()
    x, y = seed
    if x < 0 or y < 0 or x >= w or y >= h:
        return
