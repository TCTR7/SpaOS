"use client";
import * as React from "react";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { guestApi, type GuestKey, type GuestResult } from "@/components/customer/guest-booking";
import Link from "@/components/spa-link";
import { formatDateTimeVN } from "@/lib/utils";

const BOOKING_LABELS: Record<string, string> = {
  CANCELLED: "Lịch hẹn đã hủy",
  COMPLETED: "Buổi chăm sóc đã hoàn thành",
  IN_PROGRESS: "Đang phục vụ",
  NO_SHOW: "Chưa đến buổi hẹn",
};

export default function GuestRequestPage(): React.ReactElement {
  const { slug, tenant } = useCustomerTenant();
  const [result, setResult] = React.useState<GuestResult | null>(null);
  const [error, setError] = React.useState("");

  // The secret fragment is read once, used for one status call and removed from the URL.
  React.useEffect(() => {
    let key: GuestKey | null = null;
    try {
      const raw = window.location.hash.slice(1) || sessionStorage.getItem("spaos_guest_view_" + slug) || "";
      const value = JSON.parse(decodeURIComponent(raw)) as GuestKey;
      if (!/^[a-f0-9-]{36}$/.test(value.request_id) || !/^[a-f0-9]{64}$/.test(value.token)) throw new Error();
      key = value;
      try { sessionStorage.setItem("spaos_guest_view_" + slug, encodeURIComponent(JSON.stringify(value))); }
      catch { /* A valid fragment works even when browser storage is blocked. */ }
    } catch {
      setError("Không tìm thấy yêu cầu đặt lịch. Vui lòng liên hệ spa để được hỗ trợ.");
    }
    history.replaceState(history.state, "", window.location.pathname + window.location.search);
    if (!key) return;
    let alive = true;
    guestApi<GuestResult>(slug, "/status", key)
      .then((value) => { if (alive) setResult(value); })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : "Chưa tải được yêu cầu."); });
    return () => { alive = false; };
  }, [slug]);

  const title = !result
    ? ""
    : result.status === "PENDING"
      ? "Đã gửi yêu cầu đặt lịch thành công"
      : result.status === "CONFIRMED"
        ? BOOKING_LABELS[result.booking_status || ""] || "Spa đã xác nhận lịch hẹn của bạn"
        : "Spa chưa thể nhận yêu cầu này";

  return (
    <section className="space-y-4 rounded-xl border bg-card p-5">
      <h1 className="text-xl font-bold">Yêu cầu đặt lịch của bạn</h1>
      {error && <p role="alert" className="feedback-error">{error}</p>}
      {!result && !error && <p role="status" className="text-sm text-muted-foreground">Đang tải...</p>}
      {result && (
        <>
          <p className="font-semibold">{title}</p>
          {tenant && <p className="text-sm">{tenant.name}</p>}
          <p>{formatDateTimeVN(result.start_time)}</p>
          {result.status === "PENDING" && (
            <p className="text-sm text-muted-foreground">
              Spa sẽ gọi điện hoặc nhắn tin qua số điện thoại của bạn để xác nhận lịch hẹn.
            </p>
          )}
          {result.message && <p className="text-sm">{result.message}</p>}
        </>
      )}
      <Link href={"/" + slug} className="inline-flex min-h-11 items-center justify-center rounded-lg border px-4 text-sm font-semibold">
        Quay về trang chủ
      </Link>
    </section>
  );
}
