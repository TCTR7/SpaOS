"use client";
import * as React from "react";

type Guard = { dirty: boolean; pending: boolean };
const guards = new Map<string, Guard>();
const LOCK = "spaos-admin-branch-work";
let releaseLease: (() => void) | undefined;
let lease: Promise<void> | undefined;
let paused = false;

export class BranchDirtyError extends Error {}

function state(): Guard {
  const values = Array.from(guards.values());
  return { dirty: values.some((g) => g.dirty), pending: values.some((g) => g.pending) };
}

function syncLease(): void {
  if (typeof navigator === "undefined" || !navigator.locks) return;
  const active = state();
  if (paused || (!active.dirty && !active.pending)) { releaseLease?.(); return; }
  if (lease) return;
  // A shared lease keeps another tab from switching while this tab has work.
  lease = (async () => { await navigator.locks.request(LOCK, { mode: "shared" }, () => new Promise<void>((resolve) => {
    releaseLease = resolve;
    if (paused || (!state().dirty && !state().pending)) resolve();
  })); })().finally(() => { lease = undefined; releaseLease = undefined; syncLease(); });
}

export function useBranchGuard(dirty: boolean, pending: boolean): void {
  const id = React.useId();
  React.useLayoutEffect(() => {
    guards.set(id, { dirty, pending }); syncLease();
    return () => { guards.delete(id); syncLease(); };
  }, [id, dirty, pending]);
}

export async function withAdminWrite<T>(action: () => Promise<T>): Promise<T> {
  if (typeof navigator === "undefined" || !navigator.locks) return action();
  return navigator.locks.request(LOCK, { mode: "shared", ifAvailable: true }, (lock) => {
    if (!lock) throw new Error("Đang chuyển chi nhánh ở cửa sổ khác. Vui lòng chờ trước khi lưu.");
    return action();
  });
}

export async function withBranchChange<T>(action: () => Promise<T>, discard = false): Promise<T> {
  if (paused) throw new Error("\u0110ang chuy\u1ec3n chi nh\u00e1nh. Vui l\u00f2ng ch\u1edd.");
  if (state().pending) throw new Error("Còn thao tác đang xử lý hoặc cần đối chiếu kết quả. Hoàn tất trước khi đổi chi nhánh.");
  if (state().dirty && !discard) throw new BranchDirtyError("Có thay đổi chưa lưu.");
  if (!navigator.locks) throw new Error("Chưa thể chuyển chi nhánh trên trình duyệt này. Vui lòng cập nhật trình duyệt và thử lại.");
  paused = true; releaseLease?.();
  try {
    await lease;
    return await navigator.locks.request(LOCK, { mode: "exclusive", ifAvailable: true }, (lock) => {
      if (!lock) throw new Error("Tab khác còn form chưa lưu hoặc thao tác đang xử lý. Hoàn tất ở tab đó trước khi đổi chi nhánh.");
      if (state().pending) throw new Error("Cần đối chiếu kết quả trước khi đổi chi nhánh.");
      return action();
    });
  } finally { paused = false; syncLease(); }
}
