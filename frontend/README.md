This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Chế độ khách (dữ liệu mẫu)

Dùng thử toàn bộ giao diện mà không cần tài khoản, không gọi backend, không gọi AI (ADR 0015).

- **Vào:** nút "Dùng thử với dữ liệu mẫu" ở màn đăng nhập, hoặc mở `/demo` (liên kết chia sẻ được: tự bật chế độ khách rồi về trang chủ).
- **Trên thanh trên:** dải "Chế độ khách · Dữ liệu mẫu" kèm chú thích, nút đổi vai Engineer/Reviewer, "Làm lại từ đầu" và "Đăng nhập"
  (thoát chế độ khách, xóa sạch dữ liệu mẫu). Số thời gian/chi phí có nhãn "số liệu mẫu".
- **Bộ mẫu ban đầu:** một lần chạy hoàn tất có tối ưu được áp dụng, một lần chờ duyệt, một lần đã dừng (`failed`), một lần đang chạy
  (tiến độ đi theo thời gian, khoảng 35 giây tới bước chờ duyệt). Yêu cầu mới tạo ở chế độ khách đi đúng các bước: hỏi làm rõ → duyệt
  kế hoạch → chạy → chờ duyệt (đổi sang Reviewer để duyệt).
- **Lưu ở đâu:** `sessionStorage` (`p113.guest`, `p113.demo.state`). Tải lại trang vẫn giữ; đóng tab là hết.
- **Mã nguồn:** `lib/guest.ts` (cờ, người dùng khách, lưới chặn `fetch`), `lib/demo/router.ts` (thay API), `lib/demo/engine.ts`
  (trạng thái, tiến trình), `lib/demo/fixtures.ts` (dữ liệu mẫu, **sinh tự động**), `components/GuestBar.tsx` (dải khách, nhãn số liệu mẫu).
- **Hướng dẫn nhúng sẵn** (chỉ ở chế độ khách, không có tour lớp phủ): dải "Bạn đang ở Chế độ khách", khối "Quy trình 4 bước"
  đi theo trạng thái thật của lần chạy (cùng cách gom 4 giai đoạn với thanh tiến trình), khung "Bước 1" + nút "Thử ngay với ví dụ"
  (chỉ điền sẵn), khung giải thích ở từng giai đoạn, dòng giải thích theo trạng thái và dưới ô thống kê, "Từ điển nhanh", thẻ
  "Bạn vừa đi hết quy trình". Mã: `components/guide/Guide.tsx`; **toàn bộ chữ ở `lib/guideText.ts`**; màu xanh ngọc `--guide*`
  trong `styles/tokens.css`.
- **Sinh lại dữ liệu mẫu** khi API đổi khuôn (typecheck sẽ báo): từ gốc repo chạy `python scripts/demo_fixtures.py` (chạy luồng thật với
  `LLM_PROVIDER=mock` trong thư mục tạm, không dùng `.env`/DB dev, ~1–2 phút). Không sửa tay `fixtures.ts`.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
