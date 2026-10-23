import { APP_ICONS } from "@/lib/app-icons";
export const dynamic="force-dynamic";
export async function GET():Promise<Response>{
  return Response.json({id:"/admin/",name:"Quản lý Spa",short_name:"Quản lý Spa",start_url:"/admin",scope:"/admin",display:"standalone",background_color:"#ffffff",theme_color:"#213c35",icons:APP_ICONS},{headers:{"Content-Type":"application/manifest+json","Cache-Control":"no-store"}});
}
