"use client";
import * as React from "react";
import { Input, type InputProps } from "./input";

export const PasswordInput = React.forwardRef<HTMLInputElement, InputProps>(({ className, disabled, ...props }, ref) => {
  const [visible, setVisible] = React.useState(false);
  return <div className="relative min-w-0 w-full">
    <Input {...props} ref={ref} disabled={disabled} type={visible ? "text" : "password"} className={(className || "") + " pr-16"} />
    <button type="button" disabled={disabled} aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"} aria-pressed={visible}
      onClick={() => setVisible((value) => !value)} className="absolute inset-y-0 right-0 min-h-11 min-w-14 px-2 text-xs font-semibold sm:min-min-h-11">{visible ? "Ẩn" : "Hiện"}</button>
  </div>;
});
PasswordInput.displayName = "PasswordInput";
