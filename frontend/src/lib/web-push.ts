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
import { spaSlug } from "./spa-path";

type Active = () => boolean;
function sessionGuard(slug: string | undefined, active: Active): () => void {
  const identity = slug === undefined ? getAdminSessionIdentity() : getCustomerSessionIdentity(slug);
  return () => {
    const token = slug === undefined ? getStoredToken() : getCustomerToken(slug);
    const current = slug === undefined ? getAdminSessionIdentity() : getCustomerSessionIdentity(slug);
    if (!active() || !token || current !== identity) throw new Error("Tài khoản đã thay đổi. Vui lòng bật lại thông báo.");
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
    const slug = spaSlug(window.location.pathname);
    const scope = slug ? `/s/${slug}/` : "/";
    const registration = await navigator.serviceWorker.register(scope+"sw.js", {
      scope,
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
    throw new Error("Trình duyệt này chưa hỗ trợ thông báo. Hãy thử trình duyệt khác.");
  }
  const vapid = await fetchVapidPublicKey();
  check();
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Spa chưa bật dịch vụ thông báo thiết bị. Liên hệ người quản trị cấu hình Web Push; thông báo trong ứng dụng vẫn dùng được.");
  }
  const permission = await Notification.requestPermission();
  check();
  if (permission !== "granted") {
    throw new Error("Hãy cho phép nhận thông báo trong cài đặt trình duyệt rồi thử lại.");
  }
  const reg = await registerSpaServiceWorker();
  check();
  if (!reg) {
    throw new Error("Chưa thể bật thông báo trên thiết bị này. Vui lòng thử lại.");
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
    throw new Error("Chưa thể bật thông báo trên thiết bị này. Vui lòng thử lại.");
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
    throw new Error("Thiết bị này chưa hỗ trợ thông báo. Hãy thử trình duyệt khác.");
  }
  const vapid = await fetchCustomerVapidKey(slug);
  check();
  if (!vapid.enabled || !vapid.public_key) {
    throw new Error("Spa chưa bật dịch vụ thông báo thiết bị. Liên hệ người quản trị cấu hình Web Push; thông báo trong ứng dụng vẫn dùng được.");
  }
  const permission = await Notification.requestPermission();
  check();
  if (permission !== "granted") {
    throw new Error("Hãy cho phép nhận thông báo trong cài đặt trình duyệt rồi thử lại.");
  }
  const reg = await registerSpaServiceWorker();
  check();
  if (!reg) {
    throw new Error("Chưa thể bật thông báo trên thiết bị này. Vui lòng thử lại.");
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
    throw new Error("Chưa thể bật thông báo trên thiết bị này. Vui lòng thử lại.");
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
