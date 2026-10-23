import type { UserDetail } from "./types";

export interface EligibleStaff {
  /** Có kỹ năng cho toàn bộ dịch vụ đã chọn. */
  matching: UserDetail[];
  /** Chưa khai báo kỹ năng nào; backend vẫn cho xếp lịch để dữ liệu cũ không bị gián đoạn. */
  undeclared: UserDetail[];
}

/** Lọc nhân viên đang làm theo kỹ năng. Danh sách không kèm skill_service_ids (vai trò STAFF) được giữ nguyên. */
export function eligibleStaff(staff: UserDetail[], serviceIds: string[]): EligibleStaff {
  const active = staff.filter((member) => member.is_active);
  if (serviceIds.length === 0) return { matching: active, undeclared: [] };
  const matching: UserDetail[] = [];
  const undeclared: UserDetail[] = [];
  for (const member of active) {
    const skills = member.skill_service_ids;
    if (skills === undefined) matching.push(member);
    else if (skills.length === 0) undeclared.push(member);
    else if (serviceIds.every((id) => skills.includes(id))) matching.push(member);
  }
  return { matching, undeclared };
}
