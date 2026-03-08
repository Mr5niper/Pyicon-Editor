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
