export const APP_ICON_VERSION = "20261023";
export const APP_ICONS = [192, 512].flatMap((size) => [
  { src: `/icons/icon-${size}x${size}.png?v=${APP_ICON_VERSION}`, sizes: `${size}x${size}`, type: "image/png", purpose: "any" as const },
  { src: `/icons/icon-${size}x${size}.png?v=${APP_ICON_VERSION}`, sizes: `${size}x${size}`, type: "image/png", purpose: "maskable" as const },
]);
