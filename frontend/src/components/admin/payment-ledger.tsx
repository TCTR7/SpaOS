"use client";

import * as React from "react";
import { ApiError } from "@/lib/api";
import { listPaymentEntries, recordReceipt, voidReceipt, formatPaymentCurrency as formatCurrency } from "@/lib/payment-api";
import type { PaymentInvoice, PaymentEntry } from "@/lib/types";
import { formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

type ReceiptAttempt = { amount: string; method: "CASH" | "BANK_TRANSFER"; note: string | null; idempotency_key: string };
type VoidAttempt = { entryId: string; reason: string; idempotency_key: string };

export function PaymentLedger({ invoice, actorName, onChanged, onLocked }: {
  invoice: PaymentInvoice; actorName: (id: string) => string; onChanged: () => Promise<void>; onLocked: (locked: boolean) => void;
}): React.ReactElement {
  const [entries, setEntries] = React.useState<PaymentEntry[]>([]);
  const [offset, setOffset] = React.useState(0);
  const [amount, setAmount] = React.useState("");
  const [customAmount, setCustomAmount] = React.useState(false);
  const [refreshFailed, setRefreshFailed] = React.useState(false);
  const [method, setMethod] = React.useState<"CASH" | "BANK_TRANSFER">("CASH");
  const [note, setNote] = React.useState("");
  const [voidId, setVoidId] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [attempt, setAttempt] = React.useState<ReceiptAttempt | null>(null);
  const [voidAttempt, setVoidAttempt] = React.useState<VoidAttempt | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const locked = busy || attempt !== null || voidAttempt !== null || refreshFailed;
  React.useEffect(() => { onLocked(locked); return () => onLocked(false); }, [locked, onLocked]);

  const load = React.useCallback(async (): Promise<void> => {
    setEntries(await listPaymentEntries(invoice.id, offset));
  }, [invoice.id, offset]);
  React.useEffect(() => {
    let cancelled = false;
    void listPaymentEntries(invoice.id, offset).then((rows) => {
      if (!cancelled) setEntries(rows);
    }).catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được sổ thu"); });
    return () => { cancelled = true; };
  }, [invoice.id, offset]);

  const receive = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (busy || voidAttempt || refreshFailed) return;
    const body = attempt || { amount: customAmount ? amount : invoice.balance_due, method, note: note.trim() || null, idempotency_key: crypto.randomUUID() };
    setAttempt(body); setBusy(true); setError(null); setMessage(null);
    try {
      await recordReceipt(invoice.id, body);
      setAttempt(null); setAmount(""); setCustomAmount(false); setNote("");
      setMessage("Đã ghi nhận khoản thu.");
      try { await Promise.all([load(), onChanged()]); } catch { setRefreshFailed(true); setError("Đã ghi nhận. Cần tải lại số tiền trước khi tiếp tục."); }
    } catch (e) {
      if (e instanceof ApiError && e.status < 500) setAttempt(null);
      setError(e instanceof Error ? e.message : "Chưa xác định kết quả. Thử lại để đối chiếu cùng giao dịch.");
    } finally { setBusy(false); }
  };

  const reverse = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (busy || attempt || refreshFailed) return;
    const body = voidAttempt || { entryId: voidId, reason: reason.trim(), idempotency_key: crypto.randomUUID() };
    if (!body.reason || !body.entryId) return;
    setVoidAttempt(body); setBusy(true); setError(null); setMessage(null);
    try {
      await voidReceipt(body.entryId, { reason: body.reason, idempotency_key: body.idempotency_key });
      setVoidAttempt(null); setVoidId(""); setReason("");
      setMessage("Đã hoàn tác ghi nhận thu tiền.");
      try { await Promise.all([load(), onChanged()]); } catch { setRefreshFailed(true); setError("Đã ghi nhận. Cần tải lại số tiền trước khi tiếp tục."); }
    } catch (e) {
      if (e instanceof ApiError && e.status < 500) setVoidAttempt(null);
      setError(e instanceof Error ? e.message : "Chưa xác định kết quả. Thử lại với cùng mã giao dịch.");
    } finally { setBusy(false); }
  };

  const reversed = new Set(entries.filter((e) => e.reversal_of).map((e) => e.reversal_of));
  return (
    <section className="space-y-4 rounded-xl border bg-card p-4">
      <h3 className="text-base font-bold">Xác nhận tiền đã nhận</h3>
      <dl className="grid grid-cols-3 gap-3 text-sm">
        <div><dt>Giá đã chốt</dt><dd>{formatCurrency(invoice.amount_due)}</dd></div>
        <div><dt>Đã thu</dt><dd data-testid="invoice-paid">{formatCurrency(invoice.amount_paid)}</dd></div>
        <div><dt>Còn thiếu</dt><dd data-testid="invoice-balance">{formatCurrency(invoice.balance_due)}</dd></div>
      </dl>
      <p data-testid="invoice-status" className="text-sm font-semibold">
        {invoice.status === "PAID" ? "Đã thu đủ" : invoice.status === "PARTIAL" ? "Đã thu một phần" : "Chưa thu"}
      </p>
      {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
      {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}
      {attempt && !busy && <p className="text-sm">Kết quả lần xác nhận trước chưa rõ. Thử lại cùng giao dịch trước khi thu khoản khác.</p>}
      {refreshFailed && <Button disabled={busy} onClick={async () => { setBusy(true); try { await Promise.all([load(), onChanged()]); setRefreshFailed(false); setError(null); } catch { setError("Chưa tải được số tiền mới. Hãy thử tải lại."); } finally { setBusy(false); } }}>Tải lại số tiền</Button>}
      {(invoice.status !== "PAID" || attempt) && <form onSubmit={(e) => void receive(e)} className="grid gap-3 rounded-lg border p-3 sm:grid-cols-2">
        <p className="text-sm sm:col-span-2">Xác nhận đã nhận <strong>{formatCurrency(invoice.balance_due)}</strong> còn thiếu.</p>
        <label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" checked={customAmount} disabled={locked} onChange={(e) => setCustomAmount(e.target.checked)} />Nhập số tiền khác (khách trả một phần)</label>
        {customAmount && <div><Label htmlFor="receiptAmount">Số tiền thực nhận (VND)</Label>
          <Input id="receiptAmount" type="number" min="0.01" step="0.01" required value={amount}
            disabled={locked || invoice.status === "PAID"} max={invoice.balance_due} onChange={(e) => setAmount(e.target.value)} /></div>}
        <div><Label htmlFor="receiptMethod">Phương thức</Label>
          <select id="receiptMethod" className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={method} disabled={locked} onChange={(e) => setMethod(e.target.value as "CASH" | "BANK_TRANSFER")}>
            <option value="CASH">Tiền mặt</option><option value="BANK_TRANSFER">Chuyển khoản</option>
          </select></div>
        <div className="sm:col-span-2"><Label htmlFor="receiptNote">Ghi chú / mã chuyển khoản (tùy chọn)</Label>
          <Input id="receiptNote" maxLength={500} value={note} disabled={locked} onChange={(e) => setNote(e.target.value)} /></div>
        <Button type="submit" disabled={busy || refreshFailed || !!voidAttempt || (invoice.status === "PAID" && !attempt)}>
          {busy ? "Đang xử lý..." : attempt ? "Thử lại xác nhận" : "Xác nhận đã thu"}
        </Button>
      </form>}
      <p className="text-xs text-muted-foreground">Chỉ xác nhận sau khi đã kiểm tra tiền mặt hoặc giao dịch ngân hàng. Hủy lịch hẹn không tự hủy khoản thu.</p>
      <details><summary className="cursor-pointer text-sm font-bold">Lịch sử thu tiền và hoàn tác</summary>
      {entries.length === 0 && <p className="text-sm">Chưa có khoản thu.</p>}
      <div className="space-y-2">
        {entries.map((entry) => (
          <div key={entry.id} data-testid="payment-entry" className="rounded-lg border p-3 text-xs">
            <p className="font-bold">{entry.reversal_of ? "Hoàn tác ghi nhận" : "Khoản thu"}: {formatCurrency(entry.amount)}</p>
            <p>{entry.method === "CASH" ? "Tiền mặt" : "Chuyển khoản"} • {formatDateTimeVN(entry.created_at)}</p>
            <p className="break-all">Người xác nhận: {actorName(entry.recorded_by)}</p>
            {entry.note && <p>{entry.note}</p>}
            {!entry.reversal_of && !reversed.has(entry.id) && (
              <Button type="button" size="sm" variant="outline" disabled={locked} onClick={() => { setVoidId(entry.id); setReason(""); }}>
                Hoàn tác ghi nhận
              </Button>
            )}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={locked || offset === 0} onClick={() => setOffset(Math.max(0, offset-100))}>Khoản mới hơn</Button>
        <Button size="sm" variant="outline" disabled={locked || entries.length < 100} onClick={() => setOffset(offset+100)}>Khoản cũ hơn</Button>
      </div>
      </details>
      {voidId && (
        <form onSubmit={(e) => void reverse(e)} className="space-y-2 rounded-lg border border-rose-200 p-3">
          <Label htmlFor="voidReason">Lý do hoàn tác</Label>
          <Input id="voidReason" required maxLength={500} value={reason} disabled={locked} onChange={(e) => setReason(e.target.value)} />
          <div className="flex gap-2">
            <Button type="submit" variant="destructive" disabled={busy || refreshFailed || !!attempt}>
              {voidAttempt ? "Thử lại hoàn tác" : "Xác nhận hoàn tác"}
            </Button>
            <Button type="button" variant="outline" disabled={locked} onClick={() => setVoidId("")}>Đóng</Button>
          </div>
          <p className="text-xs">Thao tác này điều chỉnh sổ thu; việc hoàn tiền cho khách cần được thực hiện và đối chiếu riêng.</p>
        </form>
      )}
    </section>
  );
}
