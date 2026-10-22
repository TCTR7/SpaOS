"use client";
import * as React from "react";
import { operatorRequest } from "@/lib/operator-api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { HandoverKit } from "@/components/handover-kit";
import { formatDateTimeVN } from "@/lib/utils";
export type OwnerDetail = {id:string;full_name:string;phone_number:string;branches:{id:string;name:string;slug:string;logo_url:string|null;address:string|null;active:boolean}[]};
type Event = {id:string;action:string;created_at:string;operator_id:string|null};
const ACTIONS: Record<string,string> = {OWNER_PROVISIONED:"Cấp tài khoản",OWNER_ACCOUNT_UPDATED:"Cập nhật tài khoản",OWNER_RECOVERY_ISSUED:"Cấp liên kết khôi phục",OWNER_RECOVERY_COMPLETED:"Chủ spa đã đặt lại mật khẩu"};
export function OperatorOwner({id}: {id:string}): React.ReactElement {
  const [detail,setDetail]=React.useState<OwnerDetail|null>(null);
  const [name,setName]=React.useState(""),[phone,setPhone]=React.useState("");
  const [password,setPassword]=React.useState(""),[verified,setVerified]=React.useState(false);
  const [busy,setBusy]=React.useState(false),[error,setError]=React.useState(""),[message,setMessage]=React.useState("");
  const [link,setLink]=React.useState(""),[events,setEvents]=React.useState<Event[]>([]),[attempt,setAttempt]=React.useState(0);
  const flight=React.useRef(false);
  React.useEffect(()=>{
    let alive=true;
    void Promise.all([operatorRequest<OwnerDetail>("/owners/"+id),operatorRequest<Event[]>("/owners/"+id+"/events")]).then(([value,history])=>{if(alive){setDetail(value);setName(value.full_name);setPhone(value.phone_number);setEvents(history);}}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Chưa tải được tài khoản");});
    return ()=>{alive=false;};
  },[id,attempt]);
  async function mutate(recovery:boolean):Promise<void>{
    if(flight.current)return;flight.current=true;setBusy(true);setError("");setMessage("");setLink("");
    try{
      const body={current_password:password,identity_verified:verified};
      if(recovery){
        const result=await operatorRequest<{token:string}>("/owners/"+id+"/recovery-link",body);
        setLink(window.location.origin+"/admin/recover#"+result.token);setMessage("Đã cấp liên kết dùng một lần, hạn 30 phút. Gửi riêng cho đúng chủ spa.");
      }else{
        const value=await operatorRequest<OwnerDetail>("/owners/"+id,{...body,full_name:name,phone_number:phone},"PATCH");
        setDetail(value);setName(value.full_name);setPhone(value.phone_number);setMessage("Đã cập nhật tài khoản ở các chi nhánh và thu hồi phiên cũ.");
      }
      setPassword("");setVerified(false);
      try{setEvents(await operatorRequest<Event[]>("/owners/"+id+"/events"));}catch{setError("Thao tác đã thành công, nhưng chưa tải được lịch sử mới. Vui lòng tải lại.");}
    }catch(e){setError(e instanceof Error?e.message:"Chưa thực hiện được");}
    finally{flight.current=false;setBusy(false);}
  }
  return <section className="space-y-5 rounded-2xl border bg-card p-5" aria-label="Chi tiết chủ spa">
    <div className="flex flex-wrap justify-between gap-3"><h2 className="text-lg font-bold">Quản lý chủ spa & Bàn giao</h2><Button variant="outline" disabled={busy} onClick={()=>{setError("");setAttempt(v=>v+1);}}>Tải lại thông tin chủ spa</Button></div>
    {error&&<p role="alert" className="feedback-error">{error}</p>}{message&&<p role="status" className="feedback-success">{message}</p>}
    {detail&&<><form className="space-y-4" onSubmit={e=>{e.preventDefault();void mutate(false);}}><fieldset disabled={busy} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2"><div><Label htmlFor="editOwnerName">Họ tên hiện tại</Label><Input id="editOwnerName" required maxLength={255} value={name} onChange={e=>setName(e.target.value)}/></div><div><Label htmlFor="editOwnerPhone">Số điện thoại hiện tại</Label><Input id="editOwnerPhone" type="tel" required value={phone} onChange={e=>setPhone(e.target.value)}/></div></div>
      <p className="text-sm text-muted-foreground">Xác minh chủ spa qua kênh đã biết trước khi đổi tài khoản hoặc hỗ trợ quên mật khẩu. Thay đổi áp dụng tại mọi chi nhánh của tài khoản.</p>
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={verified} onChange={e=>setVerified(e.target.checked)}/>Tôi đã xác minh đúng chủ spa</label>
      <div><Label htmlFor="ownerOperatorPassword">Mật khẩu operator để xác nhận</Label><PasswordInput id="ownerOperatorPassword" required autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></div>
      <div className="flex flex-wrap gap-3"><Button disabled={!verified||!password||busy} type="submit">Lưu thông tin chủ spa</Button><Button disabled={!verified||!password||busy} variant="outline" type="button" onClick={()=>void mutate(true)}>Cấp liên kết đặt lại mật khẩu</Button></div>
    </fieldset></form>
    {link&&<div className="space-y-3 rounded-xl border p-4"><Label htmlFor="ownerRecoveryLink">Liên kết riêng cho chủ spa</Label><Input id="ownerRecoveryLink" readOnly value={link} onFocus={e=>e.target.select()}/><Button variant="outline" onClick={async()=>{try{await navigator.clipboard.writeText(link);setMessage("Đã sao chép liên kết riêng.");}catch{setError("Chọn và sao chép liên kết trong ô bên trên.");}}}>Sao chép liên kết khôi phục</Button></div>}
    <HandoverKit owner={detail}/>
    <details className="disclosure"><summary className="cursor-pointer py-2 font-semibold">Lịch sử hỗ trợ tài khoản</summary><ul className="space-y-3 py-3">{events.map(event=><li key={event.id} className="rounded-lg bg-muted/50 p-3 text-sm"><p>{ACTIONS[event.action]||event.action}</p><p className="text-xs text-muted-foreground">{formatDateTimeVN(event.created_at)} · {event.action==="OWNER_RECOVERY_COMPLETED"?"Chủ spa thực hiện":"Operator thực hiện"}</p></li>)}</ul></details>
    </>}
  </section>;
}
