"use client";
import * as React from "react";
import { ChevronDown } from "lucide-react";
interface Props {
  title: string; summary: React.ReactNode; description: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode; testId?: string;
}
export function DashboardPanel({ title, summary, description, icon: Icon, children, testId }: Props): React.ReactElement {
  const [open, setOpen] = React.useState(false);
  return <details data-testid={testId} className="group rounded-2xl border border-border bg-card" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary className="flex min-h-20 cursor-pointer list-none items-center gap-3 rounded-2xl p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:gap-4 sm:p-5 [&::-webkit-details-marker]:hidden">
      <Icon className="h-5 w-5 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1"><span className="block font-semibold">{title}</span><span className="mt-1 block text-sm font-normal text-muted-foreground">{description}</span></span>
      <span className="max-w-[45%] text-right text-base font-semibold tabular-nums sm:text-lg">{summary}</span>
      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
    </summary>
    {open && <div className="space-y-5 border-t border-border p-4 sm:p-5">{children}</div>}
  </details>;
}
