"use client";

import * as React from "react";
import { useBranchGuard } from "@/lib/branch-guard";
import {
  Bell,
  BellRing,
  Check,
  CheckCheck,
  Radio,
  RefreshCw,
} from "lucide-react";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  subscribeWebPush,
} from "@/lib/api";
import {
  disableAdminWebPush,
  enableAdminWebPush,
  getActivePushSubscription,
  isWebPushSupported,
} from "@/lib/web-push";
import type { NotificationItem } from "@/lib/types";
import { cn, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export function NotificationBell(): React.ReactElement {
  const [open, setOpen] = React.useState<boolean>(false);
  const [unreadCount, setUnreadCount] = React.useState<number>(0);
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [pushSubscribed, setPushSubscribed] = React.useState<boolean>(false);
  const [pushSupported, setPushSupported] = React.useState<boolean>(false);
  const [pushBusy, setPushBusy] = React.useState<boolean>(false);
  const [pushMessage, setPushMessage] = React.useState<string | null>(null);
  useBranchGuard(false, pushBusy);
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const request = React.useRef(0);
  const [error, setError] = React.useState<string | null>(null);

  const loadNotifications = React.useCallback(async (): Promise<void> => {
    const attempt = ++request.current;
    setLoading(true); setError(null);
    try {
      const res = await fetchNotifications({ limit: 30, offset: 0 });
      if (request.current !== attempt) return;
      setUnreadCount(res.unread_count);
      setItems(res.items);
    } catch {
      if (request.current === attempt) setError("Không tải được thông báo. Hãy thử làm mới.");
    } finally {
      if (request.current === attempt) setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadNotifications();
    const timer = window.setInterval(() => {
      void loadNotifications();
    }, 20000);
    return () => { request.current += 1; window.clearInterval(timer); };
  }, [loadNotifications]);

  React.useEffect(() => {
    const supported = isWebPushSupported();
    setPushSupported(supported);
    if (!supported) return;

    void (async () => {
      const existingSub = await getActivePushSubscription();
      if (existingSub) {
        setPushSubscribed(true);
        const json = existingSub.toJSON();
        if (json.endpoint && json.keys?.p256dh && json.keys?.auth) {
          await subscribeWebPush({
            endpoint: json.endpoint,
            keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
          }).catch(() => {});
        }
      }
    })();
  }, []);


  const handleEnableWebPush = async (): Promise<void> => {
    setPushBusy(true);
    setPushMessage(null);
    try {
      await enableAdminWebPush();
      setPushSubscribed(true);
      setPushMessage("Đã bật nhận thông báo đẩy trình duyệt!");
    } catch (err) {
      setPushMessage(
        err instanceof Error ? err.message : "Không thể bật Web Push"
      );
    } finally {
      setPushBusy(false);
    }
  };

  const handleDisableWebPush = async (): Promise<void> => {
    setPushBusy(true);
    setPushMessage(null);
    try {
      await disableAdminWebPush();
      setPushSubscribed(false);
      setPushMessage("Đã tắt Web Push trên thiết bị này.");
    } catch (err) {
      setPushMessage(
        err instanceof Error ? err.message : "Không thể hủy Web Push"
      );
    } finally {
      setPushBusy(false);
    }
  };

  const handleMarkOneRead = async (id: string): Promise<void> => {
    try {
      const updated = await markNotificationRead(id);
      setItems((prev) =>
        prev.map((item) => (item.id === id ? updated : item))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      setError("Kh\u00f4ng c\u1eadp nh\u1eadt \u0111\u01b0\u1ee3c th\u00f4ng b\u00e1o. H\u00e3y th\u1eed l\u1ea1i.");
    }
  };

  const handleMarkAllRead = async (): Promise<void> => {
    try {
      await markAllNotificationsRead();
      setItems((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch {
      setError("Kh\u00f4ng c\u1eadp nh\u1eadt \u0111\u01b0\u1ee3c th\u00f4ng b\u00e1o. H\u00e3y th\u1eed l\u1ea1i.");
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => {
          const nextOpen = !open;
          setOpen(nextOpen);
          if (nextOpen) void loadNotifications();
        }}
        className="relative inline-flex h-11 w-11 items-center justify-center rounded-full border border-border bg-background text-slate-700 transition hover:bg-accent"
        ref={triggerRef} aria-haspopup="dialog" aria-expanded={open}
        aria-label="Thông báo"
      >
        {unreadCount > 0 ? (
          <BellRing className="h-4 w-4 text-primary" />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground shadow">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title="Bảng thông báo" pending={pushBusy} returnFocusRef={triggerRef} historyGuard>
        <div data-layout-card="notifications" className="min-w-0 [overflow-wrap:anywhere]">
          {error && <p role="alert" className="p-3 text-sm text-rose-700">{error}</p>}
          {loading && <p role="status" className="p-3 text-sm">Đang tải thông báo...</p>}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Thông báo ({unreadCount} chưa đọc)
              </p>
              <p className="text-[11px] text-muted-foreground">
                Cập nhật lịch hẹn mới & hủy lịch theo thời gian thực
              </p>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => void loadNotifications()}
                aria-label="Làm mới thông báo" disabled={loading}
                className="min-h-11 min-w-11 rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Làm mới"
              >
                <RefreshCw
                  className={cn("h-3.5 w-3.5", loading && "animate-spin")}
                />
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => void handleMarkAllRead()}
                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Đọc tất cả
                </button>
              )}
            </div>
          </div>

          {pushSupported && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
              <div className="flex items-center gap-2 text-xs">
                <Radio
                  className={cn(
                    "h-3.5 w-3.5",
                    pushSubscribed ? "text-emerald-600" : "text-slate-400"
                  )}
                />
                <span className="text-slate-700">
                  Web Push:{" "}
                  <strong>{pushSubscribed ? "Đang bật" : "Chưa bật"}</strong>
                </span>
              </div>
              {pushSubscribed ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pushBusy}
                  onClick={() => void handleDisableWebPush()}
                >
                  Tắt Push
                </Button>
              ) : (
                <Button
                  size="sm"
                  disabled={pushBusy}
                  onClick={() => void handleEnableWebPush()}
                >
                  Bật Push
                </Button>
              )}
            </div>
          )}

          {pushMessage && (
            <div className="border-b border-border bg-accent/50 px-4 py-1.5 text-[11px] text-accent-foreground">
              {pushMessage}
            </div>
          )}

          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {items.length === 0 && !error && !loading ? (
              <div className="p-6 text-center text-xs text-muted-foreground">
                Chưa có thông báo nào.
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start justify-between gap-3 px-4 py-3 text-xs transition hover:bg-muted/50",
                    !item.is_read && "bg-primary/5"
                  )}
                >
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <div className="flex items-center gap-1.5">
                      {!item.is_read && (
                        <span className="h-2 w-2 rounded-full bg-primary" />
                      )}
                      <p className="font-semibold text-foreground">
                        {item.title}
                      </p>
                    </div>
                    <p className="text-slate-600">{item.body}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {formatDateTimeVN(item.created_at)}
                    </p>
                  </div>
                  {!item.is_read && (
                    <button
                      type="button"
                      onClick={() => void handleMarkOneRead(item.id)}
                      className="min-h-11 min-w-11 shrink-0 rounded p-1 text-primary hover:bg-primary/10"
                      title="Đánh dấu đã đọc"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}
