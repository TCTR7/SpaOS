"use client";
import * as React from "react";
import { useRouter } from "@/lib/spa-navigation";
import { API_BASE_URL, ApiError } from "@/lib/api";
import { apiErrorMessage } from "@/lib/api-error-message";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export interface GuestKey { request_id: string; token: string }
export interface GuestResult { request_id: string; status: "PENDING"|"CONFIRMED"|"REJECTED"; booking_status?:string|null; start_time: string; message: string }
export async function guestApi<T>(slug: string, path: string, body: unknown): Promise<T> {
  const response = await fetch(API_BASE_URL + "/public/guest-requests" + path, {
    method:"POST", headers:{"Content-Type":"application/json","X-Tenant-Slug":slug}, body:JSON.stringify(body), cache:"no-store",
  });
  const data = await response.json() as T & {detail?:unknown};
  if (!response.ok) throw new ApiError(response.status, apiErrorMessage(response.status,data.detail));
  return data;
}
export function GuestBooking({slug,start,services,staff,note}: {slug:string;start:string;services:string[];staff:string|null;note:string}): React.ReactElement {
  const router = useRouter();
  const [name,setName]=React.useState(""),[phone,setPhone]=React.useState("");
  const [busy,setBusy]=React.useState(false),[error,setError]=React.useState(""),[pending,setPending]=React.useState(false);
  const flight=React.useRef(false);
  const storage="spaos_guest_request_"+slug;
  const key=React.useRef<GuestKey|null>(null);
  React.useEffect(()=>{try{const old=sessionStorage.getItem(storage);if(old){key.current=JSON.parse(old) as GuestKey;setPending(true);}}catch{/* New request can still be created. */}},[storage]);
  const open=(value:GuestKey):void=>{
    // A known saved enquiry is no longer an uncertain submission. Keep its
    // private viewing link separately so another visit can start a new request.
    sessionStorage.setItem("spaos_guest_view_"+slug,encodeURIComponent(JSON.stringify(value)));
    sessionStorage.removeItem(storage);
    key.current=null;setPending(false);
    router.push("/"+slug+"/request#"+encodeURIComponent(JSON.stringify(value)));
  };
  const check=async():Promise<void>=>{
    if(!key.current||flight.current)return;flight.current=true;setBusy(true);setError("");
    try {await guestApi<GuestResult>(slug,"/status",key.current);open(key.current);}
    catch(e){setError(e instanceof Error?e.message:"Chưa kiểm tra được yêu cầu.");}
    finally{flight.current=false;setBusy(false);}
  };
  return <section className="space-y-3 rounded-xl border border-primary/30 bg-card p-4" aria-label="Đặt lịch không cần tài khoản">
    <h3 className="font-semibold">Gửi yêu cầu, không cần tài khoản</h3>
    <p className="text-sm text-muted-foreground">Spa sẽ gọi xác nhận. Yêu cầu chưa giữ chỗ, chưa thu tiền. Bạn nhận liên kết riêng để xem trạng thái; không có mật khẩu tự tạo.</p>
    {error&&<p role="alert" className="feedback-error">{error}</p>}
    {pending?<div className="space-y-2"><p className="text-sm">Có yêu cầu đã gửi từ tab này.</p><Button disabled={busy} onClick={()=>void check()}>Kiểm tra yêu cầu đã gửi</Button><p className="text-xs">Nếu chưa gửi thành công, nhấn Gửi lại để dùng cùng mã chống trùng.</p></div>:null}
    <form id="guest-request-form" className="space-y-3" onSubmit={async event=>{
      event.preventDefault();if(flight.current||!start)return;flight.current=true;setBusy(true);setError("");
      if(!key.current){const bytes=crypto.getRandomValues(new Uint8Array(32));key.current={request_id:crypto.randomUUID(),token:Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")};sessionStorage.setItem(storage,JSON.stringify(key.current));}
      try{
        // After a lost response, check before retrying the same request.
        if(pending){try{await guestApi<GuestResult>(slug,"/status",key.current);open(key.current);return;}catch(e){if(!(e instanceof ApiError&&e.status===404))throw e;}}
        await guestApi<GuestResult>(slug,"",{...key.current,full_name:name.trim(),phone_number:phone.trim(),service_ids:services,staff_id:staff,start_time:start,note:note.trim()||null});
        setPending(true);open(key.current);
      }catch(e){
        setError(e instanceof Error?e.message:"Chưa xác định kết quả. Hãy kiểm tra yêu cầu trước khi gửi lại.");
        if(e instanceof ApiError&&[400,403,404,422,429].includes(e.status)){sessionStorage.removeItem(storage);key.current=null;setPending(false);}else setPending(true);
      }finally{flight.current=false;setBusy(false);}
    }}>
      <div><Label htmlFor="guest-name">Họ và tên</Label><Input id="guest-name" autoComplete="name" required maxLength={255} disabled={busy} value={name} onChange={e=>setName(e.target.value)}/></div>
      <div><Label htmlFor="guest-phone">Số điện thoại để spa liên hệ</Label><Input id="guest-phone" type="tel" autoComplete="tel" required maxLength={20} disabled={busy} value={phone} onChange={e=>setPhone(e.target.value)}/></div>
      <Button disabled={busy||!start} type="submit">{busy?"Đang gửi...":pending?"Gửi lại cùng yêu cầu":"Gửi yêu cầu chờ spa xác nhận"}</Button>
    </form>
  </section>;
}
