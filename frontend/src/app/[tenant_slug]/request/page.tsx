"use client";
import * as React from "react";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { guestApi, type GuestKey, type GuestResult } from "@/components/customer/guest-booking";
import { Button } from "@/components/ui/button";
import { formatDateTimeVN } from "@/lib/utils";

export default function GuestRequestPage():React.ReactElement {
  const {slug}=useCustomerTenant();
  const [key,setKey]=React.useState<GuestKey|null>(null),[result,setResult]=React.useState<GuestResult|null>(null);
  const [error,setError]=React.useState(""),[busy,setBusy]=React.useState(false),[copied,setCopied]=React.useState(false);
  React.useEffect(()=>{
    try{
      const raw=window.location.hash.slice(1)||sessionStorage.getItem("spaos_guest_view_"+slug)||"";
      const value=JSON.parse(decodeURIComponent(raw)) as GuestKey;
      if(!/^[a-f0-9-]{36}$/.test(value.request_id)||!/^[a-f0-9]{64}$/.test(value.token))throw new Error();
      setKey(value);sessionStorage.setItem("spaos_guest_view_"+slug,encodeURIComponent(JSON.stringify(value)));
    }catch{setError("Thiếu liên kết riêng của yêu cầu. Mở lại liên kết bạn đã lưu hoặc liên hệ spa.");}
    // The secret fragment is never sent to the server or left in browser history.
    history.replaceState(history.state,"",window.location.pathname+window.location.search);
  },[slug]);
  const load=React.useCallback(async()=>{if(!key)return;setBusy(true);setError("");try{setResult(await guestApi<GuestResult>(slug,"/status",key));}catch(e){setError(e instanceof Error?e.message:"Chưa tải được yêu cầu.");}finally{setBusy(false);}},[key,slug]);
  React.useEffect(()=>{void load();},[load]);
  return <section className="space-y-4 rounded-xl border bg-card p-5"><h1 className="text-xl font-bold">Yêu cầu đặt lịch của bạn</h1>
    {error&&<p role="alert">{error}</p>}{result&&<><p className="font-semibold">{result.status==="PENDING"?"Chờ spa gọi xác nhận":result.status==="CONFIRMED"?(({CANCELLED:"Lịch hẹn đã hủy",COMPLETED:"Buổi chăm sóc đã hoàn thành",IN_PROGRESS:"Đang phục vụ",NO_SHOW:"Chưa đến buổi hẹn"} as Record<string,string>)[result.booking_status || ""] || "Đã được spa xác nhận"):"Spa chưa nhận yêu cầu"}</p><p>{formatDateTimeVN(result.start_time)}</p><p>{result.message}</p></>}
    <Button disabled={!key||busy} onClick={()=>void load()}>{busy?"Đang kiểm tra...":"Cập nhật trạng thái"}</Button>
    {key&&<><Button variant="outline" onClick={async()=>{try{await navigator.clipboard.writeText(window.location.origin+window.location.pathname+"#"+encodeURIComponent(JSON.stringify(key)));setCopied(true);}catch{setError("Chưa sao chép được. Dùng nút mở liên kết riêng rồi lưu địa chỉ.");}}}>{copied?"Đã sao chép liên kết":"Sao chép liên kết riêng"}</Button><a className="action-link block" href={"#"+encodeURIComponent(JSON.stringify(key))}>Mở liên kết riêng để lưu</a><p className="text-xs text-muted-foreground">Giữ liên kết cho riêng bạn. Liên kết chỉ xem yêu cầu này, không mở hồ sơ hay lịch sử khách hàng.</p></>}
  </section>;
}
