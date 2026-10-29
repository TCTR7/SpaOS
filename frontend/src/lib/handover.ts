import type { OwnerDetail } from "@/components/operator-owner";
export type Sheet = {key:string;title:string;name:string;url:string;lines:string[];logo?:string|null};
export function handoverSheets(owner:OwnerDetail, origin:string):Sheet[]{
  const base=new URL(origin).origin;
  const brand=owner.spa?"/s/"+encodeURIComponent(owner.spa.slug):"";
  const branches=owner.branches.filter(b=>b.active);
  return [
    {key:"management",title:"DÀNH CHO CHỦ SPA & NHÂN VIÊN",name:owner.spa?.name||"Trang quản lý spa",url:base+brand+"/admin/login",logo:owner.spa?.logo_url,lines:["Chủ spa: "+owner.full_name,"Số điện thoại đăng nhập: "+owner.phone_number,"Nhân viên sử dụng tài khoản riêng do chủ spa cấp.","Mật khẩu hoặc liên kết kích hoạt được gửi riêng.","Đăng nhập, mở Hướng dẫn & Cài ứng dụng để bắt đầu."]},
    {key:"customers",title:"DÀNH CHO KHÁCH HÀNG",name:owner.spa?.name||"Đặt lịch tại spa",url:base+brand+"/",logo:owner.spa?.logo_url,lines:["Chọn chi nhánh, dịch vụ và khung giờ phù hợp.","Lưu đường dẫn hoặc thêm ứng dụng vào màn hình chính.","Bạn có thể chia sẻ trang này cho khách hàng của spa."]},
    ...branches.map(b=>({key:b.id,title:"ĐẶT LỊCH TẠI CHI NHÁNH",name:b.name,url:base+(brand?brand+"/b":"")+"/"+encodeURIComponent(b.slug),logo:b.logo_url||owner.spa?.logo_url,lines:[...(b.address?[b.address]:[]),"Quét mã để xem dịch vụ và chọn lịch hẹn.","Mã này dẫn thẳng đến chi nhánh; phù hợp để in tại quầy."]})),
  ];
}
export function handoverMessage(owner:OwnerDetail,origin:string):string{
  const sheets=handoverSheets(owner,origin);
  return ["Thông tin bàn giao ứng dụng spa", "", ...sheets.flatMap(s=>[s.title+" — "+s.name,s.url,...(s.key==="management"?["SĐT chủ spa: "+owner.phone_number]:[]),""]),"Mật khẩu/liên kết kích hoạt được gửi riêng. Không chuyển thông tin đăng nhập cho khách hàng.","Mở Hướng dẫn & Cài ứng dụng trong ứng dụng để xem hướng dẫn Android/iPhone."].join("\n");
}
export async function renderHandover(sheet:Sheet):Promise<HTMLCanvasElement>{
  const QRCode=await import("qrcode");
  await document.fonts.ready;
  const canvas=document.createElement("canvas");canvas.width=1200;canvas.height=2400;
  const ctx=canvas.getContext("2d");if(!ctx)throw new Error("Trình duyệt chưa hỗ trợ xuất ảnh");
  ctx.fillStyle="#f7f8f5";ctx.fillRect(0,0,1200,2400);
  let y=90;
  const text=(value:string,size:number,color:string,gap=16):void=>{
    ctx.font=(size>=40?"600 ":"400 ")+size+"px Arial";ctx.fillStyle=color;
    let line="";
    for(const char of Array.from(value)){
      if(ctx.measureText(line+char).width>1020){ctx.fillText(line,90,y);y+=size*1.4;line="";}
      line+=char;
    }
    if(line){ctx.fillText(line,90,y);y+=size*1.4;}
    y+=gap;
  };
  text(sheet.title,24,"#60756b",28);
  if(sheet.logo){
    try{
      const url=new URL(sheet.logo,window.location.origin);
      // Export only same-origin public logos; foreign images may taint canvas.
      if(url.origin===window.location.origin){
        const response=await fetch(url,{signal:AbortSignal.timeout(5000),credentials:"omit"});
        if(response.ok){const bitmap=await createImageBitmap(await response.blob());const scale=Math.min(140/bitmap.width,140/bitmap.height);ctx.drawImage(bitmap,90,y,bitmap.width*scale,bitmap.height*scale);bitmap.close();y+=170;}
      }
    }catch{/* The information and QR remain usable without a logo. */}
  }
  text(sheet.name,48,"#213c35",30);
  const qr=document.createElement("canvas");
  await QRCode.toCanvas(qr,sheet.url,{width:560,margin:4,errorCorrectionLevel:"M",color:{dark:"#000000",light:"#ffffff"}});
  ctx.drawImage(qr,320,y);y+=610;
  text("Quét mã QR hoặc mở đường dẫn:",28,"#60756b");
  text(sheet.url,28,"#213c35",32);
  for(const line of sheet.lines)text(line,28,"#213c35",14);
  y+=20;text("Thông tin được xuất ngày "+new Date().toLocaleDateString("vi-VN"),22,"#60756b");
  const result=document.createElement("canvas");result.width=1200;result.height=Math.max(1600,Math.ceil(y+60));
  const out=result.getContext("2d");if(!out)throw new Error("Chưa xuất được ảnh");
  out.fillStyle="#f7f8f5";out.fillRect(0,0,result.width,result.height);out.drawImage(canvas,0,0);
  return result;
}
export function downloadBlob(blob:Blob,name:string):void{
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
}
export async function handoverPdf(sheets:Sheet[]):Promise<Blob>{
  const {jsPDF}=await import("jspdf");const pdf=new jsPDF({unit:"mm",format:"a4"});
  for(let i=0;i<sheets.length;i++){
    if(i)pdf.addPage();
    const canvas=await renderHandover(sheets[i]);const width=Math.min(190,277*canvas.width/canvas.height);const height=width*canvas.height/canvas.width;
    pdf.addImage(canvas.toDataURL("image/png"),"PNG",(210-width)/2,10,width,height);
    pdf.link((210-width)/2,10,width,height,{url:sheets[i].url});
  }
  return pdf.output("blob");
}
