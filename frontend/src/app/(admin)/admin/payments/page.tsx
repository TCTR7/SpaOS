"use client";

import * as React from "react";
import { useAdminAuth } from "@/components/admin/auth-context";
import { PaymentLedger } from "@/components/admin/payment-ledger";
import { apiRequest, fetchStaffList } from "@/lib/api";
import { listCollections, openPaymentInvoice, listAuditEvents, getPaymentSummary, formatPaymentCurrency as formatCurrency } from "@/lib/payment-api";
import type { PaymentCollection, PaymentInvoice, PaymentSummary, AuditEvent, UserDetail } from "@/lib/types";
import { formatDateISOInVN, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

const ACTIONS: Record<string, string> = {
  INVOICE_CREATED: "Ghi nhận khoản cần thu", PAYMENT_RECEIVED: "Xác nhận thu tiền", PAYMENT_VOIDED: "Hoàn tác ghi nhận",
  CUSTOMER_CREATED: "Tạo khách hàng", CUSTOMER_UPDATED: "Sửa hồ sơ", CUSTOMER_ASSIGNED: "Chuyển KTV phụ trách",
  PACKAGE_ISSUED: "Cấp thẻ liệu trình", BOOKING_CREATED: "Tạo lịch hẹn", BOOKING_STATUS_CHANGED: "Đổi trạng thái lịch",
  BOOKING_CANCELLED: "Hủy lịch hẹn", BOOKING_RESCHEDULED: "Dời lịch hẹn",
};
const STATUS: Record<PaymentCollection["status"], string> = {
  UNPAID: "Chưa thu", PARTIAL: "Thu một phần", PAID: "Đã thu",
  NEEDS_PRICE: "Cần đối chiếu giá cũ", COVERED: "Dùng thẻ — không thu thêm", FREE: "Không phát sinh tiền",
};

export default function PaymentsPage(): React.ReactElement {
  const { user, loading: authLoading } = useAdminAuth();
  const [rows, setRows] = React.useState<PaymentCollection[]>([]);
  const [selected, setSelected] = React.useState<PaymentInvoice | null>(null);
  const [source, setSource] = React.useState<PaymentCollection | null>(null);
  const [offset, setOffset] = React.useState(0);
  const [staff, setStaff] = React.useState<UserDetail[]>([]);
  const [query, setQuery] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [scope, setScope] = React.useState<"outstanding" | "all">("outstanding");
  const [tab, setTab] = React.useState<"collections" | "history">("collections");
  const [legacyAmount, setLegacyAmount] = React.useState("");
  const [logs, setLogs] = React.useState<AuditEvent[]>([]);
  const [auditOffset, setAuditOffset] = React.useState(0);
  const [summary, setSummary] = React.useState<PaymentSummary | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [locked, setLocked] = React.useState(false);
  const [dirty, setDirty] = React.useState(false);
  const collectionOpener = React.useRef<HTMLButtonElement | null>(null);
  const fail = (e: unknown): void => setError(e instanceof Error ? e.message : "Không thể tải dữ liệu");

  React.useEffect(() => {
    if (user?.role !== "ADMIN") return;
    let cancelled = false;
    setLoading(true); setError(null);
    void listCollections(search, scope, offset).then((data) => { if (!cancelled) setRows(data); })
      .catch((e: unknown) => { if (!cancelled) fail(e); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user?.role, search, scope, offset]);
  React.useEffect(() => {
    if (user?.role !== "ADMIN") return;
    let cancelled = false;
    const today = formatDateISOInVN();
    void Promise.all([getPaymentSummary(today, today), fetchStaffList()]).then(([total, team]) => {
      if (!cancelled) { setSummary(total); setStaff(team); }
    }).catch((e: unknown) => { if (!cancelled) fail(e); });
    return () => { cancelled = true; };
  }, [user?.role]);
  React.useEffect(() => {
    if (user?.role !== "ADMIN" || tab !== "history") return;
    let cancelled = false;
    void listAuditEvents(undefined, auditOffset).then((data) => { if (!cancelled) setLogs(data); })
      .catch((e: unknown) => { if (!cancelled) fail(e); });
    return () => { cancelled = true; };
  }, [user?.role, tab, auditOffset]);

  const refresh = async (): Promise<void> => {
    const today = formatDateISOInVN();
    const [data, total, current] = await Promise.all([
      listCollections(search, scope, offset), getPaymentSummary(today, today),
      selected ? apiRequest<PaymentInvoice>(`/payments/invoices/${selected.id}`) : Promise.resolve(null),
    ]);
    setRows(data); setSummary(total); setSelected(current);
  };
  const choose = async (row: PaymentCollection, price?: string): Promise<void> => {
    if (locked || busy) return;
    setSource(row); setLegacyAmount(""); setSelected(null); setError(null);
    if (row.status === "NEEDS_PRICE" && price === undefined) return;
    setBusy(true);
    try {
      const invoice = await openPaymentInvoice(row.source_type === "booking" ? { booking_id: row.source_id } :
        { customer_package_id: row.source_id, ...(price !== undefined ? { legacy_amount_due: price } : {}) });
      setSelected(invoice);
    } catch (e) { fail(e); } finally { setBusy(false); }
  };
  const actorName = (id: string): string => user?.id === id ? user.full_name :
    staff.find((person) => person.id === id)?.full_name || id.slice(0, 8);
  const describe = (event: AuditEvent): string => {
    const data = event.details;
    const parts: string[] = [];
    if (typeof data.amount === "string") parts.push(formatCurrency(data.amount));
    if (typeof data.amount_due === "string") parts.push("Giá đã chốt: " + formatCurrency(data.amount_due));
    if (data.method === "CASH") parts.push("Tiền mặt");
    if (data.method === "BANK_TRANSFER") parts.push("Chuyển khoản");
    if (typeof data.reason === "string") parts.push("Lý do: " + data.reason);
    if (event.action === "CUSTOMER_ASSIGNED") parts.push("KTV: " +
      (typeof data.to_staff_id === "string" ? actorName(data.to_staff_id) : "Chưa phân công"));
    return parts.join(" • ");
  };

  if (authLoading) return <p>Đang tải...</p>;
  if (user?.role !== "ADMIN") return <p role="alert">Chỉ Admin được quản lý thu tiền và nhật ký.</p>;
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold">Thu tiền</h1>
      <p className="text-sm text-muted-foreground">Khách và dịch vụ có sẵn từ lịch hẹn, thẻ liệu trình. Xác nhận khi bạn đã thực nhận tiền.</p>
      {summary && <section data-testid="payment-summary" className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-3">
        <div><p className="text-sm">Hôm nay đã thu</p><strong>{formatCurrency(summary.net_received)}</strong></div>
        <div><p className="text-sm">Tiền mặt</p><strong>{formatCurrency(summary.cash)}</strong></div>
        <div><p className="text-sm">Chuyển khoản</p><strong>{formatCurrency(summary.bank_transfer)}</strong></div>
        <p className="text-xs text-muted-foreground sm:col-span-3">Ngày {summary.date_from} theo giờ Việt Nam; đã trừ các khoản hoàn tác hôm nay.</p>
      </section>}
      <nav aria-label="Thu tiền và lịch sử" className="flex gap-2">
        <Button variant={tab === "collections" ? "default" : "outline"} disabled={locked || busy} onClick={() => setTab("collections")}>Danh sách thu tiền</Button>
        <Button variant={tab === "history" ? "default" : "outline"} disabled={locked || busy} onClick={() => setTab("history")}>Lịch sử thao tác</Button>
      </nav>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      {tab === "collections" ? <>
        <form onSubmit={(e) => { e.preventDefault(); setOffset(0); setSearch(query); }} className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          <Input aria-label="Tìm khách thu tiền" placeholder="Tên hoặc số điện thoại khách" className="col-span-2 min-w-0 sm:flex-1" value={query} disabled={locked || busy} onChange={(e) => setQuery(e.target.value)} />
          <Button type="submit" variant="outline" disabled={locked || busy}>Tìm khách</Button>
          <select aria-label="Lọc trạng thái thu tiền" className="h-11 min-w-0 rounded-md border bg-background px-2 text-base sm:h-9 sm:text-sm" value={scope} disabled={locked || busy} onChange={(e) => { setScope(e.target.value as "outstanding" | "all"); setOffset(0); }}>
            <option value="outstanding">Còn cần thu</option><option value="all">Tất cả</option>
          </select>
        </form>
        <Modal open={!!source} title="Xác nhận thu tiền" historyGuard pending={locked || busy} dirty={dirty || !!legacyAmount}
          returnFocusRef={collectionOpener}
          description={source ? `${source.customer_name} • ${source.description}` : undefined}
          onClose={() => { setSelected(null); setSource(null); }}>
        {source && <section className="space-y-3" aria-label="Xác nhận thu tiền">
          <div><h2 className="font-bold">{source.customer_name}</h2><p className="text-sm">{source.description}</p></div>
          {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
          {source.status === "NEEDS_PRICE" && !selected && <form onSubmit={(e) => { e.preventDefault(); void choose(source, legacyAmount); }} className="space-y-2">
            <p className="text-sm">Thẻ cũ chưa lưu giá bán. Đối chiếu số tiền đã thỏa thuận với khách trước khi ghi nhận.</p>
            <Label htmlFor="legacyAmount">Giá bán thẻ đã đối chiếu (VND)</Label>
            <Input id="legacyAmount" type="number" min="0" step="0.01" required value={legacyAmount} disabled={busy} onChange={(e) => setLegacyAmount(e.target.value)} />
            <Button type="submit" disabled={busy}>Xác nhận giá đã đối chiếu</Button>
          </form>}
          {busy && <p>Đang tải khoản thu...</p>}
          {selected && <PaymentLedger key={selected.id} invoice={selected} actorName={actorName} onChanged={refresh} onLocked={setLocked} onDirty={setDirty} />}
        </section>}
        </Modal>
        <section aria-label="Danh sách khách và dịch vụ" className="space-y-3">
          {loading ? <p role="status">Đang tải danh sách...</p> : <>
            {rows.length === 0 && <p className="rounded-xl border p-5">Không có khoản thu phù hợp.</p>}
            {rows.map((row) => <article key={row.source_type + row.source_id} data-testid={"collection-" + row.source_id} className="flex min-w-0 flex-col items-stretch gap-3 rounded-xl border bg-card p-4 [overflow-wrap:anywhere] sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1"><h2 className="font-bold">{row.customer_name}</h2>
                <p className="text-xs text-muted-foreground">{row.phone_number} • {formatDateTimeVN(row.occurred_at)}</p>
                <p className="mt-1 text-sm">{row.source_type === "package" ? "Thẻ liệu trình: " : ""}{row.description}</p>
                {(row.source_status === "CANCELLED" || row.source_status === "NO_SHOW") && <p className="text-xs text-amber-700">Lịch đã hủy / khách không đến — kiểm tra khoản thu cũ.</p>}
                <p className="mt-1 text-sm font-semibold">{STATUS[row.status]}</p>
                {row.amount_due !== null && <p className="text-sm">Giá {formatCurrency(row.amount_due)} • Đã thu {formatCurrency(row.amount_paid)}
                  {Number(row.balance_due) > 0 && <> • Còn thiếu <strong>{formatCurrency(row.balance_due || "0")}</strong></>}</p>}
              </div>
              {!["COVERED", "FREE"].includes(row.status) && <Button disabled={locked || busy} variant={row.status === "PAID" ? "outline" : "default"} onClick={(event) => { collectionOpener.current = event.currentTarget; void choose(row); }}>
                {row.status === "PAID" ? "Xem khoản đã thu" : row.status === "NEEDS_PRICE" ? "Đối chiếu giá cũ" : "Xác nhận đã thu"}
              </Button>}
            </article>)}
          </>}
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={locked || busy || loading || offset === 0} onClick={() => setOffset(Math.max(0, offset-50))}>Trang trước</Button>
            <Button size="sm" variant="outline" disabled={locked || busy || loading || rows.length < 50} onClick={() => setOffset(offset+50)}>Trang sau</Button>
          </div>
        </section>
      </> : <section className="space-y-3 rounded-xl border bg-card p-4">
        <h2 className="font-bold">Lịch sử thao tác</h2>
        {logs.length === 0 && <p className="text-sm">Chưa có thao tác.</p>}
        {logs.map((event) => <div key={event.id} data-testid="audit-event" className="rounded-lg border p-3 text-xs">
          <p className="font-bold">{ACTIONS[event.action] || event.action} • {formatDateTimeVN(event.created_at)}</p>
          <p>Người thao tác: {event.actor_id ? actorName(event.actor_id) : "Hệ thống"}</p>
          <p className="break-words text-muted-foreground">{describe(event)}</p>
        </div>)}
        <div className="flex gap-2">
          <Button size="sm" variant="outline" disabled={auditOffset === 0} onClick={() => setAuditOffset(Math.max(0, auditOffset-50))}>Nhật ký mới hơn</Button>
          <Button size="sm" variant="outline" disabled={logs.length < 50} onClick={() => setAuditOffset(auditOffset+50)}>Nhật ký cũ hơn</Button>
        </div>
      </section>}
    </div>
  );
}
