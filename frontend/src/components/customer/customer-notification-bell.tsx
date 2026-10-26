"use client";

import * as React from "react";
import { NotificationBookingLink } from "@/components/notification-booking-link";
import { useNotificationFeed } from "@/lib/use-notification-feed";
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
} from "@/lib/customer-api";
import {
  disableCustomerWebPush,
  enableCustomerWebPush,
  syncExistingWebPush,
  isWebPushSupported,
} from "@/lib/web-push";
import { cn, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export function CustomerNotificationBell({
  slug,
  themeColor,
}: {
  slug: string;
  themeColor: string;
}): React.ReactElement {
  const [open, setOpen] = React.useState<boolean>(false);
  const [pushSubscribed, setPushSubscribed] = React.useState<boolean>(false);
  const [pushSupported, setPushSupported] = React.useState<boolean>(false);
  const [pushBusy, setPushBusy] = React.useState<boolean>(false);
  const pushAlive = React.useRef(false);
  const pushFlight = React.useRef(false);
  React.useEffect(() => { pushAlive.current = true; return () => { pushAlive.current = false; }; }, []);
  const [pushMsg, setPushMsg] = React.useState<string | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const { items, unreadCount, loading, readBusy, error, loadNotifications,
    handleMarkOneRead, handleMarkAllRead } = useNotificationFeed(slug, {
    load: () => fetchCustomerNotifications(slug), read: (id) => markCustomerNotificationRead(slug, id), readAll: () => markAllCustomerNotificationsRead(slug),
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
    void syncExistingWebPush(slug, () => !cancelled)
      .then((subscribed) => { if (!cancelled) setPushSubscribed(subscribed); }).catch(() => {});
    return () => { cancelled = true; };
  }, [slug]);


  const handleEnablePush = async (): Promise<void> => {
    if (pushFlight.current || !pushAlive.current) return;
    pushFlight.current = true;
    setPushBusy(true);
    setPushMsg(null);
    try {
      await enableCustomerWebPush(slug, () => pushAlive.current);
      setPushSubscribed(true);
      setPushMsg("Đã bật thông báo trên thiết bị này.");
    } catch (err) {
      setPushMsg(
        err instanceof Error ? err.message : "Chưa thể bật thông báo. Vui lòng thử lại."
      );
    } finally {
      pushFlight.current = false;
      if (pushAlive.current) setPushBusy(false);
    }
  };

  const handleDisablePush = async (): Promise<void> => {
    if (pushFlight.current || !pushAlive.current) return;
    pushFlight.current = true;
    setPushBusy(true);
    setPushMsg(null);
    try {
      await disableCustomerWebPush(slug, () => pushAlive.current);
      setPushSubscribed(false);
      setPushMsg("Đã tắt thông báo trên thiết bị này.");
    } catch (err) {
      setPushMsg(
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
          const next = !open;
          setOpen(next);
          if (next) void loadNotifications();
        }}
        className="neu-control relative inline-flex h-11 w-11 items-center justify-center rounded-full border border-border bg-background text-slate-700 transition hover:bg-muted"
        ref={triggerRef} aria-haspopup="dialog" aria-expanded={open}
        aria-label="Thông báo lịch hẹn"
      >
        {unreadCount > 0 ? (
          <BellRing className="h-4 w-4" style={{ color: "var(--brand-text)" }} />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        {unreadCount > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-xs font-bold text-white"
            style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title="Bảng thông báo" returnFocusRef={triggerRef} historyGuard>
        <div data-layout-card="notifications" className="min-w-0 [overflow-wrap:anywhere]">
          {error && <p role="alert" className="p-3 text-sm text-rose-700">{error}</p>}
          {loading && <p role="status" className="p-3 text-sm">Đang tải thông báo...</p>}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3.5 py-2.5">
            <span className="text-xs font-bold text-foreground">
              Thông báo ({unreadCount} mới)
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => void loadNotifications()}
                aria-label="Làm mới thông báo" disabled={loading}
                className="min-h-11 min-w-11 rounded p-1 text-muted-foreground hover:bg-muted"
              >
                <RefreshCw
                  className={cn("h-3.5 w-3.5", loading && "animate-spin")}
                />
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  disabled={readBusy} onClick={() => void handleMarkAllRead()}
                  className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
                  style={{ color: "var(--brand-text)" }}
                >
                  <CheckCheck className="h-3 w-3" />
                  Đọc hết
                </button>
              )}
            </div>
          </div>

          {!pushSupported && <p className="px-4 py-3 text-xs text-muted-foreground">Thiết bị này chưa bật được thông báo. Bạn vẫn có thể xem thông báo tại đây. Trên iPhone, hãy thêm ứng dụng vào màn hình chính rồi mở lại để kiểm tra.</p>}
          {pushSupported && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-3.5 py-2">
              <span className="flex items-center gap-1.5 text-xs text-slate-700">
                <Radio
                  className={cn(
                    "h-3.5 w-3.5",
                    pushSubscribed ? "text-emerald-600" : "text-slate-400"
                  )}
                />
                Thông báo trên thiết bị:{" "}
                <strong>{pushSubscribed ? "Đang bật" : "Chưa bật"}</strong>
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
                  style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                  onClick={() => void handleEnablePush()}
                >
                  Bật thông báo
                </Button>
              )}
            </div>
          )}

          {pushSupported && !pushSubscribed && typeof Notification !== "undefined" && Notification.permission === "denied" && <p className="px-4 py-2 text-xs">Thông báo đang bị chặn. Mở cài đặt thông báo của trình duyệt cho trang này để cho phép, rồi thử bật lại.</p>}
          {pushMsg && (
            <div className="border-b border-border bg-accent/50 px-3.5 py-1.5 text-xs text-accent-foreground">
              {pushMsg}
            </div>
          )}

          <div className="max-h-72 overflow-y-auto divide-y divide-border">
            {items.length === 0 && !error && !loading ? (
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
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <p className="font-semibold text-foreground">
                      {item.title}
                    </p>
                    <p className="text-slate-600">{item.body}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTimeVN(item.created_at)}
                    </p>
                    {item.booking_id && <NotificationBookingLink bookingId={item.booking_id} slug={slug} disabled={pushBusy} />}
                  </div>
                  {!item.is_read && (
                    <button
                      type="button"
                      disabled={readBusy} onClick={() => void handleMarkOneRead(item.id)}
                      className="min-h-11 min-w-11 shrink-0 rounded p-1 hover:bg-muted"
                      style={{ color: "var(--brand-text)" }}
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
