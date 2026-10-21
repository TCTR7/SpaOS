import { apiErrorMessage } from "./api-error-message";
export interface OperatorIdentity { id: string; full_name: string; phone_number: string }
export interface OwnerProvision {
  id: string; tenant_id: string; owner_user_id: string; branch_name: string;
  owner_name: string; phone_number: string; created_at: string;
}
export interface OwnerCreate {
  request_id: string; branch_name: string; owner_full_name: string; phone_number: string; password: string; theme_color?: string;
}
const KEY = "spaos_operator_token";
const BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
export function clearOperatorToken(): void { window.sessionStorage.removeItem(KEY); }
export async function operatorRequest<T>(path: string, body?: unknown): Promise<T> {
  const token = typeof window === "undefined" ? null : window.sessionStorage.getItem(KEY);
  const response = await fetch(BASE + "/operator" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401 && path !== "/login") {
      clearOperatorToken(); window.location.replace("/operator/login");
    }
    const data = await response.json().catch(() => null) as { detail?: unknown } | null;
    const detail = apiErrorMessage(response.status, data?.detail);
    throw new OperatorError(response.status, detail);
  }
  return await response.json() as T;
}
export class OperatorError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function operatorLogin(phone_number: string, password: string): Promise<void> {
  const result = await operatorRequest<{access_token: string}>("/login", {phone_number,password});
  window.sessionStorage.setItem(KEY, result.access_token);
}
