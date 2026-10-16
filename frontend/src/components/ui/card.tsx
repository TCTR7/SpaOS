import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>): React.ReactElement {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card text-card-foreground shadow-sm",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>): React.ReactElement {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 p-5", className)}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>): React.ReactElement {
  return (
    <h3
      className={cn("font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>): React.ReactElement {
  return (
    <p
      className={cn("text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>): React.ReactElement {
  return <div className={cn("p-5 pt-0", className)} {...props} />;
}

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "danger";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps): React.ReactElement {
  const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
    default: "bg-primary/15 text-primary border-primary/25",
    secondary: "bg-secondary text-secondary-foreground border-border",
    outline: "bg-transparent text-foreground border-border",
    success: "bg-emerald-100 text-emerald-800 border-emerald-300",
    warning: "bg-amber-100 text-amber-800 border-amber-300",
    danger: "bg-rose-100 text-rose-800 border-rose-300",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
