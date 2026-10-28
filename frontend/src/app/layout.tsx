import type { Metadata, Viewport } from "next";
import { getServerBranding } from "@/lib/server-branding";
import { brandStyle } from "@/lib/brand-theme";
import { APP_APPLE_ICON, APP_ICON_192, APP_ICON_512 } from "@/lib/app-icons";
import { BrandProvider } from "@/components/brand-provider";
import { PwaRegister } from "@/components/pwa-register";
import { headers } from "next/headers";
import "./globals.css";

const baseMetadata: Metadata = {
  title: "SpaOS - Đặt lịch & Quản lý Spa",
  description:
    "Đặt lịch spa, theo dõi thẻ liệu trình và nhận thông báo cập nhật lịch hẹn.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "SpaOS",
  },
  icons: {
    icon: [
      { url: APP_ICON_192, sizes: "192x192", type: "image/png" },
      { url: APP_ICON_512, sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: APP_APPLE_ICON, sizes: "180x180", type: "image/png" },
    ],
  },
};

export async function generateMetadata():Promise<Metadata> {
  const slug=headers().get("x-spa-slug");
  if(!slug)return baseMetadata;
  try{
    const response=await fetch((process.env.BACKEND_INTERNAL_URL||"http://localhost:8001")+"/api/v1/spas/public/"+encodeURIComponent(slug),{cache:"no-store",signal:AbortSignal.timeout(3000)});
    if(!response.ok)return {...baseMetadata,title:"Không tìm thấy spa"};
    const spa=await response.json() as {name:string;logo_url:string|null};
    return {...baseMetadata,title:spa.name,manifest:`/s/${slug}/manifest.webmanifest`,appleWebApp:{capable:true,title:spa.name,statusBarStyle:"default"},...(spa.logo_url?{icons:{icon:spa.logo_url,apple:spa.logo_url}}:{})};
  }catch{return {...baseMetadata,manifest:`/s/${slug}/manifest.webmanifest`};}
}

export async function generateViewport(): Promise<Viewport> {
  const brand = await getServerBranding();
  return {themeColor:brand.theme_color,width:"device-width",initialScale:1,interactiveWidget:"resizes-content"};
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): Promise<React.ReactElement> {
  const branding = await getServerBranding();
  return (
    <html lang="vi" style={brandStyle(branding.theme_color)}>
      <body className="min-h-screen bg-background text-foreground">
        <BrandProvider initialBranding={branding}><PwaRegister />{children}</BrandProvider>
      </body>
    </html>
  );
}
