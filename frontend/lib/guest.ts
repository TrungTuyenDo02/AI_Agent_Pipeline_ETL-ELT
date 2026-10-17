// Chế độ khách: chạy toàn bộ giao diện bằng dữ liệu mẫu trong trình duyệt, KHÔNG gọi backend.
// Cờ và vai khách lưu ở sessionStorage (tải lại trang vẫn giữ, đóng tab là hết). Dữ liệu mẫu: lib/demo/.
// File này nhỏ và nạp sẵn; bộ dữ liệu mẫu chỉ nạp (import động) khi đã vào chế độ khách.

import type { CurrentUser } from "./types";

export type GuestRole = "engineer" | "reviewer";

const GUEST_KEY = "p113.guest";
export const DEMO_STATE_KEY = "p113.demo.state";

/** Trình duyệt chặn sessionStorage: vẫn chạy được trong lần mở trang này (mất khi tải lại). */
const memory = new Map<string, string>();

export function readSession(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return memory.get(key) ?? null;
  }
}

export function writeSession(key: string, value: string | null): void {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    if (value === null) memory.delete(key);
    else memory.set(key, value);
  }
}

/** Vai của khách; null = không ở chế độ khách. */
export function guestRole(): GuestRole | null {
  if (typeof window === "undefined") return null;
  const value = readSession(GUEST_KEY);
  return value === "engineer" || value === "reviewer" ? value : null;
}

export function setGuestRole(role: GuestRole): void {
  writeSession(GUEST_KEY, role);
}

/** Thoát chế độ khách: xóa cờ và toàn bộ dữ liệu mẫu đã đổi. */
export function clearGuest(): void {
  writeSession(GUEST_KEY, null);
  writeSession(DEMO_STATE_KEY, null);
}

/** "Làm lại từ đầu": xóa dữ liệu mẫu đã đổi, giữ chế độ khách (vai về Engineer). */
export function resetGuestData(): void {
  writeSession(DEMO_STATE_KEY, null);
  setGuestRole("engineer");
}

/** Người dùng giả của chế độ khách (tên khác nhau để Reviewer duyệt được yêu cầu do Engineer tạo). */
export const GUEST_USERS: Record<GuestRole, CurrentUser> = {
  engineer: { id: -1, name: "khach", display_name: "Khách", role: "engineer", department_id: 1 },
  reviewer: { id: -2, name: "khach-duyet", display_name: "Khách", role: "reviewer", department_id: 1 },
};

/** Mã lần chạy do khách tự tạo (khác bộ mẫu dựng sẵn): để biết khách đã tự đi hết quy trình chưa. */
export const GUEST_RUN_PREFIX = "mau-moi-";

export const GUEST_NOTE = "Kết quả là mẫu dựng sẵn, không do AI chạy thật. Đăng nhập để chạy thật.";

let guarded = false;

/**
 * Lưới an toàn: ở chế độ khách, mọi `fetch` tới backend (`apiUrl` hoặc đường dẫn /api/) bị chặn và báo lỗi rõ trong
 * console. Lớp gọi API (lib/api.ts) vốn không gửi gì khi là khách; lưới này bắt mọi lời gọi lọt ra ngoài lớp đó.
 */
export function installNetworkGuard(apiUrl: string): void {
  if (guarded || typeof window === "undefined") return;
  guarded = true;
  const original = window.fetch.bind(window);
  const backend = apiUrl ? new URL(apiUrl, window.location.href) : null;
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (guestRole()) {
      const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const url = new URL(raw, window.location.href);
      const toBackend =
        url.pathname.startsWith("/api/") ||
        (backend !== null && url.origin === backend.origin && url.origin !== window.location.origin);
      if (toBackend) {
        const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
        console.error(
          `[Chế độ khách] Đã chặn lệnh gọi mạng tới backend: ${method} ${url.href}. ` +
            "Chế độ khách chỉ dùng dữ liệu mẫu trong trình duyệt; đăng nhập để dùng máy chủ thật.",
        );
        return Promise.reject(new TypeError("Chế độ khách: đã chặn lệnh gọi tới backend."));
      }
    }
    return original(input, init);
  };
}
