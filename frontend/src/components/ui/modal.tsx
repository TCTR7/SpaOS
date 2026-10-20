"use client";

import * as React from "react";
import { useBranchGuard } from "@/lib/branch-guard";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  maxWidthClass?: string;
  footer?: React.ReactNode;
  pending?: boolean;
  dirty?: boolean;
  historyGuard?: boolean;
  returnFocusRef?: React.RefObject<HTMLElement>;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  maxWidthClass = "max-w-lg",
  footer, pending = false, dirty = false, historyGuard = false,
  returnFocusRef,
}: ModalProps): React.ReactElement | null {
  const adminSurface = typeof window !== "undefined" && window.location.pathname.startsWith("/admin/");
  useBranchGuard(adminSurface && open && dirty, adminSurface && open && pending);
  const id = React.useId();
  const dialog = React.useRef<HTMLDialogElement>(null);
  const closeButton = React.useRef<HTMLButtonElement>(null);
  const continueButton = React.useRef<HTMLButtonElement>(null);
  const [confirmClose, setConfirmClose] = React.useState(false);
  const [blocked, setBlocked] = React.useState(false);
  const latest = React.useRef({ onClose, pending, dirty });
  latest.current = { onClose, pending, dirty };
  const requestClose = React.useCallback((): void => {
    if (latest.current.pending) { setBlocked(true); return; }
    if (latest.current.dirty) { setConfirmClose(true); return; }
    latest.current.onClose();
  }, []);
  React.useLayoutEffect(() => {
    if (!open || !dialog.current) return;
    const element = dialog.current;
    const opener = returnFocusRef?.current || (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    // Portals leave the shell's CSS scope; retain the branch/customer theme.
    if (opener) {
      const theme = getComputedStyle(opener);
      for (const name of ["--brand-color", "--brand-foreground", "--brand-text", "--primary", "--primary-foreground",
        "--primary-text", "--ring", "--accent", "--accent-foreground", "--secondary", "--secondary-foreground"]) {
        const value = theme.getPropertyValue(name);
        if (value) element.style.setProperty(name, value);
      }
    }
    const oldBody = document.body.style.overflow, oldRoot = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden"; document.documentElement.style.overflow = "hidden";
    setConfirmClose(false); setBlocked(false);
    element.showModal(); closeButton.current?.focus();
    let popped = false;
    const pushGuard = (): void => window.history.pushState({ ...window.history.state, spaosDialog: id }, "");
    if (historyGuard && window.history.state?.spaosDialog !== id) pushGuard();
    const onPop = (): void => {
      if (!historyGuard) return;
      if (latest.current.pending || latest.current.dirty) { pushGuard(); requestClose(); }
      else { popped = true; latest.current.onClose(); }
    };
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop); element.close();
      document.body.style.overflow = oldBody; document.documentElement.style.overflow = oldRoot;
      queueMicrotask(() => {
        if (!element.open && historyGuard && !popped && window.history.state?.spaosDialog === id) window.history.back();
      });
      if (opener?.isConnected && !opener.closest("[inert]")) opener.focus({ preventScroll: true });
      else {
        const fallback = document.querySelector<HTMLElement>("main h1,main");
        if (fallback) { const old = fallback.getAttribute("tabindex"); fallback.tabIndex = -1;
          fallback.focus({ preventScroll: true });
          if (old === null) fallback.removeAttribute("tabindex"); else fallback.setAttribute("tabindex", old); }
      }
    };
  }, [open, historyGuard, id, requestClose, returnFocusRef]);
  React.useEffect(() => { if (confirmClose) continueButton.current?.focus(); }, [confirmClose]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <dialog ref={dialog} role="dialog" aria-labelledby={`${id}-title`} aria-describedby={description ? `${id}-description` : undefined}
      aria-modal="true" className="fixed inset-0 m-0 h-[100dvh] max-h-none w-full max-w-none border-0 bg-transparent p-0 text-foreground backdrop:bg-black/50 open:flex items-center justify-center sm:p-4"
      onCancel={(event) => { event.preventDefault(); requestClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) requestClose(); }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const targets = Array.from(dialog.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],summary,[tabindex="0"]') || [])
          .filter((element) => {
            const closed = element.closest("details:not([open])");
            return element.getClientRects().length > 0 && !element.closest("[inert]")
              && element.getAttribute("tabindex") !== "-1" && element.getAttribute("type") !== "hidden"
              && (!closed || !!closed.querySelector("summary")?.contains(element));
          });
        const first = targets[0], last = targets[targets.length - 1];
        if (!first) { event.preventDefault(); dialog.current?.focus(); }
        else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }}>
      <div
        data-layout-card="modal"
        className={cn(
          "flex h-[100dvh] w-full min-w-0 flex-col overflow-hidden border border-border bg-card shadow-xl sm:h-auto sm:max-h-[90dvh] sm:rounded-xl",
          maxWidthClass
        )}
      >
        <header className="shrink-0 border-b border-border px-4 py-3 sm:px-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 [overflow-wrap:anywhere]">
            <h2 id={`${id}-title`} className="text-lg font-semibold text-foreground">{title}</h2>
            {description && (
              <p id={`${id}-description`} className="mt-0.5 text-xs text-muted-foreground">
                {description}
              </p>
            )}
          </div>
          <Button ref={closeButton} size="icon" variant="ghost"
            type="button"
            onClick={requestClose}
            aria-label="Đóng"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        {blocked && pending && <p role="status" className="mt-2 text-sm">Đang xử lý hoặc cần đối chiếu kết quả. Hoàn tất trước khi đóng.</p>}
        {confirmClose && <section aria-label="Bỏ thay đổi đang nhập" className="mt-3 space-y-2 rounded-lg border p-3">
          <p className="text-sm">Bạn có muốn bỏ các thay đổi đang nhập?</p>
          <div className="flex flex-wrap gap-2">
            <Button ref={continueButton} variant="outline" onClick={() => { setConfirmClose(false); queueMicrotask(() => closeButton.current?.focus()); }}>Tiếp tục chỉnh sửa</Button>
            <Button variant="destructive" disabled={pending} onClick={() => latest.current.onClose()}>Bỏ thay đổi</Button>
          </div>
        </section>}
        </header>
        <div data-modal-scroll ref={(element) => { element?.toggleAttribute("inert", confirmClose); }}
          className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 [overflow-wrap:anywhere] sm:px-6">{children}</div>
        {footer && <footer ref={(element) => { element?.toggleAttribute("inert", confirmClose); }}
          className="shrink-0 border-t border-border px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">{footer}</footer>}
      </div>
    </dialog>, document.body
  );
}
