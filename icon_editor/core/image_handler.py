from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk

import os
import ctypes
from ctypes import wintypes

SUPPORTED_INPUTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".ico", ".exe", ".dll")

def _extract_icon_from_exe_windows(path: str | Path) -> Image.Image:
    """
    Extract the largest embedded icon from a Windows EXE/DLL and return it as RGBA PIL image.
    Windows-only. Raises RuntimeError on failure.
    """
    if os.name != "nt":
        raise RuntimeError("EXE/DLL icon extraction is only supported on Windows.")

    p = str(Path(path).resolve())

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Switch to PrivateExtractIconsW to bypass the 32x32 limit and force 256x256 extraction
    PrivateExtractIconsW = user32.PrivateExtractIconsW
    DestroyIcon = user32.DestroyIcon
    GetDC = user32.GetDC
    ReleaseDC = user32.ReleaseDC
    GetIconInfo = user32.GetIconInfo
    GetObjectW = gdi32.GetObjectW
    GetDIBits = gdi32.GetDIBits
    DeleteObject = gdi32.DeleteObject

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    class BITMAP(ctypes.Structure):
        _fields_ = [
            ("bmType", wintypes.LONG),
            ("bmWidth", wintypes.LONG),
            ("bmHeight", wintypes.LONG),
            ("bmWidthBytes", wintypes.LONG),
            ("bmPlanes", wintypes.WORD),
            ("bmBitsPixel", wintypes.WORD),
            ("bmBits", wintypes.LPVOID),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", wintypes.DWORD * 3),
        ]

    PrivateExtractIconsW.argtypes = [
        wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT),
        wintypes.UINT, wintypes.UINT
    ]
    PrivateExtractIconsW.restype = wintypes.UINT

    DestroyIcon.argtypes = [wintypes.HICON]
    DestroyIcon.restype = wintypes.BOOL

    GetDC.argtypes = [wintypes.HWND]
    GetDC.restype = wintypes.HDC

    ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    ReleaseDC.restype = ctypes.c_int

    GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
    GetIconInfo.restype = wintypes.BOOL

    GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID]
    GetObjectW.restype = ctypes.c_int

    GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        wintypes.LPVOID, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ]
    GetDIBits.restype = ctypes.c_int

    DeleteObject.argtypes = [wintypes.HGDIOBJ]
    DeleteObject.restype = wintypes.BOOL

    def hicon_to_image(hicon) -> Image.Image | None:
        if not hicon:
            return None
        iconinfo = ICONINFO()
        if not GetIconInfo(hicon, ctypes.byref(iconinfo)):
            return None
        try:
            bmp_handle = iconinfo.hbmColor or iconinfo.hbmMask
            if not bmp_handle:
                return None
            bmp = BITMAP()
            if not GetObjectW(bmp_handle, ctypes.sizeof(BITMAP), ctypes.byref(bmp)):
                return None
            width, height = int(bmp.bmWidth), int(bmp.bmHeight)
            if width <= 0 or height <= 0:
                return None

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0
            buf_len = width * height * 4
            pixel_data = (ctypes.c_ubyte * buf_len)()
            hdc = GetDC(None)
            if not hdc:
                return None
            try:
                scanlines = GetDIBits(hdc, bmp_handle, 0, height, ctypes.byref(pixel_data), ctypes.byref(bmi), 0)
                if scanlines == 0:
                    return None
                
                image = Image.frombuffer("RGBA", (width, height), bytes(pixel_data), "raw", "BGRA", 0, 1)
                image = image.convert("RGBA")
                
                # FIX: If the alpha channel is empty, read the actual embedded hbmMask.
                # This guarantees we only make the intended background transparent, preserving real black pixels.
                if image.getextrema()[3][1] == 0 and iconinfo.hbmColor and iconinfo.hbmMask:
                    mask_data = (ctypes.c_ubyte * buf_len)()
                    mask_scanlines = GetDIBits(hdc, iconinfo.hbmMask, 0, height, ctypes.byref(mask_data), ctypes.byref(bmi), 0)
                    if mask_scanlines > 0:
                        mask_img = Image.frombuffer("RGBA", (width, height), bytes(mask_data), "raw", "BGRA", 0, 1)
                        # In the mask: White (255) means transparent, Black (0) means opaque.
                        # We convert it to grayscale, invert it so 255 becomes opaque, and set it as the alpha channel.
                        alpha = mask_img.convert("L").point(lambda x: 255 - x)
                        image.putalpha(alpha)
                        
                return image
            finally:
                ReleaseDC(None, hdc)
        finally:
            if iconinfo.hbmColor: DeleteObject(iconinfo.hbmColor)
            if iconinfo.hbmMask: DeleteObject(iconinfo.hbmMask)

    # 1. Ask Windows how many icon resources exist
    count = PrivateExtractIconsW(p, 0, 0, 0, None, None, 0, 0)
    if count <= 0:
        raise RuntimeError(f"No icon found in: {p}")

    icon_ids = (wintypes.UINT * count)()

    # 2. Extract multiple fallback resolutions. 
    # If Windows aggressively over-stretches a small icon to 256x256, it corrupts the transparency.
    # We test descending sizes to find the absolute largest version of each icon that isn't corrupted.
    sizes_to_try = [256, 128, 64, 48, 32, 16]
    hicon_arrays = {}
    
    for sz in sizes_to_try:
        arr = (wintypes.HICON * count)()
        PrivateExtractIconsW(p, 0, sz, sz, arr, icon_ids, count, 0)
        hicon_arrays[sz] = arr

    extracted_icons = []
    try:
        for i in range(count):
            best_img = None
            for sz in sizes_to_try:
                hicon = hicon_arrays[sz][i]
                if hicon:
                    try:
                        img = hicon_to_image(hicon)
                        # If the alpha channel isn't completely invisible, it survived extraction!
                        if img and img.getextrema()[3][1] > 0:
                            best_img = img
                            break  # Found the largest valid frame, stop trying smaller sizes
                    except Exception:
                        pass
            
            if best_img:
                extracted_icons.append(best_img)
    finally:
        for sz in sizes_to_try:
            for i in range(count):
                if hicon_arrays[sz][i]:
                    DestroyIcon(hicon_arrays[sz][i])

    if not extracted_icons:
        raise RuntimeError(f"Failed to decode any valid icon image from: {p}")

    # 3. Spawn popup dialog to let the user choose which icon to open
    import tkinter as tk
    from tkinter import ttk
    from PIL import ImageTk

    top = tk.Toplevel()
    top.title("Select Icon")
    top.geometry("450x350")
    top.minsize(300, 200)
    top.grab_set()  # Make it modal
    top.focus_set()

    sys_bg = "#f0f0f0"
    top.configure(bg=sys_bg)

    style = ttk.Style()
    style.configure("IconPopup.TFrame", background=sys_bg)
    style.configure("IconPopup.TLabel", background=sys_bg, foreground="black")

    # FIX: Explicitly override the border colors to soft gray (#b8b8b8) so Dark Mode doesn't draw thick black lines
    style.configure(
        "IconPopup.Vertical.TScrollbar",
        background=sys_bg,
        troughcolor=sys_bg,
        bordercolor="#b8b8b8",
        arrowcolor="black",
        lightcolor=sys_bg,
        darkcolor=sys_bg
    )
    style.map(
        "IconPopup.Vertical.TScrollbar",
        background=[("active", "#e8e8e8"), ("pressed", "#dcdcdc")]
    )

    style.configure(
        "IconPopup.TButton",
        background="#ffffff",
        foreground="black",
        bordercolor="#b8b8b8",
        lightcolor="#ffffff",
        darkcolor="#ffffff"
    )
    style.map(
        "IconPopup.TButton",
        background=[("active", "#e8e8e8"), ("pressed", "#dcdcdc")]
    )

    lbl = ttk.Label(top, text="Select which embedded icon to extract:", font=("Arial", 10, "bold"), style="IconPopup.TLabel")
    lbl.pack(pady=(10, 5), padx=10, anchor="w")

    container = ttk.Frame(top, style="IconPopup.TFrame")
    container.pack(fill="both", expand=True, padx=10, pady=10)

    canvas = tk.Canvas(container, bg=sys_bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview, style="IconPopup.Vertical.TScrollbar")
    scrollable_frame = ttk.Frame(canvas, style="IconPopup.TFrame")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(event):
        if canvas.bbox("all") and canvas.bbox("all")[3] > canvas.winfo_height():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
    top.bind("<MouseWheel>", _on_mousewheel)

    selected_index = tk.IntVar(value=-1)
    photo_images = []  

    row, col = 0, 0
    max_cols = 4

    for idx, img in enumerate(extracted_icons):
        thumb = img.copy()
        thumb.thumbnail((64, 64), Image.LANCZOS)
        photo = ImageTk.PhotoImage(thumb)
        photo_images.append(photo)

        btn = ttk.Button(
            scrollable_frame, 
            image=photo,
            style="IconPopup.TButton",
            command=lambda i=idx: (selected_index.set(i), top.destroy())
        )
        btn.grid(row=row, column=col, padx=8, pady=8)
        
        col += 1
        if col >= max_cols:
            col = 0
            row += 1

    top.wait_window()

    final_idx = selected_index.get()
    if final_idx == -1:
        return None  # Return None to indicate the user cancelled

    return extracted_icons[final_idx]
    
def load_image_with_alpha(path: str | Path, max_edit_dimension: int | None = None) -> Image.Image:
    """
    Load an image and convert to RGBA. Supports standard image files, ICO, and
    Windows EXE/DLL icon extraction. Optionally downscale so max(width, height)
    <= max_edit_dimension for responsive editing with very large source images.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if p.suffix.lower() not in SUPPORTED_INPUTS:
        raise ValueError(f"Unsupported format: {p.suffix}")

    suffix = p.suffix.lower()

    if suffix in (".exe", ".dll"):
        img = _extract_icon_from_exe_windows(p)
        if img is None:
            return None  # Pass the cancellation up the chain
    else:
        img = Image.open(p).convert("RGBA")

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
        title="Open Image or App Icon",
        filetypes=[
            ("All supported", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff;*.webp;*.ico;*.exe;*.dll"),
            ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff;*.webp"),
            ("Windows Icons", "*.ico"),
            ("Windows Executables / Libraries", "*.exe;*.dll"),
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
