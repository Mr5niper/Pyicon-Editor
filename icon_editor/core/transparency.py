from PIL import Image


def create_checkerboard(size: tuple[int, int], square_size: int = 8) -> Image.Image:
    w, h = size
    bg = Image.new("RGB", (w, h), (192, 192, 192))
    px = bg.load()
    c1 = (220, 220, 220)
    c2 = (180, 180, 180)
    for y in range(h):
        for x in range(w):
            if ((x // square_size) + (y // square_size)) % 2 == 0:
                px[x, y] = c1
            else:
                px[x, y] = c2
    return bg
