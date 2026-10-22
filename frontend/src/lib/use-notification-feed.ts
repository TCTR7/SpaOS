"use client";
import * as React from "react";
import { useRefreshOnReturn } from "./use-refresh-on-return";
import type { NotificationItem, NotificationsListResponse } from "./types";

/** One mutation at a time; pre-mutation reads cannot restore an obsolete counter. */
export function useNotificationFeed(scope: string, actions: {
  load: () => Promise<NotificationsListResponse>;
  read: (id: string) => Promise<unknown>;
  readAll: () => Promise<unknown>;
}) {
  const latest = React.useRef(actions);
  latest.current = actions;
  const request = React.useRef(0);
  const lifetime = React.useRef(0);
  const alive = React.useRef(false);
  const flight = React.useRef(false);
  const [items, setItems] = React.useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [readBusy, setReadBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => {
    alive.current = true; lifetime.current += 1; flight.current = false;
    setItems([]); setUnreadCount(0); setReadBusy(false);
    return () => { alive.current = false; lifetime.current += 1; request.current += 1; };
  }, [scope]);
  const load = React.useCallback(async (afterMutation = false): Promise<void> => {
    if (!alive.current || (flight.current && !afterMutation)) return;
    const attempt = ++request.current;
    const generation = lifetime.current;
    const current = () => alive.current && generation === lifetime.current && request.current === attempt;
    setLoading(true); setError(null);
    try {
      const result = await latest.current.load();
      if (!current()) return;
      setItems(result.items); setUnreadCount(result.unread_count);
    } catch {
      if (current()) setError("Không tải được thông báo. Hãy thử làm mới.");
    } finally { if (current()) setLoading(false); }
  }, [scope]);
  const mark = async (id?: string): Promise<void> => {
    if (!alive.current || flight.current) return;
    flight.current = true;
    const generation = lifetime.current;
    const current = () => alive.current && generation === lifetime.current;
    request.current += 1; setLoading(false); setReadBusy(true); setError(null);
    try {
      if (id === undefined) await latest.current.readAll();
      else await latest.current.read(id);
      if (current()) await load(true);
    } catch {
      if (current()) setError("Không cập nhật được thông báo. Hãy thử lại.");
    } finally { if (current()) { flight.current = false; setReadBusy(false); } }
  };
  useRefreshOnReturn(() => void load(), !readBusy);
  const loadNotifications = React.useCallback(() => load(), [load]);
  return { items, unreadCount, loading, readBusy, error, loadNotifications,
    handleMarkOneRead: (id: string) => mark(id), handleMarkAllRead: () => mark() };
}
