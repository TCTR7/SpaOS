"use client";
import * as React from "react";
import { BUILD_INFO } from "@/lib/build-info";
import { operatorRequest } from "@/lib/operator-api";
import { Button } from "@/components/ui/button";
type Info = {version:string; release_id:string; build_id:string; built_at:string|null};
export function OperatorSystem(): React.ReactElement {
  const [state,setState] = React.useState<{server:Info;backend:Info}|null>(null);
  const [error,setError] = React.useState("");
  const [busy,setBusy] = React.useState(false);
  const check = React.useCallback(async () => {
    setBusy(true);setError("");setState(null);
    try {
      const [response,backend] = await Promise.all([fetch("/api/system/version",{cache:"no-store"}),operatorRequest<Info>("/system")]);
      if (!response.ok) throw new Error("Chưa đọc được phiên bản frontend server");
      setState({server:await response.json() as Info,backend});
    } catch(e) {setError(e instanceof Error?e.message:"Chưa kiểm tra được phiên bản");}
    finally {setBusy(false);}
  },[]);
  React.useEffect(()=>{void check();},[check]);
  const configured = [BUILD_INFO,state?.server,state?.backend].every(x=>x?.release_id && x.release_id !== "development" && x.built_at);
  const stale = state && state.server.build_id !== BUILD_INFO.build_id;
  const mismatch = state && (state.server.release_id !== state.backend.release_id || state.server.version !== state.backend.version);
  return <section className="space-y-4 rounded-2xl border neu-surface bg-card p-5" aria-labelledby="system-title">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 id="system-title" className="font-bold">Hệ thống & Phiên bản</h2><Button variant="outline" disabled={busy} onClick={()=>void check()}>{busy?"Đang kiểm tra...":"Kiểm tra lại phiên bản"}</Button></div>
    {error && <p role="alert" className="feedback-error">{error}</p>}
    {state && <p role="status" className={stale||mismatch||!configured?"feedback-error":"feedback-success"}>{stale?"Trình duyệt đang mở bản cũ. Lưu công việc rồi tải lại trang.":mismatch?"Frontend và backend khác đợt phát hành. Cần kiểm tra deploy.":!configured?"Bản phát triển: chưa gắn mã phát hành để xác nhận deploy.":"Frontend và backend cùng đợt phát hành."}</p>}
    <div className="grid gap-3 md:grid-cols-3">{[["Trình duyệt",BUILD_INFO],["Frontend server",state?.server],["Backend",state?.backend]].map(([label,info])=>{
      const value=info as Info|undefined;
      return <div key={String(label)} className="min-w-0 space-y-1 rounded-xl bg-muted/50 p-3 text-sm [overflow-wrap:anywhere]"><h3 className="font-semibold">{String(label)}</h3><p>Version: {value?.version||"—"}</p><p>Release: {value?.release_id||"—"}</p><p>Build: {value?.build_id||"—"}</p><p className="text-xs text-muted-foreground">{value?.built_at?new Date(value.built_at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"}):"Chưa có thời điểm build"}</p></div>;
    })}</div>
    <p className="text-xs text-muted-foreground">Thông tin này xác nhận bản code đang chạy. Cần kiểm tra migration, API và luồng nghiệp vụ trước khi chốt phát hành.</p>
  </section>;
}
