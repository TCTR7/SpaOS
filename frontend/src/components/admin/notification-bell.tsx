"use client";

import * as React from "react";
import { NotificationBookingLink } from "@/components/notification-booking-link";
import { useNotificationFeed } from "@/lib/use-notification-feed";
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
} from "@/lib/api";
import {
  disableAdminWebPush,
  enableAdminWebPush,
  syncExistingWebPush,
  isWebPushSupported,
} from "@/lib/web-push";
import { cn, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export function NotificationBell(): React.ReactElement {
  const [open, setOpen] = React.useState<boolean>(false);
  const [pushSubscribed, setPushSubscribed] = React.useState<boolean>(false);
  const [pushSupported, setPushSupported] = React.useState<boolean>(false);
  const [pushBusy, setPushBusy] = React.useState<boolean>(false);
  const pushAlive = React.useRef(false);
  const pushFlight = React.useRef(false);
  React.useEffect(() => { pushAlive.current = true; return () => { pushAlive.current = false; }; }, []);
  const [pushMessage, setPushMessage] = React.useState<string | null>(null);
  useBranchGuard(false, pushBusy);
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const { items, unreadCount, loading, readBusy, error, loadNotifications,
    handleMarkOneRead, handleMarkAllRead } = useNotificationFeed("admin", {
    load: () => fetchNotifications({ limit: 30, offset: 0 }), read: markNotificationRead, readAll: markAllNotificationsRead,
  });
  React.useEffect(() => {
    void loadNotifications();
    const timer = window.setInterval(() => {
      void loadNotifications();
    }, 20000);
    return () => { window.clearInterval(timer); };
  }, [loadNotifications]);

  React.useEffect(() => {
    const supported = isWebPushSupported();
    setPushSupported(supported);
    if (!supported) return;

    let cancelled = false;
    void syncExistingWebPush(undefined, () => !cancelled)
      .then((subscribed) => { if (!cancelled) setPushSubscribed(subscribed); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);


  const handleEnableWebPush = async (): Promise<void> => {
    if (pushFlight.current || !pushAlive.current) return;
    pushFlight.current = true;
    setPushBusy(true);
    setPushMessage(null);
    try {
      await enableAdminWebPush(() => pushAlive.current);
      setPushSubscribed(true);
      setPushMessage("Đã bật thông báo trên thiết bị này.");
    } catch (err) {
      setPushMessage(
        err instanceof Error ? err.message : "Chưa thể bật thông báo. Vui lòng thử lại."
      );
    } finally {
      pushFlight.current = false;
      if (pushAlive.current) setPushBusy(false);
    }
  };

  const handleDisableWebPush = async (): Promise<void> => {
    if (pushFlight.current || !pushAlive.current) return;
    pushFlight.current = true;
    setPushBusy(true);
    setPushMessage(null);
    try {
      await disableAdminWebPush(() => pushAlive.current);
      setPushSubscribed(false);
      setPushMessage("Đã tắt thông báo trên thiết bị này.");
    } catch (err) {
      setPushMessage(
        err instanceof Error ? err.message : "Chưa thể tắt thông báo. Vui lòng thử lại."
      );
    } finally {
      pushFlight.current = false;
      if (pushAlive.current) setPushBusy(false);
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
          <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-xs font-bold text-primary-foreground shadow">
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
              <p className="text-xs text-muted-foreground">
                Lịch mới và các thay đổi lịch hẹn
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
                  disabled={readBusy} onClick={() => void handleMarkAllRead()}
                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Đọc tất cả
                </button>
              )}
            </div>
          </div>

          {!pushSupported && <p className="px-4 py-3 text-xs text-muted-foreground">Thiết bị này chưa bật được thông báo. Bạn vẫn có thể xem thông báo tại đây. Trên iPhone, hãy thêm ứng dụng vào màn hình chính rồi mở lại để kiểm tra.</p>}
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
                  Thông báo trên thiết bị:{" "}
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
                  Tắt thông báo
                </Button>
              ) : (
                <Button
                  size="sm"
                  disabled={pushBusy}
                  onClick={() => void handleEnableWebPush()}
                >
                  Bật thông báo
                </Button>
              )}
            </div>
          )}

          {pushSupported && !pushSubscribed && typeof Notification !== "undefined" && Notification.permission === "denied" && <p className="px-4 py-2 text-xs">Thông báo đang bị chặn. Mở cài đặt thông báo của trình duyệt cho trang này để cho phép, rồi thử bật lại.</p>}
          {pushMessage && (
            <div className="border-b border-border bg-accent/50 px-4 py-1.5 text-xs text-accent-foreground">
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
                    <p className="text-xs text-muted-foreground">
                      {formatDateTimeVN(item.created_at)}
                    </p>
                    {item.booking_id && <NotificationBookingLink bookingId={item.booking_id} disabled={pushBusy} />}
                  </div>
                  {!item.is_read && (
                    <button
                      type="button"
                      disabled={readBusy} onClick={() => void handleMarkOneRead(item.id)}
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
