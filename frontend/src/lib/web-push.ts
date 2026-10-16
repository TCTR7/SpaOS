import {
  fetchVapidPublicKey,
  subscribeWebPush,
  unsubscribeWebPush,
} from "./api";
import {
  fetchCustomerVapidKey,
  subscribeCustomerWebPush,
  unsubscribeCustomerWebPush,
} from "./customer-api";
import { urlBase64ToUint8Array } from "./utils";

export function isWebPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function registerSpaServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return null;
  }
  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });
    return registration;
  } catch {
    return null;
  }
}

export async function getActivePushSubscription(): Promise<PushSubscription | null> {
  if (!isWebPushSupported()) return null;
  try {
    const reg = await registerSpaServiceWorker();
    if (!reg) return null;
    return await reg.pushManager.getSubscription();
  } catch {
    return null;
  }
}

export async function enableAdminWebPush(): Promise<void> {
  if (!isWebPushSupported()) {
    throw new Error("Trình duyệt không hỗ trợ Web Push Notification.");
  }
  const vapid = await fetchVapidPublicKey();
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Server chưa cấu hình VAPID_PUBLIC_KEY.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Trình duyệt đã từ chối quyền thông báo.");
  }
  const reg = await registerSpaServiceWorker();
  if (!reg) {
    throw new Error("Không thể đăng ký Service Worker (/sw.js).");
  }
  await navigator.serviceWorker.ready;
  const appServerKey = urlBase64ToUint8Array(vapid.public_key);
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: appServerKey.buffer as ArrayBuffer,
  });
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Không đọc được khóa mã hóa Push Subscription.");
  }
  await subscribeWebPush({
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    user_agent: navigator.userAgent,
  });
}

export async function disableAdminWebPush(): Promise<void> {
  const sub = await getActivePushSubscription();
  if (sub) {
    await unsubscribeWebPush(sub.endpoint).catch(() => {});
    await sub.unsubscribe();
  }
}

export async function enableCustomerWebPush(slug: string): Promise<void> {
  if (!isWebPushSupported()) {
    throw new Error("Thiết bị không hỗ trợ Web Push Notification.");
  }
  const vapid = await fetchCustomerVapidKey(slug);
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Spa chưa cấu hình khóa VAPID.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Bạn đã từ chối quyền nhận thông báo trên trình duyệt.");
  }
  const reg = await registerSpaServiceWorker();
  if (!reg) {
    throw new Error("Không thể đăng ký Service Worker (/sw.js).");
  }
  await navigator.serviceWorker.ready;
  const keyBytes = urlBase64ToUint8Array(vapid.public_key);
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: keyBytes.buffer as ArrayBuffer,
  });
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Không lấy được khóa đăng ký thiết bị.");
  }
  await subscribeCustomerWebPush(slug, {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    user_agent: navigator.userAgent,
  });
}

export async function disableCustomerWebPush(slug: string): Promise<void> {
  const sub = await getActivePushSubscription();
  if (sub) {
    await unsubscribeCustomerWebPush(slug, sub.endpoint).catch(() => {});
    await sub.unsubscribe();
  }
}
