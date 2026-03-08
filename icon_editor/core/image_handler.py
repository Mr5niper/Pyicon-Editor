from pathlib import Path
from tkinter import filedialog
from PIL import Image

SUPPORTED_INPUTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".ico")


def load_image_with_alpha(path: str | Path, max_edit_dimension: int | None = None) -> Image.Image:
    """
    Load an image and convert to RGBA. Optionally downscale so max(width, height) <= max_edit_dimension
    for responsive editing with very large source images.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() not in SUPPORTED_INPUTS:
        raise ValueError(f"Unsupported format: {p.suffix}")
    img = Image.open(p)
    img = img.convert("RGBA")
    if max_edit_dimension and max(img.width, img.height) > max_edit_dimension:
        scale = max_edit_dimension / max(img.width, img.height)
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        img = img.resize(new_size, Image.LANCZOS)
    return img


def save_png(image: Image.Image, out_path: str | Path):
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    image.save(p, format="PNG", optimize=True)


def open_image_dialog(parent) -> str | None:
    path = filedialog.askopenfilename(
        parent=parent,
        title="Open Image",
        filetypes=[
            ("All supported", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff;*.webp;*.ico"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("Bitmap", "*.bmp"),
            ("GIF", "*.gif"),
            ("TIFF", "*.tif;*.tiff"),
            ("WebP", "*.webp"),
            ("ICO", "*.ico"),
            ("All files", "*.*"),
        ],
    )
    return path or None


def save_png_dialog(parent, initialfile: str | None = None) -> str | None:
    path = filedialog.asksaveasfilename(
        parent=parent,
        title="Save PNG",
        defaultextension=".png",
        initialfile=initialfile or "image.png",
        filetypes=[("PNG", "*.png")],
    )
    return path or None
