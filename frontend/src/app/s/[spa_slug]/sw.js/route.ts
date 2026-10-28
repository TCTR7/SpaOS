import { readFile } from "node:fs/promises";
import { join } from "node:path";
export const dynamic="force-dynamic";
export async function GET(_request:Request,{params}:{params:{spa_slug:string}}):Promise<Response>{
  if(!/^[a-z0-9-]+$/.test(params.spa_slug))return new Response(null,{status:404});
  const script=await readFile(join(process.cwd(),"public","sw.js"),"utf8");
  return new Response(script,{headers:{"Content-Type":"application/javascript","Cache-Control":"no-cache","Service-Worker-Allowed":`/s/${params.spa_slug}/`}});
}
