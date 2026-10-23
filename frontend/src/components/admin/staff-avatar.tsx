"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

/** Ảnh đại diện nhân viên; hiện chữ cái đầu khi chưa có ảnh hoặc ảnh lỗi. */
export function StaffAvatar({ name, src, className }: { name: string; src?: string | null; className?: string }): React.ReactElement {
  const [failedSrc, setFailedSrc] = React.useState<string | null>(null);
  const initial = Array.from(name.trim().split(/\s+/).pop() || "")[0]?.toLocaleUpperCase("vi") || "?";
  return (
    <span className={cn("inline-flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-primary/10 text-lg font-bold text-primary", className)}>
      {src && failedSrc !== src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={src} src={src} alt={"Ảnh " + name} className="h-full w-full object-cover" onError={() => setFailedSrc(src)} />
      ) : <span role="img" aria-label={"Ảnh " + name}>{initial}</span>}
    </span>
  );
}
