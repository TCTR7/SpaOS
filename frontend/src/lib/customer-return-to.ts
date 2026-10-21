"use client";
import * as React from "react";

/** Only known customer screens in this branch can be authentication destinations. */
export function safeCustomerReturnTo(slug: string, raw: string | null): string {
  const base = "/" + encodeURIComponent(slug);
  const fallback = base + "/book";
  if (!raw || /[\\\s]/.test(raw)) return fallback;
  try {
    const url = new URL(raw, "https://spaos.invalid");
    if (!raw.startsWith("/") || raw.startsWith("//") || url.origin !== "https://spaos.invalid") return fallback;
    if (![base, base + "/book", base + "/appointments", base + "/profile"].includes(url.pathname)) return fallback;
    return url.pathname + url.search + url.hash;
  } catch { return fallback; }
}
export function useCustomerReturnTo(slug: string): string {
  const [destination, setDestination] = React.useState("/" + encodeURIComponent(slug) + "/book");
  React.useEffect(() => {
    setDestination(safeCustomerReturnTo(slug, new URLSearchParams(window.location.search).get("returnTo")));
  }, [slug]);
  return destination;
}
export function customerAuthHref(slug: string, page: "login" | "register", destination: string): string {
  return "/" + encodeURIComponent(slug) + "/" + page + "?" + new URLSearchParams({ returnTo: safeCustomerReturnTo(slug, destination) });
}
