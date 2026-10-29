import { NextRequest, NextResponse } from "next/server";
export function middleware(request: NextRequest): NextResponse {
  const headers = new Headers(request.headers);
  headers.delete("x-spa-slug");
  const match = /^\/s\/([a-z0-9-]+)(\/.*)?$/.exec(request.nextUrl.pathname);
  if (!match) return NextResponse.next({request: {headers}});
  headers.set("x-spa-slug", match[1]);
  const path = match[2] || "/";
  // Per-spa manifest and worker remain physical routes.
  if (/^\/(?:manifest\.webmanifest|sw\.js)$/.test(path)) return NextResponse.next({request: {headers}});
  if (path !== "/" && !/^\/admin(?:\/|$)/.test(path) && !path.startsWith("/b/")) {
    return new NextResponse("Không tìm thấy trang", {status:404});
  }
  // Relative routing is configured in next.config. Keep this request's verified
  // brand header through routing without an origin-dependent proxy round trip.
  return NextResponse.next({request:{headers}});
}
export const config = {matcher: ["/((?!api|_next|icons|screenshots|favicon).*)"]};
