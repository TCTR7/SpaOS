"use client";
import { useMemo } from "react";
import { usePathname as useNextPathname, useRouter as useNextRouter } from "next/navigation";
import { spaPath, spaSlug, unscopedPath } from "./spa-path";
export { useParams, useSearchParams, notFound, redirect } from "next/navigation";

export function usePathname(): string { return unscopedPath(useNextPathname()); }
export function useRouter(): ReturnType<typeof useNextRouter> {
  const router = useNextRouter();
  const slug = spaSlug(useNextPathname());
  return useMemo(() => ({...router,
    push: (href, options) => router.push(spaPath(href, slug), options),
    replace: (href, options) => router.replace(spaPath(href, slug), options),
    prefetch: (href, options) => router.prefetch(spaPath(href, slug), options),
  }), [router, slug]);
}
