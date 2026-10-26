"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowUpRight, Clock3, Leaf, MapPin, Phone } from "lucide-react";
import { SpaLogo } from "@/components/spa-logo";
import { API_BASE_URL } from "@/lib/api";
import type { PublicTenantResponse } from "@/lib/types";

type Branch = { id: string; name: string; slug: string; address?: string | null; contact_phone?: string | null };
type Directory = { brand_name: string; branches: Branch[] };
type Details = Pick<PublicTenantResponse, "logo_url" | "open_time" | "close_time">;

export default function HomePage(): React.ReactElement {
  const router = useRouter();
  const [data, setData] = React.useState<Directory | null>(null);
  const [details, setDetails] = React.useState<Record<string, Details>>({});
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    const controller = new AbortController();
    setError(null); setData(null); setDetails({});
    async function load(): Promise<void> {
      try {
        const response = await fetch(API_BASE_URL + "/branches/public", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("Không tải được danh sách chi nhánh.");
        const value = await response.json() as Directory;
        if (controller.signal.aborted) return;
        if(value.branches.length === 1){router.replace("/"+encodeURIComponent(value.branches[0].slug));return;}
        setData(value);
        // The directory contract has no logo/hours. Enrich progressively through
        // the existing public endpoint, with at most three concurrent requests.
        let next = 0;
        await Promise.all(Array.from({ length: Math.min(3, value.branches.length) }, async () => {
          while (!controller.signal.aborted && next < value.branches.length) {
            const branch = value.branches[next++];
            try {
              const result = await fetch(API_BASE_URL + "/public/tenants/" + encodeURIComponent(branch.slug), { signal: controller.signal });
              if (!result.ok) continue;
              const info = await result.json() as PublicTenantResponse;
              if (controller.signal.aborted || info.id !== branch.id || info.slug !== branch.slug) continue;
              setDetails(previous => ({ ...previous, [branch.id]: { logo_url: info.logo_url, open_time: info.open_time, close_time: info.close_time } }));
            } catch { /* Optional branding must not block branch selection. */ }
          }
        }));
      } catch {
        if (!controller.signal.aborted) setError("Chưa tải được chi nhánh. Bạn thử lại nhé.");
      }
    }
    void load();
    return () => controller.abort();
  }, [attempt, router]);
  const brand = data?.brand_name && data.brand_name !== "SpaOS" ? data.brand_name : "Đặt lịch spa";
  const onlyBranch = data?.branches.length === 1 ? data.branches[0] : null;
  return <div className="min-h-screen bg-background text-[#213c35] [overflow-wrap:anywhere]">
    <header className="border-b border-[#213c35]/10 neu-surface bg-card">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
        <div className="flex min-w-0 items-center gap-3">
          {onlyBranch && details[onlyBranch.id]?.logo_url ? <SpaLogo name={onlyBranch.name} src={details[onlyBranch.id].logo_url} /> : <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#e9eee6]"><Leaf className="h-5 w-5" aria-hidden="true" /></span>}
          <span className="text-lg font-semibold tracking-tight">{brand}</span>
        </div>
        <div className="flex w-full shrink-0 flex-wrap justify-between gap-2 sm:w-auto"><a href="#branches" className="inline-flex min-h-11 items-center gap-2 px-2 text-sm font-medium underline-offset-4 hover:underline">Chi nhánh <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></a><Link href="/admin/login" className="inline-flex min-h-11 items-center neu-control rounded-full border border-[#213c35]/30 px-4 text-sm font-semibold hover:bg-white">Đăng nhập quản lý</Link></div>
      </div>
    </header>
    <main className="mx-auto max-w-7xl px-5 pb-16 sm:px-8 lg:px-12">
      <section className="relative grid gap-8 border-b border-[#213c35]/[0.15] py-12 sm:py-16 lg:grid-cols-[1.4fr_1fr] lg:items-end lg:py-20" aria-labelledby="welcome-title">
        <div>
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.2em] text-[#60756b]">Một chút thời gian cho chính mình</p>
          <h1 id="welcome-title" className="max-w-2xl font-serif text-4xl leading-[1.12] tracking-tight sm:text-5xl lg:text-6xl">Chọn nơi bạn đến.<br /><span className="text-[#68806b]">Để mình được chăm sóc.</span></h1>
        </div>
        <div className="max-w-sm lg:ml-auto lg:pb-1">
          <p className="text-base leading-7 text-[#60756b]">Tìm chi nhánh thuận tiện, chọn dịch vụ yêu thích và xem khung giờ phù hợp với bạn.</p>
          <a href="#branches" className="mt-6 inline-flex min-h-11 items-center gap-3 neu-control rounded-full bg-[#213c35] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[#36594d] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#213c35]">Khám phá chi nhánh <ArrowRight className="h-4 w-4" aria-hidden="true" /></a>
        </div>
      </section>
      <section id="branches" className="scroll-mt-6 pt-9 sm:pt-12" aria-labelledby="branches-title">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#60756b]">Hẹn gặp bạn tại</p><h2 id="branches-title" className="font-serif text-3xl">Các chi nhánh</h2></div>
          {data && data.branches.length > 0 && <p className="text-sm text-[#60756b]">{data.branches.length} địa điểm để bạn lựa chọn</p>}
        </div>
        {error && <div role="alert" className="rounded-2xl border border-[#dce3da] neu-surface bg-card p-6"><p>{error}</p><button className="mt-3 min-h-11 rounded-full border border-[#213c35] px-5 text-sm font-medium" onClick={() => setAttempt(v => v + 1)}>Thử tải lại chi nhánh</button></div>}
        {!data && !error && <div role="status"><p className="mb-4 text-sm text-[#60756b]">Đang tìm chi nhánh cho bạn...</p><div aria-hidden="true" className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{[0,1,2].map(i => <div key={i} className="h-72 rounded-2xl border border-[#dce3da] neu-surface bg-card motion-safe:animate-pulse" />)}</div></div>}
        {data?.branches.length === 0 && <div className="rounded-2xl border border-[#dce3da] neu-surface bg-card px-6 py-12 text-center"><Leaf className="mx-auto mb-4 h-8 w-8 text-[#68806b]" aria-hidden="true" /><p className="font-medium">Chưa có chi nhánh đang hoạt động.</p><p className="mt-2 text-sm text-[#60756b]">Bạn vui lòng quay lại sau nhé.</p></div>}
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{data?.branches.map((branch, index) => {
          const info = details[branch.id];
          return <article key={branch.id} className="group flex min-w-0 flex-col rounded-2xl border border-[#dce3da] neu-surface bg-card p-6 transition-shadow hover:shadow-lg sm:p-7">
            <div className="mb-6 flex items-start justify-between gap-3"><SpaLogo name={branch.name} src={info?.logo_url} className="h-16 w-16 rounded-2xl border-[#e2e8dd] bg-[#f4f6f0] text-xl text-[#36594d] shadow-none" /><span aria-hidden="true" className="pt-1 font-serif text-3xl text-[#d3dccf]">{String(index + 1).padStart(2, "0")}</span></div>
            <h3 className="mb-4 text-xl font-semibold leading-snug tracking-tight"><Link href={"/" + branch.slug} className="rounded-sm hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">{branch.name}</Link></h3>
            <div className="mb-6 space-y-3 text-sm leading-6 text-[#60756b]">
              {branch.address ? <a className="flex min-h-11 items-start gap-3 hover:text-[#213c35] hover:underline" href={"https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(branch.address)} target="_blank" rel="noreferrer"><MapPin className="mt-1 h-4 w-4 shrink-0" aria-hidden="true" /><span>{branch.address}</span></a> : <p className="flex items-start gap-3"><MapPin className="mt-1 h-4 w-4 shrink-0" aria-hidden="true" /><span>Liên hệ chi nhánh để được hướng dẫn đường đi.</span></p>}
              {info?.open_time && info.close_time && <p className="flex items-center gap-3"><Clock3 className="h-4 w-4 shrink-0" aria-hidden="true" /><span>Giờ mở cửa: {info.open_time.slice(0,5)} – {info.close_time.slice(0,5)}</span></p>}
              {branch.contact_phone && /^\+?\d{9,15}$/.test(branch.contact_phone) && <a className="flex min-h-11 items-center gap-3 hover:text-[#213c35] hover:underline" href={"tel:" + branch.contact_phone}><Phone className="h-4 w-4 shrink-0" aria-hidden="true" />{branch.contact_phone}</a>}
            </div>
            <Link href={"/" + branch.slug + "/book"} aria-label={"Xem lịch trống tại " + branch.name} className="mt-auto flex min-h-12 items-center justify-between gap-3 neu-control rounded-xl bg-background px-4 py-3 text-sm font-semibold text-[#213c35] transition-colors hover:bg-[#dce7d5] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#213c35]">Xem lịch trống <ArrowRight className="h-4 w-4 shrink-0 transition-transform motion-safe:group-hover:translate-x-1" aria-hidden="true" /></Link>
          </article>;
        })}</div>
      </section>
    </main>
    <footer className="border-t border-[#213c35]/10"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-xs text-[#60756b] sm:px-8 lg:px-12"><span>Đặt lịch thuận tiện. Chăm sóc theo cách của bạn.</span><Link className="inline-flex min-h-11 items-center underline-offset-4 hover:underline" href="/admin/login">Dành cho quản lý spa</Link></div></footer>
  </div>;
}
