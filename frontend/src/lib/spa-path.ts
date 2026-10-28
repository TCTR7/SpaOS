export function spaSlug(path: string): string | null {
  return /^\/s\/([a-z0-9-]+)(?:\/|$)/.exec(path)?.[1] || null;
}

export function unscopedPath(path: string): string {
  return path.replace(/^\/s\/[a-z0-9-]+(?:\/b)?(?=\/|$)/, "") || "/";
}

export function spaPath(path: string, slug?: string | null): string {
  const brand = slug === undefined && typeof window !== "undefined" ? spaSlug(window.location.pathname) : slug;
  if (!brand || !path.startsWith("/") || path.startsWith("//") || /^\/(?:s|api|operator)(?:\/|$)/.test(path)) return path;
  const prefix = `/s/${encodeURIComponent(brand)}`;
  if (path === "/") return prefix + "/";
  return prefix + (/^\/admin(?:\/|$|\?)/.test(path) ? "" : "/b") + path;
}

export function adminStorageKey(key: string): string {
  const slug = typeof window === "undefined" ? null : spaSlug(window.location.pathname);
  return slug ? `${key}:${slug}` : key;
}
