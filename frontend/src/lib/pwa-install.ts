export type InstallEvent = Event & {prompt:()=>Promise<void>;userChoice:Promise<{outcome:"accepted"|"dismissed"}>};
let deferred:InstallEvent|null=null;
let manifest="";
function currentManifest():string{return typeof document==="undefined"?"":document.querySelector<HTMLLinkElement>('link[rel="manifest"]')?.href||"";}
const listeners=new Set<()=>void>();
function announce():void{listeners.forEach(listener=>listener());}
export function captureInstallPrompt(event:Event):void{event.preventDefault();manifest=currentManifest();deferred=event as InstallEvent;announce();}
export function clearInstallPrompt():void{deferred=null;announce();}
export function installAvailable():boolean{return deferred!==null&&manifest===currentManifest();}
export function subscribeInstall(listener:()=>void):()=>void{listeners.add(listener);return()=>{listeners.delete(listener);};}
export async function promptInstall():Promise<void>{if(!installAvailable())return;const event=deferred;if(!event)return;clearInstallPrompt();await event.prompt();await event.userChoice;}
