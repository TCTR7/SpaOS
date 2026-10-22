"use client";
import * as React from "react";
export function NetworkStatus(): React.ReactElement | null {
  const [offline, setOffline] = React.useState(false);
  React.useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update(); window.addEventListener("online", update); window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  return offline ? <p role="status" className="rounded-lg border bg-amber-50 p-3 text-sm text-amber-950">Bạn đang mất kết nối. Thông tin có thể chưa mới. Kết nối lại rồi kiểm tra kết quả trước khi gửi lại thao tác.</p> : null;
}
