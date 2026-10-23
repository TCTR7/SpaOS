"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
export function SpaLogo({ name, src, className, alt, onImageError }: { name: string; src?: string | null; className?: string; alt?: string; onImageError?: () => void }): React.ReactElement {
  const [failedSrc, setFailedSrc] = React.useState<string | null>(null);
  const initials = name.trim().split(/\s+/).slice(0, 2).map((word) => Array.from(word)[0] || "").join("").toLocaleUpperCase("vi") || "S";
  return <span className={cn("inline-flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-border bg-white text-lg font-bold text-slate-700 shadow-sm", className)}>
    {src && failedSrc !== src ? (
      // eslint-disable-next-line @next/next/no-img-element
      <img key={src} src={src} alt={alt ?? "Logo " + name} className="h-full w-full object-contain p-1.5" onError={() => { setFailedSrc(src); onImageError?.(); }} />
    ) : <span aria-label={alt ?? "Logo " + name} role="img">{initials}</span>}
  </span>;
}
