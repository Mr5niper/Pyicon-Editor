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
