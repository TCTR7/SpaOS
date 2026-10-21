import type { ReactElement } from "react";
export function ContactLinks({ address, phone }: {address?: string | null; phone?: string | null}): ReactElement {
  return <div className="flex min-w-0 flex-wrap gap-x-4 gap-y-2 text-sm [overflow-wrap:anywhere]">
    {address && <a className="inline-flex min-h-11 items-center underline" href={"https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(address)} target="_blank" rel="noreferrer">{address} · Đường đi</a>}
    {phone && /^\+?\d{9,15}$/.test(phone) && <a className="inline-flex min-h-11 items-center underline" href={"tel:" + phone}>Gọi spa: {phone}</a>}
  </div>;
}
