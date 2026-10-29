"use client";
import * as React from "react";
import { usePathname, useRouter } from "@/lib/spa-navigation";
import { screenGuides, type GuideRole } from "@/lib/screen-guides";
import { assertAdminNavigationSafe } from "@/lib/branch-guard";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export function ScreenHelp({role,identity,slug="",library=false}:{role:GuideRole;identity:string;slug?:string;library?:boolean}):React.ReactElement|null {
  const pathname=usePathname(),router=useRouter();
  const guides=screenGuides(role,slug);
  const current=guides.find(g=>g.path===pathname)||(pathname?.startsWith("/admin/staff/")?guides.find(g=>g.path==="/admin/staff"):undefined);
  const storage="spaos_tour_"+role+"_"+identity;
  const [open,setOpen]=React.useState(false),[error,setError]=React.useState("");
  React.useEffect(()=>{
    // The shell owns the tour dialog. The help-page library only lists guides
    // and starts a new tour, so it must not subscribe or open another dialog.
    if(library)return;
    if(current&&localStorage.getItem(storage)==="active"&&!localStorage.getItem(storage+":"+current.path))setOpen(true);
    const start=():void=>{localStorage.setItem(storage,"active");setOpen(!!current);};
    window.addEventListener("spaos:start-tour",start);return()=>window.removeEventListener("spaos:start-tour",start);
  },[storage,current?.path,library]);
  const start=():void=>{for(const g of guides)localStorage.removeItem(storage+":"+g.path);localStorage.setItem(storage,"active");if(guides[0].path===pathname)setOpen(true);else router.push(guides[0].path);};
  const skip=():void=>{localStorage.removeItem(storage);setOpen(false);};
  const list=(steps:string[]):React.ReactElement=><ol className="list-decimal space-y-3 pl-5 text-sm leading-6">{steps.map(s=><li key={s}>{s}</li>)}</ol>;
  return <>
    {library?<section className="space-y-4"><Button onClick={start}>Bắt đầu lại hướng dẫn qua các màn hình</Button>{guides.map(g=><details className="rounded-xl border p-4" key={g.path}><summary className="cursor-pointer font-semibold">{g.title}</summary><div className="pt-3">{list(g.steps)}</div></details>)}</section>:current&&<section className="mb-4"><Button variant="outline" className="text-sm" onClick={()=>setOpen(true)}>Hướng dẫn màn hình: {current.title}</Button></section>}
    <Modal open={!library&&open&&!!current} onClose={skip} title={"Hướng dẫn: "+(current?.title||"")}>
      {current&&<div className="space-y-4">{list(current.steps)}{error&&<p role="alert">{error}</p>}<p className="text-xs">Có thể bỏ qua và xem lại trong Trợ giúp &amp; Cài ứng dụng.</p><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={skip}>Bỏ qua hướng dẫn</Button><Button onClick={()=>{
        try{if(role!=="CUSTOMER")assertAdminNavigationSafe();setError("");}catch(e){setError(e instanceof Error?e.message:"Hãy hoàn tất form trước.");return;}
        localStorage.setItem(storage+":"+current.path,"seen");const index=guides.indexOf(current);setOpen(false);
        if(index+1<guides.length){localStorage.setItem(storage,"active");router.push(guides[index+1].path);}else skip();
      }}>{guides.indexOf(current)+1<guides.length?"Đến màn hình tiếp theo":"Hoàn tất"}</Button></div></div>}
    </Modal>
  </>;
}
