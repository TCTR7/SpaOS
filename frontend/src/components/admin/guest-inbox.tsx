"use client";
import * as React from "react";
import { apiRequest, fetchCustomerPage } from "@/lib/api";
import type { ServiceItem, UserDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatDateTimeVN } from "@/lib/utils";

export interface GuestEnquiry {
  id: string;
  full_name: string;
  phone_number: string;
  start_time: string;
  note: string | null;
  service_ids: string[];
  staff_id: string | null;
}

export function GuestInbox({
  services,
  staff = [],
  onSaved,
  onPrefill,
}: {
  services: ServiceItem[];
  staff?: UserDetail[];
  onSaved: () => void;
  onPrefill?: (row: GuestEnquiry) => void;
}): React.ReactElement {
  const [rows, setRows] = React.useState<GuestEnquiry[]>([]);
  const [offset, setOffset] = React.useState(0);
  const [more, setMore] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  const [target, setTarget] = React.useState<GuestEnquiry | null>(null);
  const [customers, setCustomers] = React.useState<UserDetail[]>([]);
  const [customer, setCustomer] = React.useState("");
  const [verified, setVerified] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    void apiRequest<{ items: GuestEnquiry[]; has_more: boolean }>("/guest-requests?offset=" + offset)
      .then((v) => {
        if (alive) {
          setRows(v.items);
          setMore(v.has_more);
        }
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : "Chưa tải được yêu cầu.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [attempt, offset]);

  const open = async (row: GuestEnquiry): Promise<void> => {
    setTarget(row);
    setCustomer("");
    setCustomers([]);
    setVerified(false);
    setError("");
    setBusy(true);
    try {
      const page = await fetchCustomerPage({ q: row.phone_number, limit: 50 });
      const matching = page.items.filter((c) => c.phone_number === row.phone_number);
      setCustomers(matching);
      if (matching.length === 1) setCustomer(matching[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa đối chiếu được hồ sơ khách.");
    } finally {
      setBusy(false);
    }
  };

  const decide = async (action: "confirm" | "reject"): Promise<void> => {
    if (!target || busy) return;
    setBusy(true);
    setError("");
    try {
      await apiRequest("/guest-requests/" + target.id + "/decision", {
        method: "POST",
        body: { action, identity_verified: verified, customer_id: customer || null },
      });
      setTarget(null);
      setAttempt((v) => v + 1);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa xử lý được yêu cầu.");
    } finally {
      setBusy(false);
    }
  };

  const serviceNames = (ids: string[]): string =>
    ids.map((id) => services.find((s) => s.id === id)?.name || "Dịch vụ").join(", ");
  const staffName = (staffId: string | null): string =>
    staffId ? staff.find((s) => s.id === staffId)?.full_name || "KTV đã chọn" : "Spa tự sắp xếp";

  return (
    <details className="rounded-xl border bg-card p-4" open={rows.length > 0}>
      <summary className="cursor-pointer font-semibold">
        Khách chờ liên hệ xác nhận{!loading ? " (" + rows.length + (more ? "+" : "") + ")" : ""}
      </summary>
      <p className="my-3 text-sm text-muted-foreground">
        Yêu cầu khách gửi từ trang đặt lịch. Bấm &ldquo;Gọi và xác nhận&rdquo; để tạo lịch theo đúng dịch vụ, KTV và giờ khách đã chọn, hoặc mở vào form Tạo lịch tại quầy đã điền sẵn nếu cần điều chỉnh.
      </p>
      {error && !target && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      <Button variant="outline" size="sm" disabled={loading} onClick={() => setAttempt((v) => v + 1)}>
        Tải lại yêu cầu
      </Button>
      {!loading && !rows.length && !error && <p className="py-3 text-sm">Chưa có yêu cầu chờ liên hệ.</p>}
      {rows.map((row) => (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t py-3" key={row.id}>
          <div className="min-w-0 flex-1 space-y-1">
            <p className="font-semibold">
              {row.full_name} · <span className="text-primary">{row.phone_number}</span>
            </p>
            <p className="text-sm font-medium">{formatDateTimeVN(row.start_time)}</p>
            <p className="text-xs text-muted-foreground">
              Dịch vụ: <strong>{serviceNames(row.service_ids)}</strong> · KTV: <strong>{staffName(row.staff_id)}</strong>
            </p>
            {row.note && <p className="text-xs text-slate-600">Ghi chú: {row.note}</p>}
          </div>
          <div className="flex flex-wrap gap-2">
            {onPrefill && (
              <Button variant="outline" size="sm" onClick={() => onPrefill(row)}>
                Mở form Tạo lịch (điền sẵn)
              </Button>
            )}
            <Button size="sm" onClick={() => void open(row)}>
              Gọi và xử lý
            </Button>
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        {offset > 0 && <Button variant="outline" onClick={() => setOffset((v) => Math.max(0, v - 50))}>Trang trước</Button>}
        {more && <Button variant="outline" onClick={() => setOffset((v) => v + 50)}>Trang sau</Button>}
      </div>
      <Modal open={!!target} onClose={() => setTarget(null)} pending={busy} title="Liên hệ xác nhận yêu cầu">
        {target && (
          <div className="space-y-4">
            <p className="font-semibold">
              {target.full_name} · <a className="action-link" href={"tel:" + target.phone_number}>{target.phone_number}</a>
            </p>
            <p className="text-sm">{formatDateTimeVN(target.start_time)}</p>
            <p className="text-sm">
              Dịch vụ: <strong>{serviceNames(target.service_ids)}</strong> · KTV: <strong>{staffName(target.staff_id)}</strong>
            </p>
            {target.note && <p className="text-sm">Ghi chú: {target.note}</p>}
            <label className="block text-sm">
              Hồ sơ khách đã xác minh
              <select
                className="mt-2 min-h-11 w-full rounded-lg border bg-background px-3"
                disabled={busy}
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
              >
                <option value="">Tạo hồ sơ khách mới khi xác nhận</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.full_name} · {c.phone_number}</option>
                ))}
              </select>
            </label>
            <p className="text-xs text-muted-foreground">
              Không tự gộp hồ sơ theo SĐT. Nếu số đã tồn tại, chọn đúng hồ sơ sau khi xác minh.
            </p>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={verified} disabled={busy} onChange={(e) => setVerified(e.target.checked)} />
              Đã gọi và xác minh đúng khách, dịch vụ và giờ hẹn
            </label>
            {error && <p role="alert" className="feedback-error">{error}</p>}
            <div className="flex flex-wrap gap-2">
              <Button disabled={busy || !verified} onClick={() => void decide("confirm")}>Xác nhận và tạo lịch</Button>
              <Button variant="destructive" disabled={busy || !verified} onClick={() => void decide("reject")}>Không nhận yêu cầu</Button>
            </div>
          </div>
        )}
      </Modal>
    </details>
  );
}
