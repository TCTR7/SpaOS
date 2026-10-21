"use client";
import * as React from "react";
import Link from "next/link";
import { SpaLogo } from "@/components/spa-logo";
import { ContactLinks } from "@/components/contact-links";
import { API_BASE_URL } from "@/lib/api";

export default function HomePage(): React.ReactElement {
  const [data, setData] = React.useState<{brand_name: string; branches: {id: string; name: string; slug: string; address?: string | null; contact_phone?: string | null}[]} | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    setError(null);
    let cancelled = false;
    void fetch(API_BASE_URL + "/branches/public", { cache: "no-store" }).then(async (r) => {
      if (!r.ok) throw new Error("Không tải được danh sách chi nhánh.");
      return await r.json() as NonNullable<typeof data>;
    }).then((value) => { if (!cancelled) setData(value); }).catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được chi nhánh"); });
    return () => { cancelled = true; };
  }, [attempt]);
  return <main className="mx-auto min-w-0 [overflow-wrap:anywhere] max-w-xl space-y-5 px-4 py-10">
    <h1 className="text-2xl font-bold">{data?.brand_name || "Đặt lịch spa"}</h1>
    <p>Chọn chi nhánh bạn muốn đến.</p>
    {error && <div role="alert" className="space-y-2"><p>{error}</p><button className="min-h-11 rounded border px-3" onClick={() => setAttempt((v) => v+1)}>Thử tải lại chi nhánh</button></div>}
    {!data && !error && <p>Đang tải chi nhánh...</p>}
    {data?.branches.length === 0 && <p>Chưa có chi nhánh đang hoạt động.</p>}
    <div className="space-y-3">{data?.branches.map((branch) => <section key={branch.id} className="space-y-4 rounded-2xl border bg-card p-5 shadow-sm"><div className="flex items-center gap-3"><SpaLogo name={branch.name} /><h2 className="min-w-0 text-lg font-semibold">{branch.name}</h2></div><Link href={"/" + branch.slug} className="action-link w-full">Đặt lịch tại {branch.name}</Link><ContactLinks address={branch.address} phone={branch.contact_phone} /></section>)}</div>
    <Link className="inline-block text-sm underline" href="/admin/login">Đăng nhập quản lý</Link>
  </main>;
}
