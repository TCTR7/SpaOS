"use client";
import * as React from "react";
import { useBranchGuard } from "./branch-guard";
import { ApiError, createManualBatch, fetchManualBatch, type ManualBatchInput, type ManualBatchResult } from "./api";
type Operation = { id: string; at: number; body?: ManualBatchInput };
/** Recovery drafts live only in this tab, scoped to the branch and user. No credentials. */
export function useManualBatch(key: string | null, onSaved: (result: ManualBatchResult) => void,
  onResume: () => void, onRestore?: (body: ManualBatchInput | null) => void) {
  const [state, setState] = React.useState({ busy: false, uncertain: false, error: "" });
  const [queue, setQueue] = React.useState<Operation[]>([]);
  const operation = React.useRef<Operation | null>(null);
  const current = React.useRef(key); current.current = key;
  const flight = React.useRef(false);
  const callbacks = React.useRef({ onSaved, onResume, onRestore });
  callbacks.current = { onSaved, onResume, onRestore };
  useBranchGuard(false, state.busy);
  const persist = (entries: Operation[]): void => {
    setQueue(entries);
    if (key) { sessionStorage.setItem(key + ":queue", JSON.stringify(entries)); sessionStorage.removeItem(key); }
    window.dispatchEvent(new Event("spaos:manual-batch-changed"));
  };
  React.useEffect(() => {
    current.current = key;
    flight.current = false; operation.current = null;
    let entries: Operation[] = [];
    try {
      entries = key ? JSON.parse(sessionStorage.getItem(key + ":queue") || "[]") as Operation[] : [];
      entries = entries.filter(e => /^[a-f0-9-]{36}$/i.test(e.id));
      entries = entries.map(e => Date.now() - e.at > 8 * 3600000 ? { id: e.id, at: e.at } : e);
      const legacy = key && sessionStorage.getItem(key);
      if (legacy && !entries.some(e => e.id === legacy)) entries.push({ id: legacy, at: Date.now() });
    } catch { entries = []; }
    persist(entries); setState({ busy: false, uncertain: false, error: "" });
    return () => { current.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const run = async (mode: "check" | "post", body?: Omit<ManualBatchInput, "request_id">): Promise<void> => {
    if (!key || flight.current || current.current !== key) return;
    const scope = key; flight.current = true;
    const op = operation.current || { id: crypto.randomUUID(), at: Date.now() }; operation.current = op;
    if (body) op.body = { ...body, request_id: op.id };
    const entries = [...queue.filter(e => e.id !== op.id), op]; persist(entries);
    setState({ busy: true, uncertain: true, error: "" });
    try {
      if (mode === "post" && !op.body) throw new Error("Mở bản nháp và kiểm tra lại thông tin trước khi lưu.");
      const result = mode === "check" ? await fetchManualBatch(op.id) : await createManualBatch(op.body!);
      if (current.current !== scope) return;
      persist(entries.filter(e => e.id !== op.id)); operation.current = null;
      setState({ busy: false, uncertain: false, error: "" }); callbacks.current.onSaved(result);
    } catch (error: unknown) {
      if (current.current !== scope) return;
      const absent = mode === "check" && error instanceof ApiError && error.status === 404 && error.message === "Không có lần tạo lịch đã lưu với mã này";
      const rejected = mode === "post" && error instanceof ApiError && [400,403,404,409,422].includes(error.status) && !error.message.includes("Mã tạo lịch đã dùng");
      if (rejected) persist(entries.filter(e => e.id !== op.id));
      // Retain the same UUID for edited retries, even after 404: an old POST may arrive late.
      setState({ busy: false, uncertain: !(absent || rejected), error: absent ? "Chưa có lịch nào được lưu. Bạn có thể chỉnh và lưu lại; hệ thống vẫn chống tạo trùng." : error instanceof Error ? error.message : "Chưa kiểm tra được kết quả. Có thể để sau và tạo lịch cho khách khác." });
    } finally { if (current.current === scope) flight.current = false; }
  };
  return { ...state, queue, canRetry: !!operation.current?.body,
    submit: (body: Omit<ManualBatchInput, "request_id">) => run("post", body), check: () => run("check"), retry: () => run("post"),
    defer: () => { if (flight.current) return; operation.current = null; setState({busy:false,uncertain:false,error:""}); },
    resume: (id: string) => {
      if (flight.current) return; const op = queue.find(e => e.id === id); if (!op) return;
      operation.current = op; callbacks.current.onRestore?.(op.body || null);
      setState({busy:false,uncertain:true,error:"Kiểm tra kết quả trước khi chỉnh yêu cầu này."}); callbacks.current.onResume();
    },
  };
}
