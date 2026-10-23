"""Tạo bộ biểu tượng cài ứng dụng (PWA) từ một ảnh gốc.

    python frontend/scripts/make-app-icons.py logo.png --out frontend/public/brand --bg "#ffffff"

Tạo icon-192x192.png, icon-512x512.png, apple-touch-icon.png (180x180). Ảnh được đặt giữa
nền màu và chừa lề 10% mỗi cạnh để không bị cắt khi Android bo tròn (maskable).
Dùng --full-bleed nếu ảnh gốc đã là hình vuông tràn viền có nền sẵn.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor

SIZES = {"icon-192x192.png": 192, "icon-512x512.png": 512, "apple-touch-icon.png": 180}


def build(source: Image.Image, size: int, background: str, full_bleed: bool) -> Image.Image:
    canvas = Image.new("RGB", (size, size), ImageColor.getrgb(background))
    box = size if full_bleed else round(size * 0.8)
    art = source.copy()
    art.thumbnail((box, box), Image.LANCZOS)
    canvas.paste(art, ((size - art.width) // 2, (size - art.height) // 2), art)
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Ảnh gốc (PNG/JPG/WebP), nên vuông và >= 512px")
    parser.add_argument("--out", type=Path, default=Path("frontend/public/brand"), help="Thư mục xuất ảnh")
    parser.add_argument("--bg", default="#ffffff", help="Màu nền dạng #rrggbb")
    parser.add_argument("--full-bleed", action="store_true", help="Phóng ảnh tràn viền, không chừa lề")
    args = parser.parse_args()
    if not args.source.is_file():
        print(f"Không thấy ảnh: {args.source}", file=sys.stderr)
        return 1
    source = Image.open(args.source).convert("RGBA")
    if min(source.size) < 256:
        print("Cảnh báo: ảnh gốc nhỏ hơn 256px nên icon có thể bị mờ.", file=sys.stderr)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        build(source, size, args.bg, args.full_bleed).save(args.out / name, "PNG", optimize=True)
        print(f"Đã tạo {args.out / name}")
    print("Tiếp theo: đặt NEXT_PUBLIC_BRAND_ICON_DIR=/" + args.out.name + " và tăng NEXT_PUBLIC_BRAND_ICON_VERSION rồi build lại.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
