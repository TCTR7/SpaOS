import { getServerBranding } from "@/lib/server-branding";
import type { MetadataRoute } from "next";

type PwaScreenshot = {
  src: string;
  sizes: string;
  type: string;
  form_factor: "wide" | "narrow";
  label: string;
};

export default async function manifest(): Promise<MetadataRoute.Manifest & {
  screenshots: PwaScreenshot[];
}> {
  const branding = await getServerBranding();
  return {
    id: "/",
    name: "Đặt lịch spa",
    short_name: "Đặt lịch spa",
    description:
      "Đặt lịch, theo dõi thẻ liệu trình và nhận cập nhật lịch hẹn tại spa.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: branding.theme_color,
    orientation: "portrait",
    icons: [
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    screenshots: [
      {
        src: "/screenshots/desktop-wide.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
        label: "Giao diện Quản lý & Đặt lịch SpaOS trên Desktop",
      },
      {
        src: "/screenshots/mobile-narrow.png",
        sizes: "540x720",
        type: "image/png",
        form_factor: "narrow",
        label: "Giao diện Đặt lịch SpaOS trên Điện thoại",
      },
    ],
  };
}
