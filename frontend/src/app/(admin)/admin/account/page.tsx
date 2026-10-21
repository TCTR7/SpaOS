"use client";
import * as React from "react";
import { CredentialForm } from "@/components/credential-form";
import { useAdminAuth } from "@/components/admin/auth-context";
export default function AccountPage(): React.ReactElement {
 const { user, refreshMe } = useAdminAuth();
 return <div className="mx-auto w-full max-w-2xl space-y-4"><h1 className="text-xl font-bold">Tài khoản của tôi</h1>{user && <CredentialForm key={user.id} phone={user.phone_number} onSaved={() => void refreshMe()} />}</div>;
}
