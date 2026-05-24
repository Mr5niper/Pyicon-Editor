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
        if brush_size <= 1:
            draw.point((px, py), fill=color)
        else:
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
    w, h = image.size
    px = image.load()
    x, y = seed
    if x < 0 or y < 0 or x >= w or y >= h:
        return

    target = px[seed]
    if target == fill_color:
        return

    def close_enough(c1, c2):
        return (
            abs(c1[0] - c2[0]) <= tolerance and
            abs(c1[1] - c2[1]) <= tolerance and
            abs(c1[2] - c2[2]) <= tolerance and
            abs(c1[3] - c2[3]) <= tolerance
        )

    stack = [seed]
    while stack:
        cx, cy = stack.pop()
        if cx < 0 or cy < 0 or cx >= w or cy >= h:
            continue
            
        # 1. Check if the current pixel matches our target color group first
        if close_enough(px[cx, cy], target) and px[cx, cy] != fill_color:
            # 2. Paint the pixel safely AFTER the verification check passes
            px[cx, cy] = fill_color
            
            # 3. Queue up the neighboring coordinates
            stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
