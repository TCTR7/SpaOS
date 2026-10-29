import { adminStorageKey, spaSlug, unscopedPath } from "./spa-path";
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function currentAdminBookingTarget():string|null {
  if(typeof window==="undefined"||unscopedPath(window.location.pathname)!=="/admin/bookings")return null;
  const params=new URLSearchParams(window.location.search);
  const branch=params.get("target_branch"),booking=params.get("booking_id");
  return branch&&booking&&uuid.test(branch)&&uuid.test(booking)?"/admin/bookings?"+new URLSearchParams({booking_id:booking,target_branch:branch}):null;
}
export function rememberAdminBookingTarget():void {
  const path=currentAdminBookingTarget();
  if(!path||!spaSlug(window.location.pathname))return;
  sessionStorage.setItem(adminStorageKey("spaos_admin_pending_booking"),JSON.stringify({path,at:Date.now()}));
}
export function takeAdminBookingTarget(spa:string):string|null {
  const key="spaos_admin_pending_booking:"+spa;
  const stored=sessionStorage.getItem(key);sessionStorage.removeItem(key);
  if(!stored)return null;
  try{
    const value=JSON.parse(stored) as {path?:unknown;at?:unknown};
    if(typeof value.path!=="string"||typeof value.at!=="number"||Date.now()-value.at>1800000||Date.now()<value.at)return null;
    const match=/^\/admin\/bookings\?booking_id=([^&]+)&target_branch=([^&]+)$/.exec(value.path);
    return match&&uuid.test(match[1])&&uuid.test(match[2])?value.path:null;
  }catch{return null;}
}
