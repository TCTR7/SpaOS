import type { CSSProperties } from "react";
export const DEFAULT_BRAND = "#be185d";
export function validBrandColor(color: string | null | undefined): string {
  return color && /^#[0-9a-f]{6}$/i.test(color) ? color.toLowerCase() : DEFAULT_BRAND;
}
const rgb = (hex: string): number[] => [1,3,5].map((start) => parseInt(hex.slice(start,start+2),16)/255);
const luminance = (values: number[]): number => values.map((x) => x <= .04045 ? x/12.92 : ((x+.055)/1.055)**2.4)
  .reduce((sum,x,i) => sum+x*[.2126,.7152,.0722][i],0);
export function brandForeground(hex: string): string { return luminance(rgb(validBrandColor(hex))) > .179 ? "#000000" : "#ffffff"; }
function hsl(values: number[]): string {
  const [r,g,b] = values, max = Math.max(...values), min = Math.min(...values), d = max-min, l = (max+min)/2;
  let h = 0;
  if (d) h = max === r ? ((g-b)/d)%6 : max === g ? (b-r)/d+2 : (r-g)/d+4;
  const s = d ? d/(1-Math.abs(2*l-1)) : 0;
  return `${(h*60+360)%360} ${s*100}% ${l*100}%`;
}
export function brandStyle(value: string): CSSProperties {
  const color = validBrandColor(value), original = rgb(color);
  let text = [...original];
  while ((1.05)/(luminance(text)+.05) < 7) text = text.map((x) => x*.9);
  const accent = original.map((x) => x*.08+.92);
  return {
    "--brand-color": color, "--brand-foreground": brandForeground(color), "--brand-text": `hsl(${hsl(text)})`,
    "--primary": hsl(original), "--primary-foreground": brandForeground(color) === "#000000" ? "0 0% 0%" : "0 0% 100%",
    "--primary-text": hsl(text), "--ring": hsl(text), "--accent": hsl(accent), "--accent-foreground": hsl(text),
    "--secondary": hsl(accent), "--secondary-foreground": hsl(text), "--spa-brand": color,
  } as CSSProperties;
}
