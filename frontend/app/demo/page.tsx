"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useApp } from "@/components/AppContext";
import { SparkIcon } from "@/components/icons";

// Liên kết chia sẻ: mở /demo → bật chế độ khách (dữ liệu mẫu, không cần tài khoản) rồi về trang chủ.
export default function DemoPage() {
  const { guest, auth, enterGuest } = useApp();
  const router = useRouter();

  useEffect(() => {
    if (guest && auth === "in") router.replace("/");
    else if (auth !== "checking" && !guest) enterGuest();
  }, [guest, auth, enterGuest, router]);

  return (
    <div className="page">
      <div className="splash" role="status" aria-live="polite">
        <SparkIcon size={28} className="brand-spark" />
        <span>Đang mở chế độ khách với dữ liệu mẫu…</span>
      </div>
    </div>
  );
}
