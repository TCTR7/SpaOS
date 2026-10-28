"use client";

import * as React from "react";
import Link from "@/components/spa-link";
import { CustomerVisits } from "@/components/admin/customer-visits";
import { PackageHistory } from "@/components/package-history";
import { RecoveryLink } from "@/components/admin/recovery-link";
import { useBranchGuard } from "@/lib/branch-guard";
import { useListDetail } from "@/lib/use-list-detail";
import {
  Edit2,
  Lock,
  PackagePlus,
  Plus,
  Search,
  Ticket,
  User as UserIcon,
} from "lucide-react";
import {
  createCustomer,
  fetchStaffList,
  assignCustomer,
  fetchCustomerPackages,
  fetchCustomerPage,
  fetchServices,
  issueCustomerPackage,
  updateCustomer,
} from "@/lib/api";
import { useAdminAuth } from "@/components/admin/auth-context";
import type {
  CustomerPackageItem,
  ServiceItem,
  UserDetail,
} from "@/lib/types";
import { cn, formatCurrency, formatDateTimeVN } from "@/lib/utils";
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
  const { user, tenant } = useAdminAuth();
  const detail = useListDetail();
  const customerRequest = React.useRef(0);
  const packageRequest = React.useRef(0);
  const selectedId = React.useRef<string | null>(null);
  const listQuery = React.useRef("");
  const [nextOffset, setNextOffset] = React.useState<number | null>(null);
  const [moreLoading, setMoreLoading] = React.useState(false);
  const [packagesError, setPackagesError] = React.useState<string | null>(null);
  const [servicesError, setServicesError] = React.useState<string | null>(null);
  const customerFlight = React.useRef(false);
  const packageFlight = React.useRef(false);

  const [owners, setOwners] = React.useState<UserDetail[]>([]);
  const [ownerId, setOwnerId] = React.useState<string>("");
  const [assigning, setAssigning] = React.useState(false);
  const [customers, setCustomers] = React.useState<UserDetail[]>([]);
  const [packageServices, setPackageServices] = React.useState<ServiceItem[]>(
    []
  );
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  const [selectedCustomer, setSelectedCustomer] =
    React.useState<UserDetail | null>(null);
  useBranchGuard(!!selectedCustomer && ownerId !== (selectedCustomer.assigned_staff_id || ""), assigning);
  const selectCustomer = React.useCallback((customer: UserDetail | null): void => {
    // Initialize the owner in the same render as the selected profile. A later
    // effect could overwrite a selection the user has already made.
    if (selectedId.current !== (customer?.id || null)) { setPackages([]); setPackagesError(null); setPackagesLoading(!!customer); }
    selectedId.current = customer?.id || null;
    setSelectedCustomer(customer);
    setOwnerId(customer?.assigned_staff_id || "");
  }, []);
  const [packages, setPackages] = React.useState<CustomerPackageItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [packagesLoading, setPackagesLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [otherStaffCustomerIds, setOtherStaffCustomerIds] =
    React.useState<Set<string>>(() => new Set());

  // Create / Edit Customer Modal
  const [customerModalOpen, setCustomerModalOpen] =
    React.useState<boolean>(false);
  const [editingCustomer, setEditingCustomer] =
    React.useState<UserDetail | null>(null);
  const [fullName, setFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [savingCustomer, setSavingCustomer] = React.useState<boolean>(false);

  // Issue Package Modal
  const [pkgModalOpen, setPkgModalOpen] = React.useState<boolean>(false);
  const [issueTarget, setIssueTarget] = React.useState<UserDetail | null>(null);
  const [pkgServiceId, setPkgServiceId] = React.useState<string>("");
  const [pkgName, setPkgName] = React.useState<string>("");
  const [pkgSessions, setPkgSessions] = React.useState<number>(10);
  const [pkgExpiry, setPkgExpiry] = React.useState<string>("");
  const [savingPackage, setSavingPackage] = React.useState<boolean>(false);

  const loadCustomers = React.useCallback(async (q = "", append = false): Promise<void> => {
    const request = ++customerRequest.current;
    if (append) setMoreLoading(true);
    else { setLoading(true); setCustomers([]); setNextOffset(null); listQuery.current = q; }
    setError(null);
    try {
      const page = await fetchCustomerPage({ q, limit: 50, offset: append ? nextOffset || 0 : 0 });
      if (request !== customerRequest.current) return;
      setCustomers((previous) => Array.from(new Map([...(append ? previous : []), ...page.items].map((c) => [c.id, c])).values()));
      setNextOffset(page.nextOffset);
      if (!append) selectCustomer(page.items.find((c) => c.id === selectedId.current) || page.items[0] || null);
    } catch (err) {
      if (request === customerRequest.current) setError(err instanceof Error ? err.message : "Không tải được khách hàng");
    } finally {
      if (request === customerRequest.current) { setLoading(false); setMoreLoading(false); }
    }
  }, [nextOffset, selectCustomer]);

  const loadPackageServices = React.useCallback(async (): Promise<void> => {
    setServicesError(null);
    try {
      const svcs = await fetchServices({ is_active: true, is_package: true });
      setPackageServices(svcs);
    } catch (err) {
      setServicesError(err instanceof Error ? err.message : "Không tải được danh mục thẻ");
    }
  }, []);

  const loadSelectedCustomerPackages = React.useCallback(async (customerId: string): Promise<void> => {
    if (selectedId.current !== customerId) return;
    const request = ++packageRequest.current;
    setPackagesLoading(true); setPackagesError(null); setPackages([]);
    try {
      const list = await fetchCustomerPackages(customerId);
      if (request === packageRequest.current && selectedId.current === customerId) setPackages(list);
    } catch (err) {
      if (request === packageRequest.current && selectedId.current === customerId)
        setPackagesError(err instanceof Error ? err.message : "Không tải được thẻ liệu trình");
    } finally {
      if (request === packageRequest.current && selectedId.current === customerId) setPackagesLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadCustomers("");
    void loadPackageServices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { customerRequest.current += 1; packageRequest.current += 1; };
  }, []);

  React.useEffect(() => {
    if (selectedCustomer) {
      void loadSelectedCustomerPackages(selectedCustomer.id);
    } else {
      packageRequest.current += 1; setPackages([]); setPackagesError(null); setPackagesLoading(false);
    }
  }, [selectedCustomer?.id, loadSelectedCustomerPackages]);

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
      setCustomers((prev) => prev.map((c) => c.id === updated.id ? updated : c));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể chuyển người phụ trách");
    } finally { setAssigning(false); }
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

  const handleSaveCustomer = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (customerFlight.current) return;
    if (
      editingCustomer &&
      user?.role === "STAFF" &&
      otherStaffCustomerIds.has(editingCustomer.id)
    ) {
      setError(
        "Bạn chỉ có thể sửa hồ sơ khách đang phụ trách."
      );
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
        });
        setCustomers((prev) =>
          prev.map((c) => (c.id === updated.id ? updated : c))
        );
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
        selectCustomer(created); detail.open();
      }
      setCustomerModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Lưu thông tin khách hàng thất bại"
      );
    } finally {
      customerFlight.current = false;
      setSavingCustomer(false);
    }
  };

  const openIssuePackageModal = (): void => {
    if (!selectedCustomer) return;
    setIssueTarget(selectedCustomer);
    if (
      selectedCustomer &&
      user?.role === "STAFF" &&
      otherStaffCustomerIds.has(selectedCustomer.id)
    ) {
      setError(
        "Bạn chỉ có thể cấp thẻ cho khách đang phụ trách."
      );
      return;
    }
    const firstPkg = packageServices[0];
    setPkgServiceId(firstPkg?.id || "");
    setPkgName(firstPkg?.name || "");
    setPkgSessions(firstPkg?.total_sessions || 10);
    setPkgExpiry("");
    setPkgModalOpen(true);
  };

  const handleIssuePackage = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (packageFlight.current || !issueTarget || !pkgServiceId) return;

    if (
      user?.role === "STAFF" &&
      otherStaffCustomerIds.has(issueTarget.id)
    ) {
      setError(
        "Bạn chỉ có thể cấp thẻ cho khách đang phụ trách."
      );
      return;
    }

    packageFlight.current = true;
    setSavingPackage(true);
    setError(null);
    try {
      const expiryISO = pkgExpiry
        ? new Date(`${pkgExpiry}T23:59:59+07:00`).toISOString()
        : null;
      await issueCustomerPackage({
        customer_id: issueTarget.id,
        service_id: pkgServiceId,
        package_name: pkgName.trim() || undefined,
        total_sessions: pkgSessions,
        expiry_date: expiryISO,
      });
      setPkgModalOpen(false);
      await loadSelectedCustomerPackages(issueTarget.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cấp thẻ liệu trình thất bại"
      );
    } finally {
      packageFlight.current = false;
      setSavingPackage(false);
    }
  };

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Khách hàng & Thẻ liệu trình
          </h1>
          <p className="text-xs text-muted-foreground">
            Tra cứu hồ sơ tình trạng da, lịch sử thẻ liệu trình và cấp gói liệu
            trình mới cho khách
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
        {/* Left column: Customer Search & List */}
        <div ref={detail.listRef} className={cn("min-w-0 lg:col-span-5", detail.detailOpen && "hidden lg:block")}><Card>
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
              <Button type="submit" variant="secondary" size="sm">
                Tìm
              </Button>
            </form>
          </CardHeader>
          <CardContent data-list-scroll className="max-h-[540px] overflow-y-auto divide-y divide-border pt-0">
            {loading ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Đang tải khách hàng...
              </p>
            ) : error && customers.length === 0 ? (
              <Button variant="outline" onClick={() => void loadCustomers(listQuery.current)}>Thử tải lại khách</Button>
            ) : customers.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Không tìm thấy khách hàng nào.
              </p>
            ) : (
              customers.map((c) => {
                const isSelected = selectedCustomer?.id === c.id;
                return (
                  <div
                    key={c.id}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-3 transition",
                      isSelected
                        ? "bg-primary/10 font-medium"
                        : "hover:bg-muted/60"
                    )}
                  >
                    <button type="button" aria-pressed={isSelected}
                      onClick={(event) => { selectCustomer(c); detail.open(event.currentTarget); }}
                      className="min-w-0 flex-1 text-left py-1">
                      <p className="text-sm font-semibold text-foreground">
                        {c.full_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        SĐT: {c.phone_number}
                      </p>
                      {c.notes && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
                          Ghi chú: {c.notes}
                        </p>
                      )}
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
            {!loading && <div className="space-y-2 pt-3 text-sm">
              <p>Đã tải {customers.length} khách{nextOffset !== null ? " — còn kết quả" : ""}.</p>
              {nextOffset !== null && <Button type="button" variant="outline" disabled={moreLoading} onClick={() => void loadCustomers(listQuery.current, true)}>{moreLoading ? "Đang tải thêm..." : "Tải thêm khách"}</Button>}
            </div>}
          </CardContent>
        </Card></div>

        {/* Right column: Selected Customer Profile & Treatment Packages */}
        <Card className={cn("min-w-0 lg:col-span-7", !detail.detailOpen && "hidden lg:block")}>
          <div className="p-3 pb-0 lg:hidden"><Button variant="outline" onClick={detail.back}>Quay lại danh sách khách</Button></div>
          {!selectedCustomer ? (
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <UserIcon className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">
                Chọn 1 khách hàng bên trái để xem Thẻ liệu trình
              </p>
            </CardContent>
          ) : (
            <>
              <CardHeader className="flex min-w-0 flex-col gap-3 border-b border-border sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="min-w-0 max-w-full text-lg [overflow-wrap:anywhere]">
                      {selectedCustomer.full_name}
                    </CardTitle>
                    {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id) && (
                      <Badge variant="outline" className="text-amber-700 bg-amber-50 gap-1 px-2 py-0.5 text-xs">
                        <Lock className="h-3 w-3" />
                        Thuộc KTV khác quản lý
                      </Badge>
                    )}
                  </div>
                  <CardDescription>
                    SĐT: <strong>{selectedCustomer.phone_number}</strong> • Tạo
                    lúc: {formatDateTimeVN(selectedCustomer.created_at)}
                  </CardDescription>
                  <p className="mt-1.5 text-xs text-slate-700">
                    <strong>Ghi chú da / sức khỏe:</strong>{" "}
                    {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id)
                      ? "🔒 Bảo mật (Chỉ KTV phụ trách và Quản lý mới được xem)"
                      : selectedCustomer.notes || "Chưa có ghi chú"}
                  </p>
                </div>

                {user?.role === "STAFF" && otherStaffCustomerIds.has(selectedCustomer.id) ? (
                  <Badge variant="outline" className="text-amber-700 bg-amber-50 gap-1 px-2.5 py-1 text-xs">
                    <Lock className="h-3.5 w-3.5" />
                    Chỉ xem (Không được sửa)
                  </Badge>
                ) : (
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Link className="inline-flex min-h-11 items-center rounded-lg border px-3 text-sm font-semibold" href={"/admin/bookings?customer_id=" + selectedCustomer.id}>Đặt lịch cho khách</Link>
                    {user?.role === "ADMIN" && <Link className="inline-flex min-h-11 items-center rounded-lg border px-3 text-sm font-semibold" href={"/admin/payments?customer_id=" + selectedCustomer.id}>Xem khoản cần thu</Link>}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditCustomer(selectedCustomer)}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                      Sửa hồ sơ
                    </Button>
                    <Button size="sm" disabled={!!servicesError} onClick={openIssuePackageModal}>
                      <PackagePlus className="h-4 w-4" />
                      Cấp thẻ liệu trình
                    </Button>
                  </div>
                )}
              </CardHeader>

              <CardContent className="pt-4 space-y-3">
                <CustomerVisits key={selectedCustomer.id} customerId={selectedCustomer.id} />
                {servicesError && <div role="alert"><p>{servicesError}</p><Button variant="outline" onClick={() => void loadPackageServices()}>Thử tải lại danh mục thẻ</Button></div>}
                {user?.role === "ADMIN" && (
                  <div className="space-y-2">
                    {tenant && <RecoveryLink key={selectedCustomer.id} customerId={selectedCustomer.id} slug={tenant.slug} />}
                    <Label htmlFor="customerOwner">KTV phụ trách hồ sơ</Label>
                    <select id="customerOwner" value={ownerId} onChange={(e) => setOwnerId(e.target.value)}
                      className="h-11 min-w-0 w-full rounded-md border px-3 text-base sm:h-9 sm:text-sm">
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

                <h4 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                  <Ticket className="h-4 w-4 text-primary" />
                  Thẻ liệu trình đang sở hữu ({packages.length})
                </h4>

                {packagesLoading ? (
                  <p className="py-6 text-center text-xs text-muted-foreground">
                    Đang tải thẻ liệu trình...
                  </p>
                ) : packagesError ? (
                  <div role="alert"><p>{packagesError}</p><Button variant="outline" onClick={() => void loadSelectedCustomerPackages(selectedCustomer.id)}>Thử tải lại thẻ</Button></div>
                ) : packages.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
                    Khách hàng này chưa có thẻ liệu trình nào. Nhấn &ldquo;Cấp
                    thẻ liệu trình&rdquo; để bán gói mới.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {packages.map((pkg) => {
                      const pct = Math.min(
                        100,
                        Math.round(
                          (pkg.used_sessions / Math.max(pkg.total_sessions, 1)) *
                            100
                        )
                      );
                      return (
                        <div
                          key={pkg.id}
                          className="rounded-xl border border-border bg-muted/20 p-4 space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-bold text-foreground">
                                {pkg.package_name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Ngày cấp: {formatDateTimeVN(pkg.created_at)}
                                {pkg.expiry_date &&
                                  ` • Hạn dùng: ${formatDateTimeVN(pkg.expiry_date)}`}
                              </p>
                            </div>
                            <Badge
                              variant={
                                pkg.status === "ACTIVE"
                                  ? "success"
                                  : pkg.status === "COMPLETED"
                                    ? "secondary"
                                    : "danger"
                              }
                            >
                              {{ ACTIVE: "Đang sử dụng", COMPLETED: "Đã dùng hết", EXPIRED: "Đã hết hạn" }[pkg.status]}
                            </Badge>
                          </div>

                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">Đã đặt trước: {pkg.reserved_sessions ?? 0} buổi · Các buổi đã đặt chưa được tính là đã dùng.</p>
                            <PackageHistory key={pkg.id} id={pkg.id} />
                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                              <span>
                                Đã thực hiện:{" "}
                                <strong>
                                  {pkg.used_sessions} / {pkg.total_sessions}{" "}
                                  buổi
                                </strong>
                              </span>
                              <span className="font-semibold text-primary">
                                Có thể đặt: {pkg.available_sessions ?? pkg.remaining_sessions} buổi
                              </span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>

      {/* Add / Edit Customer Modal */}
      <Modal
        open={customerModalOpen}
        onClose={() => setCustomerModalOpen(false)}
        pending={savingCustomer}
        dirty={editingCustomer ? fullName !== editingCustomer.full_name || notes !== (editingCustomer.notes || "") : !!fullName || !!phoneNumber || !!notes || !!password}
        title={
          editingCustomer
            ? "Cập nhật hồ sơ Khách hàng"
            : "Thêm Khách hàng mới"
        }
      >
        <form
          onSubmit={(e) => void handleSaveCustomer(e)}
          className="space-y-4"
        >
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

          {!editingCustomer && (
            <div className="space-y-1.5">
              <Label htmlFor="custPwd">
                Mật khẩu đăng nhập App (Để trống hệ thống tự sinh)
              </Label>
              <Input
                id="custPwd"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Tùy chọn (>= 6 ký tự)"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="custNotes">
              Ghi chú tình trạng da / dị ứng / sở thích
            </Label>
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

      {/* Issue Customer Package Modal */}
      <Modal
        open={pkgModalOpen}
        onClose={() => setPkgModalOpen(false)}
        pending={savingPackage}
        dirty={pkgServiceId !== (packageServices[0]?.id || "") || pkgName !== (packageServices.find((svc) => svc.id === pkgServiceId)?.name || "") || pkgSessions !== (packageServices.find((svc) => svc.id === pkgServiceId)?.total_sessions || 10) || !!pkgExpiry}
        title={`Cấp thẻ liệu trình mới — ${issueTarget?.full_name ?? ""}`}
        description="Chọn gói liệu trình để cấp thẻ cho khách."
      >
        <form onSubmit={(e) => void handleIssuePackage(e)} className="space-y-4">
          {packageServices.length === 0 ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
              Spa chưa có Dịch vụ nào thuộc loại Gói liệu trình (
              <code>is_package = true</code>). Hãy tạo Gói liệu trình trong mục{" "}
              <strong>Danh mục Dịch vụ</strong> trước.
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="pkgService">Chọn Gói liệu trình gốc</Label>
                <select
                  id="pkgService"
                  value={pkgServiceId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setPkgServiceId(id);
                    const found = packageServices.find((s) => s.id === id);
                    if (found) {
                      setPkgName(found.name);
                      setPkgSessions(found.total_sessions);
                    }
                  }}
                  className="h-11 min-w-0 w-full rounded-md border border-input bg-background px-3 text-base sm:h-9 sm:text-sm"
                  required
                >
                  {packageServices.map((svc) => (
                    <option key={svc.id} value={svc.id}>
                      {svc.name} ({svc.total_sessions} buổi •{" "}
                      {formatCurrency(svc.price)})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="pkgCustomName">Tên hiển thị trên thẻ</Label>
                <Input
                  id="pkgCustomName"
                  value={pkgName}
                  onChange={(e) => setPkgName(e.target.value)}
                  required
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="pkgSessions">Tổng số buổi</Label>
                  <Input
                    id="pkgSessions"
                    type="number"
                    min={1}
                    max={200}
                    value={pkgSessions}
                    onChange={(e) =>
                      setPkgSessions(parseInt(e.target.value || "1", 10))
                    }
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="pkgExpiry">Ngày hết hạn (Tùy chọn)</Label>
                  <Input
                    id="pkgExpiry"
                    type="date"
                    value={pkgExpiry}
                    onChange={(e) => setPkgExpiry(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="submit"
              disabled={savingPackage || packageServices.length === 0}
            >
              {savingPackage ? "Đang cấp thẻ..." : "Xác nhận cấp thẻ"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
