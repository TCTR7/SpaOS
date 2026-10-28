"use client";
import { WorkforceEditor } from "@/components/admin/workforce-editor";
import { useAdminAuth } from "@/components/admin/auth-context";

export default function WorkHoursPage():React.ReactElement {
  const {user}=useAdminAuth();
  if(user?.role!=="STAFF")return <p>Chủ spa xem và sắp xếp ca tại Nhân sự & Ca làm việc.</p>;
  return <WorkforceEditor key={user.id} staffId={user.id} readOnly/>;
}
