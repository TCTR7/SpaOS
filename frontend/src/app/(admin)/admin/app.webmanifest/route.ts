export const dynamic="force-dynamic";
export async function GET():Promise<Response>{
  return Response.json({id:"/admin/",name:"Quản lý Spa",short_name:"Quản lý Spa",start_url:"/admin",scope:"/admin",display:"standalone",background_color:"#ffffff",theme_color:"#213c35",icons:[{src:"/icons/icon-192x192.png",sizes:"192x192",type:"image/png"},{src:"/icons/icon-512x512.png",sizes:"512x512",type:"image/png"}]},{headers:{"Content-Type":"application/manifest+json","Cache-Control":"no-store"}});
}
