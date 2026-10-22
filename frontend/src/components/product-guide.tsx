"use client";
import * as React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { installAvailable, subscribeInstall, promptInstall } from "@/lib/pwa-install";
type Role="ADMIN"|"STAFF"|"CUSTOMER";
export function ProductGuide({role,slug,identity}:{role:Role;slug?:string;identity?:string}):React.ReactElement{
  const [open,setOpen]=React.useState(false),[step,setStep]=React.useState(0);
  const install=React.useSyncExternalStore(subscribeInstall,installAvailable,()=>false);
  const [platform,setPlatform]=React.useState<"ios"|"android"|"desktop">("desktop");
  const [standalone,setStandalone]=React.useState(false),[hint,setHint]=React.useState(false),[error,setError]=React.useState("");
  const button=React.useRef<HTMLButtonElement>(null);
  const key="spaos_guide_v1_"+role+"_"+(identity||slug||"public");
  React.useEffect(()=>{
    const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);
    setPlatform(ios?"ios":/Android/.test(navigator.userAgent)?"android":"desktop");
    const media=window.matchMedia("(display-mode: standalone)");
    const update=()=>setStandalone(media.matches||Boolean((navigator as Navigator & {standalone?:boolean}).standalone));update();
    const installed=()=>setStandalone(true);
    window.addEventListener("appinstalled",installed);media.addEventListener("change",update);
    return()=>{window.removeEventListener("appinstalled",installed);media.removeEventListener("change",update);};
  },[]);
  React.useEffect(()=>{try{setHint(!localStorage.getItem(key));}catch{setHint(true);}},[key]);
  const dismiss=()=>{setHint(false);try{localStorage.setItem(key,"seen");}catch{/* Optional preference. */}};
  const base=slug?"/"+slug:"";
  const steps=role==="ADMIN"?[
    {title:"Thiết lập spa",text:"Bổ sung tên, logo, địa chỉ và giờ mở cửa để khách dễ nhận diện chi nhánh.",href:"/admin/settings",label:"Mở cài đặt spa"},
    {title:"Chuẩn bị nhận lịch",text:"Thêm dịch vụ, nhân viên và ca làm việc. Kiểm tra giờ trống trước khi chia sẻ trang đặt lịch.",href:"/admin/staff",label:"Mở nhân sự & Ca làm"},
    {title:"Chia sẻ và vận hành",text:"Chia sẻ link/QR chi nhánh cho khách. Theo dõi lịch hẹn ở Tổng quan và ghi nhận khoản thanh toán ở Thu tiền.",href:"/admin/branches",label:"Mở danh sách chi nhánh"},
  ]:role==="STAFF"?[
    {title:"Xem công việc được giao",text:"Mở Lịch hẹn để xem khách, dịch vụ và thời gian bạn phụ trách. Lịch được giao có thể chỉ cho phép xem theo quyền hiện tại.",href:"/admin/bookings",label:"Mở lịch hẹn"},
    {title:"Kiểm tra ca làm",text:"Xem ca làm và ngày nghỉ tại Ca làm của tôi. Liên hệ chủ spa khi cần điều chỉnh.",href:"/admin/work-hours",label:"Mở ca làm của tôi"},
    {title:"Nhận cập nhật",text:"Mở biểu tượng chuông để đọc cập nhật và bật thông báo thiết bị nếu bạn muốn. Quyền thao tác phụ thuộc công việc bạn được cấp.",href:"/admin/account",label:"Mở tài khoản của tôi"},
  ]:[
    {title:"Tìm thời gian phù hợp",text:"Chọn dịch vụ trước để xem khung giờ trống phù hợp với thời lượng chăm sóc.",href:base+"/book",label:"Xem lịch trống"},
    {title:"Xác nhận lịch hẹn",text:"Chọn giờ và điền thông tin. Bạn có thể đăng nhập tài khoản khách để sử dụng thẻ liệu trình của chi nhánh.",href:base+"/book",label:"Đặt lịch hẹn"},
    {title:"Theo dõi và nhận cập nhật",text:"Đăng nhập để xem lịch hẹn, thẻ liệu trình và thông báo. Bạn tự chọn có bật thông báo thiết bị hay không.",href:base+"/appointments",label:"Xem lịch hẹn của tôi"},
  ];
  const current=steps[step];
  return <div className="space-y-2">
    {hint&&<div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-accent/50 p-3 text-sm"><span>Lần đầu sử dụng? Xem hướng dẫn nhanh để bắt đầu.</span><button className="min-h-11 px-2 text-sm underline" onClick={dismiss}>Để sau</button></div>}
    <Button ref={button} variant="outline" size="sm" onClick={()=>{setStep(0);setOpen(true);dismiss();}}>Hướng dẫn & Cài ứng dụng</Button>
    <Modal open={open} onClose={()=>setOpen(false)} title="Hướng dẫn & Cài ứng dụng" returnFocusRef={button}>
      <div className="space-y-5">
        <section className="space-y-3 rounded-xl border p-4"><h3 className="font-semibold">Thêm ứng dụng vào màn hình chính</h3>
          {standalone?<p role="status" className="feedback-success">Bạn đang dùng ứng dụng đã cài.</p>:<>
          {platform==="ios"?<ol className="list-decimal space-y-2 pl-5 text-sm"><li>Mở trang này bằng Safari trên iPhone/iPad.</li><li>Chọn Chia sẻ, rồi chọn Thêm vào Màn hình chính.</li><li>Chọn Mở dưới dạng ứng dụng web nếu có, rồi nhấn Thêm.</li></ol>:<p className="text-sm">{platform==="android"?"Trên Chrome/Android, nhấn Cài ứng dụng bên dưới khi có. Nếu chưa thấy, mở menu trình duyệt → Cài ứng dụng hoặc Thêm vào màn hình chính.":"Dùng biểu tượng cài đặt hoặc menu trình duyệt nếu được hỗ trợ. Bạn vẫn có thể sử dụng đầy đủ qua website."}</p>}
          {install&&<Button onClick={async()=>{try{await promptInstall();}catch{setError("Chưa mở được cửa sổ cài. Bạn có thể dùng menu trình duyệt.");}}}>Cài ứng dụng</Button>}
          <p className="text-xs text-muted-foreground">Nếu đang mở trong Zalo/Messenger, chọn Mở bằng trình duyệt trước. Bạn có thể cài sau; thao tác cài không tự cấp quyền thông báo.</p>
          </>}{error&&<p role="alert">{error}</p>}
        </section>
        <section className="space-y-3" aria-live="polite"><p className="text-xs text-muted-foreground">Hướng dẫn sử dụng · Bước {step+1}/{steps.length}</p><h3 className="text-lg font-semibold">{current.title}</h3><p className="text-sm leading-6">{current.text}</p><Link className="action-link" href={current.href} onClick={()=>setOpen(false)}>{current.label}</Link></section>
        <div className="flex flex-wrap justify-between gap-3"><Button variant="outline" disabled={step===0} onClick={()=>setStep(v=>v-1)}>Quay lại</Button>{step<steps.length-1?<Button onClick={()=>setStep(v=>v+1)}>Tiếp theo</Button>:<Button onClick={()=>setOpen(false)}>Hoàn tất hướng dẫn</Button>}</div>
      </div>
    </Modal>
  </div>;
}
