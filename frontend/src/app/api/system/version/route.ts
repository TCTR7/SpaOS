import { BUILD_INFO } from "@/lib/build-info";
export const dynamic = "force-dynamic";
export async function GET(): Promise<Response> {
  return Response.json(BUILD_INFO, {headers:{"Cache-Control":"no-store, max-age=0"}});
}
