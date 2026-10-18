import { DEFAULT_BRAND, validBrandColor } from "./brand-theme";
export async function getServerBranding(): Promise<{theme_color:string;configured:boolean}> {
  try {
    const response = await fetch((process.env.BACKEND_INTERNAL_URL || "http://localhost:8001")+"/api/v1/branding",
      {cache:"no-store",signal:AbortSignal.timeout(3000)});
    if (response.ok) {
      const value = await response.json() as {theme_color:string;configured:boolean};
      return {theme_color:validBrandColor(value.theme_color),configured:value.configured === true};
    }
  } catch { /* Render the default palette when the API is unavailable. */ }
  return {theme_color:DEFAULT_BRAND,configured:false};
}
