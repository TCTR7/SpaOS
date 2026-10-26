"use client";
import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, CheckCircle2, ChevronDown, ClipboardList, Copy, Settings, Sparkles, Users } from "lucide-react";
import { setupSummary, type SetupSummary } from "@/lib/experience-api";
import { Button } from "@/components/ui/button";
export function SetupGuide(): React.ReactElement {
  const [data, setData] = React.useState<SetupSummary | null>(null), [error, setError] = React.useState(false), [attempt, setAttempt] = React.useState(0);
  const [copyMessage, setCopyMessage] = React.useState("");
  React.useEffect(() => { let cancelled = false; setData(null); setError(false);
    void setupSummary().then((value) => { if (!cancelled) setData(value); }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [attempt]);
  const steps = data ? [
    { href: "/admin/settings", title: "1. Giờ mở cửa và liên hệ", description: data.contact_ready ? "Đã có địa chỉ và số liên hệ" : "Cần bổ sung thông tin liên hệ", ready: data.contact_ready, icon: Settings },
    { href: "/admin/services", title: "2. Dịch vụ", description: data.services + " đang nhận khách", ready: data.services > 0, icon: Sparkles },
    { href: "/admin/staff", title: "3. Nhân viên và giờ làm", description: data.staff_with_hours + "/" + data.staff + " nhân viên có ca tuần", ready: data.staff_with_hours > 0, icon: Users },
  ] : [];
  const readyCount = steps.filter((step) => step.ready).length;
  if (data && readyCount === 3) return <></>;
  return <details data-testid="branch-setup-guide" className="group overflow-hidden rounded-2xl border border-border neu-surface bg-card shadow-sm">
    <summary className="flex min-h-20 cursor-pointer list-none items-center gap-3 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:p-5 [&::-webkit-details-marker]:hidden">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><ClipboardList className="h-5 w-5" /></span>
      <span className="min-w-0 flex-1"><span className="block text-sm font-semibold sm:text-base">Thiết lập spa</span><span className="mt-1 block text-xs text-muted-foreground">{data ? readyCount + "/3 mục thiết lập đã có thông tin" : "Chuẩn bị thông tin để đón khách"}</span></span>
      <ChevronDown className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
    </summary>
    <div className="border-t border-border p-4 sm:p-5">
      {error ? <div role="alert" className="space-y-3"><p className="text-sm">Chưa kiểm tra được thiết lập chi nhánh.</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử lại thiết lập</Button></div> : !data ? <p role="status" className="text-sm text-muted-foreground">Đang kiểm tra thiết lập...</p> : <div className="space-y-4">
        <div className="grid gap-3 lg:grid-cols-3">{steps.map((step) => {
          const Icon = step.icon;
          return <Link key={step.href} href={step.href} className="flex min-w-0 items-start gap-3 rounded-xl border border-border p-4 transition-colors hover:border-primary/40 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            <span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{step.title}</span><span className="mt-1.5 block text-xs leading-relaxed text-muted-foreground">{step.description}</span></span>
            {step.ready ? <CheckCircle2 aria-label="Đã có thông tin" className="h-4 w-4 shrink-0 text-emerald-600" /> : <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
          </Link>;
        })}</div>
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-muted/50 p-4">
          <div className="min-w-0 flex-1"><h3 className="text-sm font-semibold">Mời khách đặt lịch online</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Kiểm tra giờ trống trước khi chia sẻ trang đặt lịch với khách.</p></div>
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <a className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" href={"/" + data.slug + "/book"} target="_blank" rel="noreferrer">Xem trang đặt lịch<ArrowUpRight className="h-4 w-4" /></a>
            <Button type="button" className="min-h-11 whitespace-normal rounded-lg" onClick={async () => { try { if (!navigator.clipboard) throw new Error(); await navigator.clipboard.writeText(window.location.origin + "/" + data.slug); setCopyMessage("Đã sao chép đường dẫn."); } catch { setCopyMessage("Chưa sao chép được. Bạn có thể sao chép địa chỉ trang đặt lịch trong thanh trình duyệt."); } }}><Copy className="h-4 w-4 shrink-0" />Sao chép đường dẫn cho khách</Button>
          </div>
          {copyMessage && <p role="status" className="w-full text-sm">{copyMessage}</p>}
        </div>
      </div>}
    </div>
  </details>;
}
