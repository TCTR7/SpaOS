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
    icon: "/icons/icon-192x192.png",
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
      targetUrl = "/spa-demo/appointments";
    }
  }

  const options = {
    body: payload.body,
    icon: payload.icon || "/icons/icon-192x192.png",
    badge: "/icons/icon-192x192.png",
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
  const targetPath = data.url || "/admin/bookings";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            if ("navigate" in client && data.url) {
              client.navigate(targetPath).catch(() => {});
            }
            return client.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetPath);
        }
        return undefined;
      })
  );
});
