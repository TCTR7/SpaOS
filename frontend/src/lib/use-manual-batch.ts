"use client";
import * as React from "react";
import { useBranchGuard } from "./branch-guard";
import { ApiError, createManualBatch, fetchManualBatch, type ManualBatchInput, type ManualBatchResult } from "./api";

/** Persist only the request UUID. Draft/customer data never enters browser storage. */
export function useManualBatch(key: string | null, onSaved: (result: ManualBatchResult) => void, onResume: () => void) {
  const [state, setState] = React.useState({ key, busy: false, uncertain: false, error: "" });
  useBranchGuard(false, state.key === key && (state.busy || state.uncertain));
  const operation = React.useRef<{ key: string | null; id: string; body?: ManualBatchInput }>({ key, id: "" });
  const current = React.useRef(key);
  current.current = key;
  const flight = React.useRef(false);
  const generation = React.useRef(0);
  const callbacks = React.useRef({ onSaved, onResume });
  callbacks.current = { onSaved, onResume };
  React.useEffect(() => {
    current.current = key;
    generation.current += 1;
    flight.current = false;
    const id = key ? sessionStorage.getItem(key) || "" : "";
    operation.current = { key, id };
    setState({ key, busy: false, uncertain: !!id, error: id ? "Có lần tạo lịch cần kiểm tra kết quả trước khi đặt thêm." : "" });
    if (id) callbacks.current.onResume();
    return () => { current.current = null; generation.current += 1; };
  }, [key]);

  const run = async (mode: "check" | "post", body?: Omit<ManualBatchInput, "request_id">): Promise<void> => {
    if (!key || flight.current || current.current !== key) return;
    flight.current = true;
    const attempt = generation.current;
    setState({ key, busy: true, uncertain: mode === "check" || !!operation.current.id, error: "" });
    try {
      const op = operation.current;
      if (op.key !== key) return;
      if (!op.id) op.id = crypto.randomUUID();
      // Keep this UUID even after a 404: an older POST might arrive late.
      // A subsequent edited request with the same UUID cannot create a second batch.
      sessionStorage.setItem(key, op.id);
      window.dispatchEvent(new Event("spaos:manual-batch-changed"));
      if (body) op.body = { ...body, request_id: op.id };
      if (mode === "post" && !op.body) throw new Error("Hãy kiểm tra kết quả trước khi nhập lại.");
      const result = mode === "check" ? await fetchManualBatch(op.id) : await createManualBatch(op.body!);
      if (current.current !== key || generation.current !== attempt) return;
      sessionStorage.removeItem(key);
      window.dispatchEvent(new Event("spaos:manual-batch-changed"));
      operation.current = { key, id: "" };
      setState({ key, busy: false, uncertain: false, error: "" });
      callbacks.current.onSaved(result);
    } catch (error: unknown) {
      if (current.current !== key || generation.current !== attempt) return;
      const absent = mode === "check" && error instanceof ApiError && error.status === 404
        && error.message === "Không có lần tạo lịch đã lưu với mã này";
      if (absent) operation.current.body = undefined;
      setState({ key, busy: false, uncertain: !absent,
        error: absent ? "Chưa có lịch nào được lưu với mã này. Bạn có thể chỉnh lại và xác nhận; mã chống lặp được giữ nguyên."
          : error instanceof Error ? error.message : "Không kiểm tra được kết quả. Vui lòng thử lại." });
    } finally {
      if (current.current === key && generation.current === attempt) flight.current = false;
    }
  };
  return {
    busy: state.key === key && state.busy, uncertain: state.key === key && state.uncertain,
    error: state.key === key ? state.error : "",
    canRetry: state.key === key && !!operation.current.body,
    submit: (body: Omit<ManualBatchInput, "request_id">) => run("post", body),
    check: () => run("check"), retry: () => run("post"),
  };
}
