"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useAnimate, useReducedMotion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useApp } from "@/components/AppContext";
import { EyeIcon, EyeOffIcon, LockIcon, SparkIcon, StatusIcon, UserIcon } from "@/components/icons";
import { Checkbox } from "@/components/ui";
import { messageOf } from "@/lib/api";

// Đăng nhập bằng tài khoản doanh nghiệp cấp. KHÔNG có đăng ký tự do (CLAUDE.md mục 1–2, 9.4).
// "Ghi nhớ" chỉ lưu TÊN đăng nhập trên máy này (không giữ phiên); mật khẩu không bao giờ lưu ở trình duyệt.
const REMEMBER_KEY = "p113.lastUser";

const schema = z.object({
  username: z.string().trim().min(1, "Nhập tên đăng nhập.").max(64),
  password: z.string().min(1, "Nhập mật khẩu.").max(256),
});
type LoginValues = z.infer<typeof schema>;

/** Chỉ quay lại đường dẫn nội bộ (chặn chuyển hướng ra trang ngoài qua ?next=). */
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/";
}

function readRemembered(): string {
  try {
    return localStorage.getItem(REMEMBER_KEY) ?? "";
  } catch {
    return "";
  }
}

function remember(username: string | null): void {
  try {
    if (username) localStorage.setItem(REMEMBER_KEY, username);
    else localStorage.removeItem(REMEMBER_KEY);
  } catch {
    // trình duyệt chặn lưu trữ: bỏ qua
  }
}

function LoginForm() {
  const { auth, login } = useApp();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [keep, setKeep] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [scope, animate] = useAnimate<HTMLFormElement>();
  const reduceMotion = useReducedMotion();
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(schema), defaultValues: { username: "", password: "" } });

  useEffect(() => {
    const first = setTimeout(() => {
      const saved = readRemembered();
      if (saved) {
        if (!getValues("username")) setValue("username", saved); // người dùng đã gõ trước thì giữ nguyên
        setKeep(true);
      }
    }, 0);
    return () => clearTimeout(first);
  }, [getValues, setValue]);

  // Đã đăng nhập (mở lại tab, bấm Back) → về trang đang cần
  useEffect(() => {
    if (auth === "in") router.replace(next);
  }, [auth, next, router]);

  /** Rung nhẹ khi báo lỗi (CLAUDE.md 9.2); tắt khi người dùng chọn giảm chuyển động. */
  function shake() {
    if (!reduceMotion && scope.current) animate(scope.current, { x: [0, -8, 8, -6, 6, -3, 0] }, { duration: 0.4 });
  }

  async function onValid({ username, password }: LoginValues) {
    setError("");
    try {
      await login(username, password);
      remember(keep ? username.toLowerCase() : null);
      setValue("password", "");
      router.replace(next);
    } catch (exc) {
      setError(messageOf(exc)); // backend trả thông báo chung, không lộ tài khoản có tồn tại hay không
      shake();
    }
  }

  return (
    // method="post": nếu bấm trước khi trang sẵn sàng (chưa hydrate), mật khẩu không bao giờ lọt lên URL
    <form
      ref={scope}
      className="login-card"
      method="post"
      onSubmit={(event) => handleSubmit(onValid, shake)(event)}
      aria-labelledby="login-title"
      noValidate
    >
      <div className="login-brand">
        <SparkIcon size={18} />
        <span>P-113 Agent Studio</span>
      </div>
      <h1 id="login-title">Đăng nhập</h1>
      <p className="login-sub">Dùng tài khoản doanh nghiệp được cấp.</p>

      <div className="login-field">
        <label htmlFor="login-user" className="sr-only">
          Tên đăng nhập
        </label>
        <span className="login-field-lead" aria-hidden>
          <UserIcon size={20} />
        </span>
        <input
          id="login-user"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="Tên đăng nhập"
          maxLength={64}
          aria-invalid={Boolean(errors.username || error) || undefined}
          aria-describedby={errors.username ? "login-user-error" : undefined}
          {...register("username")}
        />
        {errors.username && (
          <p id="login-user-error" className="login-field-error">
            {errors.username.message}
          </p>
        )}
      </div>

      <div className="login-field">
        <label htmlFor="login-password" className="sr-only">
          Mật khẩu
        </label>
        <span className="login-field-lead" aria-hidden>
          <LockIcon size={20} />
        </span>
        <input
          id="login-password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          placeholder="Mật khẩu"
          maxLength={256}
          aria-invalid={Boolean(errors.password || error) || undefined}
          aria-describedby={errors.password ? "login-password-error" : undefined}
          {...register("password")}
        />
        <button
          type="button"
          className="login-eye"
          onClick={() => setShowPassword(!showPassword)}
          aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          aria-pressed={showPassword}
        >
          {showPassword ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
        </button>
        {errors.password && (
          <p id="login-password-error" className="login-field-error">
            {errors.password.message}
          </p>
        )}
      </div>

      <Checkbox checked={keep} onChange={setKeep}>
        Ghi nhớ tên đăng nhập trên máy này
      </Checkbox>

      {error && (
        <p className="login-error" role="alert">
          <StatusIcon tone="danger" size={16} /> {error}
        </p>
      )}

      <button type="submit" className="login-btn" disabled={isSubmitting} aria-busy={isSubmitting || undefined}>
        {isSubmitting ? (
          <>
            <StatusIcon tone="running" size={18} /> Đang đăng nhập…
          </>
        ) : (
          "Đăng nhập"
        )}
      </button>

      <p className="login-foot">
        Quên mật khẩu? <strong>Liên hệ quản trị viên</strong>.
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="login-page">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
