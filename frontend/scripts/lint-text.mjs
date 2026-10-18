// Kiểm chữ giao diện tiếng Việt, không thêm thư viện (dùng trình phân tích của typescript có sẵn): npm run lint:text
// Chỉ xét chuỗi có dấu tiếng Việt (chữ giao diện), bỏ qua chú thích, code, tên lớp CSS.
//
// Quy tắc:
//   hoa-dau-cau   Chữ đầu câu, đầu tiêu đề phải viết hoa (trừ tên riêng viết thường: dbt, sqlglot…). Chỉ xét chỗ chắc
//                 chắn là đầu câu: chữ trong content/ và lib/*Text.ts, thuộc tính title/aria-label/placeholder/alt,
//                 chữ JSX đứng đầu thẻ, thông báo toast()/setError()/new Error(). Sau dấu . ! ? trong chuỗi cũng phải hoa.
//   thuat-ngu     Một ý một từ: "duyệt" (không "phê duyệt", "approve").
//   khoang-trang  Hai dấu cách liền nhau, dấu cách trước dấu câu.
// Có lỗi → thoát mã 1. Chuỗi cố ý viết thường (nối sau con số, sau biến) ghi vào ALLOW kèm lý do.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DIRS = ["content", "lib", "app", "components"];
// Dữ liệu mẫu của chế độ khách (log, SQL, lời agent giả lập): không phải chữ giao diện
const SKIP = [/^lib\/demo\//];
const CURATED = [/^content\//, /^lib\/[A-Za-z]*Text\.ts$/];
const VI = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;
// Tên riêng, mã viết thường, tên định danh trong code (useApp…)
const LOWER_OK = /^(dbt|sqlglot|models\/|select\b|from\b|https?:|v\d|\.|[a-z]+[A-Z]\w*)/;
// Thẻ chữ nằm giữa câu: chữ đầu thẻ không phải đầu câu
const INLINE_TAGS = new Set(["strong", "em", "b", "i", "code", "mark"]);
const TEXT_ATTRS = new Set(["title", "aria-label", "placeholder", "alt", "label"]);
const MESSAGE_CALLS = new Set(["toast", "setError", "Error", "confirm", "alert"]);
const TERMS = [
  [/phê duyệt/i, 'dùng "duyệt"'],
  [/\bapprove[ds]?\b/i, 'dùng "duyệt" trong câu tiếng Việt'],
];
/** Chuỗi cố ý viết thường ở đầu. */
const ALLOW = new Map([
  // Nhãn đứng ngay sau con số lớn ("93% lỗi cố ý…"), đọc liền một câu
  ["lỗi cố ý bị bộ kiểm chứng bắt", "nối sau con số"],
  ["thời gian truy vấn được cắt giảm", "nối sau con số"],
  ["ca nguồn đổi cấu trúc không lọt sai", "nối sau con số"],
  ["mã nguồn được test tự động phủ", "nối sau con số"],
]);

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (/\.(ts|tsx)$/.test(name) && !name.endsWith(".d.ts")) out.push(path);
  }
  return out;
}

/** Chuỗi này có đứng ở đầu câu không (chỉ những vị trí chắc chắn). */
function startsSentence(node, curated) {
  if (curated) return true;
  const parent = node.parent;
  if (ts.isJsxText(node)) {
    const tag = ts.isJsxElement(parent) ? parent.openingElement.tagName.getText() : "";
    if (INLINE_TAGS.has(tag)) return false;
    // chữ đầu tiên trong thẻ, không đứng sau một biểu thức {…} hay thẻ khác
    const siblings = parent.children ?? [];
    const index = siblings.indexOf(node);
    return siblings.slice(0, index).every((child) => ts.isJsxText(child) && !child.text.trim());
  }
  if (ts.isJsxAttribute(parent)) return TEXT_ATTRS.has(parent.name.getText());
  if (ts.isCallExpression(parent) || ts.isNewExpression(parent)) {
    const callee = parent.expression.getText().split(".").pop();
    return MESSAGE_CALLS.has(callee) && parent.arguments?.[0] === node;
  }
  return false;
}

function check(text, sentenceStart, isJsx) {
  const problems = [];
  const t = text.replace(/\s+/g, " ").trim();
  if (!VI.test(t) || ALLOW.has(t)) return problems;
  const first = t.replace(/^[“"'«\[–—•…\s]+/, "");
  // Chữ mở đầu bằng "(" hoặc "·" là chú thích nối sau chữ đứng trước, không phải đầu câu
  if (sentenceStart && /^\p{Ll}/u.test(first) && !LOWER_OK.test(first)) {
    problems.push(["hoa-dau-cau", "viết hoa chữ đầu"]);
  }
  for (const m of t.matchAll(/[.!?]["”)]?\s+(\p{Ll}\S*)/gu)) {
    if (!LOWER_OK.test(m[1])) problems.push(["hoa-dau-cau", `viết hoa sau dấu câu: "${m[1]}"`]);
  }
  for (const [re, hint] of TERMS) if (re.test(t)) problems.push(["thuat-ngu", hint]);
  if (!isJsx && /\S {2,}\S/.test(text)) problems.push(["khoang-trang", "hai dấu cách liền nhau"]);
  if (/\p{L} +[,.;:!?](\s|$)/u.test(t)) problems.push(["khoang-trang", "dấu cách trước dấu câu"]);
  return problems;
}

const issues = [];
for (const path of DIRS.flatMap((dir) => walk(join(ROOT, dir)))) {
  const rel = relative(ROOT, path).replace(/\\/g, "/");
  if (SKIP.some((re) => re.test(rel))) continue;
  const curated = CURATED.some((re) => re.test(rel));
  const source = readFileSync(path, "utf8");
  const file = ts.createSourceFile(rel, source, ts.ScriptTarget.Latest, true, rel.endsWith("x") ? 4 : 3);
  const visit = (node) => {
    const isText =
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      (ts.isJsxText(node) && node.text.trim()) ||
      ts.isTemplateHead(node);
    const inImport = node.parent && (ts.isImportDeclaration(node.parent) || ts.isExportDeclaration(node.parent));
    const isKey = node.parent && ts.isPropertyAssignment(node.parent) && node.parent.name === node;
    if (isText && !inImport && !isKey) {
      const text = node.text;
      const head = ts.isTemplateHead(node) || !startsSentence(node, curated) ? false : true;
      const line = file.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      for (const [rule, hint] of check(text, head, ts.isJsxText(node))) {
        issues.push({ file: rel, line, rule, hint, text: text.replace(/\s+/g, " ").trim() });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
}

if (process.argv.includes("--json")) {
  console.log(JSON.stringify(issues, null, 2));
} else {
  for (const issue of issues) {
    console.log(`${issue.file}:${issue.line}  [${issue.rule}] ${issue.hint}  «${issue.text.slice(0, 100)}»`);
  }
  console.log(issues.length ? `\n${issues.length} lỗi chữ giao diện.` : "Chữ giao diện sạch.");
}
process.exit(issues.length ? 1 : 0);
