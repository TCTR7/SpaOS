/** Keep useful business errors while hiding infrastructure and validation internals. */
export function apiErrorMessage(status: number, detail: unknown): string {
  const fallback = status === 401 ? "Thông tin đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại."
    : status === 403 ? "Bạn chưa thể thực hiện thao tác này. Vui lòng liên hệ spa để được hỗ trợ."
    : status === 404 ? "Không tìm thấy thông tin. Vui lòng tải lại và thử lại."
    : status === 409 ? "Thông tin đã thay đổi hoặc bị trùng. Vui lòng kiểm tra lại."
    : status === 422 ? "Thông tin chưa hợp lệ. Vui lòng kiểm tra các mục đã nhập."
    : status === 429 ? "Bạn thao tác quá nhanh. Vui lòng chờ một chút rồi thử lại."
    : "Chưa thể xử lý yêu cầu. Vui lòng thử lại sau.";

  let raw = "";
  if (typeof detail === "string") {
    raw = detail;
  } else if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "object" && first !== null && "msg" in first) {
      raw = String(first.msg).replace(/^Value error,\s*/i, "");
    }
  }

  if (status >= 500 || !raw) return fallback;
  const message = raw.trim().replace(/PENDING\/CONFIRMED/g, "đang chờ hoặc đã xác nhận");
  if (!/[À-ỹ]/.test(message) || /customer_id|staff_id|service_id|is_package|PENDING|CONFIRMED|COMPLETED|IN_PROGRESS|CANCELLED|NO_SHOW|tenant|slug|jwt|token|vapid|rls|sql|database|traceback|exception|constraint|validation|value_error|uuid|deployment|backend|frontend|service\.worker|ADMIN|STAFF|CUSTOMER|\bAPI\b/i.test(message)) return fallback;
  return message;
}
