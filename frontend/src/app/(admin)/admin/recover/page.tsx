"use client";
import * as React from "react";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
export default function OwnerRecovery():React.ReactElement{
  const token=React.useRef("");
  const [ready,setReady]=React.useState(false),[password,setPassword]=React.useState(""),[confirm,setConfirm]=React.useState("");
  const [busy,setBusy]=React.useState(false),[done,setDone]=React.useState(false),[error,setError]=React.useState("");
  React.useEffect(()=>{if(window.location.hash){token.current=window.location.hash.slice(1);history.replaceState(history.state,"",window.location.pathname);}setReady(true);},[]);
  return <main className="mx-auto max-w-md space-y-5 px-4 py-12"><h1 className="text-2xl font-bold">Đặt lại mật khẩu chủ spa</h1>{done?<><p role="status" className="feedback-success">Đã đặt lại mật khẩu. Các phiên cũ đã hết hiệu lực.</p><Link className="action-link" href="/admin/login">Đăng nhập quản lý</Link></>:<form className="space-y-4 rounded-xl border neu-surface bg-card p-5" onSubmit={async e=>{e.preventDefault();if(busy)return;if(password!==confirm){setError("Mật khẩu nhập lại không khớp.");return;}setBusy(true);setError("");try{const result=await fetch(API_BASE_URL+"/operator/recovery",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:token.current,password}),cache:"no-store"});if(!result.ok)throw new Error("Liên kết không còn hiệu lực hoặc mật khẩu chưa hợp lệ. Liên hệ đơn vị triển khai để được hỗ trợ.");token.current="";setPassword("");setConfirm("");setDone(true);}catch(e){setError(e instanceof Error?e.message:"Chưa đặt được mật khẩu");}finally{setBusy(false);}}}>
    <p className="text-sm text-muted-foreground">Liên kết dùng một lần trong 30 phút. Mật khẩu mới áp dụng cho tài khoản ở mọi chi nhánh.</p>
    {ready&&!token.current&&<p role="alert">Thiếu liên kết khôi phục. Liên hệ đơn vị triển khai.</p>}
    <Label htmlFor="ownerRecoveryPassword">Mật khẩu mới</Label><PasswordInput id="ownerRecoveryPassword" required minLength={8} maxLength={72} autoComplete="new-password" disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/>
    <Label htmlFor="ownerRecoveryConfirm">Nhập lại mật khẩu</Label><PasswordInput id="ownerRecoveryConfirm" required autoComplete="new-password" disabled={busy} value={confirm} onChange={e=>setConfirm(e.target.value)}/>
    <Button disabled={!ready||!token.current||busy}>{busy?"Đang lưu...":"Đặt mật khẩu mới"}</Button>{error&&<p role="alert" className="feedback-error">{error}</p>}
    </form>}</main>;
}
