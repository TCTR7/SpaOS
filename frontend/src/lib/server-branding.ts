import { DEFAULT_BRAND, validBrandColor } from "./brand-theme";
import { headers } from "next/headers";
export async function getServerBranding(): Promise<{theme_color:string;configured:boolean;name?:string;logo_url?:string|null}> {
  try {
    const slug = headers().get("x-spa-slug");
    const response = await fetch((process.env.BACKEND_INTERNAL_URL || "http://localhost:8001")+(slug ? "/api/v1/spas/public/"+encodeURIComponent(slug) : "/api/v1/branding"),
      {cache:"no-store",signal:AbortSignal.timeout(3000)});
    if (response.ok) {
      const value = await response.json() as {theme_color:string;configured:boolean;name?:string;logo_url?:string|null};
      return {theme_color:validBrandColor(value.theme_color),configured:!!slug || value.configured === true,...(slug?{name:value.name,logo_url:value.logo_url}:{})};
    }
  } catch { /* Render the default palette when the API is unavailable. */ }
  return {theme_color:DEFAULT_BRAND,configured:false};
}
