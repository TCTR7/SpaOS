"use client";
import * as React from "react";
import { API_BASE_URL } from "@/lib/api";
import { brandStyle, DEFAULT_BRAND, validBrandColor } from "@/lib/brand-theme";
export interface Branding { theme_color: string; configured: boolean }
const Context = React.createContext<{branding: Branding; refresh: () => Promise<void>}>({
  branding: {theme_color: DEFAULT_BRAND, configured: false}, refresh: async () => {},
});
export function BrandProvider({children,initialBranding}: {children: React.ReactNode;initialBranding?:Branding}): React.ReactElement {
  const [branding, setBranding] = React.useState<Branding>(initialBranding || {theme_color: DEFAULT_BRAND, configured: false});
  const sequence = React.useRef(0);
  const refresh = React.useCallback(async (): Promise<void> => {
    const current = ++sequence.current;
    try {
      const response = await fetch(API_BASE_URL+"/branding", {cache:"no-store"});
      if (!response.ok) return;
      const data = await response.json() as Branding;
      if (current === sequence.current) setBranding({theme_color: validBrandColor(data.theme_color), configured: data.configured === true});
    } catch { /* Keep the last known theme when offline. */ }
  }, []);
  React.useEffect(() => {
    void refresh();
    const focus = (): void => { if (!document.hidden) void refresh(); };
    const storage = (event: StorageEvent): void => { if (event.key === "spaos_branding_changed") void refresh(); };
    window.addEventListener("focus", focus); document.addEventListener("visibilitychange", focus);
    window.addEventListener("storage", storage); window.addEventListener("spaos-branding-updated", focus);
    return () => { ++sequence.current; window.removeEventListener("focus",focus); document.removeEventListener("visibilitychange",focus); window.removeEventListener("storage",storage); window.removeEventListener("spaos-branding-updated",focus); };
  }, [refresh]);
  React.useEffect(() => {
    const style = brandStyle(branding.theme_color);
    for (const [name,value] of Object.entries(style)) document.documentElement.style.setProperty(name,String(value));
    document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => meta.setAttribute("content",branding.theme_color));
  }, [branding]);
  return <Context.Provider value={{branding,refresh}}>{children}</Context.Provider>;
}
export function useBranding(): React.ContextType<typeof Context> { return React.useContext(Context); }
export function useBrandColor(fallback?: string | null): string {
  const {branding} = useBranding();
  return branding.configured ? branding.theme_color : validBrandColor(fallback);
}
export function announceBranding(): void {
  window.dispatchEvent(new Event("spaos-branding-updated"));
  window.localStorage.setItem("spaos_branding_changed",String(Date.now()));
}
