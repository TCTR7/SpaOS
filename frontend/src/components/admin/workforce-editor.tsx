"use client";
import * as React from "react";
import { apiRequest } from "@/lib/api";
import { useAdminAuth } from "./auth-context";
import { useBranchGuard } from "@/lib/branch-guard";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { DAY_OF_WEEK_LABELS } from "@/lib/utils";

interface Assignment {tenant_id:string|null; weekday:number|null; day:string|null; effective_from:string; start_time:string|null; end_time:string|null}
export interface Workforce {account_id:string;default_branch_id?:string|null;branches:{id:string;name:string;staff_id:string}[];assignments:Assignment[]}
const today = ():string => new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
const order = [1,2,3,4,5,6,0];

export function WorkforceEditor({staffId, readOnly=false,onDirtyChange,onBusyChange}: {staffId:string;readOnly?:boolean;onDirtyChange?:(value:boolean)=>void;onBusyChange?:(value:boolean)=>void}):React.ReactElement {
  const {branches} = useAdminAuth();
  const [data,setData]=React.useState<Workforce|null>(null),[error,setError]=React.useState(""),[message,setMessage]=React.useState("");
  const [attempt,setAttempt]=React.useState(0),[busy,setBusy]=React.useState(false),[dirty,setDirty]=React.useState(false);
  const [from,setFrom]=React.useState(today),[days,setDays]=React.useState<Assignment[]>([]);
  const [selected,setSelected]=React.useState<string[]>([]),[defaultBranch,setDefaultBranch]=React.useState("");
  const [exception,setException]=React.useState(today),[exceptionBranch,setExceptionBranch]=React.useState(""),[start,setStart]=React.useState("09:00"),[end,setEnd]=React.useState("17:00");
  const flight=React.useRef(false);
  useBranchGuard(dirty,busy);
  React.useEffect(()=>{onDirtyChange?.(dirty);return()=>onDirtyChange?.(false);},[dirty,onDirtyChange]);
  React.useEffect(()=>{onBusyChange?.(busy);return()=>onBusyChange?.(false);},[busy,onBusyChange]);
  React.useEffect(()=>{let alive=true;setData(null);setError("");
    void apiRequest<Workforce>(`/workforce/staff/${staffId}`).then(v=>{if(!alive)return;setData(v);setSelected(v.branches.map(b=>b.id));setDefaultBranch(v.default_branch_id||v.branches[0]?.id||"");setDirty(false);}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Chưa tải được phân công");});
    return ()=>{alive=false;};
  },[staffId,attempt]);
  React.useEffect(()=>{if(!data)return;setDays(order.map(weekday=>{
    const row=data.assignments.filter(r=>r.day===null&&r.weekday===weekday&&r.effective_from<=from).sort((a,b)=>b.effective_from.localeCompare(a.effective_from))[0];
    return row?{...row}:{tenant_id:null,weekday,day:null,effective_from:from,start_time:null,end_time:null};
  }));},[data,from]);
  function changeDay(index:number, patch:Partial<Assignment>):void {setDirty(true);setDays(v=>v.map((r,i)=>i===index?{...r,...patch}:r));}
  async function save(kind:"week"|"day"|"access"|"remove-day"):Promise<void>{
    if(flight.current)return;
    if(kind==="remove-day"&&!window.confirm("Bỏ ngoại lệ ngày "+exception+" và áp dụng lại ca tuần?"))return;
    if(kind==="access"&&data?.branches.some(b=>!selected.includes(b.id))&&!window.confirm("Thu hồi quyền chi nhánh đã bỏ chọn? Chỉ hoàn tất khi lịch và khách đã bàn giao."))return;
    flight.current=true;setBusy(true);setError("");setMessage("");
    try{
      const body=kind==="week"?{effective_from:from,days:days.map(r=>({weekday:r.weekday,tenant_id:r.tenant_id,start_time:r.start_time,end_time:r.end_time}))}:
        kind==="day"?{day:exception,tenant_id:exceptionBranch||null,start_time:exceptionBranch?start:null,end_time:exceptionBranch?end:null}:
        {branch_ids:selected,default_branch_id:defaultBranch};
      if(kind==="remove-day")await apiRequest(`/workforce/staff/${staffId}/day/${exception}`,{method:"DELETE"});
      else await apiRequest(`/workforce/staff/${staffId}/${kind}`,{method:"PUT",body});
      setDirty(false);setMessage("Đã lưu. Lịch hẹn và dữ liệu lịch sử được giữ nguyên.");setAttempt(v=>v+1);
    }catch(e){setError(e instanceof Error?e.message:"Chưa lưu được thay đổi");}
    finally{flight.current=false;setBusy(false);}
  }
  if(!data)return <div className="p-4">{error?<><p role="alert">{error}</p><Button onClick={()=>setAttempt(v=>v+1)}>Thử lại phân công</Button></>:<p role="status">Đang tải phân công...</p>}</div>;
  const names=new Map(data.branches.map(b=>[b.id,b.name]));
  return <section aria-label="Phân công chi nhánh theo ngày" className="space-y-4 p-4">
    <h2 className="text-lg font-bold">Phân công chi nhánh theo ngày</h2>
    <p className="text-sm">Mỗi ngày làm tại một chi nhánh. Ngoại lệ theo ngày được ưu tiên hơn lịch tuần.</p>
    {error&&<p role="alert" className="feedback-error">{error}</p>}{message&&<p role="status" className="feedback-success">{message}</p>}
    <div><Label htmlFor={`effective-${staffId}`}>Lịch tuần từ ngày</Label><Input id={`effective-${staffId}`} disabled={busy} type="date" min={readOnly?undefined:today()} value={from} onChange={e=>{if(dirty&&!window.confirm("Đổi ngày xem lịch sẽ bỏ các thay đổi chưa lưu. Tiếp tục?"))return;setDirty(false);setFrom(e.target.value);}}/></div>
    <fieldset disabled={busy||readOnly} className="space-y-4">
      <div className="space-y-3">{days.map((row,index)=><div key={row.weekday} className="flex flex-wrap items-center gap-3 rounded-xl border p-3">
        <strong className="w-24 text-sm">{DAY_OF_WEEK_LABELS[row.weekday||0]}</strong>
        <select aria-label={`Chi nhánh ${DAY_OF_WEEK_LABELS[row.weekday||0]}`} className="min-h-11 max-w-full rounded-lg border bg-background px-3" value={row.tenant_id||""} onChange={e=>changeDay(index,{tenant_id:e.target.value||null,start_time:e.target.value?row.start_time||"09:00":null,end_time:e.target.value?row.end_time||"17:00":null})}>
          <option value="">Nghỉ / chưa phân công</option>{data.branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        {row.tenant_id&&<><Input aria-label={`Giờ bắt đầu ${DAY_OF_WEEK_LABELS[row.weekday||0]}`} type="time" className="w-32" value={row.start_time?.slice(0,5)||""} onChange={e=>changeDay(index,{start_time:e.target.value})}/><Input aria-label={`Giờ kết thúc ${DAY_OF_WEEK_LABELS[row.weekday||0]}`} type="time" className="w-32" value={row.end_time?.slice(0,5)||""} onChange={e=>changeDay(index,{end_time:e.target.value})}/></>}
      </div>)}</div>
      {!readOnly&&<div className="flex flex-wrap gap-2"><Button variant="outline" disabled={!days[0]?.tenant_id} onClick={()=>{const monday=days[0];setDays(v=>v.map(r=>r.tenant_id?{...r,start_time:monday.start_time,end_time:monday.end_time}:r));setDirty(true);}}>Áp dụng giờ Thứ 2 cho các ngày</Button><Button onClick={()=>void save("week")}>Lưu phân công tuần</Button></div>}
      {!readOnly&&<details className="disclosure"><summary>Sửa riêng một ngày</summary><div className="space-y-3 pt-3">
        <Input aria-label="Ngày ngoại lệ" type="date" min={today()} value={exception} onChange={e=>{setException(e.target.value);setDirty(true);}}/>
        <select aria-label="Chi nhánh ngày ngoại lệ" value={exceptionBranch} className="min-h-11 w-full rounded-lg border bg-background px-3" onChange={e=>{setExceptionBranch(e.target.value);setDirty(true);}}><option value="">Nghỉ</option>{data.branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select>
        {exceptionBranch&&<div className="flex gap-3"><Input aria-label="Giờ bắt đầu ngoại lệ" type="time" value={start} onChange={e=>{setStart(e.target.value);setDirty(true);}}/><Input aria-label="Giờ kết thúc ngoại lệ" type="time" value={end} onChange={e=>{setEnd(e.target.value);setDirty(true);}}/></div>}
        <div className="flex flex-wrap gap-2"><Button onClick={()=>void save("day")}>Lưu ngày ngoại lệ</Button><Button variant="outline" onClick={()=>void save("remove-day")}>Trở về ca tuần</Button></div>
      </div></details>}
      {!readOnly&&<details className="disclosure"><summary>Chi nhánh được cấp quyền / điều chuyển</summary><div className="space-y-3 pt-3">
        <p className="text-sm">Bỏ chọn chi nhánh chỉ hoàn tất sau khi bàn giao lịch hẹn và khách đang phụ trách.</p>
        {branches.filter(b=>b.is_owner).map(b=><label key={b.tenant.id} className="flex min-h-11 items-center gap-3"><input type="checkbox" checked={selected.includes(b.tenant.id)} onChange={e=>{setSelected(v=>e.target.checked?[...v,b.tenant.id]:v.filter(x=>x!==b.tenant.id));setDirty(true);}}/>{b.tenant.name}</label>)}
        <Label htmlFor="default-workplace">Chi nhánh mặc định khi không có ca</Label><select id="default-workplace" className="min-h-11 w-full rounded-lg border bg-background px-3" value={defaultBranch} onChange={e=>{setDefaultBranch(e.target.value);setDirty(true);}}>{branches.filter(b=>selected.includes(b.tenant.id)).map(b=><option key={b.tenant.id} value={b.tenant.id}>{b.tenant.name}</option>)}</select>
        <Button disabled={!selected.length||!selected.includes(defaultBranch)} onClick={()=>void save("access")}>Lưu quyền chi nhánh</Button>
      </div></details>}
    </fieldset>
    {data.assignments.some(r=>r.day!==null)&&<div className="space-y-2"><h3 className="font-semibold">Ngoại lệ đã lưu</h3>{data.assignments.filter(r=>r.day!==null&&r.day>=today()).map(r=><p className="text-sm" key={r.day}>{r.day} · {r.tenant_id?names.get(r.tenant_id)||"Chi nhánh đã ngưng quyền":"Nghỉ"} {r.start_time?.slice(0,5)} {r.end_time?"– "+r.end_time.slice(0,5):""}</p>)}</div>}
  </section>;
}
