import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path

from core.image_handler import (
    load_image_with_alpha,
    save_png,
    open_image_dialog,
    save_png_dialog,
)
from core.icon_generator import export_ico_dialog, export_icns_dialog
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

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20

        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        bg = getattr(self.widget.winfo_toplevel(), "_tooltip_bg", "#3a3d41")
        fg = getattr(self.widget.winfo_toplevel(), "_tooltip_fg", "#f1f1f1")
        bd = getattr(self.widget.winfo_toplevel(), "_tooltip_bd", "#5a5f66")

        lbl = tk.Label(
            tw,
            text=self.text,
            bg=bg,
            fg=fg,
            bd=1,
            relief="solid",
            padx=6,
            pady=3,
            highlightthickness=1,
            highlightbackground=bd,
            highlightcolor=bd
        )
        lbl.pack()

    def _hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class IconFactory:
    def __init__(self, size=22, fg=(0, 0, 0, 255)):
        self.size = size
        self.fg = fg
        self.cache = {}

    def _img(self):
        return Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))

    def _photo(self, im):
        return ImageTk.PhotoImage(im)

    def _key(self, name):
        return f"{name}:{self.size}:{self.fg}"

    def get(self, name):
        if Image is None:
            return None

        k = self._key(name)
        if k in self.cache:
            return self.cache[k]

        im = self._img()
        d = ImageDraw.Draw(im)
        s = self.size

        fg = self.fg
        blue = (40, 130, 255, 255)
        gray_dark = (120, 120, 120, 255)
        gray_mid = (160, 160, 160, 255)
        gray_light = (200, 200, 200, 255)
        gray_lighter = (220, 220, 220, 255)
        cyan = (0, 150, 255, 255)
        gold = (255, 200, 0, 255)
        fill_blue = (0, 120, 220, 255)
        brush_tip = (50, 50, 50, 255)
        eraser_fill = (230, 230, 230, 255)

        if name == "select":
            d.rectangle([3, 3, s - 4, s - 4], outline=blue, width=2)
            d.line([(3, 7), (s - 4, 7)], fill=blue)
            d.line([(7, 3), (7, s - 4)], fill=blue)

        elif name == "move":
            d.polygon([(s // 2, 3), (s // 2 - 3, 8), (s // 2 + 3, 8)], fill=fg)
            d.polygon([(s // 2, s - 3), (s // 2 - 3, s - 8), (s // 2 + 3, s - 8)], fill=fg)
            d.polygon([(3, s // 2), (8, s // 2 - 3), (8, s // 2 + 3)], fill=fg)
            d.polygon([(s - 3, s // 2), (s - 8, s // 2 - 3), (s - 8, s // 2 + 3)], fill=fg)

        elif name == "brush":
            d.line([(4, s - 5), (s - 5, 4)], fill=fg, width=3)
            d.ellipse([3, s - 7, 8, s - 2], fill=brush_tip)

        elif name == "eraser":
            d.polygon(
                [(4, s - 6), (s - 10, 4), (s - 4, 10), (10, s - 4)],
                fill=eraser_fill,
                outline=gray_dark
            )

        elif name == "fill":
            d.polygon([(5, 5), (s - 9, 5), (s - 12, 12)], fill=gray_dark)
            d.polygon([(s - 9, 5), (s - 5, 9), (s - 12, 12)], fill=gray_mid)
            d.polygon([(s - 12, 12), (s - 5, 19), (5, 19)], fill=fill_blue)

        elif name == "eyedrop":
            d.line([(5, s - 6), (s - 5, 6)], fill=fg, width=2)
            d.ellipse([s - 8, 3, s - 3, 8], outline=fg, fill=cyan)

        elif name == "magic":
            d.line([(4, s - 5), (s - 5, 4)], fill=fg, width=2)
            for off in (-4, 0, 4):
                d.line([(s // 2 + off, 4), (s // 2 + off, 8)], fill=gold, width=1)
                d.line([(s // 2 + off, s - 4), (s // 2 + off, s - 8)], fill=gold, width=1)

        elif name == "text":
            d.text((6, 3), "T", fill=fg)

        elif name == "line":
            d.line([(4, s - 5), (s - 5, 4)], fill=fg, width=2)

        elif name == "rect":
            d.rectangle([4, 4, s - 5, s - 5], outline=fg, width=2)

        elif name == "ellipse":
            d.ellipse([4, 4, s - 5, s - 5], outline=fg, width=2)

        elif name == "open":
            d.rectangle([3, 9, s - 4, s - 4], outline=fg)
            d.polygon([(4, 9), (9, 4), (s - 6, 4), (s - 11, 9)], fill=gray_light, outline=fg)

        elif name == "save":
            d.rectangle([4, 4, s - 4, s - 4], outline=fg, fill=gray_lighter)
            d.rectangle([6, 6, s - 6, 10], fill=fg)

        elif name == "export":
            d.rectangle([4, 6, s - 6, s - 4], outline=fg)
            d.polygon([(s - 6, 10), (s - 2, 10), (s - 4, 6)], fill=fill_blue)

        elif name == "grid":
            for i in range(4, s - 3, 4):
                d.line([(i, 3), (i, s - 3)], fill=fg)
                d.line([(3, i), (s - 3, i)], fill=fg)

        elif name == "fit":
            d.rectangle([6, 6, s - 6, s - 6], outline=fg)
            d.line([(3, 3), (9, 3)], fill=fg)
            d.line([(3, 3), (3, 9)], fill=fg)

        elif name == "reset":
            d.arc([4, 4, s - 4, s - 4], start=30, end=330, fill=fg, width=2)
            d.polygon([(s - 6, 7), (s - 2, 7), (s - 4, 3)], fill=fg)

        else:
            d.rectangle([2, 2, s - 3, s - 3], outline=fg)

        ph = self._photo(im)
        self.cache[k] = ph
        return ph


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mr5niper's Pyicon Editor and Creator v1.3.0.0")
        self.geometry("1560x910+20+20")
        self.minsize(1350, 720)

        self._set_app_icon()

        self.config_mgr = AppConfig()
        self.recent_files = self.config_mgr.recent_files.copy()
        self.theme = self.config_mgr.theme or "System"

        self._theme_colors = {}
        self._tooltip_bg = "#3a3d41"
        self._tooltip_fg = "#f1f1f1"
        self._tooltip_bd = "#5a5f66"
        self._toolbar_buttons = []
        self._scales = []

        self._menu_buttons = {}
        self._active_popup = None
        self._active_menu_name = None
        self._ignore_next_global_click = False

        self.style = ttk.Style()
        self._apply_theme(self.theme)

        self.current_file: Path | None = None
        self._pending_zoom = None
        self.current_tool = ToolType.PENCIL
        self.tool_buttons: dict[tk.Button, ToolType] = {}
        self.current_color = (0, 0, 0, 255)
        self.shape_fill_var = tk.BooleanVar(value=False)
        self.grid_var = tk.BooleanVar(value=False)

        self._build_menu()
        self._build_statusbar()
        self._build_canvas()
        self._build_toolbar()

        # Leave vertical room for the custom menu row
        self.toolbar.grid_configure(pady=(30, 0))

        self._apply_widget_theme()

        self.after_idle(lambda: self.canvas_editor.new_blank((256, 256)))
        self._update_status("Ready")

        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _set_app_icon(self):
        if hasattr(sys, "_MEIPASS"):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parent.parent.parent

        icon_path = base_path / "icon.ico"

        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception as e:
                print(f"Could not load taskbar icon: {e}")

    def _default_theme_colors(self):
        root_bg = self.cget("bg")
        return {
            "bg": root_bg,
            "panel": root_bg,
            "control": "#f0f0f0",
            "hover": "#e8e8e8",
            "pressed": "#dcdcdc",
            "text": "#111111",
            "muted_text": "#333333",
            "border": "#b8b8b8",
            "accent": "#4a90ff",
            "field": "#ffffff",
            "menu_bg": "#f0f0f0",
            "menu_fg": "#111111",
            "menu_active_bg": "#dfe8f7",
            "menu_active_fg": "#111111",
            "canvas_bg": "#d9d9d9",
            "status_bg": root_bg,
            "tooltip_bg": "#ffffe1",
            "tooltip_fg": "#111111",
            "tooltip_bd": "#a0a0a0",
            "scale_trough": "#ffffff",
            "scale_bg": root_bg,
        }

    def _apply_theme(self, mode: str):
        try:
            mode_l = (mode or "System").lower()

            if mode_l == "dark":
                self.style.theme_use("clam")

                colors = {
                    "bg": "#2f3136",
                    "panel": "#3a3d41",
                    "control": "#44484d",
                    "hover": "#4b5157",
                    "pressed": "#58606a",
                    "text": "#f1f1f1",
                    "muted_text": "#cfcfcf",
                    "border": "#5a5f66",
                    "accent": "#6aa2ff",
                    "field": "#40444b",
                    "menu_bg": "#2f3136",
                    "menu_fg": "#f1f1f1",
                    "menu_active_bg": "#4b5157",
                    "menu_active_fg": "#ffffff",
                    "canvas_bg": "#3b3b3b",
                    "status_bg": "#2b2d31",
                    "tooltip_bg": "#3a3d41",
                    "tooltip_fg": "#f1f1f1",
                    "tooltip_bd": "#5a5f66",
                    "scale_trough": "#40444b",
                    "scale_bg": "#2f3136",
                }

                self._theme_colors = colors
                self._tooltip_bg = colors["tooltip_bg"]
                self._tooltip_fg = colors["tooltip_fg"]
                self._tooltip_bd = colors["tooltip_bd"]

                self.configure(bg=colors["bg"])

                self.style.configure(".", background=colors["bg"], foreground=colors["text"])
                self.style.configure("TFrame", background=colors["bg"])
                self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["text"])
                self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["text"])
                self.style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
                self.style.configure("TCheckbutton", background=colors["bg"], foreground=colors["text"])
                self.style.map(
                    "TCheckbutton",
                    background=[("active", colors["bg"])],
                    foreground=[("active", colors["text"])]
                )

                self.style.configure(
                    "TButton",
                    background=colors["control"],
                    foreground=colors["text"],
                    bordercolor=colors["border"],
                    focusthickness=1,
                    focuscolor=colors["accent"],
                    lightcolor=colors["control"],
                    darkcolor=colors["control"]
                )
                self.style.map(
                    "TButton",
                    background=[("active", colors["hover"]), ("pressed", colors["pressed"])],
                    foreground=[("active", colors["text"]), ("pressed", colors["text"])]
                )

                self.style.configure(
                    "TEntry",
                    fieldbackground=colors["field"],
                    foreground=colors["text"],
                    insertcolor=colors["text"]
                )

                self.style.configure(
                    "Horizontal.TScale",
                    background=colors["scale_bg"],
                    troughcolor=colors["scale_trough"],
                    bordercolor=colors["border"],
                    lightcolor=colors["scale_trough"],
                    darkcolor=colors["scale_trough"]
                )
                self.style.map(
                    "Horizontal.TScale",
                    background=[("active", colors["scale_bg"])],
                    troughcolor=[("active", colors["scale_trough"])]
                )

                self.style.configure(
                    "Vertical.TScrollbar",
                    background=colors["control"],
                    troughcolor=colors["bg"],
                    bordercolor=colors["border"],
                    arrowcolor=colors["text"],
                    lightcolor=colors["control"],
                    darkcolor=colors["control"]
                )
                self.style.map(
                    "Vertical.TScrollbar",
                    background=[("active", colors["hover"]), ("pressed", colors["pressed"])]
                )

                self.style.configure(
                    "Horizontal.TScrollbar",
                    background=colors["control"],
                    troughcolor=colors["bg"],
                    bordercolor=colors["border"],
                    arrowcolor=colors["text"],
                    lightcolor=colors["control"],
                    darkcolor=colors["control"]
                )
                self.style.map(
                    "Horizontal.TScrollbar",
                    background=[("active", colors["hover"]), ("pressed", colors["pressed"])]
                )

                self.style.configure("TSeparator", background=colors["border"])

            elif mode_l == "light":
                self.style.theme_use("clam")
                bg = "#f0f0f0"
                self.configure(bg=bg)
                for elem in ["TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TButton", "TMenubutton"]:
                    self.style.configure(elem, background=bg, foreground="#111")
                # reset the checkbutton hover state in light mode
                self.style.map(
                    "TCheckbutton",
                    background=[("active", bg)],
                    foreground=[("active", "#111")]
                )                
                self.style.configure("TEntry", fieldbackground="#ffffff", foreground="#111")
                self.style.configure(
                    "Horizontal.TScale",
                    background="#f0f0f0",
                    troughcolor="#ffffff",
                    bordercolor="#b8b8b8",
                    lightcolor="#ffffff",
                    darkcolor="#ffffff"
                )
                self.style.map(
                    "Horizontal.TScale",
                    background=[("active", "#f0f0f0")],
                    troughcolor=[("active", "#ffffff")]
                )
                self.style.configure(
                    "Vertical.TScrollbar",
                    background="#f0f0f0",
                    troughcolor="#f0f0f0",
                    bordercolor="#b8b8b8",
                    arrowcolor="#111111",
                    lightcolor="#f0f0f0",
                    darkcolor="#f0f0f0"
                )
                self.style.configure(
                    "Horizontal.TScrollbar",
                    background="#f0f0f0",
                    troughcolor="#f0f0f0",
                    bordercolor="#b8b8b8",
                    arrowcolor="#111111",
                    lightcolor="#f0f0f0",
                    darkcolor="#f0f0f0"
                )
                self.style.map("TButton", background=[("active", "#e8e8e8"), ("pressed", "#dcdcdc")], foreground=[("active", "#111111"), ("pressed", "#111111")])
                self.style.map("Vertical.TScrollbar", background=[("active", "#e8e8e8"), ("pressed", "#dcdcdc")])
                self.style.map("Horizontal.TScrollbar", background=[("active", "#e8e8e8"), ("pressed", "#dcdcdc")])

                self._theme_colors = {
                    "bg": "#f0f0f0",
                    "panel": "#f6f6f6",
                    "control": "#ffffff",
                    "hover": "#e8e8e8",
                    "pressed": "#dcdcdc",
                    "text": "#111111",
                    "muted_text": "#333333",
                    "border": "#b8b8b8",
                    "accent": "#4a90ff",
                    "field": "#ffffff",
                    "menu_bg": "#f0f0f0",
                    "menu_fg": "#111111",
                    "menu_active_bg": "#dfe8f7",
                    "menu_active_fg": "#111111",
                    "canvas_bg": "#d9d9d9",
                    "status_bg": "#f0f0f0",
                    "tooltip_bg": "#ffffe1",
                    "tooltip_fg": "#111111",
                    "tooltip_bd": "#a0a0a0",
                    "scale_trough": "#ffffff",
                    "scale_bg": "#f0f0f0",
                }
                self._tooltip_bg = self._theme_colors["tooltip_bg"]
                self._tooltip_fg = self._theme_colors["tooltip_fg"]
                self._tooltip_bd = self._theme_colors["tooltip_bd"]

            else:
                try:
                    if os.name == "nt":
                        self.style.theme_use("vista")
                    else:
                        self.style.theme_use("default")
                except Exception:
                    self.style.theme_use("clam")

                # IMPORTANT:
                # Treat System as a clean reset of all manual dark-mode colors.
                # Using the same neutral palette as Light prevents dark values from lingering.
                self._theme_colors = {
                    "bg": "#f0f0f0",
                    "panel": "#f6f6f6",
                    "control": "#ffffff",
                    "hover": "#e8e8e8",
                    "pressed": "#dcdcdc",
                    "text": "#111111",
                    "muted_text": "#333333",
                    "border": "#b8b8b8",
                    "accent": "#4a90ff",
                    "field": "#ffffff",
                    "menu_bg": "#f0f0f0",
                    "menu_fg": "#111111",
                    "menu_active_bg": "#dfe8f7",
                    "menu_active_fg": "#111111",
                    "canvas_bg": "#d9d9d9",
                    "status_bg": "#f0f0f0",
                    "tooltip_bg": "#ffffe1",
                    "tooltip_fg": "#111111",
                    "tooltip_bd": "#a0a0a0",
                    "scale_trough": "#ffffff",
                    "scale_bg": "#f0f0f0",
                }

                self._tooltip_bg = self._theme_colors["tooltip_bg"]
                self._tooltip_fg = self._theme_colors["tooltip_fg"]
                self._tooltip_bd = self._theme_colors["tooltip_bd"]

                self.configure(bg=self._theme_colors["bg"])

                self.style.configure(".", background=self._theme_colors["bg"], foreground=self._theme_colors["text"])
                self.style.configure("TFrame", background=self._theme_colors["bg"])
                self.style.configure("TLabelframe", background=self._theme_colors["bg"], foreground=self._theme_colors["text"])
                self.style.configure("TLabelframe.Label", background=self._theme_colors["bg"], foreground=self._theme_colors["text"])
                self.style.configure("TLabel", background=self._theme_colors["bg"], foreground=self._theme_colors["text"])
                self.style.configure("TCheckbutton", background=self._theme_colors["bg"], foreground=self._theme_colors["text"])
                self.style.map(
                    "TCheckbutton",
                    background=[("active", self._theme_colors["bg"])],
                    foreground=[("active", self._theme_colors["text"])]
                )

                self.style.configure(
                    "TButton",
                    background=self._theme_colors["control"],
                    foreground=self._theme_colors["text"],
                    bordercolor=self._theme_colors["border"]
                )
                self.style.map(
                    "TButton",
                    background=[("active", self._theme_colors["hover"]), ("pressed", self._theme_colors["pressed"])],
                    foreground=[("active", self._theme_colors["text"]), ("pressed", self._theme_colors["text"])]
                )

                self.style.configure(
                    "TEntry",
                    fieldbackground=self._theme_colors["field"],
                    foreground=self._theme_colors["text"],
                    insertcolor=self._theme_colors["text"]
                )

                self.style.configure(
                    "Horizontal.TScale",
                    background=self._theme_colors["scale_bg"],
                    troughcolor=self._theme_colors["scale_trough"],
                    bordercolor=self._theme_colors["border"],
                    lightcolor=self._theme_colors["scale_trough"],
                    darkcolor=self._theme_colors["scale_trough"]
                )
                self.style.map(
                    "Horizontal.TScale",
                    background=[("active", self._theme_colors["scale_bg"])],
                    troughcolor=[("active", self._theme_colors["scale_trough"])]
                )

                self.style.configure(
                    "Vertical.TScrollbar",
                    background=self._theme_colors["control"],
                    troughcolor=self._theme_colors["bg"],
                    bordercolor=self._theme_colors["border"],
                    arrowcolor=self._theme_colors["text"],
                    lightcolor=self._theme_colors["control"],
                    darkcolor=self._theme_colors["control"]
                )
                self.style.map(
                    "Vertical.TScrollbar",
                    background=[("active", self._theme_colors["hover"]), ("pressed", self._theme_colors["pressed"])]
                )

                self.style.configure(
                    "Horizontal.TScrollbar",
                    background=self._theme_colors["control"],
                    troughcolor=self._theme_colors["bg"],
                    bordercolor=self._theme_colors["border"],
                    arrowcolor=self._theme_colors["text"],
                    lightcolor=self._theme_colors["control"],
                    darkcolor=self._theme_colors["control"]
                )
                self.style.map(
                    "Horizontal.TScrollbar",
                    background=[("active", self._theme_colors["hover"]), ("pressed", self._theme_colors["pressed"])]
                )

                self.style.configure("TSeparator", background=self._theme_colors["border"])

            self._apply_widget_theme()

        except Exception as e:
            print(f"Theme apply failed: {e}")

    def _build_menu(self):
        self.config(menu="")
        self.menu_row = tk.Frame(self, bd=0, highlightthickness=0)
        self.menu_row.place(x=0, y=0, relwidth=1, height=30)
        self.menu_row.lift()

        for name in ("File", "Edit", "View", "Help"):
            lbl = tk.Label(
                self.menu_row,
                text=name,
                padx=10,
                pady=4,
                bd=0,
                relief="flat",
                cursor="hand2"
            )
            lbl.pack(side="left", padx=(2, 0))
            lbl.bind("<Button-1>", lambda e, n=name: self._toggle_custom_menu(n))
            lbl.bind("<Enter>", lambda e, n=name: self._on_menu_label_hover(n))
            lbl.bind("<Leave>", lambda e, n=name: self._on_menu_label_leave(n))
            self._menu_buttons[name] = lbl

        self.bind_all("<Button-1>", self._global_menu_click_close, add="+")
        self.bind("<Escape>", lambda e: self._close_active_menu(), add="+")

    def _toggle_custom_menu(self, menu_name: str):
        if self._active_menu_name == menu_name and self._active_popup is not None:
            self._close_active_menu()
            return
        self._ignore_next_global_click = True
        self._open_custom_menu(menu_name)

    def _open_custom_menu(self, menu_name: str):
        self._close_active_menu()

        btn = self._menu_buttons.get(menu_name)
        if btn is None:
            return

        colors = self._theme_colors or {}
        is_dark = (self.theme or "System").lower() == "dark"

        menu_bg = colors.get("menu_bg", "#2f3136" if is_dark else "#f0f0f0")
        menu_fg = colors.get("menu_fg", "#f1f1f1" if is_dark else "#111111")
        menu_hover = colors.get("menu_active_bg", "#4b5157" if is_dark else "#dfe8f7")
        menu_hover_fg = colors.get("menu_active_fg", "#ffffff" if is_dark else "#111111")
        menu_border = colors.get("border", "#5a5f66" if is_dark else "#b8b8b8")

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.transient(self)
        popup.configure(bg=menu_border)
        popup.attributes("-topmost", True)
        popup.lift()

        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        popup.geometry(f"+{x}+{y}")
        popup.update_idletasks()

        outer = tk.Frame(popup, bg=menu_border, bd=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)

        inner = tk.Frame(outer, bg=menu_bg, bd=0, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        items = self._get_menu_items(menu_name)

        for item in items:
            if item == "---":
                sep = tk.Frame(inner, height=1, bg=menu_border, bd=0, highlightthickness=0)
                sep.pack(fill="x", padx=4, pady=4)
                continue

            label = item["label"]
            command = item.get("command")
            checked = item.get("checked", False)
            enabled = item.get("enabled", True)

            row_text = f"✓ {label}" if checked else f"   {label}"

            row = tk.Label(
                inner,
                text=row_text,
                anchor="w",
                justify="left",
                padx=12,
                pady=6,
                bg=menu_bg,
                fg=menu_fg if enabled else colors.get("muted_text", "#888888"),
                bd=0,
                relief="flat"
            )
            row.pack(fill="x")

            if enabled and command is not None:
                row.bind("<Enter>", lambda e, w=row: w.configure(bg=menu_hover, fg=menu_hover_fg))
                row.bind("<Leave>", lambda e, w=row, fg0=menu_fg: w.configure(bg=menu_bg, fg=fg0))
                row.bind("<Button-1>", lambda e, cmd=command: self._execute_menu_command(cmd))

        self._active_popup = popup
        self._active_menu_name = menu_name
        self._style_menu_buttons()

    def _execute_menu_command(self, command):
        self._close_active_menu()
        if command is not None:
            self.after(1, command)

    def _close_active_menu(self):
        if self._active_popup is not None:
            try:
                self._active_popup.destroy()
            except Exception:
                pass
        self._active_popup = None
        self._active_menu_name = None
        self._style_menu_buttons()

    def _global_menu_click_close(self, event):
        if self._ignore_next_global_click:
            self._ignore_next_global_click = False
            return

        if self._active_popup is None:
            return

        widget = event.widget

        if widget in self._menu_buttons.values():
            return

        try:
            popup_widget = self._active_popup
            while widget is not None:
                if widget == popup_widget:
                    return
                widget = widget.master
        except Exception:
            pass

        self._close_active_menu()

    def _on_menu_label_hover(self, menu_name: str):
        if self._active_popup is not None and self._active_menu_name != menu_name:
            self._open_custom_menu(menu_name)
        else:
            self._style_menu_buttons(hover_name=menu_name)

    def _on_menu_label_leave(self, menu_name: str):
        self._style_menu_buttons()

    def _style_menu_buttons(self, hover_name=None):
        colors = self._theme_colors or {}
        is_dark = (self.theme or "System").lower() == "dark"

        bg = colors.get("bg", "#2f3136" if is_dark else "#f0f0f0")
        fg = colors.get("text", "#f1f1f1" if is_dark else "#111111")
        hover_bg = colors.get("menu_active_bg", "#4b5157" if is_dark else "#dfe8f7")
        hover_fg = colors.get("menu_active_fg", "#ffffff" if is_dark else "#111111")

        if hasattr(self, "menu_row"):
            self.menu_row.configure(bg=bg)

        for name, lbl in self._menu_buttons.items():
            active = (name == self._active_menu_name)
            hovered = (name == hover_name)
            if active or hovered:
                lbl.configure(bg=hover_bg, fg=hover_fg)
            else:
                lbl.configure(bg=bg, fg=fg)

    def _get_menu_items(self, menu_name: str):
        if menu_name == "File":
            return [
                {"label": "New (Ctrl+N)", "command": self.new_canvas},
                {"label": "Open... (Ctrl+O)", "command": self.open_image},
                "---",
                *self._get_recent_menu_items(),
                "---",
                {"label": "Save PNG... (Ctrl+S)", "command": self.save_png},
                {"label": "Export ICO... (Ctrl+E)", "command": self.export_ico},
                {"label": "Export ICNS... (macOS)", "command": self.export_icns},
                "---",
                {"label": "Exit", "command": self._on_exit},
            ]

        if menu_name == "Edit":
            return [
                {"label": "Undo (Ctrl+Z)", "command": self.undo},
                {"label": "Redo (Ctrl+Y)", "command": self.redo},
                "---",
                {"label": "Copy (Ctrl+C)", "command": self.copy_selection},
                {"label": "Paste (Ctrl+V)", "command": self.paste_selection},
                "---",
                {"label": "Invert Colors", "command": self._quick_invert},
                {"label": "Grayscale", "command": self._quick_grayscale},
                {"label": "Flip Horizontal", "command": self._quick_flip_h},
                {"label": "Flip Vertical", "command": self._quick_flip_v},
                {"label": "Trim Transparent", "command": self._quick_trim},
                "---",
                {"label": "Select All (Ctrl+A)", "command": self.select_all},
                {"label": "Deselect (Esc)", "command": self._deselect},
            ]

        if menu_name == "View":
            return [
                {"label": "Show Grid", "command": self._toggle_grid, "checked": bool(self.grid_var.get())},
                "---",
                {"label": "Theme: Light", "command": lambda: self._set_theme("Light")},
                {"label": "Theme: Dark", "command": lambda: self._set_theme("Dark")},
                {"label": "Theme: System", "command": lambda: self._set_theme("System")},
            ]

        if menu_name == "Help":
            return [
                {"label": "About", "command": self._about},
            ]

        return []

    def _get_recent_menu_items(self):
        if not self.recent_files:
            return [{"label": "Open Recent: (Empty)", "command": None, "enabled": False}]

        items = []
        for path_str in self.recent_files:
            p = Path(path_str)
            label = p.name if len(p.name) < 48 else "..." + p.name[-45:]
            items.append({
                "label": f"Open Recent: {label}",
                "command": lambda s=path_str: self._open_recent(s)
            })
        return items

    def _restyle_scales(self):
        for scale in getattr(self, "_scales", []):
            try:
                scale.configure(style="Horizontal.TScale")
                scale.update_idletasks()
            except Exception:
                pass

    def _force_full_theme_refresh(self):
        try:
            self._apply_widget_theme()

            if hasattr(self, "menu_row"):
                self.menu_row.update_idletasks()
                self.menu_row.lift()

            if hasattr(self, "toolbar"):
                self.toolbar.update_idletasks()

            if hasattr(self, "main_frame"):
                self.main_frame.update_idletasks()

            if hasattr(self, "statusbar"):
                self.statusbar.update_idletasks()

            self.update()
        except Exception as e:
            print(f"Theme refresh failed: {e}")

    def _apply_widget_theme(self):
        colors = self._theme_colors or {}
        mode_l = (self.theme or "System").lower()
        is_dark = mode_l == "dark"

        bg = colors.get("bg", "#f0f0f0")
        control = colors.get("control", "#ffffff")
        text = colors.get("text", "#111111")
        border = colors.get("border", "#b8b8b8")
        accent = colors.get("accent", "#4a90ff")
        status_bg = colors.get("status_bg", bg)

        try:
            self.configure(bg=bg)
        except Exception:
            pass

        if hasattr(self, "menu_row"):
            try:
                self.menu_row.configure(bg=bg)
                self.menu_row.lift()
            except Exception:
                pass

        self._style_menu_buttons()

        if hasattr(self, "toolbar"):
            try:
                self.toolbar.configure(style="TFrame")
            except Exception:
                pass

        if hasattr(self, "main_frame"):
            try:
                self.main_frame.configure(style="TFrame")
            except Exception:
                pass

        if hasattr(self, "statusbar"):
            try:
                self.statusbar.configure(style="TFrame")
            except Exception:
                pass

        if hasattr(self, "canvas_editor") and self.canvas_editor is not None:
            try:
                self.canvas_editor.configure(style="TFrame")
            except Exception:
                pass

        for attr in ("status_label", "cursor_label", "dim_label", "zoom_label"):
            lbl = getattr(self, attr, None)
            if lbl is not None:
                try:
                    lbl.configure(background=status_bg, foreground=text)
                except Exception:
                    pass

        if hasattr(self, "color_display"):
            try:
                self.color_display.configure(
                    highlightbackground=border,
                    highlightcolor=accent
                )
            except Exception:
                pass

        hover = colors.get("hover", "#4b5157")
        light_hover = "#e8e8e8"

        for btn in getattr(self, "_toolbar_buttons", []):
            try:
                if is_dark:
                    btn.configure(
                        bg=control,
                        fg=text,
                        activebackground=hover,
                        activeforeground=text,
                        relief=btn.cget("relief"),
                        bd=1,
                        highlightthickness=1,
                        highlightbackground=border,
                        highlightcolor=accent,
                        disabledforeground="#888888"
                    )
                else:
                    btn.configure(
                        bg="#f0f0f0",
                        fg="#111111",
                        activebackground=light_hover,
                        activeforeground="#111111",
                        relief=btn.cget("relief"),
                        bd=1,
                        highlightthickness=1,
                        highlightbackground="#b8b8b8",
                        highlightcolor="#4a90ff",
                        disabledforeground="#888888"
                    )
            except Exception:
                pass

        self._style_menu_buttons()
        self._restyle_scales()
        self._rebuild_toolbar_icons()

    def _rebuild_toolbar_icons(self):
        if not hasattr(self, "_toolbar_buttons"):
            return

        icon_fg = (240, 240, 240, 255) if (self.theme or "System").lower() == "dark" else (0, 0, 0, 255)
        icons = IconFactory(size=22, fg=icon_fg)

        button_order = [
            "open", "save", "export",
            "select", "move", "brush", "eraser", "fill", "eyedrop", "magic", "text", "line", "rect", "ellipse",
            "grid", "fit", "reset"
        ]

        for btn, icon_name in zip(self._toolbar_buttons, button_order):
            try:
                img = icons.get(icon_name)
                btn.configure(image=img)
                btn.image = img
            except Exception:
                pass

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

    def _build_canvas(self):
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")
        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        self.canvas_editor = CanvasEditor(
            self.main_frame,
            on_status=lambda msg: self.after_idle(lambda: self._update_status(msg)),
            on_cursor=lambda x, y: self.after_idle(lambda: self._update_cursor(x, y)),
            on_size_change=lambda w, h: self.after_idle(lambda: self._update_image_info(w, h)),
            on_zoom_change=lambda z: self.after_idle(lambda: self._update_zoom_info(z)),
            on_layers_changed=lambda: self.after_idle(self._refresh_layers_ui),
            on_color_ui=lambda rgba: self.after_idle(lambda: self._set_ui_color(rgba))
        )
        self.canvas_editor.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _build_toolbar(self):
        self.toolbar = ttk.Frame(self, padding=(6, 6))
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)

        icon_fg = (240, 240, 240, 255) if (self.theme or "System").lower() == "dark" else (0, 0, 0, 255)
        icons = IconFactory(size=22, fg=icon_fg)

        # ADD THIS: Helper function to calculate slider value based on pointer X coordinate
        def make_slider_snapable(scale_widget):
            def jump_to_pointer(event):
                val_min = float(scale_widget.cget('from'))
                val_max = float(scale_widget.cget('to'))
                width = scale_widget.winfo_width()
                
                if width > 0:
                    # Keep the X coordinate safely within the bounds of the widget
                    x = max(0, min(event.x, width))
                    fraction = x / width
                    new_val = val_min + (fraction * (val_max - val_min))
                    scale_widget.set(new_val)
                    
                # Prevent Tkinter's default "page jumping" behavior from fighting our smooth snap
                return "break"
                
            scale_widget.bind("<Button-1>", jump_to_pointer)
            scale_widget.bind("<B1-Motion>", jump_to_pointer)

        def add_btn(parent, icon_name, cmd, tip):
            img = icons.get(icon_name)
            c = self._theme_colors or {}
            is_dark = (self.theme or "System").lower() == "dark"

            btn = tk.Button(
                parent,
                image=img,
                width=28,
                height=28,
                command=cmd,
                relief="raised",
                bd=1,
                bg=c.get("control", "#44484d") if is_dark else "#f0f0f0",
                fg=c.get("text", "#f1f1f1") if is_dark else "#111111",
                activebackground=c.get("control", "#44484d") if is_dark else "#f0f0f0",
                activeforeground=c.get("text", "#f1f1f1") if is_dark else "#111111",
                highlightthickness=1,
                highlightbackground=c.get("border", "#5a5f66") if is_dark else "#b8b8b8",
                highlightcolor=c.get("accent", "#6aa2ff") if is_dark else "#4a90ff",
                padx=0,
                pady=0
            )
            btn.image = img
            btn.pack(side="left", padx=2)
            Tooltip(btn, tip)
            self._toolbar_buttons.append(btn)
            return btn

        file_grp = ttk.Frame(self.toolbar)
        file_grp.pack(side="left", padx=(0, 8))
        add_btn(file_grp, "open", self.open_image, "Open Image (Ctrl+O)")
        add_btn(file_grp, "save", self.save_png, "Save PNG (Ctrl+S)")
        add_btn(file_grp, "export", self.export_ico, "Export ICO (Ctrl+E)")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

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

        shape_grp = ttk.Frame(self.toolbar)
        shape_grp.pack(side="left", padx=(0, 8))
        ttk.Checkbutton(
            shape_grp,
            text="Filled",
            variable=self.shape_fill_var,
            command=self._on_shape_fill_toggle
        ).pack(side="left")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        size_grp = ttk.Frame(self.toolbar)
        size_grp.pack(side="left", padx=(0, 8))
        ttk.Label(size_grp, text="Size").pack(side="left", padx=(0, 4))
        self.brush_size_var = tk.IntVar(value=5)
        size_scale = ttk.Scale(
            size_grp,
            from_=1,
            to=64,
            orient="horizontal",
            command=lambda v: self._on_brush_size_change(int(float(v)))
        )
        size_scale.set(5)
        size_scale.pack(side="left", fill="x", expand=True, padx=2)
        make_slider_snapable(size_scale) 
        self._scales.append(size_scale)
        Tooltip(size_scale, "Brush Size")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        color_grp = ttk.Frame(self.toolbar)
        color_grp.pack(side="left", padx=(0, 8))
        ttk.Label(color_grp, text="Color").pack(side="left", padx=(0, 4))
        self.color_display = tk.Canvas(
            color_grp,
            width=30,
            height=18,
            bg="#000000",
            highlightthickness=1,
            highlightbackground=self._theme_colors.get("border", "#b8b8b8"),
            highlightcolor=self._theme_colors.get("accent", "#4a90ff")
        )
        self.color_display.pack(side="left")
        self.color_display.bind("<Button-1>", self._pick_color)
        Tooltip(self.color_display, "Pick Color")
        ttk.Label(color_grp, text="Alpha").pack(side="left", padx=(10, 4))
        self.alpha_var = tk.IntVar(value=255)
        alpha_scale = ttk.Scale(
            color_grp,
            from_=0,
            to=255,
            orient="horizontal",
            command=lambda v: self._on_alpha_change(int(float(v)))
        )
        alpha_scale.set(255)
        alpha_scale.pack(side="left", fill="x", expand=True, padx=2)
        make_slider_snapable(alpha_scale)
        self._scales.append(alpha_scale)
        Tooltip(alpha_scale, "Alpha (opacity 0–255)")
        ttk.Label(color_grp, text="Tol").pack(side="left", padx=(10, 4))
        self.tol_var = tk.IntVar(value=0)
        tol_scale = ttk.Scale(
            color_grp,
            from_=0,
            to=100,
            orient="horizontal",
            command=lambda v: self.canvas_editor.set_fill_tolerance(int(float(v)))
        )
        tol_scale.set(0)
        tol_scale.pack(side="left", fill="x", expand=True, padx=2)
        make_slider_snapable(tol_scale) 
        self._scales.append(tol_scale)
        Tooltip(tol_scale, "Fill Tolerance")

        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", padx=6, fill="y")

        view_grp = ttk.Frame(self.toolbar)
        view_grp.pack(side="left", padx=(0, 8))
        add_btn(view_grp, "grid", self._toggle_grid, "Toggle Grid")
        add_btn(view_grp, "fit", self._fit_to_window, "Fit to Window (F)")
        add_btn(view_grp, "reset", self._reset_scroll, "Reset Scroll")
        ttk.Label(view_grp, text="Zoom").pack(side="left", padx=(10, 4))
        self.zoom_var = tk.IntVar(value=4)
        zoom_scale = ttk.Scale(
            view_grp,
            from_=1,
            to=16,
            orient="horizontal",
            variable=self.zoom_var,  # <--- ADD THIS LINE HERE
            command=lambda v: self._set_zoom_from_scale(int(float(v)))
        )
        zoom_scale.set(4)
        zoom_scale.pack(side="left", fill="x", expand=True, padx=2)
        make_slider_snapable(zoom_scale)
        self._scales.append(zoom_scale)
        Tooltip(zoom_scale, "Zoom 1x–16x")

    def _update_tool_visuals(self):
        for btn, t in self.tool_buttons.items():
            btn.config(relief="sunken" if t == self.current_tool else "raised")

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
            _ = human_readable_size(sz)

    def _update_zoom_info(self, zoom):
        if hasattr(self, "zoom_label"):
            self.zoom_label.config(text=f"Zoom: {zoom}x")
        else:
            self._pending_zoom = zoom
        if hasattr(self, "zoom_var"):
            self.zoom_var.set(zoom)
            
    def _set_ui_color(self, rgba):
        self.current_color = tuple(rgba)
        r, g, b, _ = self.current_color
        self.color_display.config(bg=f"#{r:02x}{g:02x}{b:02x}")

    def _select_tool(self, tool: ToolType):
        self.current_tool = tool
        self._update_tool_visuals()
        if hasattr(self, "canvas_editor"):
            self.canvas_editor.set_tool(tool)

    def _pick_color(self, event=None):
        color = colorchooser.askcolor(
            color=f"#{self.current_color[0]:02x}{self.current_color[1]:02x}{self.current_color[2]:02x}"
        )
        if color and color[0]:
            r, g, b = [int(c) for c in color[0]]
            current_alpha = int(self.alpha_var.get())
            self.current_color = (r, g, b, current_alpha)
            self.color_display.config(bg=f"#{r:02x}{g:02x}{b:02x}")
            self.canvas_editor.set_color(self.current_color)

    def _on_alpha_change(self, alpha: int):
        r, g, b, _ = self.current_color
        self.current_color = (r, g, b, alpha)
        self.canvas_editor.set_alpha(alpha)
        self.canvas_editor.set_color(self.current_color)

    def _on_brush_size_change(self, size: int):
        self.canvas_editor.set_brush_size(int(size))

    def _on_shape_fill_toggle(self):
        self.canvas_editor.set_shape_fill(self.shape_fill_var.get())

    def _toggle_grid(self, event=None):
        new_state = not self.canvas_editor.show_grid
        self.canvas_editor.set_grid(new_state)

        if hasattr(self, "grid_var"):
            self.grid_var.set(new_state)

        if new_state:
            self._update_status("Grid enabled (Requires Zoom >= 4x to display)")
        else:
            self._update_status("Grid disabled")

    def _about(self):
        messagebox.showinfo(
            "About",
            "Mr5niper's Pyicon Editor and Creator v1.3.0.0\n"
            "\n"
            "Created by Mr5niper\n"
            "© 2026 Mr5niper5oft\n"
            "MIT License\n"
            "\n"
            "Credits:\n"
            "Python / tkinter, Pillow\n"
            "\n"
            "GitHub:\n"
            "https://github.com/Mr5niper/Pyicon-Editor\n"
            "\n"
            "Release:\n"
            "https://github.com/Mr5niper/Pyicon-Editor/releases\n"
        )

    def _set_theme(self, theme: str):
        self.theme = theme
        self._apply_theme(theme)
        self.config_mgr.theme = theme
        self.config_mgr.save()

    def _on_exit(self):
        if getattr(self, "canvas_editor", None) and getattr(self.canvas_editor, "is_unsaved", False):
            resp = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?"
            )
            if resp is True:
                self.save_png()
                # If they cancelled the save dialog, abort the exit
                if self.canvas_editor.is_unsaved:
                    return
            elif resp is None:
                return

        self.config_mgr.recent_files = self.recent_files[:5]
        self.config_mgr.theme = self.theme
        self.config_mgr.save()
        self.destroy()

    def _refresh_recent_menu(self):
        pass

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
        # Check for unsaved changes before opening the dialog
        if getattr(self, "canvas_editor", None) and getattr(self.canvas_editor, "is_unsaved", False):
            resp = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before creating a new canvas?"
            )
            if resp is True:
                self.save_png()
                # If they cancelled the save dialog, abort
                if getattr(self.canvas_editor, "is_unsaved", False):
                    return
            elif resp is None:
                return

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
        # Check for unsaved changes before loading a new image
        if getattr(self, "canvas_editor", None) and getattr(self.canvas_editor, "is_unsaved", False):
            resp = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening another file?"
            )
            if resp is True:
                self.save_png()
                # If they cancelled the save dialog, abort
                if getattr(self.canvas_editor, "is_unsaved", False):
                    return
            elif resp is None:
                return

        try:
            img = load_image_with_alpha(p, max_edit_dimension=3072)
            # FIX: If img is None, the user hit 'X' on the icon popup. Silently abort.
            if img is None:
                return
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
            self.canvas_editor.is_unsaved = False            
            self._update_status(f"Saved PNG: {Path(out).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PNG:\n{e}")

    def export_ico(self):
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

    def export_icns(self):
        comp = self.canvas_editor.get_composite()
        if comp is None:
            messagebox.showinfo("No image", "Create or open an image first.")
            return
        try:
            sizes = [1024, 512, 256, 128, 64, 32, 16]
            export_icns_dialog(self, comp, sizes, "Lanczos", True)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export ICNS:\n{e}")

    def undo(self):
        self.canvas_editor.undo()

    def redo(self):
        self.canvas_editor.redo()

    def copy_selection(self):
        self.canvas_editor.copy_selection()
        
    def paste_selection(self):
        # If the paste is successful, automatically switch the UI to the Move tool
        if self.canvas_editor.paste_selection():
            self._select_tool(ToolType.MOVE)

    def select_all(self):
        if self.canvas_editor.select_all():
            self._select_tool(ToolType.SELECTION)

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

    def _refresh_layers_ui(self):
        pass

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda event: self.new_canvas() or "break")
        self.bind("<Control-o>", lambda event: self.open_image() or "break")
        self.bind("<Control-s>", lambda event: self.save_png() or "break")
        self.bind("<Control-e>", lambda event: self.export_ico() or "break")

        self.bind("<Control-z>", lambda event: self.undo() or "break")
        self.bind("<Control-y>", lambda event: self.redo() or "break")
        
        self.bind("<Control-c>", lambda event: self.copy_selection() or "break")
        self.bind("<Control-v>", lambda event: self.paste_selection() or "break")
        
        self.bind("<Control-a>", lambda event: self.select_all() or "break")
        self.bind("<Escape>", lambda event: self._deselect())
        self.bind("<Delete>", lambda event: self.canvas_editor.delete_selection())

        self.bind("<f>", lambda event: self._fit_to_window())
        self.bind("<F>", lambda event: self._fit_to_window())

        self.bind("<s>", lambda event: self._select_tool(ToolType.SELECTION))
        self.bind("<S>", lambda event: self._select_tool(ToolType.SELECTION))
        self.bind("<v>", lambda event: self._select_tool(ToolType.MOVE))
        self.bind("<V>", lambda event: self._select_tool(ToolType.MOVE))
        self.bind("<b>", lambda event: self._select_tool(ToolType.PENCIL))
        self.bind("<B>", lambda event: self._select_tool(ToolType.PENCIL))
        self.bind("<e>", lambda event: self._select_tool(ToolType.ERASER))
        self.bind("<E>", lambda event: self._select_tool(ToolType.ERASER))
        self.bind("<g>", lambda event: self._select_tool(ToolType.FILL))
        self.bind("<G>", lambda event: self._select_tool(ToolType.FILL))
        self.bind("<i>", lambda event: self._select_tool(ToolType.EYEDROPPER))
        self.bind("<I>", lambda event: self._select_tool(ToolType.EYEDROPPER))
        self.bind("<m>", lambda event: self._select_tool(ToolType.MAGIC_ERASER))
        self.bind("<M>", lambda event: self._select_tool(ToolType.MAGIC_ERASER))
        self.bind("<t>", lambda event: self._select_tool(ToolType.TEXT))
        self.bind("<T>", lambda event: self._select_tool(ToolType.TEXT))
        self.bind("<l>", lambda event: self._select_tool(ToolType.SHAPE_LINE))
        self.bind("<L>", lambda event: self._select_tool(ToolType.SHAPE_LINE))
        self.bind("<r>", lambda event: self._select_tool(ToolType.SHAPE_RECT))
        self.bind("<R>", lambda event: self._select_tool(ToolType.SHAPE_RECT))
        self.bind("<c>", lambda event: self._select_tool(ToolType.SHAPE_ELLIPSE))
        self.bind("<C>", lambda event: self._select_tool(ToolType.SHAPE_ELLIPSE))


def run_app():
    app = MainWindow()
    app.mainloop()
