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
from utils.helpers import human_readable_size
from utils.config import AppConfig


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Icon Creator & Editor")
        self.geometry("1400x900")
        self.minsize(1200, 700)

        # Config
        self.config_mgr = AppConfig()
        self.recent_files = self.config_mgr.recent_files.copy()
        self.theme = self.config_mgr.theme or "System"

        # Theme
        self.style = ttk.Style()
        self._apply_theme(self.theme)

        # State
        self.current_file: Path | None = None
        self.maintain_aspect = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=False)
        self._pending_zoom = None

        # Ribbon state
        self.current_tool = ToolType.PENCIL
        self.tool_buttons: dict[tk.Button, ToolType] = {}
        self.current_color = (0, 0, 0, 255)

        # Build order: menus -> statusbar -> ribbon -> layout (canvas)
        self._build_menu()
        self._build_statusbar()
        self._build_ribbon()
        self._build_layout()

        # Initialize canvas after UI is ready
        self.after_idle(lambda: self.canvas_editor.new_blank((256, 256)))
        self._update_status("Ready")

        # Shortcuts
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    # -------------------- Theme --------------------
    def _apply_theme(self, mode: str):
        try:
            if mode.lower() == "dark":
                self.style.theme_use("clam")
                dark_bg = "#2b2b2b"
                light_bg = "#3a3a3a"
                fg = "#e8e8e8"
                self.configure(bg=dark_bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton", "TNotebook", "TNotebook.Tab"]:
                    self.style.configure(elem, background=dark_bg, foreground=fg)
                self.style.configure("TEntry", fieldbackground=light_bg, foreground=fg)
            elif mode.lower() == "light":
                self.style.theme_use("clam")
                bg = "#f0f0f0"
                self.configure(bg=bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton", "TNotebook", "TNotebook.Tab"]:
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

    # -------------------- Shortcuts --------------------
    def _bind_shortcuts(self):
        self.bind_all("<Control-o>", lambda e: self.open_image())
        self.bind_all("<Control-s>", lambda e: self.save_png())
        self.bind_all("<Control-e>", lambda e: self.export_ico())
        self.bind_all("<Control-n>", lambda e: self.new_canvas())
        self.bind_all("<Control-z>", lambda e: self.canvas_editor.undo())
        self.bind_all("<Control-Shift-Z>", lambda e: self.canvas_editor.redo())
        self.bind_all("<Control-y>", lambda e: self.canvas_editor.redo())
        self.bind_all("<Key-f>", lambda e: self._fit_to_window())
        self.bind_all("<Escape>", lambda e: self._deselect())

        # Tools
        self.bind_all("<Key-s>", lambda e: self._select_tool(ToolType.SELECTION))
        self.bind_all("<Key-v>", lambda e: self._select_tool(ToolType.MOVE))
        self.bind_all("<Key-b>", lambda e: self._select_tool(ToolType.PENCIL))
        self.bind_all("<Key-e>", lambda e: self._select_tool(ToolType.ERASER))
        self.bind_all("<Key-g>", lambda e: self._select_tool(ToolType.FILL))
        self.bind_all("<Key-i>", lambda e: self._select_tool(ToolType.EYEDROPPER))
        self.bind_all("<Key-m>", lambda e: self._select_tool(ToolType.MAGIC_ERASER))
        self.bind_all("<Key-t>", lambda e: self._select_tool(ToolType.TEXT))
        self.bind_all("<Key-l>", lambda e: self._select_tool(ToolType.SHAPE_LINE))
        self.bind_all("<Key-r>", lambda e: self._select_tool(ToolType.SHAPE_RECT))
        self.bind_all("<Key-c>", lambda e: self._select_tool(ToolType.SHAPE_ELLIPSE))

    # -------------------- Menu --------------------
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
        edit_menu.add_command(label="Deselect (Esc)", command=self._deselect)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label="Show Grid", variable=self.show_grid, command=self._toggle_grid)
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

    # -------------------- Ribbon (Notebook tabs) --------------------
    def _build_ribbon(self):
        self.ribbon = ttk.Notebook(self)
        self.ribbon.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        self.columnconfigure(0, weight=1)

        self.tab_home = ttk.Frame(self.ribbon)
        self.tab_view = ttk.Frame(self.ribbon)
        self.tab_export = ttk.Frame(self.ribbon)

        self.ribbon.add(self.tab_home, text="Home")
        self.ribbon.add(self.tab_view, text="View")
        self.ribbon.add(self.tab_export, text="Export")

        # Build each tab
        self._build_tab_home(self.tab_home)
        self._build_tab_view(self.tab_view)
        self._build_tab_export(self.tab_export)

    def _group(self, parent, text):
        f = ttk.LabelFrame(parent, text=text, padding=6)
        f.pack(side="left", padx=(0, 8), pady=2, fill="y")
        return f

    def _build_tab_home(self, tab):
        # File group
        gf = self._group(tab, "File")
        ttk.Button(gf, text="New", width=10, command=self.new_canvas).pack(side="left", padx=2)
        ttk.Button(gf, text="Open", width=10, command=self.open_image).pack(side="left", padx=2)
        ttk.Button(gf, text="Save PNG", width=10, command=self.save_png).pack(side="left", padx=2)
        ttk.Button(gf, text="Export ICO", width=10, command=self.export_ico).pack(side="left", padx=2)

        # Tools group
        tg = self._group(tab, "Tools")
        tools = [
            ("Select", ToolType.SELECTION),
            ("Move", ToolType.MOVE),
            ("Brush", ToolType.PENCIL),
            ("Eraser", ToolType.ERASER),
            ("Fill", ToolType.FILL),
            ("Eyedrop", ToolType.EYEDROPPER),
            ("Magic", ToolType.MAGIC_ERASER),
            ("Text", ToolType.TEXT),
            ("Line", ToolType.SHAPE_LINE),
            ("Rect", ToolType.SHAPE_RECT),
            ("Ellipse", ToolType.SHAPE_ELLIPSE),
        ]
        for label, tool in tools:
            btn = tk.Button(tg, text=label, width=9, command=lambda t=tool: self._select_tool(t),
                            relief="sunken" if tool == self.current_tool else "raised")
            btn.pack(side="left", padx=2)
            self.tool_buttons[btn] = tool

        # Brush group
        sg = self._group(tab, "Brush")
        self.brush_size_var = tk.IntVar(value=5)
        ttk.Scale(sg, from_=1, to=64, orient="horizontal", variable=self.brush_size_var,
                  command=lambda v: self._on_brush_size_change(int(float(v)))).pack(fill="x", padx=6)

        # Color group
        cg = self._group(tab, "Color")
        self.color_display = tk.Canvas(cg, width=42, height=24, bg="#000000", highlightthickness=1)
        self.color_display.pack(padx=4, pady=2, side="left")
        self.color_display.bind("<Button-1>", self._pick_color)

        # Alpha
        ag = self._group(tab, "Alpha")
        self.alpha_var = tk.IntVar(value=255)
        ttk.Scale(ag, from_=0, to=255, orient="horizontal", variable=self.alpha_var,
                  command=lambda v: self._on_alpha_change(int(float(v)))).pack(fill="x", padx=6)

        # Fill tolerance
        fg = self._group(tab, "Fill Tol")
        self.tol_var = tk.IntVar(value=0)
        ttk.Scale(fg, from_=0, to=100, orient="horizontal", variable=self.tol_var,
                  command=lambda v: self.canvas_editor.set_fill_tolerance(int(float(v)))).pack(fill="x", padx=6)

        # Quick Adjust
        qg = self._group(tab, "Adjust")
        ttk.Button(qg, text="Invert", width=10, command=self._quick_invert).pack(side="left", padx=2)
        ttk.Button(qg, text="Gray", width=10, command=self._quick_grayscale).pack(side="left", padx=2)
        ttk.Button(qg, text="Flip H", width=10, command=self._quick_flip_h).pack(side="left", padx=2)
        ttk.Button(qg, text="Flip V", width=10, command=self._quick_flip_v).pack(side="left", padx=2)
        ttk.Button(qg, text="Trim", width=10, command=self._quick_trim).pack(side="left", padx=2)
        ttk.Button(qg, text="BG→Transparent", width=14, command=self.make_bg_transparent).pack(side="left", padx=2)

        # Layers group
        lg = self._group(tab, "Layers")
        self.layers_combo_var = tk.StringVar()
        self.layers_combo = ttk.Combobox(lg, textvariable=self.layers_combo_var, state="readonly", width=22, values=[])
        self.layers_combo.pack(side="left", padx=(4, 4))
        self.layers_combo.bind("<<ComboboxSelected>>", self._on_layer_combo_changed)
        ttk.Button(lg, text="Add", width=6, command=self._layer_add).pack(side="left", padx=2)
        ttk.Button(lg, text="Del", width=6, command=self._layer_delete).pack(side="left", padx=2)
        ttk.Button(lg, text="Up", width=6, command=lambda: self._layer_move(-1)).pack(side="left", padx=2)
        ttk.Button(lg, text="Down", width=6, command=lambda: self._layer_move(1)).pack(side="left", padx=2)
        ttk.Button(lg, text="👁", width=4, command=self._layer_toggle_vis).pack(side="left", padx=2)

    def _build_tab_view(self, tab):
        vg = self._group(tab, "Zoom")
        self.zoom_var = tk.IntVar(value=4)
        ttk.Scale(vg, from_=1, to=16, orient="horizontal",
                  command=lambda v: self._set_zoom_from_scale(int(float(v)))).pack(side="left", padx=8)
        ttk.Button(vg, text="Fit", width=8, command=self._fit_to_window).pack(side="left", padx=4)
        ttk.Button(vg, text="Reset", width=8, command=self._reset_scroll).pack(side="left", padx=4)

        og = self._group(tab, "Options")
        ttk.Checkbutton(og, text="Show Grid", variable=self.show_grid, command=self._toggle_grid).pack(side="left", padx=6)

    def _build_tab_export(self, tab):
        sg = self._group(tab, "Sizes")
        self.size_vars = {}
        sizes = [256, 128, 64, 48, 32, 24, 16]
        # Arrange in two columns to fit ribbon width
        for idx, size in enumerate(sizes):
            var = tk.BooleanVar(value=True)
            r = idx // 4
            c = idx % 4
            cb = ttk.Checkbutton(sg, text=f"{size}×{size}", variable=var)
            cb.grid(row=r, column=c, padx=6, pady=2, sticky="w")
            self.size_vars[size] = var

        ag = self._group(tab, "Algorithm")
        self.resample_combo = ttk.Combobox(ag, values=["Nearest", "Bilinear", "Bicubic", "Lanczos"], state="readonly", width=12)
        self.resample_combo.set("Lanczos")
        self.resample_combo.pack(side="left", padx=6)
        ttk.Checkbutton(ag, text="Maintain Aspect", variable=self.maintain_aspect).pack(side="left", padx=6)

        eg = self._group(tab, "Export")
        ttk.Button(eg, text="Export ICO", width=12, command=self.export_ico).pack(side="left", padx=4)
        ttk.Button(eg, text="Save PNG", width=12, command=self.save_png).pack(side="left", padx=4)

    # -------------------- Layout (canvas + statusbar already built) --------------------
    def _build_layout(self):
        # Separator between ribbon and main content
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")

        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Canvas editor (callbacks deferred via after_idle)
        self.canvas_editor = CanvasEditor(
            self.main_frame,
            on_status=lambda msg: self.after_idle(lambda: self._update_status(msg)),
            on_cursor=lambda x, y: self.after_idle(lambda: self._update_cursor(x, y)),
            on_size_change=lambda w, h: self.after_idle(lambda: self._update_image_info(w, h)),
            on_zoom_change=lambda z: self.after_idle(lambda: self._update_zoom_info(z)),
            on_layers_changed=lambda: self.after_idle(self._refresh_layers_ui)
        )
        self.canvas_editor.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # -------------------- Status bar --------------------
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

    # -------------------- Update handlers --------------------
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
            self.info_label_text = f"Size: {w} x {h} | RGBA | Mem ~ {human_readable_size(sz)}"
        else:
            self.info_label_text = f"Size: {w} x {h} | RGBA"

    def _update_zoom_info(self, zoom):
        if hasattr(self, "zoom_label"):
            self.zoom_label.config(text=f"Zoom: {zoom}x")
        else:
            self._pending_zoom = zoom

    # -------------------- Toolbar bridges --------------------
    def _select_tool(self, tool: ToolType):
        self.current_tool = tool
        for btn, t in self.tool_buttons.items():
            btn.config(relief="sunken" if t == tool else "raised")
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

    # -------------------- Menu actions --------------------
    def _toggle_grid(self):
        self.canvas_editor.set_grid(self.show_grid.get())

    def _about(self):
        messagebox.showinfo(
            "About",
            "Icon Creator & Editor (Ribbon UI)\n"
            "- Multi-resolution ICO export\n"
            "- Drawing, selection, shapes, text\n"
            "- Layers, panning/zoom, recent files"
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

    # -------------------- Recent files --------------------
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

    # -------------------- File ops --------------------
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

    # -------------------- Layers UI --------------------
    def _refresh_layers_ui(self):
        # Update combobox with layer names and visibility marks
        if not hasattr(self, "layers_combo"):
            return
        try:
            layers = self.canvas_editor.get_layer_list()
        except Exception:
            return
        names = []
        for name, vis in layers:
            mark = "👁" if vis else "☐"
            names.append(f"{mark} {name}")
        self.layers_combo["values"] = names
        idx = self.canvas_editor.active_layer_index()
        if 0 <= idx < len(names):
            self.layers_combo.current(idx)

    def _on_layer_combo_changed(self, event):
        idx = self.layers_combo.current()
        if idx >= 0:
            self.canvas_editor.set_active_layer(idx)

    def _layer_add(self):
        self.canvas_editor.layer_add()
        self._refresh_layers_ui()

    def _layer_delete(self):
        self.canvas_editor.layer_delete()
        self._refresh_layers_ui()

    def _layer_move(self, direction):
        self.canvas_editor.layer_move(direction)
        self._refresh_layers_ui()

    def _layer_toggle_vis(self):
        self.canvas_editor.layer_toggle_visibility()
        self._refresh_layers_ui()


def run_app():
    app = MainWindow()
    app.mainloop()
