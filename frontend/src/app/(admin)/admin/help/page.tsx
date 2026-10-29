"use client";
import * as React from "react";
import { ScreenHelp } from "@/components/screen-help";
import { ProductGuide } from "@/components/product-guide";
import { useAdminAuth } from "@/components/admin/auth-context";
export default function HelpPage(): React.ReactElement {
  const { user, branches } = useAdminAuth();
  return <div className="mx-auto max-w-2xl space-y-6"><div><h1 className="text-xl font-bold">Trợ giúp &amp; Cài ứng dụng</h1><p className="mt-2 text-sm text-muted-foreground">Xem lại hướng dẫn hoặc thêm ứng dụng vào màn hình chính.</p></div>{user && <ProductGuide role={user.role === "ADMIN" ? "ADMIN" : "STAFF"} identity={user.id} identities={branches.map((branch) => branch.user.id)} mode="page" />}{user&&<ScreenHelp role={user.role === "ADMIN" ? "ADMIN" : "STAFF"} identity={user.id} library/>}</div>;
}
