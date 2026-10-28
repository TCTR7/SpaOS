"use client";
import * as React from "react";
import Link from "@/components/spa-link";
import { BookOpen, Download, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { installAvailable, subscribeInstall, promptInstall } from "@/lib/pwa-install";
import { APP_ICON_192 } from "@/lib/app-icons";
import { useBranding } from "@/components/brand-provider";

type Role = "ADMIN" | "STAFF" | "CUSTOMER";
type View = "welcome" | "guide" | "install";
const memorySeen = new Set<string>();
interface Props {
  role: Role; slug?: string; identity?: string; identities?: string[];
  mode?: "auto" | "page"; autoOpen?: boolean;
}

export function ProductGuide({ role, slug, identity, identities = [], mode = "auto", autoOpen = true }: Props): React.ReactElement {
  const {branding}=useBranding();
  const brandName=branding.name||"SpaOS";
  const [open, setOpen] = React.useState(false);
  const [view, setView] = React.useState<View>(mode === "page" ? "guide" : "welcome");
  const [step, setStep] = React.useState(0);
  const [platform, setPlatform] = React.useState<"ios" | "android" | "desktop">("desktop");
  const [standalone, setStandalone] = React.useState(false);
  const [error, setError] = React.useState("");
  const install = React.useSyncExternalStore(subscribeInstall, installAvailable, () => false);
  // All server-verified membership identities share dismissal across branches.
  const ids = Array.from(new Set([identity || slug || "public", ...identities])).sort();
  const audience = role === "CUSTOMER" ? "CUSTOMER" : "MANAGEMENT";
  const keys = ids.map((id) => "spaos_guide_v2_" + audience + "_" + id);
  if (role === "CUSTOMER" && slug) keys.push("spaos_guide_v2_CUSTOMER_" + slug);
  const keySignature = JSON.stringify(keys);
  const oldKeys = ids.flatMap((id) => (role === "CUSTOMER" ? [role] : ["ADMIN", "STAFF"]).map((r) => "spaos_guide_v1_" + r + "_" + id));
  const remember = React.useCallback((): void => {
    const currentKeys = JSON.parse(keySignature) as string[];
    for (const key of currentKeys) {
      memorySeen.add(key);
      try { localStorage.setItem(key, "seen"); } catch { /* Optional device preference. */ }
    }
  }, [keySignature]);
  React.useEffect(() => {
    const seen = [...keys, ...oldKeys].some((key) => {
      if (memorySeen.has(key)) return true;
      try { return Boolean(localStorage.getItem(key)); } catch { return false; }
    });
    if (seen || mode === "page") { remember(); setOpen(false); }
    else if (autoOpen) { setView("welcome"); setOpen(true); }
    // Preference keys are a stable serialization of verified identities.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keySignature, mode, autoOpen, remember]);
  React.useEffect(() => {
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    setPlatform(ios ? "ios" : /Android/.test(navigator.userAgent) ? "android" : "desktop");
    const media = window.matchMedia("(display-mode: standalone)");
    const update = (): void => setStandalone(media.matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone));
    const installed = (): void => setStandalone(true);
    update(); window.addEventListener("appinstalled", installed); media.addEventListener("change", update);
    return () => { window.removeEventListener("appinstalled", installed); media.removeEventListener("change", update); };
  }, []);
  const close = (): void => { remember(); setOpen(false); };
  const choose = (next: View): void => { remember(); setStep(0); setView(next); };
  const base = slug ? "/" + slug : "";
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

  const current = steps[step];
  const content = <div className="space-y-6">
    {view === "welcome" ? <>
      <div className="space-y-3 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={branding.logo_url||APP_ICON_192} alt={brandName} className="mx-auto h-16 w-16 rounded-2xl" />
        <p className="text-sm leading-6 text-muted-foreground">{role === "ADMIN" ? "Quản lý spa thuận tiện hơn, bắt đầu từ vài thao tác đơn giản." : role === "STAFF" ? "Xem lịch được giao và theo dõi công việc của bạn." : "Đặt lịch và theo dõi các buổi chăm sóc của bạn dễ dàng hơn."}</p>
      </div>
      <div className="space-y-3">
        {([{ value: "guide", title: "Xem hướng dẫn nhanh", text: "Ba bước ngắn, phù hợp với công việc của bạn.", icon: BookOpen }, { value: "install", title: "Cài ứng dụng", text: `Thêm ${brandName} vào màn hình chính để mở nhanh hơn.`, icon: Download }] as const).map((item) => <button type="button" key={item.value} onClick={() => choose(item.value)} className="flex min-h-20 w-full items-center gap-4 rounded-xl border p-4 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <item.icon className="h-6 w-6 shrink-0 text-primary" aria-hidden="true" /><span className="min-w-0 flex-1"><span className="block font-semibold">{item.title}</span><span className="mt-1 block text-sm text-muted-foreground">{item.text}</span></span><ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
        </button>)}
      </div>
      <div className="space-y-2 text-center"><Button variant="ghost" className="min-h-11" onClick={close}>Để sau</Button><p className="text-xs text-muted-foreground">Bạn có thể mở lại trong menu Trợ giúp &amp; Cài ứng dụng.</p></div>
    </> : <>
      <nav aria-label="Nội dung trợ giúp" className="flex flex-wrap gap-2 border-b pb-4">
        <Button variant={view === "guide" ? "default" : "outline"} aria-pressed={view === "guide"} onClick={() => choose("guide")}><BookOpen className="h-4 w-4" />Hướng dẫn sử dụng</Button>
        <Button variant={view === "install" ? "default" : "outline"} aria-pressed={view === "install"} onClick={() => choose("install")}><Download className="h-4 w-4" />Cài ứng dụng</Button>
      </nav>
      {view === "guide" ? <>
        <section className="space-y-3" aria-live="polite"><p className="text-sm text-muted-foreground">Bước {step + 1}/{steps.length}</p><h3 className="text-lg font-semibold">{current.title}</h3><p className="text-sm leading-6">{current.text}</p><Link className="action-link" href={current.href} onClick={close}>{current.label}</Link></section>
        <div className="flex flex-wrap justify-between gap-3"><Button variant="outline" disabled={step === 0} onClick={() => setStep((v) => v - 1)}>Quay lại</Button>{step < steps.length - 1 ? <Button onClick={() => setStep((v) => v + 1)}>Tiếp theo</Button> : <Button onClick={() => mode === "page" ? setStep(0) : close()}>{mode === "page" ? "Xem lại từ đầu" : "Hoàn tất hướng dẫn"}</Button>}</div>
      </> : <section className="space-y-4">
        <h3 className="text-lg font-semibold">Thêm ứng dụng vào màn hình chính</h3>
        {standalone ? <p role="status" className="feedback-success">Bạn đang dùng ứng dụng đã cài.</p> : <>
          {platform === "ios" ? <ol className="list-decimal space-y-3 pl-5 text-sm leading-6"><li>Mở trang này bằng Safari trên iPhone/iPad.</li><li>Chọn Chia sẻ, rồi chọn Thêm vào Màn hình chính.</li><li>Chọn Mở dưới dạng ứng dụng web nếu có, rồi nhấn Thêm.</li></ol> : <p className="text-sm leading-6">{platform === "android" ? "Trên Chrome/Android, nhấn Cài ứng dụng bên dưới khi có. Nếu chưa thấy, mở menu trình duyệt → Cài ứng dụng hoặc Thêm vào màn hình chính." : "Dùng biểu tượng cài đặt hoặc menu trình duyệt nếu được hỗ trợ. Bạn vẫn có thể sử dụng đầy đủ qua website."}</p>}
          {install && <Button onClick={async () => { try { await promptInstall(); } catch { setError("Chưa mở được cửa sổ cài. Bạn có thể dùng menu trình duyệt."); } }}>Cài ứng dụng trên thiết bị</Button>}
          <p className="text-sm text-muted-foreground">Nếu đang mở trong Zalo/Messenger, chọn Mở bằng trình duyệt trước. Bạn có thể cài sau; thao tác cài không tự cấp quyền thông báo.</p>
        </>}
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      </section>}
    </>}
  </div>;
  return mode === "page" ? content : <Modal open={open} onClose={close} title={view === "welcome" ? `Bắt đầu sử dụng ${brandName}` : "Trợ giúp & Cài ứng dụng"}>{content}</Modal>;
}
