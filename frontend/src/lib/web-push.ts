import {
  getAdminSessionIdentity,
  getStoredToken,
  fetchVapidPublicKey,
  subscribeWebPush,
  unsubscribeWebPush,
} from "./api";
import {
  getCustomerSessionIdentity,
  getCustomerToken,
  fetchCustomerVapidKey,
  subscribeCustomerWebPush,
  unsubscribeCustomerWebPush,
} from "./customer-api";
import { urlBase64ToUint8Array } from "./utils";

type Active = () => boolean;
function sessionGuard(slug: string | undefined, active: Active): () => void {
  const identity = slug === undefined ? getAdminSessionIdentity() : getCustomerSessionIdentity(slug);
  return () => {
    const token = slug === undefined ? getStoredToken() : getCustomerToken(slug);
    const current = slug === undefined ? getAdminSessionIdentity() : getCustomerSessionIdentity(slug);
    if (!active() || !token || current !== identity) throw new Error("Phiên đã thay đổi. Hãy bật thông báo lại từ tài khoản hiện tại.");
  };
}

/** Reattach an existing browser subscription only to the session that started this operation. */
export async function syncExistingWebPush(slug?: string, active: Active = () => true): Promise<boolean> {
  const check = sessionGuard(slug, active);
  check();
  const sub = await getActivePushSubscription();
  check();
  if (!sub) return false;
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return false;
  const payload = { endpoint: json.endpoint, keys: { p256dh: json.keys.p256dh, auth: json.keys.auth } };
  if (slug === undefined) await subscribeWebPush(payload);
  else await subscribeCustomerWebPush(slug, payload);
  check();
  return true;
}

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

export async function enableAdminWebPush(active: Active = () => true): Promise<void> {
  const check = sessionGuard(undefined, active);
  check();
  if (!isWebPushSupported()) {
    throw new Error("Trình duyệt không hỗ trợ Web Push Notification.");
  }
  const vapid = await fetchVapidPublicKey();
  check();
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Server chưa cấu hình VAPID_PUBLIC_KEY.");
  }
  const permission = await Notification.requestPermission();
  check();
  if (permission !== "granted") {
    throw new Error("Trình duyệt đã từ chối quyền thông báo.");
  }
  const reg = await registerSpaServiceWorker();
  check();
  if (!reg) {
    throw new Error("Không thể đăng ký Service Worker (/sw.js).");
  }
  await navigator.serviceWorker.ready;
  check();
  const appServerKey = urlBase64ToUint8Array(vapid.public_key);
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: appServerKey.buffer as ArrayBuffer,
  });
  check();
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Không đọc được khóa mã hóa Push Subscription.");
  }
  await subscribeWebPush({
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  });
  check();
}

export async function disableAdminWebPush(active: Active = () => true): Promise<void> {
  const check = sessionGuard(undefined, active);
  check();
  const sub = await getActivePushSubscription();
  check();
  if (sub) {
    await unsubscribeWebPush(sub.endpoint);
    check();
    await sub.unsubscribe();
    check();
  }
}

export async function enableCustomerWebPush(slug: string, active: Active = () => true): Promise<void> {
  const check = sessionGuard(slug, active);
  check();
  if (!isWebPushSupported()) {
    throw new Error("Thiết bị không hỗ trợ Web Push Notification.");
  }
  const vapid = await fetchCustomerVapidKey(slug);
  check();
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Spa chưa cấu hình khóa VAPID.");
  }
  const permission = await Notification.requestPermission();
  check();
  if (permission !== "granted") {
    throw new Error("Bạn đã từ chối quyền nhận thông báo trên trình duyệt.");
  }
  const reg = await registerSpaServiceWorker();
  check();
  if (!reg) {
    throw new Error("Không thể đăng ký Service Worker (/sw.js).");
  }
  await navigator.serviceWorker.ready;
  check();
  const keyBytes = urlBase64ToUint8Array(vapid.public_key);
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: keyBytes.buffer as ArrayBuffer,
  });
  check();
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Không lấy được khóa đăng ký thiết bị.");
  }
  await subscribeCustomerWebPush(slug, {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  });
  check();
}

export async function disableCustomerWebPush(slug: string, active: Active = () => true): Promise<void> {
  const check = sessionGuard(slug, active);
  check();
  const sub = await getActivePushSubscription();
  check();
  if (sub) {
    await unsubscribeCustomerWebPush(slug, sub.endpoint);
    check();
    await sub.unsubscribe();
    check();
  }
}
