"use client";

import * as React from "react";
import { DateOverrides } from "@/components/admin/date-overrides";
import { CredentialForm } from "@/components/credential-form";
import { useBranchGuard } from "@/lib/branch-guard";
import { useListDetail } from "@/lib/use-list-detail";
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
  const detail = useListDetail();
  const [accountDirty, setAccountDirty] = React.useState(false);
  const [accountBusy, setAccountBusy] = React.useState(false);
  const [dateDirty, setDateDirty] = React.useState(false), [dateBusy, setDateBusy] = React.useState(false);
  const staffRequest = React.useRef(0);
  const selectedId = React.useRef<string | null>(null);
  const [schedError, setSchedError] = React.useState<string | null>(null);
  const [schedDirty, setSchedDirty] = React.useState(false);
  const [pendingStaff, setPendingStaff] = React.useState<UserDetail | null>(null);
  const scheduleFlight = React.useRef(false);
  const staffFlight = React.useRef(false);
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

  useBranchGuard(schedDirty, savingSched);
  const loadStaff = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchStaffList();
      setStaffList(list);
      if (selectedStaff) setSelectedStaff((current) => list.find((row) => row.id === current?.id) || null);
      if (list.length > 0 && !selectedStaff) {
        setSchedLoading(true);
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

  selectedId.current = selectedStaff?.id || null;
  const loadSchedulesForStaff = React.useCallback(async (staffId: string): Promise<void> => {
    const request = ++staffRequest.current;
    setSchedLoading(true); setSchedError(null); setSuccessMsg(null);
    try {
      const existing = await fetchStaffSchedules(staffId);
      if (request !== staffRequest.current || selectedId.current !== staffId) return;
      const byDay = new Map(existing.map((item) => [item.day_of_week, item]));
      setSchedules(buildDefaultWeekSchedules().map((item) => byDay.get(item.day_of_week) || item));
      setSchedDirty(false);
    } catch (err) {
      if (request === staffRequest.current && selectedId.current === staffId) {
        setSchedules([]); setSchedError(err instanceof Error ? err.message : "Không tải được lịch làm việc");
      }
    } finally {
      if (request === staffRequest.current && selectedId.current === staffId) setSchedLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (selectedStaff) {
      void loadSchedulesForStaff(selectedStaff.id);
    }
    return () => { staffRequest.current += 1; };
  }, [selectedStaff?.id, loadSchedulesForStaff]);

  const openAddStaff = (): void => {
    if (scheduleFlight.current) return;
    setEditingStaff(null);
    setFullName("");
    setPhoneNumber("");
    setPassword("");
    setNotes("");
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditStaff = (st: UserDetail): void => {
    if (scheduleFlight.current) return;
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
    if (staffFlight.current) return;
    staffFlight.current = true;
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
          notes: notes.trim() || null,
          is_active: isActive,
        };

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
        setSchedules([]); setSchedLoading(true); setSelectedStaff(created); detail.open();
      }
      setModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Lưu thông tin nhân sự thất bại"
      );
    } finally {
      staffFlight.current = false;
      setSavingStaff(false);
    }
  };

  const updateDaySchedule = (
    dayOfWeek: number,
    patch: Partial<StaffScheduleItem>
  ): void => {
    setSchedDirty(true);
    setSchedules((prev) =>
      prev.map((item) =>
        item.day_of_week === dayOfWeek ? { ...item, ...patch } : item
      )
    );
  };

  const handleSaveSchedules = async (): Promise<void> => {
    if (scheduleFlight.current || !selectedStaff || schedLoading || schedError) return;
    scheduleFlight.current = true;
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
      setSchedDirty(false);
      setSuccessMsg(
        `Đã lưu lịch làm việc 7 ngày trong tuần cho KTV ${selectedStaff.full_name}!`
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cập nhật lịch làm việc thất bại"
      );
    } finally {
      scheduleFlight.current = false;
      setSavingSched(false);
    }
  };

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Nhân viên và lịch làm việc
          </h1>
          <p className="text-xs text-muted-foreground">
            Quản lý nhân viên và sắp xếp lịch làm
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
        <div ref={detail.listRef} className={cn("min-w-0 lg:col-span-4", detail.detailOpen && "hidden lg:block")}><Card>
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
            ) : error && staffList.length === 0 ? (
              <Button variant="outline" onClick={() => void loadStaff()}>Thử tải lại nhân sự</Button>
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
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-lg border p-3 transition",
                      active
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted/50"
                    )}
                  >
                    <button type="button" aria-pressed={active} disabled={savingSched || accountBusy || dateBusy}
                      onClick={(event) => {
                        if ((schedDirty || accountDirty || dateDirty) && selectedStaff?.id !== st.id) setPendingStaff(st);
                        else { if (selectedStaff?.id !== st.id) { setSchedules([]); setSchedLoading(true); } setSelectedStaff(st); detail.open(event.currentTarget); }
                      }} className="min-w-0 flex-1 py-1 text-left">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">
                          {st.full_name}
                        </p>
                        <Badge variant={st.is_active ? "success" : "outline"}>
                          {st.is_active ? "Đang làm việc" : "Ngưng làm việc"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        SĐT: {st.phone_number}
                      </p>
                      {st.notes && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
                          {st.notes}
                        </p>
                      )}
                    </button>
                    <Button
                      variant="ghost"
                      aria-label={`Sửa thông tin ${st.full_name}`}
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
        </Card></div>

        {/* Right: 7-Day Schedule Editor */}
        <Card className={cn("min-w-0 lg:col-span-8", !detail.detailOpen && "hidden lg:block")}>
          {!selectedStaff ? (
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <UserCheck className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">
                Chọn 1 Kỹ thuật viên để cấu hình ca làm việc
              </p>
            </CardContent>
          ) : (
            <>
              <div className="p-3 pb-0 lg:hidden"><Button variant="outline" onClick={detail.back}>Quay lại danh sách KTV</Button></div>
              <CardHeader className="flex min-w-0 flex-col gap-3 border-b border-border sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CalendarClock className="h-4 w-4 text-primary" />
                    Lịch làm việc 7 ngày — {selectedStaff.full_name}
                  </CardTitle>
                  <CardDescription>
                    Hệ thống dùng ca làm việc này kết hợp với giờ mở cửa của Spa
                    để xác định giờ có thể nhận khách.
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  disabled={savingSched || schedLoading || !!schedError}
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
                ) : schedError ? (
                  <div role="alert"><p>{schedError}</p><Button variant="outline" onClick={() => void loadSchedulesForStaff(selectedStaff.id)}>Thử tải lại ca làm</Button></div>
                ) : (
                  <div className="space-y-2.5">
                    <details className="rounded-lg border p-3">
                      <summary className="min-h-11 cursor-pointer py-2 text-sm font-semibold">Sao chép giờ làm cho cả tuần</summary>
                      <p className="mb-2 text-xs text-muted-foreground">Sao chép giờ từ Thứ 2; giữ nguyên các ngày nghỉ. Kiểm tra từng ngày rồi nhấn Lưu lịch tuần.</p>
                      <Button type="button" variant="outline" disabled={savingSched} onClick={() => {
                        const source = schedules.find((item) => item.day_of_week === 1);
                        if (!source) return;
                        setSchedules((previous) => previous.map((item) => ({ ...item, start_time: source.start_time, end_time: source.end_time })));
                        setSchedDirty(true);
                      }}>Áp dụng giờ Thứ 2 cho các ngày</Button>
                    </details>
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

                        <div className="flex min-w-0 w-full flex-wrap items-center gap-2 sm:w-auto">
                          <Input
                            type="time"
                            aria-label={`Giờ bắt đầu ${DAY_OF_WEEK_LABELS[s.day_of_week]}`}
                            value={s.start_time.slice(0, 5)}
                            disabled={s.is_day_off || savingSched}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                start_time: e.target.value,
                              })
                            }
                            className="min-w-0 flex-1 sm:w-32 sm:flex-none"
                          />
                          <span className="text-xs text-muted-foreground">
                            đến
                          </span>
                          <Input
                            type="time"
                            aria-label={`Giờ kết thúc ${DAY_OF_WEEK_LABELS[s.day_of_week]}`}
                            value={s.end_time.slice(0, 5)}
                            disabled={s.is_day_off || savingSched}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                end_time: e.target.value,
                              })
                            }
                            className="min-w-0 flex-1 sm:w-32 sm:flex-none"
                          />
                        </div>

                        <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-700">
                          <input
                            type="checkbox"
                            checked={s.is_day_off}
                            disabled={savingSched}
                            onChange={(e) =>
                              updateDaySchedule(s.day_of_week, {
                                is_day_off: e.target.checked,
                              })
                            }
                            className="h-4 w-4 accent-primary"
                          />
                          <span>Nghỉ hằng tuần</span>
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

      {selectedStaff && detail.detailOpen && <div className="ml-auto w-full max-w-2xl space-y-4">
        <DateOverrides key={selectedStaff.id + ":dates"} staffId={selectedStaff.id} onBusyChange={setDateBusy} onDirtyChange={setDateDirty} />
        <CredentialForm key={selectedStaff.id + ":account"} staffId={selectedStaff.id} phone={selectedStaff.phone_number} onSaved={() => void loadStaff()} onBusyChange={setAccountBusy} onDirtyChange={setAccountDirty} />
      </div>}
      {/* Add / Edit Staff Modal */}
      <Modal open={!!pendingStaff} onClose={() => setPendingStaff(null)} title="Bỏ thay đổi chưa lưu?">
        <p>Đổi nhân viên sẽ bỏ các thay đổi chưa lưu.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setPendingStaff(null)}>Tiếp tục chỉnh sửa</Button>
          <Button onClick={() => { setSelectedStaff(pendingStaff); setSchedules([]); setSchedLoading(true); setSchedDirty(false); setPendingStaff(null); detail.open(); }}>Bỏ thay đổi và chọn KTV</Button>
        </div>
      </Modal>
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        pending={savingStaff}
        dirty={editingStaff ? fullName !== editingStaff.full_name || phoneNumber !== editingStaff.phone_number || notes !== (editingStaff.notes || "") || isActive !== editingStaff.is_active || !!password : !!fullName || !!phoneNumber || !!notes || !!password}
        title={
          editingStaff
            ? "Cập nhật Kỹ thuật viên"
            : "Thêm kỹ thuật viên"
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
              id="stPhone" readOnly={Boolean(editingStaff)}
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0900000015"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stPwd">
              {editingStaff
                ? "Đổi mật khẩu ở mục Tài khoản đăng nhập bên dưới lịch làm"
                : "Mật khẩu đăng nhập (>= 6 ký tự)"}
            </Label>
            <Input
              id="stPwd" disabled={Boolean(editingStaff)}
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
            <Button type="submit" disabled={savingStaff}>
              {savingStaff ? "Đang lưu..." : "Lưu Kỹ thuật viên"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
