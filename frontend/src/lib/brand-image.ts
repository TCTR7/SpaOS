export async function brandImage(file:File, cover=false):Promise<string> {
  if(!file.type.startsWith("image/"))throw new Error("Chọn một ảnh hợp lệ.");
  const url=URL.createObjectURL(file);
  try{
    const image=new Image();
    await new Promise<void>((resolve,reject)=>{image.onload=()=>resolve();image.onerror=()=>reject(new Error("Không đọc được ảnh."));image.src=url;});
    const canvas=document.createElement("canvas");canvas.width=cover?1024:512;canvas.height=512;
    const context=canvas.getContext("2d");if(!context)throw new Error("Không xử lý được ảnh.");
    const scale=Math.max(canvas.width/image.width,canvas.height/image.height);
    context.drawImage(image,(canvas.width-image.width*scale)/2,(canvas.height-image.height*scale)/2,image.width*scale,image.height*scale);
    const result=canvas.toDataURL("image/png").split(",")[1];
    if(result.length>2800000)throw new Error("Ảnh sau xử lý quá lớn. Chọn ảnh đơn giản hơn.");
    return result;
  }finally{URL.revokeObjectURL(url);}
}
