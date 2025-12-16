from PIL import Image


def default_icon_sizes() -> list[int]:
    return [16, 24, 32, 48, 64, 128, 256]


def get_resample_by_name(name: str):
    lname = (name or "").lower()
    try:
        Resampling = Image.Resampling  # type: ignore
        if lname == "nearest":
            return Resampling.NEAREST
        elif lname == "bilinear":
            return Resampling.BILINEAR
        elif lname == "bicubic":
            return Resampling.BICUBIC
        else:
            return Resampling.LANCZOS
    except Exception:
        if lname == "nearest":
            return Image.NEAREST
        elif lname == "bilinear":
            return Image.BILINEAR
        elif lname == "bicubic":
            return Image.BICUBIC
        else:
            return Image.LANCZOS


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def human_readable_size(bytes_count: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    i = 0
    v = float(bytes_count)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.2f} {units[i]}"


def parse_sizes_list(s: str) -> list[int]:
    if not s:
        return []
    out = []
    for token in s.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            val = int(token)
            if 1 <= val <= 1024:
                out.append(val)
        except Exception:
            pass
    return out
