"use client";
import * as React from "react";
import { apiRequest, fetchCustomerPage } from "@/lib/api";
import type { ServiceItem, UserDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatDateTimeVN } from "@/lib/utils";
interface Enquiry {id:string;full_name:string;phone_number:string;start_time:string;note:string|null;service_ids:string[];staff_id:string|null}
export function GuestInbox({services,onSaved}:{services:ServiceItem[];onSaved:()=>void}):React.ReactElement {
  const [rows,setRows]=React.useState<Enquiry[]>([]),[offset,setOffset]=React.useState(0),[more,setMore]=React.useState(false);
  const [attempt,setAttempt]=React.useState(0),[target,setTarget]=React.useState<Enquiry|null>(null),[customers,setCustomers]=React.useState<UserDetail[]>([]);
  const [customer,setCustomer]=React.useState(""),[verified,setVerified]=React.useState(false),[busy,setBusy]=React.useState(false),[loading,setLoading]=React.useState(true),[error,setError]=React.useState("");
  React.useEffect(()=>{let alive=true;setLoading(true);setError("");void apiRequest<{items:Enquiry[];has_more:boolean}>("/guest-requests?offset="+offset).then(v=>{if(alive){setRows(v.items);setMore(v.has_more);}}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Chưa tải được yêu cầu.");}).finally(()=>{if(alive)setLoading(false);});return()=>{alive=false;};},[attempt,offset]);
  const open=async(row:Enquiry):Promise<void>=>{setTarget(row);setCustomer("");setCustomers([]);setVerified(false);setError("");setBusy(true);try{const page=await fetchCustomerPage({q:row.phone_number,limit:50});setCustomers(page.items.filter(c=>c.phone_number===row.phone_number));}catch(e){setError(e instanceof Error?e.message:"Chưa đối chiếu được hồ sơ khách.");}finally{setBusy(false);}};
  const decide=async(action:"confirm"|"reject"):Promise<void>=>{if(!target||busy)return;setBusy(true);setError("");try{await apiRequest("/guest-requests/"+target.id+"/decision",{method:"POST",body:{action,identity_verified:verified,customer_id:customer||null}});setTarget(null);setAttempt(v=>v+1);onSaved();}catch(e){setError(e instanceof Error?e.message:"Chưa xử lý được yêu cầu.");}finally{setBusy(false);}};
  return <details className="rounded-xl border bg-card p-4"><summary className="cursor-pointer font-semibold">Khách chờ liên hệ xác nhận{!loading?" ("+rows.length+(more?"+":"")+")":""}</summary>
    <p className="my-3 text-sm text-muted-foreground">Yêu cầu chưa giữ giờ và chưa tạo tài khoản. Gọi xác minh, đối chiếu hồ sơ rồi xác nhận; hệ thống sẽ kiểm tra trùng lịch một lần nữa.</p>
    {error&&!target&&<p role="alert">{error}</p>}<Button variant="outline" disabled={loading} onClick={()=>setAttempt(v=>v+1)}>Tải lại yêu cầu</Button>
    {!loading&&!rows.length&&!error&&<p className="py-3 text-sm">Chưa có yêu cầu chờ liên hệ.</p>}
    {rows.map(row=><div className="flex flex-wrap items-center justify-between gap-3 border-t py-3" key={row.id}><div><p className="font-semibold">{row.full_name}</p><p className="text-sm">{row.phone_number} · {formatDateTimeVN(row.start_time)}</p></div><Button variant="outline" onClick={()=>void open(row)}>Gọi và xử lý</Button></div>)}
    <div className="flex gap-2">{offset>0&&<Button variant="outline" onClick={()=>setOffset(v=>Math.max(0,v-50))}>Trang trước</Button>}{more&&<Button variant="outline" onClick={()=>setOffset(v=>v+50)}>Trang sau</Button>}</div>
    <Modal open={!!target} onClose={()=>setTarget(null)} pending={busy} title="Liên hệ xác nhận yêu cầu">
      {target&&<div className="space-y-4"><p>{target.full_name} · <a className="action-link" href={"tel:"+target.phone_number}>{target.phone_number}</a></p><p>{formatDateTimeVN(target.start_time)}</p><p>{target.service_ids.map(id=>services.find(s=>s.id===id)?.name||"Dịch vụ không còn mở bán").join(", ")}</p>{target.note&&<p>{target.note}</p>}
        <label className="block text-sm">Hồ sơ khách đã xác minh<select className="mt-2 min-h-11 w-full rounded-lg border bg-background px-3" disabled={busy} value={customer} onChange={e=>setCustomer(e.target.value)}><option value="">Tạo hồ sơ khách mới khi xác nhận</option>{customers.map(c=><option key={c.id} value={c.id}>{c.full_name} · {c.phone_number}</option>)}</select></label>
        <p className="text-xs">Không tự gộp hồ sơ theo SĐT. Nếu số đã tồn tại, chọn đúng hồ sơ sau khi xác minh. Hồ sơ ngoài quyền của bạn cần chủ spa xử lý.</p>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={verified} disabled={busy} onChange={e=>setVerified(e.target.checked)}/>Đã gọi và xác minh đúng khách, dịch vụ và giờ hẹn</label>
        {error&&<p role="alert" className="feedback-error">{error}</p>}
        <div className="flex flex-wrap gap-2"><Button disabled={busy||!verified} onClick={()=>void decide("confirm")}>Xác nhận và tạo lịch</Button><Button variant="destructive" disabled={busy||!verified} onClick={()=>void decide("reject")}>Không nhận yêu cầu</Button></div>
      </div>}
    </Modal>
  </details>;
}
