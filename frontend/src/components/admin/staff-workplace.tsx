"use client";
import * as React from "react";
import Link from "@/components/spa-link";
import { apiRequest } from "@/lib/api";
import { formatDateISOInVN } from "@/lib/utils";
import type { Workforce } from "./workforce-editor";

export function StaffWorkplace({staffId, branchId}: {staffId:string;branchId:string}):React.ReactElement {
  const [view,setView]=React.useState<{data:Workforce;day:string}|null>(null);
  const [error,setError]=React.useState(false);
  React.useEffect(()=>{
    let alive=true,pending=false;
    const load=async ():Promise<void>=>{
      if(pending||document.visibilityState!=="visible")return;
      pending=true;
      try {
        const data=await apiRequest<Workforce>(`/workforce/staff/${staffId}`);
        if(alive){setView({data,day:formatDateISOInVN()});setError(false);}
      } catch {if(alive)setError(true);}
      finally{pending=false;}
    };
    void load();
    const refresh=():void=>{void load();};
    const timer=window.setInterval(refresh,30000);
    window.addEventListener("focus",refresh);document.addEventListener("visibilitychange",refresh);
    return()=>{alive=false;window.clearInterval(timer);window.removeEventListener("focus",refresh);document.removeEventListener("visibilitychange",refresh);};
  },[staffId,branchId]);
  if(error)return <p className="mb-3 text-sm">Chưa kiểm tra được ca hôm nay. <Link className="underline" href="/admin/work-hours">Xem ca làm</Link></p>;
  if(!view)return <></>;
  const weekday=new Date(view.day+"T12:00:00+07:00").getUTCDay();
  const {data,day}=view;
  const row=data.assignments.find(r=>r.day===day)||data.assignments.filter(r=>r.day===null&&r.weekday===weekday&&r.effective_from<=day).sort((a,b)=>b.effective_from.localeCompare(a.effective_from))[0];
  const branch=data.branches.find(b=>b.id===row?.tenant_id);
  return <p data-testid="today-workplace" className="mb-3 rounded-lg border p-3 text-sm">
    {branch&&row?<>Ca hôm nay ({day}): <strong>{branch.name}</strong> · {row.start_time?.slice(0,5)}–{row.end_time?.slice(0,5)}.{branch.id!==branchId&&" Bạn đang xem một chi nhánh khác."}</>:<>Bạn nghỉ hoặc chưa được phân công hôm nay ({day}).</>}
    {" "}<Link className="underline" href="/admin/work-hours">Xem ca làm</Link>
  </p>;
}
