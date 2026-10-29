import { APP_ICONS } from "@/lib/app-icons";
export const dynamic="force-dynamic";
export async function GET(_request:Request,{params}:{params:{spa_slug:string}}):Promise<Response>{
  const response=await fetch((process.env.BACKEND_INTERNAL_URL||"http://localhost:8001")+"/api/v1/spas/public/"+encodeURIComponent(params.spa_slug),{cache:"no-store",signal:AbortSignal.timeout(5000)});
  if(!response.ok)return new Response("Không tìm thấy spa",{status:404});
  const spa=await response.json() as {id:string;name:string;slug:string;theme_color:string;logo_url:string|null};
  const prefix=`/s/${spa.slug}/`;
  return Response.json({id:`/pwa/spa/${spa.id}`,name:spa.name,short_name:spa.name.slice(0,24),start_url:prefix+"?launch=1",scope:prefix,display:"standalone",background_color:"#ffffff",theme_color:spa.theme_color,
    icons:spa.logo_url?[{src:spa.logo_url,sizes:"any",purpose:"any"}]:APP_ICONS},{headers:{"Content-Type":"application/manifest+json","Cache-Control":"no-store"}});
}
