from pathlib import Path
from tkinter import filedialog, messagebox, ttk, Toplevel, BooleanVar
from PIL import Image, ImageOps, ImageTk
from utils.helpers import get_resample_by_name


def prepare_image_for_size(base_image: Image.Image, size: int, resample_name: str, maintain_aspect: bool, pad_to_square: bool) -> Image.Image:
    """
    Always returns an RGBA image of exactly (size, size).
    If maintain_aspect True, the image is contained and centered on a transparent square.
    If False, the image is stretched to (size, size).
    """
    img = base_image.convert("RGBA")
    resample = get_resample_by_name(resample_name)
    if maintain_aspect:
        fitted = ImageOps.contain(img, (size, size), resample=resample)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - fitted.width) // 2
        y = (size - fitted.height) // 2
        out.paste(fitted, (x, y), fitted)
        return out
    else:
        return img.resize((size, size), resample=resample)


def save_ico_from_images(images_by_size: list[tuple[int, Image.Image]], out_path: Path):
    if not images_by_size:
        raise ValueError("No images to save.")
    images_sorted = sorted(images_by_size, key=lambda t: t[0], reverse=True)
    frames = [im.convert("RGBA") for _, im in images_sorted]
    sizes = [(im.width, im.height) for im in frames]
    base = frames[0]
    rest = frames[1:]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="ICO", append_images=rest, sizes=sizes)


def export_ico_dialog(parent, base_image: Image.Image, sizes: list[int], resample: str, maintain_aspect: bool):
    preview = Toplevel(parent)
    preview.title("Preview & Export ICO")
    preview.resizable(False, False)
    frm = ttk.Frame(preview, padding=10)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="Preview of generated sizes:").pack(anchor="w", pady=(0, 8))

    thumbs = []
    thumb_imgs = []
    for size in sizes:
        img = prepare_image_for_size(base_image, size, resample, maintain_aspect, pad_to_square=True)
        thumb = img.resize((min(128, size), min(128, size)), Image.NEAREST)
        tkimg = ImageTk.PhotoImage(thumb)
        line = ttk.Frame(frm)
        line.pack(fill="x", pady=4)
        ttk.Label(line, text=f"{size} x {size}").pack(side="left", padx=(0, 8))
        lbl = ttk.Label(line, image=tkimg)
        lbl.image = tkimg
        lbl.pack(side="left")
        thumbs.append((size, img))
        thumb_imgs.append(tkimg)

    png_var = BooleanVar(value=False)
    png_row = ttk.Frame(frm)
    png_row.pack(fill="x", pady=(10, 0))
    ttk.Checkbutton(png_row, text="Also export PNG set to folder (next to ICO)", variable=png_var).pack(anchor="w")

    btns = ttk.Frame(frm)
    btns.pack(fill="x", pady=(10, 0))

    def do_export():
        out_path_str = filedialog.asksaveasfilename(
            parent=parent,
            title="Export ICO",
            defaultextension=".ico",
            filetypes=[("Windows Icon", "*.ico")],
            initialfile="icon.ico",
        )
        if not out_path_str:
            return
        out_path = Path(out_path_str)
        try:
            images_sorted = sorted(thumbs, key=lambda t: t[0], reverse=True)
            save_ico_from_images(images_sorted, out_path)
            if png_var.get():
                png_dir = out_path.parent / f"{out_path.stem}_png"
                png_dir.mkdir(parents=True, exist_ok=True)
                for sz, im in images_sorted:
                    (png_dir / f"{out_path.stem}_{sz}.png").write_bytes(pil_to_png_bytes(im))
            messagebox.showinfo("Exported", f"ICO exported:\n{out_path}")
            preview.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export ICO:\n{e}")

    ttk.Button(btns, text="Export", command=do_export).pack(side="left")
    ttk.Button(btns, text="Cancel", command=preview.destroy).pack(side="left", padx=(8, 0))
    preview.grab_set()
    parent.wait_window(preview)


def pil_to_png_bytes(im: Image.Image) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
