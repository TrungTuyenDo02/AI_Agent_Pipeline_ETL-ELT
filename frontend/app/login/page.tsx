"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useAnimate, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useApp } from "@/components/AppContext";
import { PipeSmithWordmark } from "@/components/PipeSmithWordmark";
import { PipSprite } from "@/components/PipSprite";
import { EyeIcon, EyeOffIcon, Icon, LockIcon, SparkIcon, StatusIcon, UserIcon } from "@/components/icons";
import { LoginShowcase } from "@/components/login/LoginShowcase";
import { Checkbox } from "@/components/ui";
import { messageOf } from "@/lib/api";
import { ADMIN_CONTACT, LANG_KEY, LOGIN_TEXT, type Lang, type LoginText } from "@/lib/loginText";

// Đăng nhập bằng tài khoản doanh nghiệp cấp. KHÔNG có đăng ký tự do (CLAUDE.md mục 1–2, 9.4).
// "Ghi nhớ" chỉ lưu TÊN đăng nhập trên máy này (không giữ phiên); mật khẩu không bao giờ lưu ở trình duyệt.
const REMEMBER_KEY = "p113.lastUser";

function makeSchema(t: LoginText) {
  return z.object({
    username: z.string().trim().min(1, t.userError).max(64),
    password: z.string().min(1, t.passwordError).max(256),
  });
}
type LoginValues = z.infer<ReturnType<typeof makeSchema>>;

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

function LoginForm({ t, pick }: { t: LoginText; pick: { user: string; password: string; n: number } | null }) {
  const { auth, login, enterGuest } = useApp();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [keep, setKeep] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [contactOpen, setContactOpen] = useState(false);
  const [scope, animate] = useAnimate<HTMLFormElement>();
  const reduceMotion = useReducedMotion();
  const schema = useMemo(() => makeSchema(t), [t]);
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

  // Bấm một tài khoản demo ở khung bên trái → điền sẵn tên và mật khẩu
  useEffect(() => {
    if (!pick) return;
    setValue("username", pick.user);
    setValue("password", pick.password);
  }, [pick, setValue]);

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
      <h1 id="login-title">
        {t.welcome} <span className="login-accent">{t.welcomeAccent}</span>
      </h1>
      <p className="login-sub">{t.sub}</p>

      <div className="login-field">
        <label htmlFor="login-user" className="sr-only">
          {t.user}
        </label>
        <span className="login-field-lead" aria-hidden>
          <UserIcon size={20} />
        </span>
        <input
          id="login-user"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          placeholder={t.user}
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
          {t.password}
        </label>
        <span className="login-field-lead" aria-hidden>
          <LockIcon size={20} />
        </span>
        <input
          id="login-password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          placeholder={t.password}
          maxLength={256}
          aria-invalid={Boolean(errors.password || error) || undefined}
          aria-describedby={errors.password ? "login-password-error" : undefined}
          {...register("password")}
        />
        <button
          type="button"
          className="login-eye"
          onClick={() => setShowPassword(!showPassword)}
          aria-label={showPassword ? t.hidePassword : t.showPassword}
          title={showPassword ? t.hidePassword : t.showPassword}
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
        {t.remember}
      </Checkbox>

      {error && (
        <p className="login-error" role="alert">
          <StatusIcon tone="danger" size={16} /> {error}
        </p>
      )}

      <button type="submit" className="login-btn" disabled={isSubmitting} aria-busy={isSubmitting || undefined}>
        {isSubmitting ? (
          <>
            <StatusIcon tone="running" size={18} /> {t.submitting}
          </>
        ) : (
          <>
            {t.submit} <Icon name="start" size={18} weight="bold" />
          </>
        )}
      </button>

      {/* Chế độ khách: chạy giao diện bằng dữ liệu mẫu trong trình duyệt, không gọi máy chủ */}
      <div className="login-guest">
        <button
          type="button"
          className="btn login-guest-btn"
          onClick={() => {
            enterGuest();
            router.replace("/");
          }}
        >
          <Icon name="show" size={18} weight="bold" /> {t.guestTry}
        </button>
        <p className="login-guest-hint">{t.guestHint}</p>
      </div>

      <p className="login-foot">
        {t.forgot}{" "}
        <button
          type="button"
          className="login-link"
          aria-expanded={contactOpen}
          aria-controls="login-contact"
          onClick={() => setContactOpen(!contactOpen)}
        >
          {t.forgotAction}
        </button>
      </p>
      {contactOpen && (
        <div id="login-contact" className="login-contact" role="note">
          <p>{t.contactText}</p>
          {/^[^\s@<>]+@[^\s@<>]+$/.test(ADMIN_CONTACT) && (
            <a href={`mailto:${ADMIN_CONTACT}`}>
              {t.contactMail}: {ADMIN_CONTACT}
            </a>
          )}
        </div>
      )}
    </form>
  );
}

function readLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "vi" || saved === "en") return saved;
  } catch {
    // trình duyệt chặn lưu trữ: dùng mặc định
  }
  return "vi";
}

export default function LoginPage() {
  const { dark, setTheme } = useApp();
  const [lang, setLang] = useState<Lang>("vi");
  const [pick, setPick] = useState<{ user: string; password: string; n: number } | null>(null);
  const t = LOGIN_TEXT[lang];

  // Đọc ngôn ngữ đã lưu sau khi trang hiện (tránh lệch giữa máy chủ và trình duyệt)
  useEffect(() => {
    const first = setTimeout(() => setLang(readLang()), 0);
    return () => clearTimeout(first);
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  function chooseLang(next: Lang) {
    setLang(next);
    try {
      localStorage.setItem(LANG_KEY, next);
    } catch {
      // bỏ qua
    }
  }

  return (
    <main className="login-page">
      <div className="login-tools">
        <Link href="/docs" className="login-docs-link">
          <Icon name="docs" size={18} /> {t.docs}
        </Link>
        <div className="login-lang" role="group" aria-label={t.langLabel}>
          {(["vi", "en"] as const).map((value) => (
            <button key={value} type="button" aria-pressed={lang === value} onClick={() => chooseLang(value)}>
              {value.toUpperCase()}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="login-tool"
          onClick={() => setTheme(dark ? "light" : "dark")}
          aria-label={dark ? t.themeToLight : t.themeToDark}
          title={dark ? t.themeToLight : t.themeToDark}
        >
          <Icon name={dark ? "light" : "dark"} size={18} weight="fill" />
        </button>
      </div>

      <section className="login-hero">
        <div className="login-hero-brand">
          <SparkIcon size={28} />
          <PipeSmithWordmark />
        </div>
        <h2>{t.heroTitle}</h2>
        <p className="login-hero-sub">{t.heroSub}</p>
        <blockquote>{t.quote}</blockquote>
        <div className="pip-intro">
          <PipSprite
            pose="idle"
            size={72}
            label={lang === "vi" ? "Pip, chú mèo pixel của PipeSmith" : "Pip, PipeSmith's pixel cat"}
          />
          <div className="pip-intro-copy">
            <strong>{lang === "vi" ? "Pip đồng hành cùng bạn" : "Meet your companion, Pip"}</strong>
            <p>
              {lang === "vi"
                ? "Chú mèo nhỏ sẽ theo nhịp công việc của mỗi lần chạy."
                : "A little cat that follows each run's actual state."}
            </p>
          </div>
        </div>
        <LoginShowcase t={t} onPickAccount={(user, password) => setPick({ user, password, n: Date.now() })} />
        <p className="login-hero-foot">{t.footer}</p>
      </section>

      <div className="login-side">
        <Suspense fallback={null}>
          <LoginForm t={t} pick={pick} />
        </Suspense>
      </div>
    </main>
  );
}
