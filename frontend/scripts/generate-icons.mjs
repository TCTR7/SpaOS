// Rebuild the code-native SpaOS icon: node scripts/generate-icons.mjs
// Shared curves keep the SVG and PNG in sync. No image library needed.
import { writeFile } from "node:fs/promises";
import { deflateSync } from "node:zlib";
const output = new URL("../public/icons/", import.meta.url);
const background = [33, 60, 53];
const curves = [
  [[318,202],[318,174],[291,158],[256,158]],
  [[256,158],[219,158],[192,177],[192,207]],
  [[192,207],[192,261],[320,245],[320,302]],
  [[320,302],[320,333],[291,354],[254,354]],
  [[254,354],[217,354],[190,336],[190,306]],
];
const path = "M318 202C318 174 291 158 256 158C219 158 192 177 192 207C192 261 320 245 320 302C320 333 291 354 254 354C217 354 190 336 190 306";
const points = curves.flatMap((curve) => Array.from({length:49}, (_,i) => {
  const t=i/48,u=1-t;
  return [0,1].map((a) => u**3*curve[0][a]+3*u**2*t*curve[1][a]+3*u*t**2*curve[2][a]+t**3*curve[3][a]);
}));
function onMark(x,y) { return points.some(([px,py]) => (x-px)**2+(y-py)**2<=17**2); }
function crc32(bytes) {
  let crc=0xffffffff;
  for(const byte of bytes) { crc^=byte; for(let bit=0;bit<8;bit++) crc=(crc>>>1)^(crc&1?0xedb88320:0); }
  return (crc^0xffffffff)>>>0;
}
function chunk(type,data) {
  const name=Buffer.from(type),length=Buffer.alloc(4),checksum=Buffer.alloc(4);
  length.writeUInt32BE(data.length);checksum.writeUInt32BE(crc32(Buffer.concat([name,data])));
  return Buffer.concat([length,name,data,checksum]);
}
function png(size) {
  const header=Buffer.alloc(13);header.writeUInt32BE(size);header.writeUInt32BE(size,4);header[8]=8;header[9]=2;
  const pixels=Buffer.alloc((size*3+1)*size);
  for(let y=0;y<size;y++) for(let x=0;x<size;x++) {
    let coverage=0;
    for(const dy of [0.25,0.75]) for(const dx of [0.25,0.75]) if(onMark((x+dx)*512/size,(y+dy)*512/size)) coverage++;
    const offset=y*(size*3+1)+1+x*3;
    for(let c=0;c<3;c++) pixels[offset+c]=Math.round(background[c]+(255-background[c])*coverage/4);
  }
  return Buffer.concat([Buffer.from("89504e470d0a1a0a","hex"),chunk("IHDR",header),chunk("IDAT",deflateSync(pixels)),chunk("IEND",Buffer.alloc(0))]);
}
for(const size of [180,192,512]) {
  const name=size===180?"apple-touch-icon":"icon-"+size+"x"+size;
  await writeFile(new URL(name+".png",output),png(size));
  if(size!==180) await writeFile(new URL(name+".svg",output),'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="'+size+'" height="'+size+'"><rect width="512" height="512" rx="104" fill="#213c35"/><path d="'+path+'" fill="none" stroke="white" stroke-width="34" stroke-linecap="round"/></svg>\n');
}
