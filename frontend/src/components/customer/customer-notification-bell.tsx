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
  fetchCustomerNotifications,
  markAllCustomerNotificationsRead,
  markCustomerNotificationRead,
  subscribeCustomerWebPush,
} from "@/lib/customer-api";
import {
  disableCustomerWebPush,
  enableCustomerWebPush,
  getActivePushSubscription,
  isWebPushSupported,
} from "@/lib/web-push";
import type { NotificationItem } from "@/lib/types";
import { cn, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function CustomerNotificationBell({
  slug,
  themeColor,
}: {
  slug: string;
  themeColor: string;
}): React.ReactElement {
  const [open, setOpen] = React.useState<boolean>(false);
  const [unreadCount, setUnreadCount] = React.useState<number>(0);
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [pushSubscribed, setPushSubscribed] = React.useState<boolean>(false);
  const [pushSupported, setPushSupported] = React.useState<boolean>(false);
  const [pushBusy, setPushBusy] = React.useState<boolean>(false);
  const [pushMsg, setPushMsg] = React.useState<string | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  const loadNotifications = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const res = await fetchCustomerNotifications(slug);
      setUnreadCount(res.unread_count);
      setItems(res.items);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [slug]);

  React.useEffect(() => {
    void loadNotifications();
    const timer = window.setInterval(() => {
      void loadNotifications();
    }, 20000);
    return () => window.clearInterval(timer);
  }, [loadNotifications]);

  React.useEffect(() => {
    const supported = isWebPushSupported();
    setPushSupported(supported);
    if (!supported) return;

    void (async () => {
      const sub = await getActivePushSubscription();
      if (sub) {
        setPushSubscribed(true);
        const json = sub.toJSON();
        if (json.endpoint && json.keys?.p256dh && json.keys?.auth) {
          await subscribeCustomerWebPush(slug, {
            endpoint: json.endpoint,
            keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
            user_agent: navigator.userAgent,
          }).catch(() => {});
        }
      }
    })();
  }, [slug]);

  React.useEffect(() => {
    if (!open) return;
    const onOutside = (e: MouseEvent): void => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [open]);

  const handleEnablePush = async (): Promise<void> => {
    setPushBusy(true);
    setPushMsg(null);
    try {
      await enableCustomerWebPush(slug);
      setPushSubscribed(true);
      setPushMsg("Đã bật thông báo nhắc lịch trên điện thoại!");
    } catch (err) {
      setPushMsg(
        err instanceof Error ? err.message : "Không thể bật thông báo đẩy"
      );
    } finally {
      setPushBusy(false);
    }
  };

  const handleDisablePush = async (): Promise<void> => {
    setPushBusy(true);
    setPushMsg(null);
    try {
      await disableCustomerWebPush(slug);
      setPushSubscribed(false);
      setPushMsg("Đã tắt thông báo đẩy trên thiết bị này.");
    } catch (err) {
      setPushMsg(
        err instanceof Error ? err.message : "Không thể tắt thông báo đẩy"
      );
    } finally {
      setPushBusy(false);
    }
  };

  const handleMarkOneRead = async (id: string): Promise<void> => {
    try {
      const updated = await markCustomerNotificationRead(slug, id);
      setItems((prev) => prev.map((n) => (n.id === id ? updated : n)));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async (): Promise<void> => {
    try {
      await markAllCustomerNotificationsRead(slug);
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
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
          const next = !open;
          setOpen(next);
          if (next) void loadNotifications();
        }}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-background text-slate-700 transition hover:bg-muted"
        aria-label="Thông báo lịch hẹn"
      >
        {unreadCount > 0 ? (
          <BellRing className="h-4 w-4" style={{ color: themeColor }} />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        {unreadCount > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-bold text-white"
            style={{ backgroundColor: themeColor }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-border bg-card shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
            <span className="text-xs font-bold text-foreground">
              Thông báo ({unreadCount} mới)
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => void loadNotifications()}
                className="rounded p-1 text-muted-foreground hover:bg-muted"
              >
                <RefreshCw
                  className={cn("h-3.5 w-3.5", loading && "animate-spin")}
                />
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => void handleMarkAllRead()}
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold"
                  style={{ color: themeColor }}
                >
                  <CheckCheck className="h-3 w-3" />
                  Đọc hết
                </button>
              )}
            </div>
          </div>

          {pushSupported && (
            <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/40 px-3.5 py-2">
              <span className="flex items-center gap-1.5 text-[11px] text-slate-700">
                <Radio
                  className={cn(
                    "h-3.5 w-3.5",
                    pushSubscribed ? "text-emerald-600" : "text-slate-400"
                  )}
                />
                Nhắc lịch tự động:{" "}
                <strong>{pushSubscribed ? "Bật" : "Tắt"}</strong>
              </span>
              {pushSubscribed ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={pushBusy}
                  onClick={() => void handleDisablePush()}
                >
                  Tắt
                </Button>
              ) : (
                <Button
                  size="sm"
                  disabled={pushBusy}
                  style={{ backgroundColor: themeColor }}
                  onClick={() => void handleEnablePush()}
                >
                  Bật Push
                </Button>
              )}
            </div>
          )}

          {pushMsg && (
            <div className="border-b border-border bg-accent/50 px-3.5 py-1.5 text-[11px] text-accent-foreground">
              {pushMsg}
            </div>
          )}

          <div className="max-h-72 overflow-y-auto divide-y divide-border">
            {items.length === 0 ? (
              <p className="p-6 text-center text-xs text-muted-foreground">
                Chưa có thông báo nào từ Spa.
              </p>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start justify-between gap-2 px-3.5 py-2.5 text-xs",
                    !item.is_read && "bg-primary/5"
                  )}
                >
                  <div className="space-y-0.5">
                    <p className="font-semibold text-foreground">
                      {item.title}
                    </p>
                    <p className="text-slate-600">{item.body}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {formatDateTimeVN(item.created_at)}
                    </p>
                  </div>
                  {!item.is_read && (
                    <button
                      type="button"
                      onClick={() => void handleMarkOneRead(item.id)}
                      className="rounded p-1 hover:bg-muted"
                      style={{ color: themeColor }}
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
