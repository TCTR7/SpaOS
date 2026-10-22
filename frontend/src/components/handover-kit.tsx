"use client";
import * as React from "react";
import type { OwnerDetail } from "@/components/operator-owner";
import { handoverSheets,handoverMessage,renderHandover,handoverPdf,downloadBlob } from "@/lib/handover";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/input";
export function HandoverKit({owner}:{owner:OwnerDetail}):React.ReactElement{
  const [key,setKey]=React.useState("management"),[busy,setBusy]=React.useState(false),[error,setError]=React.useState(""),[message,setMessage]=React.useState("");
  const [origin,setOrigin]=React.useState("");
  const preview=React.useRef<HTMLCanvasElement>(null);
  React.useEffect(()=>{setOrigin(window.location.origin);},[]);
  const sheets=React.useMemo(()=>origin?handoverSheets(owner,origin):[],[owner,origin]);
  const selected=sheets.find(s=>s.key===key)||sheets[0];
  React.useEffect(()=>{
    let alive=true;setError("");setMessage("");
    if(selected)void renderHandover(selected).then(canvas=>{if(alive&&preview.current){preview.current.width=canvas.width;preview.current.height=canvas.height;preview.current.getContext("2d")?.drawImage(canvas,0,0);}}).catch(()=>{if(alive)setError("Chưa tạo được bản xem trước. Vui lòng thử lại.");});
    return()=>{alive=false;};
  },[selected]);
  async function exportFile(pdf:boolean):Promise<void>{
    if(busy||!selected)return;setBusy(true);setError("");setMessage("");
    try{
      if(pdf)downloadBlob(await handoverPdf(sheets),"spa-ban-giao.pdf");
      else{const canvas=await renderHandover(selected);const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(v=>v?resolve(v):reject(new Error("Chưa xuất được PNG")),"image/png"));downloadBlob(blob,"spa-"+selected.key+".png");}
      setMessage(pdf?"Đã tải PDF gồm trang quản lý và các trang chia sẻ cho khách.":"Đã tải ảnh PNG. Kiểm tra đúng đối tượng trước khi gửi.");
    }catch(e){setError(e instanceof Error?e.message:"Chưa xuất được bộ bàn giao");}finally{setBusy(false);}
  }
  return <section className="space-y-4 border-t pt-5" aria-label="Bộ thông tin bàn giao"><h3 className="font-bold">Bộ thông tin bàn giao</h3>
    <p className="text-sm text-muted-foreground">Gửi ảnh kèm tin nhắn có link qua Zalo/Messenger. Trang quản lý gửi riêng cho chủ spa; trang khách và chi nhánh có thể chia sẻ công khai. PDF gồm cả trang quản lý, dùng để bàn giao riêng.</p>
    <Label htmlFor="handoverSheet">Chọn trang để tải ảnh</Label><select id="handoverSheet" disabled={busy} value={selected?.key||key} onChange={e=>setKey(e.target.value)} className="min-h-11 w-full rounded-lg border bg-background px-3 text-sm">{sheets.map(s=><option key={s.key} value={s.key}>{s.title} — {s.name}</option>)}</select>
    {selected&&<a className="action-link break-all" href={selected.url}>{selected.url}</a>}
    <canvas ref={preview} aria-label="Bản xem trước bộ bàn giao" role="img" className="mx-auto w-full max-w-sm rounded-xl border"/>
    <div className="flex flex-wrap gap-3"><Button disabled={busy||!selected} onClick={()=>void exportFile(false)}>Tải ảnh PNG</Button><Button variant="outline" disabled={busy||!selected} onClick={()=>void exportFile(true)}>Tải PDF bàn giao</Button><Button variant="outline" disabled={busy||!origin} onClick={async()=>{setError("");try{await navigator.clipboard.writeText(handoverMessage(owner,origin));setMessage("Đã sao chép tin nhắn bàn giao.");}catch{setError("Trình duyệt chưa cho sao chép. Chọn nội dung tin nhắn bên dưới.");}}}>Sao chép tin nhắn bàn giao</Button></div>
    <details className="disclosure"><summary className="cursor-pointer py-2 text-sm font-semibold">Nội dung tin nhắn</summary><textarea readOnly aria-label="Tin nhắn bàn giao" value={origin?handoverMessage(owner,origin):""} className="min-h-48 w-full rounded-lg border bg-background p-3 text-sm" onFocus={e=>e.target.select()}/></details>
    {busy&&<p role="status">Đang xuất tài liệu...</p>}{error&&<p role="alert" className="feedback-error">{error}</p>}{message&&<p role="status" className="feedback-success">{message}</p>}
  </section>;
}
