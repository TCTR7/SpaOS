"use client";
import * as React from "react";
import { apiRequest } from "@/lib/api";
import type { SpaBrand } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input,Label } from "@/components/ui/input";
import { BrandColorPicker } from "@/components/brand-color-picker";
import { announceBranding } from "@/components/brand-provider";
import { useAdminAuth } from "./auth-context";
import { useBranchGuard } from "@/lib/branch-guard";
import { brandImage } from "@/lib/brand-image";

export function SpaBrandSettings():React.ReactElement {
  const {reloadTenant}=useAdminAuth();
  const [spa,setSpa]=React.useState<SpaBrand|null>(null),[logo,setLogo]=React.useState<string|undefined>(),[cover,setCover]=React.useState<string|undefined>();
  const [busy,setBusy]=React.useState(false),[dirty,setDirty]=React.useState(false),[error,setError]=React.useState(""),[message,setMessage]=React.useState("");
  const [attempt,setAttempt]=React.useState(0);const flight=React.useRef(false);
  useBranchGuard(dirty,busy);
  React.useEffect(()=>{let alive=true;void apiRequest<SpaBrand>("/spas/me").then(v=>{if(alive)setSpa(v);}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Chưa tải được spa");});return()=>{alive=false;};},[attempt]);
  async function save(e:React.FormEvent):Promise<void>{
    e.preventDefault();if(!spa||flight.current)return;flight.current=true;setBusy(true);setError("");setMessage("");
    try{
      const updated=await apiRequest<SpaBrand>("/spas/me",{method:"PATCH",body:{name:spa.name,theme_color:spa.theme_color,contact_phone:spa.contact_phone,logo_data:logo,cover_data:cover,cover_url:spa.cover_url}});
      setSpa({...updated,is_owner:spa.is_owner,plan:spa.plan});setDirty(false);setLogo(undefined);setCover(undefined);
      announceBranding();await reloadTenant();setMessage("Đã cập nhật nhận diện spa.");
    }catch(e){setError(e instanceof Error?e.message:"Chưa lưu được nhận diện");}finally{flight.current=false;setBusy(false);}
  }
  return <div className="mx-auto max-w-2xl space-y-4"><h1 className="text-xl font-bold">Thương hiệu & Gói sử dụng</h1>
    {error&&<div role="alert"><p className="feedback-error">{error}</p>{!spa&&<Button onClick={()=>setAttempt(v=>v+1)}>Thử tải lại</Button>}</div>}{message&&<p role="status" className="feedback-success">{message}</p>}
    {spa?.plan&&<p className="rounded-xl border p-4 text-sm">Gói thử nghiệm {spa.plan.price_usd} USD/tháng · Chi nhánh {spa.plan.branches}/{spa.plan.branch_limit} · Nhân viên {spa.plan.staff}/{spa.plan.staff_limit}</p>}
    {spa?.is_owner&&<form className="space-y-4 rounded-xl border p-4" onSubmit={e=>void save(e)}><fieldset disabled={busy} className="space-y-4">
      <div><Label htmlFor="spa-brand-name">Tên spa / thương hiệu</Label><Input id="spa-brand-name" required maxLength={255} value={spa.name} onChange={e=>{setSpa({...spa,name:e.target.value});setDirty(true);}}/></div>
      <BrandColorPicker id="spa-brand-color" value={spa.theme_color} onChange={value=>{setSpa({...spa,theme_color:value});setDirty(true);}}/>
      <div><Label htmlFor="spa-brand-phone">Số điện thoại liên hệ</Label><Input id="spa-brand-phone" type="tel" value={spa.contact_phone||""} onChange={e=>{setSpa({...spa,contact_phone:e.target.value||null});setDirty(true);}}/></div>
      {([false,true] as const).map(isCover=><div key={String(isCover)}><Label htmlFor={isCover?"spa-cover":"spa-logo"}>{isCover?"Ảnh bìa":"Logo / biểu tượng ứng dụng"}</Label><Input id={isCover?"spa-cover":"spa-logo"} type="file" accept="image/*" onChange={e=>{const file=e.target.files?.[0];if(file){setBusy(true);void brandImage(file,isCover).then(value=>{if(isCover)setCover(value);else setLogo(value);setDirty(true);}).catch(e=>setError(e instanceof Error?e.message:"Ảnh không hợp lệ")).finally(()=>setBusy(false));}}}/></div>)}
      {(logo||spa.logo_url)&&<img alt="Logo spa" className="h-24 w-24 rounded-xl object-contain" src={logo?"data:image/png;base64,"+logo:spa.logo_url||""}/>}
      <Button type="submit" disabled={!dirty||busy}>Lưu nhận diện spa</Button>
    </fieldset></form>}
    {spa&&!spa.is_owner&&<p>Chỉ chủ spa được thay đổi nhận diện thương hiệu.</p>}
  </div>;
}
