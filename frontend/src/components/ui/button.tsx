import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> =
      {
        default:
          "bg-primary text-primary-foreground shadow-sm hover:opacity-90",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:opacity-90",
      };

    const sizeClasses: Record<NonNullable<ButtonProps["size"]>, string> = {
      default: "h-auto min-h-11 px-4 py-2 text-sm sm:min-h-9",
      sm: "h-auto min-h-11 rounded-md px-3 text-sm sm:min-h-8 sm:text-xs",
      lg: "h-auto min-h-12 rounded-md px-6 text-base sm:min-h-10 sm:text-sm",
      icon: "h-11 min-h-11 w-11 min-w-11 shrink-0 sm:h-9 sm:min-h-9 sm:w-9 sm:min-w-9",
    };

    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 max-w-full whitespace-normal text-center [overflow-wrap:anywhere] rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
