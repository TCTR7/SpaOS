"use client";

import * as React from "react";
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
  fetchVapidPublicKey,
  markAllNotificationsRead,
  markNotificationRead,
  subscribeWebPush,
  unsubscribeWebPush,
} from "@/lib/api";
import type { NotificationItem } from "@/lib/types";
import { cn, formatDateTimeVN, urlBase64ToUint8Array } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function NotificationBell(): React.ReactElement {
  const [open, setOpen] = React.useState<boolean>(false);
  const [unreadCount, setUnreadCount] = React.useState<number>(0);
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [pushSubscribed, setPushSubscribed] = React.useState<boolean>(false);
  const [pushSupported, setPushSupported] = React.useState<boolean>(false);
  const [pushBusy, setPushBusy] = React.useState<boolean>(false);
  const [pushMessage, setPushMessage] = React.useState<string | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  const loadNotifications = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const res = await fetchNotifications({ limit: 30, offset: 0 });
      setUnreadCount(res.unread_count);
      setItems(res.items);
    } catch {
      // ignore background poll errors
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll notifications every 20s and on initial mount
  React.useEffect(() => {
    void loadNotifications();
    const timer = window.setInterval(() => {
      void loadNotifications();
    }, 20000);
    return () => window.clearInterval(timer);
  }, [loadNotifications]);

  // Check Service Worker & Web Push subscription state
  React.useEffect(() => {
    if (
      typeof window === "undefined" ||
      !("serviceWorker" in navigator) ||
      !("PushManager" in window)
    ) {
      setPushSupported(false);
      return;
    }
    setPushSupported(true);

    void (async () => {
      try {
        const reg = await navigator.serviceWorker.register("/sw.js");
        const existingSub = await reg.pushManager.getSubscription();
        if (existingSub) {
          setPushSubscribed(true);
          const json = existingSub.toJSON();
          if (json.endpoint && json.keys?.p256dh && json.keys?.auth) {
            await subscribeWebPush({
              endpoint: json.endpoint,
              keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
              user_agent: navigator.userAgent,
            }).catch(() => {});
          }
        }
      } catch {
        // SW registration failed
      }
    })();
  }, []);

  // Close dropdown on click outside
  React.useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent): void => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const handleEnableWebPush = async (): Promise<void> => {
    setPushBusy(true);
    setPushMessage(null);
    try {
      const vapid = await fetchVapidPublicKey();
      if (!vapid.enabled || !vapid.public_key) {
        setPushMessage("Server chưa cấu hình VAPID_PUBLIC_KEY.");
        return;
      }
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setPushMessage("Trình duyệt đã từ chối quyền thông báo.");
        return;
      }
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const appServerKey = urlBase64ToUint8Array(vapid.public_key);
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appServerKey.buffer as ArrayBuffer,
      });
      const json = sub.toJSON();
      if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
        setPushMessage("Không đọc được khóa mã hóa Push Subscription.");
        return;
      }
      await subscribeWebPush({
        endpoint: json.endpoint,
        keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
        user_agent: navigator.userAgent,
      });
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
      const reg = await navigator.serviceWorker.getRegistration();
      const sub = await reg?.pushManager.getSubscription();
      if (sub) {
        await unsubscribeWebPush(sub.endpoint).catch(() => {});
        await sub.unsubscribe();
      }
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
      // ignore
    }
  };

  const handleMarkAllRead = async (): Promise<void> => {
    try {
      await markAllNotificationsRead();
      setItems((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
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
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-background text-slate-700 transition hover:bg-accent"
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

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl border border-border bg-card shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
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
                className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
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
            <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
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
            {items.length === 0 ? (
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
                  <div className="space-y-0.5">
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
                      className="shrink-0 rounded p-1 text-primary hover:bg-primary/10"
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
      )}
    </div>
  );
}
