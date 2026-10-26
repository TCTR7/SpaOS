"use client";
import * as React from "react";
import { brandStyle, validBrandColor } from "@/lib/brand-theme";
import { Input, Label } from "@/components/ui/input";
export function BrandColorPicker({value,onChange,disabled=false,id}: {value:string;onChange:(value:string)=>void;disabled?:boolean;id:string}): React.ReactElement {
  const valid = /^#[0-9a-f]{6}$/i.test(value);
  return <div className="space-y-3">
    <Label htmlFor={id}>Màu thương hiệu (HEX)</Label>
    <div className="flex gap-2"><input aria-label="Bảng chọn màu thương hiệu" type="color" value={validBrandColor(value)} disabled={disabled} onChange={(e) => onChange(e.target.value)} className="h-10 w-14 rounded border p-1" />
      <Input id={id} value={value} disabled={disabled} required pattern="#[0-9a-fA-F]{6}" maxLength={7} placeholder="#2563eb" onChange={(e) => onChange(e.target.value)} /></div>
    {!valid && <p className="text-xs text-rose-700">Nhập đúng mã #RRGGBB gồm 6 chữ số HEX.</p>}
    <div data-testid={"preview-"+id} style={brandStyle(validBrandColor(value))} className="space-y-3 rounded-xl border neu-surface bg-card p-4">
      <p className="text-sm font-semibold text-primary">Xem trước thương hiệu</p>
      <div className="flex flex-wrap items-center gap-2"><span className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">Đặt lịch ngay</span><span className="rounded-lg bg-accent px-3 py-2 text-sm text-accent-foreground">Chi nhánh của bạn</span></div>
      <p className="text-xs text-muted-foreground">Chữ tự đổi sáng/tối để dễ đọc. Màu cảnh báo và lỗi được giữ riêng.</p>
    </div>
  </div>;
}
