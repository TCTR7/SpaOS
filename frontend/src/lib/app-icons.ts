/**
 * Biểu tượng cài ứng dụng của deployment này. Mỗi spa đặt bộ ảnh riêng trong thư mục
 * `public/<thư mục>/` rồi trỏ tới đó bằng biến môi trường lúc build, không cần sửa code:
 *   NEXT_PUBLIC_BRAND_ICON_DIR=/brand        (mặc định /icons)
 *   NEXT_PUBLIC_BRAND_ICON_VERSION=20261101  (đổi số này để điện thoại tải lại ảnh mới)
 * Thư mục cần có: icon-192x192.png, icon-512x512.png, apple-touch-icon.png (180x180).
 * Tạo đủ 3 ảnh từ 1 ảnh gốc: python frontend/scripts/make-app-icons.py logo.png --out frontend/public/brand
 */
const DIR = (process.env.NEXT_PUBLIC_BRAND_ICON_DIR || "/icons").replace(/\/+$/, "");
export const APP_ICON_VERSION = process.env.NEXT_PUBLIC_BRAND_ICON_VERSION || "20261023";
export const APP_ICON_192 = `${DIR}/icon-192x192.png?v=${APP_ICON_VERSION}`;
export const APP_ICON_512 = `${DIR}/icon-512x512.png?v=${APP_ICON_VERSION}`;
export const APP_APPLE_ICON = `${DIR}/apple-touch-icon.png?v=${APP_ICON_VERSION}`;
export const APP_ICONS = ([[192, APP_ICON_192], [512, APP_ICON_512]] as const).flatMap(([size, src]) => [
  { src, sizes: `${size}x${size}`, type: "image/png", purpose: "any" as const },
  { src, sizes: `${size}x${size}`, type: "image/png", purpose: "maskable" as const },
]);
