"use client";
import * as React from "react";
import { BrandColorPicker } from "@/components/brand-color-picker";
import { announceBranding, useBranding } from "@/components/brand-provider";
import { operatorRequest } from "@/lib/operator-api";
import type { Branding } from "@/components/brand-provider";
import { DEFAULT_BRAND } from "@/lib/brand-theme";
import { Button } from "@/components/ui/button";

export function OperatorBranding({disabled=false}: {disabled?:boolean}): React.ReactElement {
  const {branding,refresh} = useBranding();
  const [color,setColor] = React.useState(DEFAULT_BRAND);
  const [dirty,setDirty] = React.useState(false);
  React.useEffect(() => { if (!dirty && branding.configured) setColor(branding.theme_color); },[branding,dirty]);
  const [ready,setReady] = React.useState(false);
  const [busy,setBusy] = React.useState(false);
  const [error,setError] = React.useState<string|null>(null);
  const [message,setMessage] = React.useState("");
  const [attempt,setAttempt] = React.useState(0);
  React.useEffect(() => {
    let cancelled = false;
    void operatorRequest<Branding>("/branding").then((value) => { if (!cancelled) { setColor(value.theme_color); setReady(true); } })
      .catch((e:unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được màu thương hiệu"); });
    return () => {cancelled=true;};
  },[attempt]);
  return <form className="space-y-4 rounded-xl border neu-surface bg-card p-5" onSubmit={async (e) => {
    e.preventDefault(); if (busy || disabled) return; setBusy(true); setError(null); setMessage("");
    try {
      const value = await operatorRequest<Branding>("/branding",{theme_color:color});
      setColor(value.theme_color); setDirty(false); await refresh(); announceBranding();
      setMessage("Đã lưu màu thương hiệu cho toàn bộ hệ thống.");
    } catch (e) { setError(e instanceof Error ? e.message : "Không lưu được màu"); }
    finally {setBusy(false);}
  }}>
    <h2 className="font-bold">Màu thương hiệu của spa</h2>
    <p className="text-sm text-muted-foreground">Áp dụng cho các chi nhánh, trang quản trị và trang đặt lịch.</p>
    <BrandColorPicker id="deploymentColor" value={color} onChange={(value) => {setColor(value); setDirty(true);}} disabled={!ready || busy || disabled} />
    {error && <div role="alert" className="space-y-2 text-sm text-rose-700"><p>{error}</p>{!ready && <Button variant="outline" type="button" onClick={() => {setError(null);setAttempt((v)=>v+1);}}>Thử tải lại màu</Button>}</div>}
    {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}
    <Button type="submit" disabled={!ready || busy || disabled || !/^#[0-9a-f]{6}$/i.test(color)}>{busy ? "Đang lưu màu..." : "Lưu màu thương hiệu"}</Button>
  </form>;
}
