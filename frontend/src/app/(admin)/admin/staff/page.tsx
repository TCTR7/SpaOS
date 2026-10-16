"use client";

import * as React from "react";
import { CalendarClock, Edit2, Plus, Save, UserCheck } from "lucide-react";
import {
  createStaff,
  fetchStaffList,
  fetchStaffSchedules,
  saveStaffSchedules,
  updateStaff,
} from "@/lib/api";
import type { StaffScheduleItem, UserDetail } from "@/lib/types";
import { cn, DAY_OF_WEEK_LABELS } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

const DAY_ORDER: number[] = [1, 2, 3, 4, 5, 6, 0]; // Thứ 2 -> Chủ Nhật

function buildDefaultWeekSchedules(): StaffScheduleItem[] {
  return DAY_ORDER.map((dow) => ({
    day_of_week: dow,
    start_time: "09:00:00",
    end_time: "20:00:00",
    is_day_off: false,
  }));
}

export default function AdminStaffPage(): React.ReactElement {
  const [staffList, setStaffList] = React.useState<UserDetail[]>([]);
  const [selectedStaff, setSelectedStaff] = React.useState<UserDetail | null>(
    null
  );
  const [schedules, setSchedules] = React.useState<StaffScheduleItem[]>(
    buildDefaultWeekSchedules
  );
  const [loading, setLoading] = React.useState<boolean>(true);
  const [schedLoading, setSchedLoading] = React.useState<boolean>(false);
  const [savingSched, setSavingSched] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  // Staff Create / Edit Modal
  const [modalOpen, setModalOpen] = React.useState<boolean>(false);
  const [editingStaff, setEditingStaff] = React.useState<UserDetail | null>(
    null
  );
  const [fullName, setFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [isActive, setIsActive] = React.useState<boolean>(true);
  const [savingStaff, setSavingStaff] = React.useState<boolean>(false);

  const loadStaff = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchStaffList();
      setStaffList(list);
      if (list.length > 0 && !selectedStaff) {
        setSelectedStaff(list[0]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách Kỹ thuật viên"
      );
    } finally {
      setLoading(false);
    }
  }, [selectedStaff]);

  const loadSchedulesForStaff = React.useCallback(
    async (staffId: string): Promise<void> => {
      setSchedLoading(true);
      setSuccessMsg(null);
      try {
        const existing = await fetchStaffSchedules(staffId);
        const byDay = new Map<number, StaffScheduleItem>();
        for (const item of existing) {
          byDay.set(item.day_of_week, {
            day_of_week: item.day_of_week,
            start_time: item.start_time.slice(0, 5),
            end_time: item.end_time.slice(0, 5),
            is_day_off: item.is_day_off,
          });
        }
        const merged = DAY_ORDER.map(
          (dow) =>
            byDay.get(dow) ?? {
              day_of_week: dow,
              start_time: "09:00",
              end_time: "20:00",
              is_day_off: false,
            }
        );
        setSchedules(merged);
      } catch {
        setSchedules(buildDefaultWeekSchedules());
      } finally {
        setSchedLoading(false);
      }
    },
    []
  );

  React.useEffect(() => {
    void loadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (selectedStaff) {
      void loadSchedulesForStaff(selectedStaff.id);
    }
  }, [selectedStaff, loadSchedulesForStaff]);

  const openAddStaff = (): void => {
    setEditingStaff(null);
    setFullName("");
    setPhoneNumber("");
    setPassword("");
    setNotes("");
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditStaff = (st: UserDetail): void => {
    setEditingStaff(st);
    setFullName(st.full_name);
    setPhoneNumber(st.phone_number);
    setPassword("");
    setNotes(st.notes || "");
    setIsActive(st.is_active);
    setModalOpen(true);
  };

  const handleSaveStaff = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setSavingStaff(true);
    setError(null);
    setSuccessMsg(null);
    try {
      if (editingStaff) {
        const payload: Partial<{
          full_name: string;
          phone_number: string;
          password: string;
          notes: string | null;
          is_active: boolean;
        }> = {
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim(),
          notes: notes.trim() || null,
          is_active: isActive,
        };
        if (password.trim()) {
          payload.password = password.trim();
        }
        const updated = await updateStaff(editingStaff.id, payload);
        setStaffList((prev) =>
          prev.map((s) => (s.id === updated.id ? updated : s))
        );
        if (selectedStaff?.id === updated.id) {
          setSelectedStaff(updated);
        }
      } else {
        const created = await createStaff({
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim(),
          password: password.trim(),
          notes: notes.trim() || null,
        });
        setStaffList((prev) => [created, ...prev]);
        setSelectedStaff(created);
      }
      setModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Lưu thông tin nhân sự thất bại"
      );
    } finally {
      setSavingStaff(false);
    }
  };

  const updateDaySchedule = (
    dayOfWeek: number,
    patch: Partial<StaffScheduleItem>
  ): void => {
    setSchedules((prev) =>
      prev.map((item) =>
        item.day_of_week === dayOfWeek ? { ...item, ...patch } : item
      )
    );
  };

  const handleSaveSchedules = async (): Promise<void> => {
    if (!selectedStaff) return;
    setSavingSched(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const normalized = schedules.map((s) => ({
        day_of_week: s.day_of_week,
        start_time:
          s.start_time.length === 5 ? `${s.start_time}:00` : s.start_time,
        end_time: s.end_time.length === 5 ? `${s.end_time}:00` : s.end_time,
        is_day_off: s.is_day_off,
      }));
      await saveStaffSchedules(selectedStaff.id, normalized);
      setSuccessMsg(
        `Đã lưu lịch làm việc 7 ngày trong tuần cho KTV ${selectedStaff.full_name}!`
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cập nhật lịch làm việc thất bại"
      );
    } finally {
      setSavingSched(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Nhân sự Kỹ thuật viên & Ca làm việc
          </h1>
          <p className="text-xs text-muted-foreground">
            Quản lý tài khoản Kỹ thuật viên (STAFF) và cấu hình khung giờ làm
            việc 7 ngày trong tuần
          </p>
        </div>
        <Button size="sm" onClick={openAddStaff}>
          <Plus className="h-4 w-4" />
          Thêm Kỹ thuật viên mới
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-800">
          {successMsg}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-12">
        {/* Left: Staff List */}
        <Card className="lg:col-span-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Danh sách Kỹ thuật viên ({staffList.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {loading ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Đang tải nhân sự...
              </p>
            ) : staffList.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Chưa có Kỹ thuật viên nào.
              </p>
            ) : (
              staffList.map((st) => {
                const active = selectedStaff?.id === st.id;
                return (
                  <div
                    key={st.id}
                    onClick={() => setSelectedStaff(st)}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-lg border p-3 transition",
                      active
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted/50"
                    )}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-semibold text-foreground">
                          {st.full_name}
                        </p>
                        <Badge variant={st.is_active ? "success" : "outline"}>
                          {st.is_active ? "Active" : "Ngưng"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        SĐT: {st.phone_number}
                      </p>
                      {st.notes && (
                        <p className="mt-0.5 truncate text-[11px] text-slate-600">
                          {st.notes}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditStaff(st);
                      }}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Right: 7-Day Schedule Editor */}
        <Card className="lg:col-span-8">
          {!selectedStaff ? (
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <UserCheck className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">
                Chọn 1 Kỹ thuật viên để cấu hình ca làm việc
              </p>
            </CardContent>
          ) : (
            <>
              <CardHeader className="flex flex-col gap-3 border-b border-border sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CalendarClock className="h-4 w-4 text-primary" />
                    Lịch làm việc 7 ngày — {selectedStaff.full_name}
                  </CardTitle>
                  <CardDescription>
                    Hệ thống dùng ca làm việc này kết hợp với giờ mở cửa của Spa
                    để tính khung giờ trống (Available Slots).
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  disabled={savingSched || schedLoading}
                  onClick={() => void handleSaveSchedules()}
                >
                  <Save className="h-4 w-4" />
                  {savingSched ? "Đang lưu..." : "Lưu lịch tuần"}
                </Button>
              </CardHeader>

              <CardContent className="pt-4">
                {schedLoading ? (
                  <p className="py-8 text-center text-xs text-muted-foreground">
                    Đang tải lịch làm việc...
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {schedules.map((s) => (
                      <div
                        key={s.day_of_week}
                        className={cn(
                          "flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3",
                          s.is_day_off
                            ? "border-border bg-muted/40 opacity-75"
                            : "border-border bg-card"
                        )}
                      >
                        <div className="w-28 font-semibold text-sm text-foreground">
                          {DAY_OF_WEEK_LABELS[s.day_of_week]}
                        </div>

                        <div className="flex items-center gap-2">
                          <Input
                            type="time"
                            value={s.start_time.slice(0, 5)}
                            disabled={s.is_day_off}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                start_time: e.target.value,
                              })
                            }
                            className="w-32"
                          />
                          <span className="text-xs text-muted-foreground">
                            đến
                          </span>
                          <Input
                            type="time"
                            value={s.end_time.slice(0, 5)}
                            disabled={s.is_day_off}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                end_time: e.target.value,
                              })
                            }
                            className="w-32"
                          />
                        </div>

                        <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-700">
                          <input
                            type="checkbox"
                            checked={s.is_day_off}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                is_day_off: e.target.checked,
                              })
                            }
                            className="h-4 w-4 accent-primary"
                          />
                          <span>Ngày nghỉ phép (Day-off)</span>
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>

      {/* Add / Edit Staff Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={
          editingStaff
            ? "Cập nhật Kỹ thuật viên"
            : "Thêm Kỹ thuật viên (STAFF)"
        }
      >
        <form onSubmit={(e) => void handleSaveStaff(e)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="stName">Họ và tên Kỹ thuật viên</Label>
            <Input
              id="stName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Trần Ngọc Mai"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stPhone">Số điện thoại đăng nhập</Label>
            <Input
              id="stPhone"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0900000015"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stPwd">
              {editingStaff
                ? "Mật khẩu mới (Để trống nếu giữ nguyên)"
                : "Mật khẩu đăng nhập (>= 6 ký tự)"}
            </Label>
            <Input
              id="stPwd"
              type="password"
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required={!editingStaff}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stNotes">Chuyên môn / Ghi chú</Label>
            <Textarea
              id="stNotes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Chuyên viên điều trị mụn, massage cổ vai gáy..."
            />
          </div>

          {editingStaff && (
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              <span>Tài khoản đang hoạt động (nhận lịch hẹn)</span>
            </label>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={savingStaff}>
              {savingStaff ? "Đang lưu..." : "Lưu Kỹ thuật viên"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
