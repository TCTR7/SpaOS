import manifest from "@/lib/public-manifest";
// Serve a normal route instead of root file-based metadata: the latter takes
// precedence over each branch's asynchronous generateMetadata manifest.
export const dynamic="force-dynamic";
export async function GET():Promise<Response>{
  return Response.json(await manifest(),{headers:{"Content-Type":"application/manifest+json","Cache-Control":"no-store"}});
}
