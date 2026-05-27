import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps, ImageChops, ImageFont
from core.editor_tools import ToolType, UndoRedoStack, flood_fill, draw_brush_line
from core.transparency import create_checkerboard
from utils.helpers import clamp


class CanvasEditor(ttk.Frame):
    def __init__(
        self,
        parent,
        on_status=None,
        on_cursor=None,
        on_size_change=None,
        on_zoom_change=None,
        on_layers_changed=None,
        on_color_ui=None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.on_status = on_status or (lambda text: None)
        self.on_cursor = on_cursor or (lambda x, y: None)
        self.on_size_change = on_size_change or (lambda w, h: None)
        self.on_zoom_change = on_zoom_change or (lambda z: None)
        self.on_layers_changed = on_layers_changed or (lambda: None)
        self.on_color_ui = on_color_ui or (lambda rgba: None)

        self._bg_cache = None

        self.layers: list[Image.Image] = []
        self.layer_visible: list[bool] = []
        self.layer_names: list[str] = []
        self.active_layer = 0

        self._composite_cache: Image.Image | None = None
        self._composite_dirty = True

        self._display_image = None
        self._canvas_image_id = None
        self.zoom = 4
        self.show_grid = False

        self._space_pan_active = False

        self.tool = ToolType.PENCIL
        self.brush_size = 5
        self.color = (0, 0, 0, 255)
        self.alpha = 255
        self.fill_tolerance = 0
        self.shape_fill = False

        # Selection / move
        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.sel_floating = None
        self.sel_offset = (0, 0)

        # Gestures
        self.is_drawing = False
        self.last_pos = None

        # Shapes
        self.shape_start = None
        self.preview_image = None
        self.clipboard_image = None
        
        self.history = UndoRedoStack(limit=50)
        self.is_unsaved = False
        
        self._build_ui()
        # NOTE: Do not call new_blank here; main_window triggers it after widget exists.

    # ---------- Size helpers ----------

    def width(self):
        return self.layers[0].width if self.layers else 0

    def height(self):
        return self.layers[0].height if self.layers else 0

    # ---------- Composite ----------
    def _mark_dirty(self):
        self._composite_dirty = True
        self.is_unsaved = True

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

    # ---------- Layer controls ----------
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

    # ---------- UI ----------
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.canvas = tk.Canvas(self, bg="#3a3a3a", highlightthickness=0, cursor="cross")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Restore the missing scrollbars
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        # Link scroll updates to immediately refresh our viewport-cropped image
        self.canvas.configure(
            xscrollcommand=lambda f, l: (self.hbar.set(f, l), self._refresh_display()),
            yscrollcommand=lambda f, l: (self.vbar.set(f, l), self._refresh_display())
        )
        
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
        self.canvas.bind("<Shift-MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Shift-Button-5>", self._on_mouse_wheel)
        
        # Safely bind Linux horizontal scroll buttons (Windows will ignore this without crashing)
        try:
            self.canvas.bind("<Button-6>", self._on_mouse_wheel)
            self.canvas.bind("<Button-7>", self._on_mouse_wheel)
        except tk.TclError:
            pass

        self._first_fit_done = False
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

    def _on_canvas_configure(self, event):
        if not self._first_fit_done and self.layers:
            self.fit_to_window()
            self._first_fit_done = True

    # ---------- Lifecycle ----------
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
        self.is_unsaved = False

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
        self.is_unsaved = False

    def _reset_selection(self):
        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.sel_floating = None
        self.sel_offset = (0, 0)
        self.preview_image = None

    # ---------- View ----------
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

        # If the image is smaller than the viewport, always pin to top-left
        if w <= cw:
            self.canvas.xview_moveto(0)
        else:
            self.canvas.xview_moveto(0)

        if h <= ch:
            self.canvas.yview_moveto(0)
        else:
            self.canvas.yview_moveto(0)

    def set_grid(self, show: bool):
        self.show_grid = show
        self._refresh_display()

    # ---------- Tool settings ----------
    def set_tool(self, tool: ToolType):
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
        # Force the color tuple to use the current live canvas alpha variable 
        # instead of letting the color dialog override it with 255
        self.color = (
            clamp(int(rgba[0]), 0, 255),
            clamp(int(rgba[1]), 0, 255),
            clamp(int(rgba[2]), 0, 255),
            self.alpha  # <--- Retain your slider's value here
        )
        try:
            self.on_color_ui(self.color)
        except Exception:
            pass
        self.on_status(f"Color: RGBA{self.color}")

    def set_shape_fill(self, filled: bool):
        self.shape_fill = bool(filled)
        self.on_status(f"Shape fill: {'On' if self.shape_fill else 'Off'}")

    def set_fill_tolerance(self, tolerance: int):
        self.fill_tolerance = clamp(tolerance, 0, 255)
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
    
    def select_all(self):
        if not self.layers:
            return False
            
        # If we are dragging a floating selection, commit it to the canvas first
        if self.sel_floating is not None:
            self._commit_floating_selection()
            
        # Set the selection rectangle to the full dimensions of the canvas
        self.sel_active = True
        self.sel_start = (0, 0)
        self.sel_rect = (0, 0, self.width(), self.height())
        
        self._refresh_display()
        self.on_status("Selected all")
        return True
    
    def clear_selection(self):
        if self.sel_floating is not None:
            self._commit_floating_selection()
        self.sel_active = False
        self.sel_start = None
        self.sel_rect = None
        self.preview_image = None
        self._refresh_display()
        self.on_status("Selection cleared")

    def delete_selection(self):
        """Fills the currently selected bounding box area with full transparency."""
        if not self.layers or not self.sel_active or not self.sel_rect:
            return
            
        self._push_state()
        x0, y0, x1, y1 = self._norm_rect(self.sel_rect)
        
        # Draw a transparent rectangle. 
        # By using x1 and y1 directly (exclusive boundary), 
        # Pillow will cover the range from x0 to x1-1 (which includes the last pixel).
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
        
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Selection cleared to transparency")

    def _copy_to_os_clipboard(self, image: Image.Image):
        """Helper to push PIL images to the Windows OS clipboard in DIB and PNG formats."""
        import os
        if os.name != 'nt':
            return
            
        import ctypes
        from ctypes import wintypes
        from io import BytesIO
        
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # FIX: Explicitly define 64-bit handle types so ctypes doesn't truncate the memory pointers!
            user32.OpenClipboard.argtypes = [wintypes.HWND]
            user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
            user32.SetClipboardData.restype = wintypes.HANDLE
            
            kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
            kernel32.GlobalAlloc.restype = wintypes.HANDLE
            
            kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
            kernel32.GlobalLock.restype = wintypes.LPVOID
            
            kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
            
            user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
            user32.RegisterClipboardFormatW.restype = wintypes.UINT
            
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            
            # 1. DIB Format (Fallback for older apps like classic MS Paint)
            output_dib = BytesIO()
            bg = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg.paste(image, mask=image.convert("RGBA").split()[3])
            else:
                bg.paste(image)
            bg.save(output_dib, "DIB")
            data_dib = output_dib.getvalue()
            
            hMem_dib = kernel32.GlobalAlloc(0x0002, len(data_dib)) # GMEM_MOVEABLE
            pMem_dib = kernel32.GlobalLock(hMem_dib)
            ctypes.memmove(pMem_dib, data_dib, len(data_dib))
            kernel32.GlobalUnlock(hMem_dib)
            user32.SetClipboardData(8, hMem_dib) # CF_DIB = 8
            
            # 2. PNG Format (For modern apps like Discord/Photoshop to preserve alpha transparency)
            png_format = user32.RegisterClipboardFormatW("PNG")
            output_png = BytesIO()
            image.save(output_png, "PNG")
            data_png = output_png.getvalue()
            
            hMem_png = kernel32.GlobalAlloc(0x0002, len(data_png))
            pMem_png = kernel32.GlobalLock(hMem_png)
            ctypes.memmove(pMem_png, data_png, len(data_png))
            kernel32.GlobalUnlock(hMem_png)
            user32.SetClipboardData(png_format, hMem_png)
            
            user32.CloseClipboard()
        except Exception as e:
            print(f"OS Clipboard error: {e}")
            try:
                ctypes.windll.user32.CloseClipboard()
            except Exception:
                pass

    def copy_selection(self):
        if not self.layers:
            return False
            
        if self.sel_floating is not None:
            self.clipboard_image = self.sel_floating.copy()
            self._copy_to_os_clipboard(self.clipboard_image)  # <-- Push to Windows
            self.on_status("Selection copied to system clipboard")
            return True
        elif self.sel_active and self.sel_rect is not None:
            x0, y0, x1, y1 = self._norm_rect(self.sel_rect)
            self.clipboard_image = self.layers[self.active_layer].crop((x0, y0, x1, y1))
            self._copy_to_os_clipboard(self.clipboard_image)  # <-- Push to Windows
            self.on_status("Selection copied to system clipboard")
            return True
        else:
            self.on_status("Nothing selected to copy")
            return False

    def paste_selection(self):
        # Try to intercept pixel data directly from the Windows OS clipboard first
        from PIL import ImageGrab
        try:
            os_clip = ImageGrab.grabclipboard()
            if isinstance(os_clip, Image.Image):
                self.clipboard_image = os_clip.convert("RGBA")
            # Bonus: If the user copied an image file from Windows Explorer, intercept the file path and open it
            elif isinstance(os_clip, list) and len(os_clip) > 0 and isinstance(os_clip[0], str):
                try:
                    self.clipboard_image = Image.open(os_clip[0]).convert("RGBA")
                except Exception:
                    pass
        except Exception:
            pass

        if not getattr(self, "clipboard_image", None):
            self.on_status("Clipboard is empty")
            return False
            
        # If we are already dragging something else, commit it to the canvas first
        if self.sel_floating is not None:
            self._commit_floating_selection()
            
        self._push_state()
        
        # Load the clipboard image as a new floating selection
        self.sel_floating = self.clipboard_image.copy()
        
        # Calculate coordinates to paste it near the top-left of the user's current scroll view
        x0 = int(self.canvas.canvasx(0) / self.zoom)
        y0 = int(self.canvas.canvasy(0) / self.zoom)
        
        self.sel_offset = (x0, y0)
        x1 = x0 + self.sel_floating.width
        y1 = y0 + self.sel_floating.height
        
        self.sel_rect = (x0, y0, x1, y1)
        self.sel_active = True
        self.tool = ToolType.MOVE
        
        self._mark_dirty()
        self._refresh_display()
        self.on_status("Pasted selection from system clipboard")
        return True

    # ---------- Events ----------
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

        # REMOVED self._push_state() from here
        
        # Track that a drawing action has started (excluding tools that don't draw)
        if self.tool not in (ToolType.TEXT, ToolType.EYEDROPPER):
            self.is_drawing = True

        if self.tool == ToolType.PENCIL:
            self._draw_point(ix, iy, self.color)
        elif self.tool == ToolType.ERASER:
            self._draw_point(ix, iy, (0, 0, 0, 0))
        elif self.tool == ToolType.EYEDROPPER:
            comp = self._get_composite_with_preview() or self.get_composite()
            if comp:
                try:
                    # Explicitly lock the coordinates to target pixel integers
                    cx = max(0, min(int(ix), comp.width - 1))
                    cy = max(0, min(int(iy), comp.height - 1))
                    r, g, b, a = comp.getpixel((cx, cy))
                    self.set_color((r, g, b, a))
                except Exception as e:
                    print(f"Eyedropper sample failed: {e}")
        elif self.tool == ToolType.FILL:
            flood_fill(self.layers[self.active_layer], (ix, iy), self.color, tolerance=self.fill_tolerance)
        elif self.tool == ToolType.MAGIC_ERASER:
            r, g, b, a = self.layers[self.active_layer].getpixel((ix, iy))
            flood_fill(self.layers[self.active_layer], (ix, iy), (r, g, b, 0), tolerance=self.fill_tolerance)
        elif self.tool == ToolType.SELECTION:
            # Deselect if clicking on a new area without dragging
            self.sel_active = True
            self.sel_start = (ix, iy)
            self.sel_rect = None  # Don't create a 1x1 box yet; wait for drag
        elif self.tool == ToolType.MOVE:
            if self.sel_floating is None and self.sel_rect and self._point_in_rect((ix, iy), self.sel_rect):
                x0, y0, x1, y1 = self._norm_rect(self.sel_rect)
                box = (x0, y0, x1, y1)
                self.sel_floating = self.layers[self.active_layer].crop(box)
                draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
                draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
                self.sel_offset = (x0, y0)
                self.sel_rect = (x0, y0, x1, y1)
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
        elif self.tool == ToolType.SELECTION and self.sel_active:
            # Only start the rectangle once the mouse has moved from the start point
            if self.sel_start:
                x0, y0 = self.sel_start
                self.sel_rect = (x0, y0, ix, iy)
        elif self.tool == ToolType.MOVE and self.sel_floating is not None:
            dx = ix - self.last_pos[0]
            dy = iy - self.last_pos[1]
            self.sel_offset = (self.sel_offset[0] + dx, self.sel_offset[1] + dy)

            # Keep the visible selection box aligned with the floating selection
            x0, y0 = self.sel_offset
            x1 = x0 + self.sel_floating.width
            y1 = y0 + self.sel_floating.height
            self.sel_rect = (x0, y0, x1, y1)
        elif self.tool in (ToolType.SHAPE_LINE, ToolType.SHAPE_RECT, ToolType.SHAPE_ELLIPSE) and self.shape_start:
            self._update_shape_preview(self.shape_start, (ix, iy))

        self.last_pos = (ix, iy)
        self._mark_dirty()
        self._refresh_display()

    def _on_mouse_up(self, event):
        if not self.layers:
            return
        
        # If we clicked but never dragged (sel_rect is still None), clear selection
        if self.tool == ToolType.SELECTION and self.sel_active and self.sel_rect is None:
            self.clear_selection()
            
        if self.tool in (ToolType.SHAPE_LINE, ToolType.SHAPE_RECT, ToolType.SHAPE_ELLIPSE) and self.shape_start:
            self._commit_shape(self.shape_start, self.last_pos)
            self.shape_start = None
            self.preview_image = None
            
        # ADD THIS BLOCK to save the state AFTER the stroke is finished
        if getattr(self, "is_drawing", False):
            self._push_state()
            self.is_drawing = False
            
        self._mark_dirty()
        self._refresh_display()

    def _on_mouse_wheel(self, event):
        ctrl = (event.state & 0x4) != 0
        shift = (event.state & 0x1) != 0

        if not ctrl:
            # Check if Shift is held OR if horizontal scroll buttons (6/7) are triggered
            if shift or getattr(event, "num", 0) in (6, 7):
                if hasattr(event, "delta") and event.delta != 0:
                    dx = -1 if event.delta > 0 else 1
                    self.canvas.xview_scroll(dx, "units")
                else:
                    if getattr(event, "num", 0) in (4, 6):
                        self.canvas.xview_scroll(-1, "units")
                    elif getattr(event, "num", 0) in (5, 7):
                        self.canvas.xview_scroll(1, "units")
            else:
                if hasattr(event, "delta") and event.delta != 0:
                    dy = -1 if event.delta > 0 else 1
                    self.canvas.yview_scroll(dy, "units")
                else:
                    if getattr(event, "num", 0) == 4:
                        self.canvas.yview_scroll(-1, "units")
                    elif getattr(event, "num", 0) == 5:
                        self.canvas.yview_scroll(1, "units")
            return
            
        delta = 0
        if hasattr(event, "delta") and event.delta != 0:
            delta = 1 if event.delta > 0 else -1
        else:
            if getattr(event, "num", 0) == 4:
                delta = 1
            elif getattr(event, "num", 0) == 5:
                delta = -1
                
        if delta != 0:
            new_zoom = clamp(self.zoom + delta, 1, 16)
            if new_zoom != self.zoom:
                cx = self.canvas.canvasx(event.x)
                cy = self.canvas.canvasy(event.y)
                old_zoom = self.zoom
                
                self.set_zoom(new_zoom)
                
                scale = new_zoom / old_zoom
                new_cx = cx * scale
                new_cy = cy * scale
                
                # Run the view adjustment 1ms later so Tkinter has time to process the new boundaries smoothly
                def adjust_view():
                    # Calculate total virtual bounds mathematically (bypassing bbox which is now cropped)
                    total_w = self.width() * new_zoom
                    total_h = self.height() * new_zoom
                    cw = max(1, self.canvas.winfo_width())
                    ch = max(1, self.canvas.winfo_height())
                    
                    sr_w = max(total_w, cw)
                    sr_h = max(total_h, ch)
                    
                    if total_w > cw:
                        self.canvas.xview_moveto((new_cx - event.x) / sr_w)
                    if total_h > ch:
                        self.canvas.yview_moveto((new_cy - event.y) / sr_h)
                            
                self.canvas.after(1, adjust_view)

    # ---------- Drawing helpers ----------
    def _draw_point(self, x, y, color):
        if not (0 <= x < self.width() and 0 <= y < self.height()):
            return
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        half = self.brush_size // 2
        
        if self.brush_size <= 1:
            draw.point((x, y), fill=color)
        else:
            # Strict integer pixel bounding box configuration
            bbox = [x - half, y - half, x + half, y + half]
            draw.ellipse(bbox, fill=color)

    def _draw_text(self, x, y, text, size_px):
        self._push_state()
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")
        
        font = None
        # Check common cross-platform font fallbacks
        for font_name in ["arial.ttf", "calibri.ttf", "Helvetica.ttf", "DejaVuSans.ttf"]:
            try:
                font = ImageFont.truetype(font_name, size_px)
                break
            except IOError:
                continue
                
        if font is None:
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

        # Normalize the coordinates instantly to allow multi-directional drawing
        x0, y0, x1, y1 = self._norm_rect((start[0], start[1], end[0], end[1]))

        if self.tool == ToolType.SHAPE_LINE:
            # Lines don't require sorting, use original track points
            draw.line([start[0], start[1], end[0], end[1]], fill=self.color, width=self.brush_size)
        elif self.tool == ToolType.SHAPE_RECT:
            if self.shape_fill:
                draw.rectangle([x0, y0, x1, y1], fill=self.color, outline=self.color, width=self.brush_size)
            else:
                draw.rectangle([x0, y0, x1, y1], outline=self.color, width=self.brush_size)
        elif self.tool == ToolType.SHAPE_ELLIPSE:
            if self.shape_fill:
                draw.ellipse([x0, y0, x1, y1], fill=self.color, outline=self.color, width=self.brush_size)
            else:
                draw.ellipse([x0, y0, x1, y1], outline=self.color, width=self.brush_size)

    def _commit_shape(self, start, end):
        draw = ImageDraw.Draw(self.layers[self.active_layer], "RGBA")

        # Normalize coordinates before final commitment to the layer
        x0, y0, x1, y1 = self._norm_rect((start[0], start[1], end[0], end[1]))

        if self.tool == ToolType.SHAPE_LINE:
            draw.line([start[0], start[1], end[0], end[1]], fill=self.color, width=self.brush_size)
            self.on_status("Line drawn")
        elif self.tool == ToolType.SHAPE_RECT:
            if self.shape_fill:
                draw.rectangle([x0, y0, x1, y1], fill=self.color, outline=self.color, width=self.brush_size)
                self.on_status("Filled rectangle drawn")
            else:
                draw.rectangle([x0, y0, x1, y1], outline=self.color, width=self.brush_size)
                self.on_status("Rectangle drawn")
        elif self.tool == ToolType.SHAPE_ELLIPSE:
            if self.shape_fill:
                draw.ellipse([x0, y0, x1, y1], fill=self.color, outline=self.color, width=self.brush_size)
                self.on_status("Filled ellipse drawn")
            else:
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

    # ---------- BG transparency ----------
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
    def _compose_display_image(self, ix0=0, iy0=0, ix1=None, iy1=None):
        if not self.layers:
            return None
        comp = self._get_composite_with_preview()
        if comp is None:
            return None

        # 1. Handle or initialize the background checkerboard cache
        if self._bg_cache is None or self._bg_cache.size != comp.size:
            self._bg_cache = create_checkerboard((comp.width, comp.height), square_size=8).convert("RGBA")
            
        composed = Image.alpha_composite(self._bg_cache, comp)

        # 2. Crop to the active visible viewport
        if ix1 is None: ix1 = comp.width
        if iy1 is None: iy1 = comp.height
        
        ix0 = max(0, min(ix0, comp.width))
        iy0 = max(0, min(iy0, comp.height))
        ix1 = max(0, min(ix1, comp.width))
        iy1 = max(0, min(iy1, comp.height))
        
        if ix0 >= ix1 or iy0 >= iy1:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            
        cropped = composed.crop((ix0, iy0, ix1, iy1))
        
        # 3. Scale only the small cropped chunk
        if self.zoom != 1:
            scaled = cropped.resize((cropped.width * self.zoom, cropped.height * self.zoom), Image.NEAREST)
        else:
            scaled = cropped
            
        # 4. Apply the Selection Marquee on top of the scaled chunk
        draw = ImageDraw.Draw(scaled)
        if self.sel_active:
            if self.sel_floating is not None:
                sx0, sy0 = self.sel_offset
                sx1 = sx0 + self.sel_floating.width
                sy1 = sy0 + self.sel_floating.height
            elif self.sel_rect:
                sx0, sy0, sx1, sy1 = self._norm_rect(self.sel_rect)
            else:
                sx0 = sy0 = sx1 = sy1 = None

            if sx0 is not None:
                # Map global unscaled coordinates to local cropped & scaled coordinates
                rx0 = (sx0 - ix0) * self.zoom
                ry0 = (sy0 - iy0) * self.zoom
                rx1 = (sx1 - ix0 + 1) * self.zoom
                ry1 = (sy1 - iy0 + 1) * self.zoom
                draw.rectangle([rx0, ry0, rx1, ry1], outline=(0, 200, 255, 255), width=1)

        # 5. Lay down the guide grid lines safely
        if self.show_grid and self.zoom >= 4:
            w, h = scaled.size
            for x in range(0, w, self.zoom):
                draw.line([(x, 0), (x, h)], fill=(0, 0, 0, 40))
            for y in range(0, h, self.zoom):
                draw.line([(0, y), (w, y)], fill=(0, 0, 0, 40))
                
        return scaled

    def _refresh_display(self):
        # Prevent recursive calls caused by config(scrollregion=...)
        if getattr(self, "_is_refreshing", False):
            return
        self._is_refreshing = True
        
        try:
            if not self.layers:
                return

            comp_w = self.width()
            comp_h = self.height()
            total_w = comp_w * self.zoom
            total_h = comp_h * self.zoom

            cw = max(1, self.canvas.winfo_width())
            ch = max(1, self.canvas.winfo_height())

            sr_w = max(total_w, cw)
            sr_h = max(total_h, ch)

            # 1. Update the scroll bounds ONLY if they actually changed to prevent event flooding
            current_sr = self.canvas.cget("scrollregion")
            needs_sr_update = True
            if current_sr:
                try:
                    if tuple(map(int, str(current_sr).split())) == (0, 0, sr_w, sr_h):
                        needs_sr_update = False
                except Exception:
                    pass
            
            if needs_sr_update:
                self.canvas.config(scrollregion=(0, 0, sr_w, sr_h))

            # Get the visible viewport in scaled pixels
            vx0 = max(0, int(self.canvas.canvasx(0)))
            vy0 = max(0, int(self.canvas.canvasy(0)))
            vx1 = vx0 + cw
            vy1 = vy0 + ch

            # Convert to unscaled image bounds (expand by 1 to cover edges cleanly)
            ix0 = vx0 // self.zoom
            iy0 = vy0 // self.zoom
            ix1 = (vx1 // self.zoom) + 1
            iy1 = (vy1 // self.zoom) + 1

            composed = self._compose_display_image(ix0, iy0, ix1, iy1)
            if composed is None:
                return

            self._display_image = ImageTk.PhotoImage(composed)

            # Map the unscaled start coordinates back to scaled canvas coordinates
            anchor_x = ix0 * self.zoom
            anchor_y = iy0 * self.zoom

            if getattr(self, "_canvas_image_id", None) is None:
                self._canvas_image_id = self.canvas.create_image(anchor_x, anchor_y, image=self._display_image, anchor="nw")
            else:
                self.canvas.itemconfig(self._canvas_image_id, image=self._display_image)
                self.canvas.coords(self._canvas_image_id, anchor_x, anchor_y)
                
            # Note: xview_moveto(0) and yview_moveto(0) were completely removed here 
            # to fix the infinite event queue lockup. Tkinter automatically pins 
            # undersized canvases to 0,0 based on the scrollregion anyway.
                
        finally:
            self._is_refreshing = False
