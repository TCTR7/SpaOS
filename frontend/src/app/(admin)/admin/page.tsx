import { redirect } from "next/navigation";
import { headers } from "next/headers";

export default function AdminRootPage(): never {
  const slug = headers().get("x-spa-slug");
  redirect(slug ? `/s/${slug}/admin/dashboard` : "/admin/dashboard");
}
