// Kiểm tương phản chữ/nền ≥ 4.5:1 (WCAG AA) cho mọi cặp màu giao diện dùng thật, cả sáng lẫn tối.
// Đọc styles/tokens.css (mỗi biến dạng light-dark(<sáng>, <tối>)). Cặp nào trượt → thoát mã 1: chỉnh màu, không bỏ qua.
//   npm run check:contrast

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const MIN_RATIO = 4.5;
const TOKENS = join(dirname(fileURLToPath(import.meta.url)), "..", "styles", "tokens.css");

// [chữ, nền, chỗ dùng] — thêm cặp mới khi globals.css dùng một tổ hợp mới.
const PAIRS = [
  ["text", "bg", "chữ thường trên nền trang"],
  ["text", "surface", "chữ trong thẻ"],
  ["text", "surface-2", "chữ trong ô thống kê, tiêu đề bảng"],
  ["muted", "bg", "chữ phụ trên nền trang"],
  ["muted", "surface", "chữ phụ trong thẻ"],
  ["muted", "surface-2", "nhãn ô thống kê, tiêu đề cột"],
  ["primary", "surface", "liên kết, tab đang chọn"],
  ["primary", "bg", "liên kết trên nền trang"],
  ["primary", "primary-soft", "mục điều hướng đang chọn, nhãn thông tin"],
  ["primary-ink", "primary", "nút chính"],
  ["ok", "ok-soft", "nhãn đạt"],
  ["ok", "surface", "dấu đạt trên thẻ"],
  ["ok-ink", "ok", "nút duyệt"],
  ["warn", "warn-soft", "nhãn chờ người, cảnh báo"],
  ["warn", "surface", "chữ cảnh báo trên thẻ"],
  ["fail", "fail-soft", "nhãn lỗi, hộp lỗi"],
  ["fail", "surface", "nút từ chối (viền), chữ lỗi"],
  ["text", "frame", "chữ trên khung kính (tiêu đề trang, thanh điều hướng)"],
  ["muted", "frame", "chữ phụ trên khung kính, chân trang"],
  ["primary", "frame", "tab điều hướng đang chọn"],
  ["primary-ink", "accent", "chữ trên logo gradient"],
  ["ai", "ai-soft", "nhãn Code AI sinh (hồ sơ dữ liệu)"],
  ["text", "ok-soft", "lời kết luận hồ sơ dữ liệu: ổn"],
  ["text", "warn-soft", "lời kết luận hồ sơ dữ liệu: cần xem"],
  ["text", "fail-soft", "lời kết luận hồ sơ dữ liệu: chưa ổn"],
  ["fail", "surface", "số ô không đọc được trên thẻ cột"],
  ["type-num", "type-num-bg", "nhãn kiểu số (schema)"],
  ["type-text", "type-text-bg", "nhãn kiểu chữ (schema)"],
  ["type-time", "type-time-bg", "nhãn kiểu thời gian (schema)"],
  ["type-bool", "type-bool-bg", "nhãn kiểu đúng/sai (schema)"],
  ["login-hero-ink", "login-hero-solid", "chữ chính khung thông tin đăng nhập"],
  ["login-hero-muted", "login-hero-solid", "chữ phụ khung thông tin đăng nhập"],
  ["login-hero-ink", "login-hero-card-solid", "chữ trong thẻ thông tin đăng nhập"],
  ["login-hero-muted", "login-hero-card-solid", "chữ phụ trong thẻ thông tin đăng nhập"],
  ["login-accent", "login-glass-solid", "chữ nhấn TRỞ LẠI trên thẻ đăng nhập"],
  ["console-text", "console-bg", "dòng log trong console"],
  ["console-muted", "console-bg", "giờ, nhãn phụ trong console"],
  ["console-ok", "console-bg", "nhãn OK trong console"],
  ["console-fail", "console-bg", "nhãn LỖI trong console"],
  ["console-info", "console-bg", "nhãn bước trong console"],
  ["console-warn", "console-bg", "nhãn CẢNH BÁO trong nhật ký chạy"],
  ["console-text", "console-error-bg", "dòng lỗi (nền đỏ rất nhạt) trong nhật ký chạy"],
  ["console-fail", "console-error-bg", "nhãn LỖI trên dòng lỗi"],
  ["console-muted", "console-error-bg", "giờ trên dòng lỗi"],
  ["console-live", "console-bg", "dòng 'đang làm' (mô tả, không phải log đo)"],
  ["text", "glass-solid", "chữ trong thẻ kính"],
  ["muted", "glass-solid", "chữ phụ trong thẻ kính"],
  ["primary", "glass-solid", "liên kết, số lớn trong thẻ kính"],
  ["hero-ink", "bg-page", "tiêu đề lớn trên nền trang phẳng"],
  ["text", "bg-page", "chữ chính trên nền trang phẳng"],
  ["muted", "bg-page", "chữ phụ trên nền trang phẳng"],
  ["text", "card", "chữ chính trong thẻ trắng"],
  ["muted", "card", "chữ phụ trong thẻ trắng"],
  ["primary", "card", "liên kết, số lớn trong thẻ trắng"],
  ["accent", "card", "màu nhấn trong thẻ trắng"],
  ["rail-ink", "rail", "biểu tượng thanh điều hướng dọc đang chọn"],
  ["text", "btn-bottom", "chữ trên nút mềm nổi (mép dưới)"],
  ["primary-ink", "primary-hi", "chữ nút chính (mép trên sáng)"],
  ["ok-ink", "ok-hi", "chữ nút duyệt (mép trên sáng)"],
  ["fail", "btn-bottom", "nút từ chối trên mặt nút"],
  ["check-ink", "check-b", "dấu tích trong ô chọn"],
  ["login-ink", "login-glass-solid", "tiêu đề, chữ nhập trên thẻ kính đăng nhập"],
  ["login-muted", "login-glass-solid", "chữ phụ, gợi ý trên thẻ kính đăng nhập"],
  ["login-cta-ink", "login-cta-b", "chữ nút Đăng nhập (giữa)"],
  ["login-cta-ink", "login-cta-solid", "chữ nút Đăng nhập (mép dưới)"],
  ["fail", "login-glass-solid", "lỗi dưới ô nhập trên thẻ kính đăng nhập"],
  ["login-cta-b", "login-glass-solid", "viền ô đang nhập, vòng focus trên thẻ đăng nhập"],
  ["login-error", "login-error-bg", "lỗi đăng nhập"],
  ["warn", "warn-soft", "nhãn vai trò Admin"],
  ["guide-ink", "guide-soft", "chữ trong khung hướng dẫn (chế độ khách)"],
  ["pip-bubble-ink", "pip-bubble-bg", "Pip: tiêu đề lời nhắn"],
  ["pip-bubble-muted", "pip-bubble-bg", "Pip: nội dung, nhãn khách và nút ẩn"],
  ["primary", "pip-bubble-bg", "Pip: liên kết trong lời nhắn"],
  ["pip-bubble-muted", "card", "Pip: biểu tượng chọn góc"],
  ["text", "guide-soft", "chữ thường trong khung hướng dẫn"],
  ["guide-on", "guide", "chữ trên nút / dấu bước hướng dẫn nền đặc"],
  ["guide", "card", "viền, chữ nhấn hướng dẫn trên thẻ trắng"],
  ["guide-ink", "card", "tiêu đề bước hướng dẫn trên thẻ trắng"],
  ["primary", "primary-soft", "mục điều hướng đang chọn (thanh trên, Thêm, lọc nhanh)"],
  ["muted", "surface-2", "mục điều hướng khi rê chuột"],
  ["primary", "bg-page", "trang giới thiệu: nhãn mục, liên kết neo đang đọc"],
  ["warn", "bg-page", "trang giới thiệu: nguyên tắc Con người quyết định"],
  ["ai", "bg-page", "trang giới thiệu: nguyên tắc AI thực thi"],
  ["ok", "bg-page", "trang giới thiệu: nguyên tắc Code kiểm chứng"],
  ["warn", "warn-soft", "trang giới thiệu: nhãn Con người"],
  ["ai", "ai-soft", "trang giới thiệu: nhãn AI"],
  ["ok", "ok-soft", "trang giới thiệu: nhãn Code"],
  ["text", "tint", "trang giới thiệu: chữ trên khối nền nhạt màu nhấn"],
  ["muted", "tint", "trang giới thiệu: chữ phụ trên khối nền nhạt màu nhấn"],
  ["primary", "tint", "trang giới thiệu: nhãn mục, liên kết trên khối nền nhạt"],
  ["highlight", "bg-page", "trang giới thiệu: chữ nhấn phụ trên nền trang"],
  ["highlight", "card", "trang giới thiệu: chữ nhấn phụ trong thẻ trắng"],
  ["highlight", "tint", "trang giới thiệu: chữ nhấn phụ trên khối nền nhạt"],
  ["highlight", "highlight-soft", "nhãn nhấn phụ"],
];

// Khối nền tối (.docs-band) đặt lại token bằng giá trị tối: chỉ kiểm cặp ở chế độ tối.
const DARK_PAIRS = [
  ["text", "band", "khối nền tối: chữ chính"],
  ["muted", "band", "khối nền tối: chữ phụ"],
  ["primary", "band", "khối nền tối: nhãn mục, liên kết"],
  ["highlight", "band", "khối nền tối: số liệu, chữ nhấn phụ"],
  ["text", "band-card", "khối nền tối: chữ trong thẻ"],
  ["muted", "band-card", "khối nền tối: chữ phụ trong thẻ"],
  ["highlight", "band-card", "khối nền tối: số liệu trong thẻ"],
  ["ok", "band-card", "khối nền tối: nhãn chạy thử đạt"],
  ["ai", "band-card", "khối nền tối: chữ nhấn AI trong thẻ"],
  ["console-text", "band-card", "khối nền tối: dòng code demo"],
];

function parseTokens(css) {
  const tokens = {};
  for (const match of css.matchAll(/--([a-z0-9-]+):\s*light-dark\(\s*(#[0-9a-f]{6})\s*,\s*(#[0-9a-f]{6})\s*\)/gi)) {
    tokens[match[1]] = { light: match[2], dark: match[3] };
  }
  return tokens;
}

function luminance(hex) {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const tokens = parseTokens(readFileSync(TOKENS, "utf8"));
let failed = 0;
for (const mode of ["light", "dark"]) {
  console.log(`\n${mode === "light" ? "Sáng" : "Tối"}`);
  for (const [fg, bg, usage] of PAIRS) {
    if (!tokens[fg] || !tokens[bg]) {
      console.log(`  ✗ thiếu biến --${!tokens[fg] ? fg : bg} trong tokens.css`);
      failed += 1;
      continue;
    }
    const value = ratio(tokens[fg][mode], tokens[bg][mode]);
    const ok = value >= MIN_RATIO;
    if (!ok) failed += 1;
    console.log(`  ${ok ? "✓" : "✗"} ${value.toFixed(2).padStart(5)}:1  --${fg} / --${bg}  (${usage})`);
  }
}
console.log("\nKhối nền tối (chỉ chế độ tối)");
// Giá trị đặt lại trong .docs-band phải trùng cột tối của token, nếu không các cặp dưới không phản ánh màu thật.
const band = readFileSync(TOKENS, "utf8").match(/\.docs-band\s*\{([^}]*)\}/);
for (const [, name, value] of (band ? band[1] : "").matchAll(/--([a-z0-9-]+):\s*(#[0-9a-f]{6})\s*;/gi)) {
  if (tokens[name] && tokens[name].dark.toLowerCase() !== value.toLowerCase()) {
    console.log(`  ✗ .docs-band --${name}: ${value} khác giá trị tối ${tokens[name].dark}`);
    failed += 1;
  }
}
for (const [fg, bg, usage] of DARK_PAIRS) {
  if (!tokens[fg] || !tokens[bg]) {
    console.log(`  ✗ thiếu biến --${!tokens[fg] ? fg : bg} trong tokens.css`);
    failed += 1;
    continue;
  }
  const value = ratio(tokens[fg].dark, tokens[bg].dark);
  const ok = value >= MIN_RATIO;
  if (!ok) failed += 1;
  console.log(`  ${ok ? "✓" : "✗"} ${value.toFixed(2).padStart(5)}:1  --${fg} / --${bg}  (${usage})`);
}
if (failed) {
  console.error(`\n${failed} cặp dưới ${MIN_RATIO}:1 — chỉnh màu trong styles/tokens.css.`);
  process.exit(1);
}
console.log(`\nMọi cặp đạt ≥ ${MIN_RATIO}:1.`);
