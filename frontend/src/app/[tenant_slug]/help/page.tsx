"use client";
import * as React from "react";
import { ScreenHelp } from "@/components/screen-help";
import { ProductGuide } from "@/components/product-guide";
import { useCustomerTenant } from "@/components/customer/customer-context";
export default function CustomerHelpPage(): React.ReactElement {
  const { slug, user, tenant } = useCustomerTenant();
  return <div className="space-y-6"><div><h1 className="text-xl font-bold">Trợ giúp &amp; Cài ứng dụng</h1><p className="mt-2 text-sm text-muted-foreground">Hướng dẫn đặt lịch và mở ứng dụng trên thiết bị của bạn.</p></div><ProductGuide role="CUSTOMER" slug={slug} identity={user?.id} mode="page" /><ScreenHelp role="CUSTOMER" identity={user?.id || tenant?.id || slug} slug={slug} library/></div>;
}
