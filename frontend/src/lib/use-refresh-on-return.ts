"use client";
import * as React from "react";
/** Read refresh only. Never replays a write or runs while a form is being saved. */
export function useRefreshOnReturn(refresh: () => void, enabled = true): void {
  const callback = React.useRef(refresh); callback.current = refresh;
  React.useEffect(() => {
    const update = () => { if (enabled && document.visibilityState === "visible" && navigator.onLine) callback.current(); };
    window.addEventListener("focus", update); window.addEventListener("online", update); document.addEventListener("visibilitychange", update);
    return () => { window.removeEventListener("focus", update); window.removeEventListener("online", update); document.removeEventListener("visibilitychange", update); };
  }, [enabled]);
}
