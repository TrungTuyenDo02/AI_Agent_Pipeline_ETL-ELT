"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { API_URL, apiGet, apiPost, UNAUTHORIZED_EVENT } from "@/lib/api";
import {
  clearGuest,
  guestRole,
  GUEST_USERS,
  installNetworkGuard,
  resetGuestData,
  setGuestRole,
  type GuestRole,
} from "@/lib/guest";
import type { AgentStatus, CurrentUser, Role, RunRecord } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

export type ThemeChoice = "system" | "light" | "dark";
export const THEME_LABELS: Record<ThemeChoice, string> = { system: "Theo máy", light: "Sáng", dark: "Tối" };
export const THEME_ORDER: ThemeChoice[] = ["system", "light", "dark"];
const THEME_KEY = "p113.theme";
export const RUNS_LIMIT = 100; // API trả tối đa 100 lần chạy mới nhất

/** checking = đang hỏi /auth/me; out = chưa đăng nhập (hoặc phiên hết hạn / đã đăng xuất). */
export type AuthState = "checking" | "in" | "out";

interface AppState {
  status: AgentStatus | null;
  statusError: string;
  /** Người dùng của phiên đăng nhập; null khi chưa đăng nhập. Vai trò thật do backend kiểm. */
  user: CurrentUser | null;
  auth: AuthState;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Chế độ khách: dữ liệu mẫu trong trình duyệt, không gọi backend (lib/guest.ts). */
  guest: boolean;
  enterGuest: () => void;
  switchGuestRole: (role: GuestRole) => void;
  /** "Làm lại từ đầu": xóa mọi thao tác trên dữ liệu mẫu rồi tải lại trang chủ. */
  resetGuest: () => void;
  /** Thoát chế độ khách (xóa sạch dữ liệu mẫu) rồi tải lại ở `to`. */
  exitGuest: (to?: string) => void;
  theme: ThemeChoice;
  setTheme: (theme: ThemeChoice) => void;
  dark: boolean;
  /** Danh sách lần chạy dùng chung (chuông, trang chủ, tìm kiếm, bảng) — một lần hỏi API cho cả app. */
  runs: RunRecord[] | null;
  runsError: string;
  refreshRuns: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

function readTheme(): ThemeChoice {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

function useSystemDark(): boolean {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setDark(query.matches);
    const first = setTimeout(update, 0);
    query.addEventListener("change", update);
    return () => {
      clearTimeout(first);
      query.removeEventListener("change", update);
    };
  }, []);
  return dark;
}

function useStoredTheme(): [ThemeChoice, (t: ThemeChoice) => void] {
  const [theme, setThemeState] = useState<ThemeChoice>("system");
  useEffect(() => {
    const first = setTimeout(() => setThemeState(readTheme()), 0);
    return () => clearTimeout(first);
  }, []);
  const setTheme = useCallback((next: ThemeChoice) => {
    try {
      if (next === "system") localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, next);
    } catch {
      // không lưu được: chỉ áp dụng trong phiên này
    }
    if (next === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = next;
    setThemeState(next);
  }, []);
  return [theme, setTheme];
}

/** Tải lại HẲN trang (không dùng router): mọi dữ liệu mẫu đang giữ trong bộ nhớ (các lần hỏi định kỳ) biến mất. */
function reloadAt(to: string): void {
  window.location.assign(to);
}

/** Thoát chế độ khách: xóa cờ và dữ liệu mẫu rồi tải lại ở `to`. */
function leaveGuest(to: string): void {
  clearGuest();
  reloadAt(to);
}

/**
 * Phiên đăng nhập: hỏi /auth/me một lần; API trả 401 ở bất kỳ đâu → về trạng thái chưa đăng nhập.
 * Chế độ khách (cờ trong sessionStorage, hoặc mở /demo): không hỏi /auth/me, dùng người dùng giả.
 */
function useSession() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [auth, setAuth] = useState<AuthState>("checking");
  const [guest, setGuest] = useState(false);
  const activateGuest = useCallback((role: GuestRole) => {
    setGuestRole(role);
    installNetworkGuard(API_URL);
    setUser(GUEST_USERS[role]);
    setGuest(true);
    setAuth("in");
  }, []);
  useEffect(() => {
    let alive = true;
    const signedOut = () => {
      if (guestRole()) return; // khách không có phiên máy chủ để hết hạn
      setUser(null);
      setAuth("out");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, signedOut);
    const role = guestRole() ?? (window.location.pathname.startsWith("/demo") ? "engineer" : null);
    const first = setTimeout(() => {
      if (role) {
        activateGuest(role);
        return;
      }
      apiGet<CurrentUser>("/auth/me")
        .then((me) => {
          if (!alive || guestRole()) return; // đã vào chế độ khách trong lúc chờ
          setUser(me);
          setAuth("in");
        })
        .catch(() => {
          if (alive && !guestRole()) setAuth("out");
        });
    }, 0);
    return () => {
      alive = false;
      clearTimeout(first);
      window.removeEventListener(UNAUTHORIZED_EVENT, signedOut);
    };
  }, [activateGuest]);
  const login = useCallback(async (username: string, password: string) => {
    await apiPost("/auth/login", { username, password });
    setUser(await apiGet<CurrentUser>("/auth/me"));
    setAuth("in");
  }, []);
  const logout = useCallback(async () => {
    if (guestRole()) return leaveGuest("/login");
    try {
      await apiPost("/auth/logout", {});
    } finally {
      setUser(null);
      setAuth("out");
    }
  }, []);
  const enterGuest = useCallback(() => activateGuest(guestRole() ?? "engineer"), [activateGuest]);
  const switchGuestRole = useCallback((role: GuestRole) => {
    if (!guestRole()) return;
    setGuestRole(role);
    setUser(GUEST_USERS[role]);
  }, []);
  const resetGuest = useCallback(() => {
    resetGuestData();
    reloadAt("/");
  }, []);
  const exitGuest = useCallback((to = "/login") => leaveGuest(to), []);
  return { user, auth, login, logout, guest, enterGuest, switchGuestRole, resetGuest, exitGuest };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const { user, auth, login, logout, guest, enterGuest, switchGuestRole, resetGuest, exitGuest } = useSession();
  const signedIn = auth === "in";
  // Chưa đăng nhập thì không hỏi API (tránh loạt 401)
  const polled = usePoll<AgentStatus>(signedIn ? "/status" : null, 30000);
  const runs = usePoll<RunRecord[]>(signedIn ? `/runs?limit=${RUNS_LIMIT}` : null, 6000);
  const [theme, setTheme] = useStoredTheme();
  const systemDark = useSystemDark();
  const dark = theme === "dark" || (theme === "system" && systemDark);
  const value = useMemo<AppState>(
    () => ({
      status: polled.data,
      statusError: polled.error,
      user,
      auth,
      login,
      logout,
      guest,
      enterGuest,
      switchGuestRole,
      resetGuest,
      exitGuest,
      theme,
      setTheme,
      dark,
      runs: runs.data,
      runsError: runs.error,
      refreshRuns: runs.refresh,
    }),
    [
      polled.data,
      polled.error,
      user,
      auth,
      login,
      logout,
      guest,
      enterGuest,
      switchGuestRole,
      resetGuest,
      exitGuest,
      theme,
      setTheme,
      dark,
      runs.data,
      runs.error,
      runs.refresh,
    ],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const state = useContext(AppContext);
  if (!state) throw new Error("useApp phải nằm trong AppProvider");
  return state;
}

/** Người dùng hiện tại có đúng vai trò không (chỉ để ẩn/khóa nút; phân quyền thật ở backend). */
export function useHasRole(role: Role): boolean {
  return useApp().user?.role === role;
}
