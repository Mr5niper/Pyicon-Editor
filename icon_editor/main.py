import sys
import os
import argparse
from pathlib import Path

# Ensure local package import
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from gui.main_window import run_app
from core.image_handler import load_image_with_alpha
from core.icon_generator import prepare_image_for_size, save_ico_from_images
from utils.helpers import parse_sizes_list


def run_cli_single(args):
    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    try:
        img = load_image_with_alpha(input_path, max_edit_dimension=args.max_dim)
    except Exception as e:
        print(f"Error: Failed to load image: {e}")
        sys.exit(1)

    sizes = parse_sizes_list(args.sizes) if args.sizes else [16, 24, 32, 48, 64, 128, 256]
    if not sizes:
        print("Error: No sizes specified.")
        sys.exit(1)
    resample_name = args.resample or "lanczos"

    prepared = []
    for s in sorted(set(sizes), reverse=True):
        prepared.append((s, prepare_image_for_size(
            img, s, resample_name,
            maintain_aspect=(not args.no_aspect),
            pad_to_square=True
        )))

    try:
        save_ico_from_images(prepared, output_path)
    except Exception as e:
        print(f"Error: Failed to export ICO: {e}")
        sys.exit(1)

    if args.export_pngs:
        png_dir = output_path.parent / f"{output_path.stem}_png"
        png_dir.mkdir(parents=True, exist_ok=True)
        for sz, im in prepared:
            out_png = png_dir / f"{output_path.stem}_{sz}.png"
            im.save(out_png, format="PNG", optimize=True)
        print(f"Saved PNG set to: {png_dir}")

    print(f"Exported ICO: {output_path}")


def run_cli_batch(args):
    in_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir) if args.out_dir else in_dir / "ico_output"
    pattern = args.pattern or "*.png"
    if not in_dir.exists():
        print(f"Error: Input directory not found: {in_dir}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    sizes = parse_sizes_list(args.sizes) if args.sizes else [16, 24, 32, 48, 64, 128, 256]
    if not sizes:
        print("Error: No sizes specified.")
        sys.exit(1)
    resample_name = args.resample or "lanczos"

    count = 0
    for path in in_dir.rglob(pattern):
        if not path.is_file():
            continue
        try:
            img = load_image_with_alpha(path, max_edit_dimension=args.max_dim)
        except Exception as e:
            print(f"[SKIP] {path.name}: {e}")
            continue

        prepared = []
        for s in sorted(set(sizes), reverse=True):
            prepared.append((s, prepare_image_for_size(
                img, s, resample_name,
                maintain_aspect=(not args.no_aspect),
                pad_to_square=True
            )))

        out_ico = out_dir / f"{path.stem}.ico"
        try:
            save_ico_from_images(prepared, out_ico)
            if args.export_pngs:
                png_dir = out_dir / f"{path.stem}_png"
                png_dir.mkdir(parents=True, exist_ok=True)
                for sz, im in prepared:
                    (png_dir / f"{path.stem}_{sz}.png").write_bytes(pil_to_png_bytes(im))
            print(f"[OK] {path.name} -> {out_ico.name}")
            count += 1
        except Exception as e:
            print(f"[FAIL] {path.name}: {e}")
    print(f"Batch complete. {count} icons exported to {out_dir}")


def pil_to_png_bytes(im):
    from io import BytesIO
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Icon Creator & Editor")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode")
    parser.add_argument("--input", type=str, help="Input image path (for single export)")
    parser.add_argument("--output", type=str, help="Output .ico path (for single export)")
    parser.add_argument("--sizes", type=str, help="Comma-separated sizes (e.g., 16,32,48,256)")
    parser.add_argument("--resample", type=str, default="lanczos",
                        choices=["nearest", "bilinear", "bicubic", "lanczos"],
                        help="Resampling algorithm")
    parser.add_argument("--no-aspect", action="store_true", help="Do not maintain aspect ratio (stretches)")
    parser.add_argument("--export-pngs", action="store_true", help="Also export PNG set for each size")
    parser.add_argument("--max-dim", type=int, default=3072, help="Max dimension to downscale large images for editing (CLI)")

    # Batch mode
    parser.add_argument("--input-dir", type=str, help="Input directory for batch")
    parser.add_argument("--pattern", type=str, help="Glob pattern for input (e.g., '*.png')")
    parser.add_argument("--out-dir", type=str, help="Output directory for batch output")

    args = parser.parse_args()

    if args.cli:
        if args.input_dir:
            run_cli_batch(args)
            return
        if not args.input or not args.output:
            parser.error("--cli requires --input and --output (or use --input-dir for batch mode)")
        run_cli_single(args)
        return

    # GUI mode
    try:
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI Aware
            except Exception:
                pass
    except Exception:
        pass
    run_app()


if __name__ == "__main__":
    main()
