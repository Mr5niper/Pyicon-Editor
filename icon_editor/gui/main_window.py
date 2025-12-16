import os
import json
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
    # adjust import path as appropriate
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

        # If zoom update arrives before statusbar is built
        self._pending_zoom = None

        # 1) Menu, 2) Statusbar (so labels exist), 3) Layout (CanvasEditor)
        self._build_menu()
        self._build_statusbar()
        self._build_layout()

        self._update_status("Ready")

        # Shortcuts
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
        
        # Toolbar
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
        
        # Main area frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=2, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Canvas editor (CREATE THIS FIRST!)
        self.canvas_editor = CanvasEditor(
            self.main_frame,
            on_status=self._update_status,
            on_cursor=self._update_cursor,
            on_size_change=self._update_image_info,
            on_zoom_change=self._update_zoom_info,
            on_layers_changed=self._refresh_layers_panel
        )
        self.canvas_editor.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # Side panel (references canvas_editor, so must come AFTER)
        self.side_panel = ttk.Frame(self.main_frame)
        self.side_panel.grid(row=0, column=1, sticky="ns", padx=(5, 10), pady=10)
        self._build_side_panel(self.side_panel)
        
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
        # Apply pending zoom if any
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
        # This can be called before self.canvas_editor is assigned (during construction).
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
        # Guard in case called before side panel is built
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
