export const dynamic="force-dynamic";
export async function GET(_request:Request,{params}:{params:{tenant_slug:string}}):Promise<Response>{
  const slug=encodeURIComponent(params.tenant_slug.trim().toLowerCase());
  const base=process.env.BACKEND_INTERNAL_URL||"http://localhost:8001";
  const response=await fetch(base+"/api/v1/public/tenants/"+slug,{cache:"no-store"});
  if(!response.ok)return new Response("Not found",{status:404});
  const tenant=await response.json() as {name:string;theme_color:string|null};
  return Response.json({id:"/"+slug+"/",name:tenant.name+" — Đặt lịch",short_name:tenant.name,start_url:"/"+slug,scope:"/"+slug,display:"standalone",background_color:"#ffffff",theme_color:tenant.theme_color||"#213c35",icons:[{src:"/icons/icon-192x192.png",sizes:"192x192",type:"image/png"},{src:"/icons/icon-512x512.png",sizes:"512x512",type:"image/png"}]},{headers:{"Content-Type":"application/manifest+json","Cache-Control":"no-store"}});
}
