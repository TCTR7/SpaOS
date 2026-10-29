"use client";
import * as React from "react";
import { spaSlug } from "./spa-path";

type Guard = { dirty: boolean; pending: boolean };
const guards = new Map<string, Guard>();
function lockName(): string {
  const slug=typeof window!=="undefined"?spaSlug(window.location.pathname):null;
  return "spaos-admin-branch-work"+(slug?":"+slug:"");
}
let releaseLease: (() => void) | undefined;
let lease: Promise<void> | undefined;
let paused = false;
let channel: BroadcastChannel | undefined;
let channelName = "";
type Work = { tab: string; title: string; path: string; pending: boolean };
let replies: Work[] = [];
function location(): Work {
  if (!window.name.startsWith("spaos-work-")) window.name = "spaos-work-" + crypto.randomUUID();
  return { tab: window.name, title: document.querySelector("dialog[open] h2")?.textContent || document.querySelector("h1")?.textContent || "Màn hình quản lý", path: window.location.pathname, pending: state().pending };
}
function workChannel(): BroadcastChannel | undefined {
  if (typeof BroadcastChannel === "undefined") return;
  if (channelName !== lockName()) { channel?.close(); channel=undefined; channelName=lockName(); }
  if (!channel) {
    channel = new BroadcastChannel(channelName);
    channel.onmessage = event => {
      if (event.data?.type === "locate" && (state().dirty || state().pending)) channel?.postMessage({ type:"work", work:location() });
      if (event.data?.type === "work") replies.push(event.data.work as Work);
    };
  }
  return channel;
}
async function showWork(): Promise<void> {
  replies = state().dirty || state().pending ? [location()] : [];
  workChannel()?.postMessage({ type:"locate" });
  await new Promise(resolve => setTimeout(resolve, 180));
  window.dispatchEvent(new CustomEvent("spaos:unfinished-work", { detail:replies }));
}

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
  lease = (async () => { await navigator.locks.request(lockName(), { mode: "shared" }, () => new Promise<void>((resolve) => {
    releaseLease = resolve;
    if (paused || (!state().dirty && !state().pending)) resolve();
  })); })().finally(() => { lease = undefined; releaseLease = undefined; syncLease(); });
}

export function useBranchGuard(dirty: boolean, pending: boolean): void {
  const id = React.useId();
  React.useLayoutEffect(() => {
    workChannel(); location();
    guards.set(id, { dirty, pending }); syncLease();
    return () => { guards.delete(id); syncLease(); };
  }, [id, dirty, pending]);
}

export async function withAdminWrite<T>(action: () => Promise<T>): Promise<T> {
  if (typeof navigator === "undefined" || !navigator.locks) return action();
  return navigator.locks.request(lockName(), { mode: "shared", ifAvailable: true }, (lock) => {
    if (!lock) throw new Error("Đang chuyển chi nhánh ở cửa sổ khác. Vui lòng chờ trước khi lưu.");
    return action();
  });
}

export async function withBranchChange<T>(action: () => Promise<T>, discard = false): Promise<T> {
  if (paused) throw new Error("\u0110ang chuy\u1ec3n chi nh\u00e1nh. Vui l\u00f2ng ch\u1edd.");
  if (state().pending) { await showWork(); throw new Error("Còn thao tác đang xử lý. Mở công việc đang dở bên dưới để tiếp tục."); }
  if (state().dirty && !discard) throw new BranchDirtyError("Có thay đổi chưa lưu.");
  if (!navigator.locks) throw new Error("Chưa thể chuyển chi nhánh trên trình duyệt này. Vui lòng cập nhật trình duyệt và thử lại.");
  paused = true; releaseLease?.();
  try {
    await lease;
    return await navigator.locks.request(lockName(), { mode: "exclusive", ifAvailable: true }, async (lock) => {
      if (!lock) { await showWork(); throw new Error("Tab khác còn form chưa lưu hoặc thao tác đang xử lý. Chọn Đến công việc đang dở bên dưới."); }
      if (state().pending) throw new Error("Cần đối chiếu kết quả trước khi đổi chi nhánh.");
      return action();
    });
  } finally { paused = false; syncLease(); }
}

/** Same-branch navigation only: protect this page without acquiring a branch-switch lock. */
export function assertAdminNavigationSafe(): void {
  if (state().pending || state().dirty) throw new Error("Hãy lưu hoặc hoàn tất công việc đang làm trước khi mở lịch hẹn.");
}
