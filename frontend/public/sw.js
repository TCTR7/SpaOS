/* eslint-disable no-restricted-globals */
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let payload = {
    title: "SpaOS - Thông báo lịch hẹn",
    body: "Bạn có cập nhật mới về lịch hẹn tại Spa.",
    icon: "/icons/icon-192x192.png?v=20261023",
    url: "",
    booking_id: "",
    type: "BOOKING_CREATED",
    tenant_slug: "",
  };

  if (event.data) {
    try {
      const parsed = event.data.json();
      payload = { ...payload, ...parsed };
    } catch {
      payload.body = event.data.text();
    }
  }

  let targetUrl = payload.url;
  if (!targetUrl) {
    if (payload.tenant_slug) {
      targetUrl = `/${payload.tenant_slug}/appointments`;
    } else if (payload.type === "BOOKING_CREATED") {
      targetUrl = "/admin/bookings";
    } else {
      targetUrl = "/";
    }
  }

  const options = {
    body: payload.body,
    icon: payload.icon || "/icons/icon-192x192.png?v=20261023",
    badge: "/icons/icon-192x192.png?v=20261023",
    tag: payload.booking_id ? `booking-${payload.booking_id}` : "spaos-push",
    data: {
      url: targetUrl,
      booking_id: payload.booking_id || "",
      type: payload.type || "",
    },
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  let targetPath = new URL(self.registration.scope).pathname;
  try {
    const target = new URL(data.url || "/admin/bookings", self.location.origin);
    const allowed = /^\/(?:s\/[a-z0-9-]+\/(?:admin\/bookings|b\/[^/]+\/appointments)|admin\/bookings|[^/]+\/appointments)(?:$|\?)/;
    const scope = new URL(self.registration.scope).pathname;
    if (target.origin === self.location.origin && allowed.test(target.pathname + target.search) && (scope === "/" || target.pathname.startsWith(scope))) targetPath = target.pathname + target.search;
  } catch { /* Fall back to the branch chooser. */ }
  // Open another window so a notification never replaces an unfinished form.
  event.waitUntil(self.clients.openWindow ? self.clients.openWindow(targetPath) : Promise.resolve());
});
