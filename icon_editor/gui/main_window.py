import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
from utils.helpers import human_readable_size
from utils.config import AppConfig

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:
    Image = None
    ImageDraw = None
    ImageTk = None


class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after = None
        self._tip = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")
    def _on_enter(self, _):
        self._schedule()
    def _on_leave(self, _):
        self._cancel()
        self._hide()
    def _schedule(self):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)
    def _cancel(self):
        if self._after:
            try:
                self.widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None
    def _show(self):
        if self._tip:
            return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.winfo_viewable() else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = ttk.Label(tw, text=self.text, relief="solid", padding=(6, 3), borderwidth=1)
        lbl.pack()
    def _hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class IconFactory:
    def __init__(self, size=22):
        self.size = size
        self.cache = {}
    def _img(self):
        return Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
    def _photo(self, im):
        return ImageTk.PhotoImage(im)
    def _key(self, name):
        return f"{name}:{self.size}"
    def get(self, name):
        if Image is None:
            # Fallback: no PIL
            return None
        k = self._key(name)
        if k in self.cache:
            return self.cache[k]
        draw = None
        im = self._img()
        d = ImageDraw.Draw(im)
        s = self.size
        c = (30, 30, 30, 255)
        a = (0, 0, 0, 0)
        if name == "select":
            d.rectangle([3, 3, s - 4, s - 4], outline=(40, 130, 255, 255), width=2)
            d.line([(3, 7), (s - 4, 7)], fill=(40, 130, 255, 255))
            d.line([(7, 3), (7, s - 4)], fill=(40, 130, 255, 255))
        elif name == "move":
            d.polygon([(s//2, 3), (s//2-3, 8), (s//2+3, 8)], fill=(0, 0, 0))
            d.polygon([(s//2, s-3), (s//2-3, s-8), (s//2+3, s-8)], fill=(0, 0, 0))
            d.polygon([(3, s//2), (8, s//2-3), (8, s//2+3)], fill=(0, 0, 0))
            d.polygon([(s-3, s//2), (s-8, s//2-3), (s-8, s//2+3)], fill=(0, 0, 0))
        elif name == "brush":
            d.line([(4, s-5), (s-5, 4)], fill=(0, 0, 0), width=3)
            d.ellipse([3, s-7, 8, s-2], fill=(50, 50, 50))
        elif name == "eraser":
            d.polygon([(4, s-6), (s-10, 4), (s-4, 10), (10, s-4)], fill=(230, 230, 230), outline=(120, 120, 120))
        elif name == "fill":
            d.polygon([(5, 5), (s-9, 5), (s-12, 12)], fill=(120, 120, 120))
            d.polygon([(s-9, 5), (s-5, 9), (s-12, 12)], fill=(160, 160, 160))
            d.polygon([(s-12, 12), (s-5, 19), (5, 19)], fill=(0, 120, 220))
        elif name == "eyedrop":
            d.line([(5, s-6), (s-5, 6)], fill=(0, 0, 0), width=2)
            d.ellipse([s-8, 3, s-3, 8], outline=(0, 0, 0), fill=(0, 150, 255))
        elif name == "magic":
            d.line([(4, s-5), (s-5, 4)], fill=(0, 0, 0), width=2)
            for off in (-4, 0, 4):
                d.line([(s//2+off, 4), (s//2+off, 8)], fill=(255, 200, 0), width=1)
                d.line([(s//2+off, s-4), (s//2+off, s-8)], fill=(255, 200, 0), width=1)
        elif name == "text":
            d.text((6, 3), "T", fill=(0, 0, 0))
        elif name == "line":
            d.line([(4, s-5), (s-5, 4)], fill=(0, 0, 0), width=2)
        elif name == "rect":
            d.rectangle([4, 4, s-5, s-5], outline=(0, 0, 0), width=2)
        elif name == "ellipse":
            d.ellipse([4, 4, s-5, s-5], outline=(0, 0, 0), width=2)
        elif name == "open":
            d.rectangle([3, 9, s-4, s-4], outline=(0, 0, 0))
            d.polygon([(4, 9), (9, 4), (s-6, 4), (s-11, 9)], fill=(200, 200, 200), outline=(0, 0, 0))
        elif name == "save":
            d.rectangle([4, 4, s-4, s-4], outline=(0, 0, 0), fill=(220, 220, 220))
            d.rectangle([6, 6, s-6, 10], fill=(0, 0, 0))
        elif name == "export":
            d.rectangle([4, 6, s-6, s-4], outline=(0, 0, 0))
            d.polygon([(s-6, 10), (s-2, 10), (s-4, 6)], fill=(0, 120, 220))
        elif name == "grid":
            for i in range(4, s-3, 4):
                d.line([(i, 3), (i, s-3)], fill=(0, 0, 0))
                d.line([(3, i), (s-3, i)], fill=(0, 0, 0))
        elif name == "fit":
            d.rectangle([6, 6, s-6, s-6], outline=(0, 0, 0))
            d.line([(3, 3), (9, 3)], fill=(0, 0, 0))
            d.line([(3, 3), (3, 9)], fill=(0, 0, 0))
        elif name == "reset":
            d.arc([4, 4, s-4, s-4], start=30, end=330, fill=(0, 0, 0), width=2)
            d.polygon([(s-6, 7), (s-2, 7), (s-4, 3)], fill=(0, 0, 0))
        else:
            d.rectangle([2, 2, s-3, s-3], outline=(0, 0, 0))
        ph = self._photo(im)
        self.cache[k] = ph
        return ph


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Icon Creator & Editor")
        self.geometry("1400x900")
        self.minsize(1100, 720)

        # Config
        self.config_mgr = AppConfig()
        self.recent_files = self.config_mgr.recent_files.copy()
        self.theme = self.config_mgr.theme or "System"

        # Theme
        self.style = ttk.Style()
        self._apply_theme(self.theme)

        # State
        self.current_file: Path | None = None
        self._pending_zoom = None
        self.current_tool = ToolType.PENCIL
        self.tool_buttons: dict[tk.Button, ToolType] = {}
        self.current_color = (0, 0, 0, 255)

        # Build order
        self._build_menu()
        self._build_statusbar()
        self._build_toolbar()
        self._build_canvas()

        # Init canvas after widgets
        self.after_idle(lambda: self.canvas_editor.new_blank((256, 256)))
        self._update_status("Ready")

        # Shortcuts
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    # ---------------- Theming ----------------
    def _apply_theme(self, mode: str):
        try:
            if mode.lower() == "dark":
                self.style.theme_use("clam")
                dark_bg = "#2b2b2b"
                fg = "#e8e8e8"
                self.configure(bg=dark_bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton"]:
                    self.style.configure(elem, background=dark_bg, foreground=fg)
                self.style.configure("TEntry", fieldbackground="#3a3a3a", foreground=fg)
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

    # ---------------- Menu ----------------
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
        edit_menu.add_command(label="Invert Colors", command=self._quick_invert)
        edit_menu.add_command(label="Grayscale", command=self._quick_grayscale)
        edit_menu.add_command(label="Flip Horizontal", command=self._quick_flip_h)
        edit_menu.add_command(label="Flip Vertical", command=self._quick_flip_v)
        edit_menu.add_command(label="Trim Transparent", command=self._quick_trim)
        edit_menu.add_separator()
        edit_menu.add_command(label="Deselect (Esc)", command=self._deselect)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label="Show Grid", variable=tk.BooleanVar(value=False), command=self._toggle_grid)
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

    # ---------------- Toolbar (Ribbon-like single row) ----------------
    def _build_toolbar(self):
        self.toolbar = ttk.Frame(self, padding=(6, 6))
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)

        icons = IconFactory(size=22)

        def add_btn(parent, icon_name, cmd, tip):
            img = icons.get(icon_name)
            btn = tk.Button(parent, image=img, width=28, height=28, command=cmd, relief="raised")
            btn.image = img
            btn.pack(side="left", padx=2)
            Tooltip(btn, tip)
            return btn

        # File group
        file_grp = ttk.Frame(self.toolbar)
        file_grp.pack(side="left", padx=(0, 8))
        add_btn(file_grp, "open", self.open_image, "Open Image (Ctrl+O)")
        add_btn(file_grp, "save", self.save_png, "Save PNG (Ctrl+S)")
        add_btn(file_grp, "export", self.export_ico, "Export ICO (Ctrl+E)")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        # Tools group
        tools_grp = ttk.Frame(self.toolbar)
        tools_grp.pack(side="left", padx=(0, 8))
        self.tool_buttons.clear()
        for name, tool, tip in [
            ("select", ToolType.SELECTION, "Selection (S)"),
            ("move", ToolType.MOVE, "Move (V)"),
            ("brush", ToolType.PENCIL, "Brush (B)"),
            ("eraser", ToolType.ERASER, "Eraser (E)"),
            ("fill", ToolType.FILL, "Fill (G)"),
            ("eyedrop", ToolType.EYEDROPPER, "Eyedropper (I)"),
            ("magic", ToolType.MAGIC_ERASER, "Magic Eraser (M)"),
            ("text", ToolType.TEXT, "Text (T)"),
            ("line", ToolType.SHAPE_LINE, "Line (L)"),
            ("rect", ToolType.SHAPE_RECT, "Rectangle (R)"),
            ("ellipse", ToolType.SHAPE_ELLIPSE, "Ellipse (C)"),
        ]:
            btn = add_btn(tools_grp, name, lambda t=tool: self._select_tool(t), tip)
            self.tool_buttons[btn] = tool
        self._update_tool_visuals()

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        # Brush size
        size_grp = ttk.Frame(self.toolbar)
        size_grp.pack(side="left", padx=(0, 8))
        ttk.Label(size_grp, text="Size").pack(side="left", padx=(0, 4))
        self.brush_size_var = tk.IntVar(value=5)
        size_scale = ttk.Scale(size_grp, from_=1, to=64, orient="horizontal",
                               command=lambda v: self._on_brush_size_change(int(float(v))))
        size_scale.set(5)
        size_scale.pack(side="left", ipadx=40)
        Tooltip(size_scale, "Brush Size")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        # Color + alpha + tolerance
        color_grp = ttk.Frame(self.toolbar)
        color_grp.pack(side="left", padx=(0, 8))
        ttk.Label(color_grp, text="Color").pack(side="left", padx=(0, 4))
        self.color_display = tk.Canvas(color_grp, width=30, height=18, bg="#000000", highlightthickness=1)
        self.color_display.pack(side="left")
        self.color_display.bind("<Button-1>", self._pick_color)
        Tooltip(self.color_display, "Pick Color")
        ttk.Label(color_grp, text="Alpha").pack(side="left", padx=(10, 4))
        self.alpha_var = tk.IntVar(value=255)
        alpha_scale = ttk.Scale(color_grp, from_=0, to=255, orient="horizontal",
                                command=lambda v: self._on_alpha_change(int(float(v))))
        alpha_scale.set(255)
        alpha_scale.pack(side="left", ipadx=30)
        Tooltip(alpha_scale, "Alpha (opacity 0–255)")
        ttk.Label(color_grp, text="Tol").pack(side="left", padx=(10, 4))
        self.tol_var = tk.IntVar(value=0)
        tol_scale = ttk.Scale(color_grp, from_=0, to=100, orient="horizontal",
                              command=lambda v: self.canvas_editor.set_fill_tolerance(int(float(v))))
        tol_scale.set(0)
        tol_scale.pack(side="left", ipadx=30)
        Tooltip(tol_scale, "Fill Tolerance")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        # View: grid, fit, reset, zoom
        view_grp = ttk.Frame(self.toolbar)
        view_grp.pack(side="left", padx=(0, 8))
        add_btn(view_grp, "grid", self._toggle_grid, "Toggle Grid")
        add_btn(view_grp, "fit", self._fit_to_window, "Fit to Window (F)")
        add_btn(view_grp, "reset", self._reset_scroll, "Reset Scroll")
        ttk.Label(view_grp, text="Zoom").pack(side="left", padx=(10, 4))
        self.zoom_var = tk.IntVar(value=4)
        zoom_scale = ttk.Scale(view_grp, from_=1, to=16, orient="horizontal",
                               command=lambda v: self._set_zoom_from_scale(int(float(v))))
        zoom_scale.set(4)
        zoom_scale.pack(side="left", ipadx=40)
        Tooltip(zoom_scale, "Zoom 1x–16x")

    def _update_tool_visuals(self):
        for btn, t in self.tool_buttons.items():
            btn.config(relief="sunken" if t == self.current_tool else "raised")

    # ---------------- Canvas ----------------
    def _build_canvas(self):
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Defer callbacks to avoid construction-time races
        self.canvas_editor = CanvasEditor(
            self.main_frame,
            on_status=lambda msg: self.after_idle(lambda: self._update_status(msg)),
            on_cursor=lambda x, y: self.after_idle(lambda: self._update_cursor(x, y)),
            on_size_change=lambda w, h: self.after_idle(lambda: self._update_image_info(w, h)),
            on_zoom_change=lambda z: self.after_idle(lambda: self._update_zoom_info(z)),
            on_layers_changed=lambda: self.after_idle(self._refresh_layers_ui),
            on_color_ui=lambda rgba: self.after_idle(lambda: self._set_ui_color(rgba))  # eyedropper updates UI
        )
        self.canvas_editor.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # ---------------- Status bar ----------------
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

    # ---------------- Update handlers ----------------
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
            # Can be added to a tooltip if desired
        # else: keep quiet

    def _update_zoom_info(self, zoom):
        if hasattr(self, "zoom_label"):
            self.zoom_label.config(text=f"Zoom: {zoom}x")
        else:
            self._pending_zoom = zoom

    def _set_ui_color(self, rgba):
        self.current_color = tuple(rgba)
        r, g, b, _ = self.current_color
        self.color_display.config(bg=f"#{r:02x}{g:02x}{b:02x}")

    # ---------------- Toolbar bridges ----------------
    def _select_tool(self, tool: ToolType):
        self.current_tool = tool
        self._update_tool_visuals()
        if hasattr(self, "canvas_editor"):
            self.canvas_editor.set_tool(tool)

    def _pick_color(self, event=None):
        from tkinter import colorchooser
        color = colorchooser.askcolor(color=f"#{self.current_color[0]:02x}{self.current_color[1]:02x}{self.current_color[2]:02x}")
        if color and color[0]:
            r, g, b = [int(c) for c in color[0]]
            self.current_color = (r, g, b, self.alpha_var.get())
            self.color_display.config(bg=f"#{r:02x}{g:02x}{b:02x}")
            self.canvas_editor.set_color(self.current_color)

    def _on_alpha_change(self, alpha: int):
        r, g, b, _ = self.current_color
        self.current_color = (r, g, b, alpha)
        self.canvas_editor.set_alpha(alpha)
        self.canvas_editor.set_color(self.current_color)

    def _on_brush_size_change(self, size: int):
        self.canvas_editor.set_brush_size(int(size))

    # ---------------- Menu actions ----------------
    def _toggle_grid(self):
        # Toggle internal state based on current label text
        # Better: keep a BooleanVar if you want live check; here we just toggle canvas flag.
        self.canvas_editor.set_grid(not self.canvas_editor.show_grid)

    def _about(self):
        messagebox.showinfo(
            "About",
            "Icon Creator & Editor (Ribbon)\n- Multi-resolution ICO export\n- Paint-like compact toolbar\n- Eyedropper color sync\n- PyInstaller-friendly"
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

    # ---------------- Recent files ----------------
    def _refresh_recent_menu(self):
        # Menubar may call this before canvas exists; safe anyway
        if not hasattr(self, "recent_menu"):
            return
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

    # ---------------- File ops ----------------
    def new_canvas(self):
        dialog = tk.Toplevel(self)
        dialog.title("New Canvas")
        dialog.transient(self)
        dialog.resizable(False, False)
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        w_var = tk.IntVar(value=256)
        h_var = tk.IntVar(value=256)
        ttk.Entry(dialog, textvariable=w_var, width=10).grid(row=0, column=1, padx=10, pady=8)
        ttk.Entry(dialog, textvariable=h_var, width=10).grid(row=1, column=1, padx=10, pady=8)

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
        # Use defaults suitable for Windows icons; the dialog will let user confirm and save.
        comp = self.canvas_editor.get_composite()
        if comp is None:
            messagebox.showinfo("No image", "Create or open an image first.")
            return
        try:
            sizes = [256, 128, 64, 48, 32, 24, 16]
            export_ico_dialog(
                self,
                base_image=comp,
                sizes=sizes,
                resample="Lanczos",
                maintain_aspect=True
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export ICO:\n{e}")

    # -------------------- Undo/Redo --------------------
    def undo(self):
        self.canvas_editor.undo()

    def redo(self):
        self.canvas_editor.redo()

    # -------------------- Selection/Zoom wrappers --------------------
    def _deselect(self):
        self.canvas_editor.clear_selection()

    def make_bg_transparent(self):
        self.canvas_editor.make_background_transparent()

    def _fit_to_window(self):
        self.canvas_editor.fit_to_window()

    def _reset_scroll(self):
        self.canvas_editor.reset_scroll()

    def _set_zoom_from_scale(self, v):
        self.canvas_editor.set_zoom(v)

    # -------------------- Quick actions --------------------
    def _quick_invert(self):
        self.canvas_editor.quick_invert()

    def _quick_grayscale(self):
        self.canvas_editor.quick_grayscale()

    def _quick_flip_h(self):
        self.canvas_editor.quick_flip_h()

    def _quick_flip_v(self):
        self.canvas_editor.quick_flip_v()

    def _quick_trim(self):
        self.canvas_editor.quick_trim_transparent()

    # -------------------- Layers UI (no visible layers widget in compact toolbar;
    # keep a no-op refresh for safety if callbacks fire) --------------------
    def _refresh_layers_ui(self):
        # No layers combobox in the compact toolbar layout; ignore.
        pass


def run_app():
    app = MainWindow()
    app.mainloop()
