import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SpaOS — Nền tảng Quản lý & Đặt lịch Spa chuẩn SaaS",
  description: "Hệ thống quản lý lịch hẹn, thẻ liệu trình và nhân sự cho Spa",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
