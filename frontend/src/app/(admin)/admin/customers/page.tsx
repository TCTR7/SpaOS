"use client";

import * as React from "react";
import { apiRequest } from "@/lib/api";
import Link from "@/components/spa-link";
import { CustomerVisits } from "@/components/admin/customer-visits";
import type { GuestEnquiry } from "@/components/admin/guest-inbox";
import { useBranchGuard } from "@/lib/branch-guard";
import { useListDetail } from "@/lib/use-list-detail";
import {
  CalendarPlus,
  Edit2,
  Lock,
  Plus,
  Search,
  User as UserIcon,
} from "lucide-react";
import {
  createCustomer,
  fetchStaffList,
  assignCustomer,
  fetchCustomerPage,
  fetchServices,
  updateCustomer,
} from "@/lib/api";
import { useAdminAuth } from "@/components/admin/auth-context";
import type {
  ServiceItem,
  UserDetail,
} from "@/lib/types";
import { cn, formatDateTimeVN } from "@/lib/utils";
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

export default function AdminCustomersPage(): React.ReactElement {
  const { user } = useAdminAuth();
  const detail = useListDetail();
  const customerRequest = React.useRef(0);
  const selectedId = React.useRef<string | null>(null);
  const listQuery = React.useRef("");
  const [nextOffset, setNextOffset] = React.useState<number | null>(null);
  const [moreLoading, setMoreLoading] = React.useState(false);
  const customerFlight = React.useRef(false);

  const [owners, setOwners] = React.useState<UserDetail[]>([]);
  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [guestRequests, setGuestRequests] = React.useState<GuestEnquiry[]>([]);
  const [confirmingGuestId, setConfirmingGuestId] = React.useState<string | null>(null);
  const [ownerId, setOwnerId] = React.useState<string>("");
  const [assigning, setAssigning] = React.useState(false);
  const [customers, setCustomers] = React.useState<UserDetail[]>([]);
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  const [selectedCustomer, setSelectedCustomer] = React.useState<UserDetail | null>(null);
  useBranchGuard(!!selectedCustomer && ownerId !== (selectedCustomer.assigned_staff_id || ""), assigning);

  const selectCustomer = React.useCallback((customer: UserDetail | null): void => {
    selectedId.current = customer?.id || null;
    setSelectedCustomer(customer);
    setOwnerId(customer?.assigned_staff_id || "");
  }, []);

  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [otherStaffCustomerIds] = React.useState<Set<string>>(() => new Set());

  // Create / Edit Customer Modal
  const [customerModalOpen, setCustomerModalOpen] = React.useState<boolean>(false);
  const [editingCustomer, setEditingCustomer] = React.useState<UserDetail | null>(null);
  const [fullName, setFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [savingCustomer, setSavingCustomer] = React.useState<boolean>(false);

  const loadGuestRequests = React.useCallback(async (): Promise<void> => {
    try {
      const res = await apiRequest<{ items: GuestEnquiry[] }>("/guest-requests?offset=0");
      setGuestRequests(res.items || []);
    } catch {
      setGuestRequests([]);
    }
  }, []);

  const loadCustomers = React.useCallback(async (q = "", append = false, initialTarget: string | null = null): Promise<void> => {
    const request = ++customerRequest.current;
    if (append) setMoreLoading(true);
    else { setLoading(true); setCustomers([]); setNextOffset(null); listQuery.current = q; }
    setError(null);
    try {
      const page = await fetchCustomerPage({ q, limit: 50, offset: append ? nextOffset || 0 : 0 });
      if (request !== customerRequest.current) return;
      setCustomers((previous) => Array.from(new Map([...(append ? previous : []), ...page.items].map((c) => [c.id, c])).values()));
      setNextOffset(page.nextOffset);
      if (!append) {
        const target = initialTarget;
        const found = page.items.find((c) => c.id === (target || selectedId.current));
        if (target && !found) {
          const customer = await apiRequest<UserDetail>("/customers/" + encodeURIComponent(target));
          if (request !== customerRequest.current) return;
          setCustomers((rows) => [customer, ...rows.filter((c) => c.id !== customer.id)]);
          selectCustomer(customer);
          detail.open();
        } else {
          selectCustomer(found || page.items[0] || null);
          if (target) detail.open();
        }
      }
    } catch (err) {
      if (request === customerRequest.current) setError(err instanceof Error ? err.message : "Không tải được khách hàng");
    } finally {
      if (request === customerRequest.current) { setLoading(false); setMoreLoading(false); }
    }
  }, [nextOffset, selectCustomer, detail]);

  React.useEffect(() => {
    const target = new URLSearchParams(window.location.search).get("customer_id");
    let q = "";
    try {
      const saved = JSON.parse(sessionStorage.getItem("spaos_crm_return_" + user?.tenant_id + "_" + user?.id) || "null") as { id: string; q: string; y: number; at: number } | null;
      if (target && saved?.id === target && Date.now() - saved.at < 8 * 3600000) {
        q = saved.q;
        setSearchQuery(q);
      }
    } catch { /* Optional list restoration. */ }
    void loadCustomers(q, false, target);
    void fetchServices().then(setServices).catch(() => setServices([]));
    void loadGuestRequests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { customerRequest.current += 1; };
  }, []);

  React.useEffect(() => {
    if (user?.role === "ADMIN") void fetchStaffList().then(setOwners).catch(() => setOwners([]));
  }, [user]);

  const handleAssign = async (): Promise<void> => {
    if (!selectedCustomer) return;
    setAssigning(true);
    setError(null);
    try {
      const updated = await assignCustomer(selectedCustomer.id, ownerId || null);
      if (selectedId.current === updated.id) selectCustomer(updated);
      setCustomers((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể chuyển người phụ trách");
    } finally {
      setAssigning(false);
    }
  };

  const handleConfirmGuestRequest = async (req: GuestEnquiry, customerId: string): Promise<void> => {
    if (confirmingGuestId) return;
    setConfirmingGuestId(req.id);
    setError(null);
    try {
      await apiRequest(`/guest-requests/${req.id}/decision`, {
        method: "POST",
        body: { action: "confirm", identity_verified: true, customer_id: customerId },
      });
      await loadGuestRequests();
      await loadCustomers(listQuery.current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể xác nhận yêu cầu đặt lịch");
    } finally {
      setConfirmingGuestId(null);
    }
  };

  const openAddCustomer = (): void => {
    setEditingCustomer(null);
    setFullName("");
    setPhoneNumber("");
    setNotes("");
    setPassword("");
    setCustomerModalOpen(true);
  };

  const openEditCustomer = (c: UserDetail): void => {
    setEditingCustomer(c);
    setFullName(c.full_name);
    setPhoneNumber(c.phone_number);
    setNotes(c.notes || "");
    setPassword("");
    setCustomerModalOpen(true);
  };

  const handleSaveCustomer = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (customerFlight.current) return;
    if (editingCustomer && user?.role === "STAFF" && otherStaffCustomerIds.has(editingCustomer.id)) {
      setError("Bạn chỉ có thể sửa hồ sơ khách đang phụ trách.");
      return;
    }

    customerFlight.current = true;
    setSavingCustomer(true);
    setError(null);
    try {
      if (editingCustomer) {
        const updated = await updateCustomer(editingCustomer.id, {
          full_name: fullName.trim(),
          notes: notes.trim() || null,
          ...(password.trim() ? { password: password.trim() } : {}),
        });
        setCustomers((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
        if (selectedCustomer?.id === updated.id) {
          selectCustomer(updated);
        }
        await loadCustomers(listQuery.current);
      } else {
        const created = await createCustomer({
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim(),
          notes: notes.trim() || null,
          password: password.trim() || undefined,
        });
        setSearchQuery(created.phone_number);
        await loadCustomers(created.phone_number);
        selectCustomer(created);
        detail.open();
      }
      setCustomerModalOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thông tin khách hàng thất bại");
    } finally {
      customerFlight.current = false;
      setSavingCustomer(false);
    }
  };

  const matchingGuestRequests = React.useMemo(() => {
    if (!selectedCustomer) return [];
    return guestRequests.filter((r) => r.phone_number === selectedCustomer.phone_number);
  }, [guestRequests, selectedCustomer]);

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Khách hàng</h1>
          <p className="text-xs text-muted-foreground">
            Tra cứu hồ sơ tình trạng da, lịch sử các lần đến spa và hỗ trợ đặt lịch cho khách
          </p>
        </div>
        <Button size="sm" onClick={openAddCustomer}>
          <Plus className="h-4 w-4" />
          Thêm khách hàng mới
        </Button>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-12">
        <div ref={detail.listRef} className={cn("min-w-0 lg:col-span-5", detail.detailOpen && "hidden lg:block")}>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Danh sách Khách hàng</CardTitle>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void loadCustomers(searchQuery);
                }}
                className="mt-2 flex gap-2"
              >
                <div className="relative min-w-0 flex-1">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Tìm theo Tên hoặc Số điện thoại..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Button type="submit" variant="secondary" size="sm">Tìm</Button>
              </form>
            </CardHeader>
            <CardContent data-list-scroll className="max-h-[540px] divide-y divide-border overflow-y-auto pt-0">
              {loading ? (
                <p className="py-8 text-center text-xs text-muted-foreground">Đang tải khách hàng...</p>
              ) : error && customers.length === 0 ? (
                <Button variant="outline" onClick={() => void loadCustomers(listQuery.current)}>Thử tải lại khách</Button>
              ) : customers.length === 0 ? (
                <p className="py-8 text-center text-xs text-muted-foreground">Không tìm thấy khách hàng nào.</p>
              ) : (
                customers.map((c) => {
                  const isSelected = selectedCustomer?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-3 transition",
                        isSelected ? "bg-primary/10 font-medium" : "hover:bg-muted/60"
                      )}
                    >
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={(event) => {
                          selectCustomer(c);
                          detail.open(event.currentTarget);
                        }}
                        className="min-w-0 flex-1 py-1 text-left"
                      >
                        <p className="text-sm font-semibold text-foreground">{c.full_name}</p>
                        <p className="text-xs text-muted-foreground">SĐT: {c.phone_number}</p>
                        {c.notes && <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">Ghi chú: {c.notes}</p>}
                      </button>
                      {(!user || user.role === "ADMIN" || !otherStaffCustomerIds.has(c.id)) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditCustomer(c);
                          }}
                          title="Sửa thông tin"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  );
                })
              )}
              {!loading && (
                <div className="space-y-2 pt-3 text-sm">
                  <p>Đã tải {customers.length} khách{nextOffset !== null ? " — còn kết quả" : ""}.</p>
                  {nextOffset !== null && (
                    <Button type="button" variant="outline" disabled={moreLoading} onClick={() => void loadCustomers(listQuery.current, true)}>
                      {moreLoading ? "Đang tải thêm..." : "Tải thêm khách"}
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className={cn("min-w-0 lg:col-span-7", !detail.detailOpen && "hidden lg:block")}>
          <div className="p-3 pb-0 lg:hidden">
            <Button variant="outline" onClick={detail.back}>Quay lại danh sách khách</Button>
          </div>
          {!selectedCustomer ? (
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <UserIcon className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">Chọn 1 khách hàng bên trái để xem hồ sơ &amp; lịch sử</p>
            </CardContent>
          ) : (
            <>
              <CardHeader className="flex min-w-0 flex-col gap-3 border-b border-border sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="min-w-0 max-w-full text-lg [overflow-wrap:anywhere]">
                      {selectedCustomer.full_name}
                    </CardTitle>
                    {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id) && (
                      <Badge variant="outline" className="gap-1 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                        <Lock className="h-3 w-3" />
                        Thuộc KTV khác quản lý
                      </Badge>
                    )}
                  </div>
                  <CardDescription>
                    SĐT: <strong>{selectedCustomer.phone_number}</strong> • Tạo lúc: {formatDateTimeVN(selectedCustomer.created_at)}
                  </CardDescription>
                  <p className="mt-1.5 text-xs text-slate-700">
                    <strong>Ghi chú da / sức khỏe:</strong>{" "}
                    {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id)
                      ? "🔒 Bảo mật (Chỉ KTV phụ trách và Quản lý mới được xem)"
                      : selectedCustomer.notes || "Chưa có ghi chú"}
                  </p>
                </div>

                {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id) ? (
                  <Badge variant="outline" className="gap-1 bg-amber-50 px-2.5 py-1 text-xs text-amber-700">
                    <Lock className="h-3.5 w-3.5" />
                    Chỉ xem (Không được sửa)
                  </Badge>
                ) : (
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Link
                      className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border px-3 text-sm font-semibold"
                      href={"/admin/bookings?customer_id=" + selectedCustomer.id}
                    >
                      <CalendarPlus className="h-4 w-4" />
                      + Tạo buổi hẹn mới tại quầy
                    </Link>
                    {user?.role === "ADMIN" && (
                      <Link
                        className="inline-flex min-h-11 items-center rounded-lg border px-3 text-sm font-semibold"
                        onClick={() =>
                          sessionStorage.setItem(
                            "spaos_crm_return_" + user?.tenant_id + "_" + user?.id,
                            JSON.stringify({ id: selectedCustomer.id, q: searchQuery, y: window.scrollY, at: Date.now() })
                          )
                        }
                        href={"/admin/payments?customer_id=" + selectedCustomer.id}
                      >
                        Xem khoản cần thu
                      </Link>
                    )}
                    <Button variant="outline" size="sm" onClick={() => openEditCustomer(selectedCustomer)}>
                      <Edit2 className="h-3.5 w-3.5" />
                      Sửa hồ sơ / Mật khẩu
                    </Button>
                  </div>
                )}
              </CardHeader>

              <CardContent className="space-y-4 pt-4">
                {matchingGuestRequests.length > 0 && (
                  <div className="space-y-3 rounded-xl border border-amber-300 bg-amber-50/70 p-4">
                    <p className="text-sm font-bold text-amber-900">
                      Khách đang có yêu cầu đặt lịch chờ xác nhận ({matchingGuestRequests.length})
                    </p>
                    {matchingGuestRequests.map((req) => {
                      const svcLabel = req.service_ids
                        .map((id) => services.find((s) => s.id === id)?.name || "Dịch vụ")
                        .join(", ");
                      const stfLabel = req.staff_id
                        ? owners.find((s) => s.id === req.staff_id)?.full_name || "KTV đã chọn"
                        : "Spa tự sắp xếp";
                      const prefillHref =
                        `/admin/bookings?customer_id=${encodeURIComponent(selectedCustomer.id)}` +
                        `&service_ids=${encodeURIComponent(req.service_ids.join(","))}` +
                        (req.staff_id ? `&staff_id=${encodeURIComponent(req.staff_id)}` : "") +
                        `&start_time=${encodeURIComponent(req.start_time)}` +
                        (req.note ? `&note=${encodeURIComponent(req.note)}` : "");
                      return (
                        <div key={req.id} className="space-y-2 rounded-lg border border-amber-200 bg-card p-3 text-xs">
                          <p className="font-semibold text-foreground">{formatDateTimeVN(req.start_time)}</p>
                          <p className="text-muted-foreground">
                            Dịch vụ khách đã chọn: <strong className="text-foreground">{svcLabel}</strong> · KTV:{" "}
                            <strong className="text-foreground">{stfLabel}</strong>
                          </p>
                          {req.note && <p className="text-muted-foreground">Ghi chú: {req.note}</p>}
                          <div className="flex flex-wrap gap-2 pt-1">
                            <Button
                              size="sm"
                              disabled={confirmingGuestId === req.id}
                              onClick={() => void handleConfirmGuestRequest(req, selectedCustomer.id)}
                            >
                              {confirmingGuestId === req.id ? "Đang xác nhận..." : "Xác nhận ngay theo lựa chọn của khách"}
                            </Button>
                            <Link
                              href={prefillHref}
                              className="inline-flex min-h-9 items-center rounded-md border px-3 text-xs font-semibold hover:bg-accent"
                            >
                              Mở trong form Tạo lịch (điền sẵn)
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <CustomerVisits key={selectedCustomer.id + ":" + confirmingGuestId} customerId={selectedCustomer.id} />

                {user?.role === "ADMIN" && (
                  <div className="space-y-2 border-t pt-3">
                    <Label htmlFor="customerOwner">KTV phụ trách hồ sơ</Label>
                    <select
                      id="customerOwner"
                      value={ownerId}
                      onChange={(e) => setOwnerId(e.target.value)}
                      className="h-11 min-w-0 w-full rounded-md border px-3 text-base sm:h-9 sm:text-sm"
                    >
                      <option value="">Chưa phân công</option>
                      {owners.filter((staff) => staff.is_active).map((staff) => (
                        <option key={staff.id} value={staff.id}>{staff.full_name}</option>
                      ))}
                    </select>
                    <Button size="sm" disabled={assigning} onClick={() => void handleAssign()}>
                      {assigning ? "Đang chuyển..." : "Chuyển người phụ trách"}
                    </Button>
                  </div>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>

      <Modal
        open={customerModalOpen}
        onClose={() => setCustomerModalOpen(false)}
        pending={savingCustomer}
        dirty={editingCustomer ? fullName !== editingCustomer.full_name || notes !== (editingCustomer.notes || "") || !!password : !!fullName || !!phoneNumber || !!notes || !!password}
        title={editingCustomer ? "Cập nhật hồ sơ Khách hàng" : "Thêm Khách hàng mới"}
      >
        <form onSubmit={(e) => void handleSaveCustomer(e)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="custName">Họ và tên khách hàng</Label>
            <Input
              id="custName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Nguyễn Thu Trang"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="custPhone">Số điện thoại</Label>
            <Input
              id="custPhone"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0901234567"
              disabled={Boolean(editingCustomer)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="custPwd">
              {editingCustomer
                ? "Đặt mật khẩu mới cho khách (Để trống nếu không đổi)"
                : "Mật khẩu đăng nhập App (Để trống hệ thống tự sinh)"}
            </Label>
            <Input
              id="custPwd"
              type="password"
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Tùy chọn (>= 6 ký tự)"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="custNotes">Ghi chú tình trạng da / dị ứng / sở thích</Label>
            <Textarea
              id="custNotes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Da nhạy cảm, thích lực massage nhẹ..."
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="submit" disabled={savingCustomer}>
              {savingCustomer ? "Đang lưu..." : "Lưu thông tin"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
