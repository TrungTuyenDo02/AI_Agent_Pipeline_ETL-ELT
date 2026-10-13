"use client";

// Hộp xác nhận cho quyết định khó đảo ngược (CLAUDE.md 9.6: bấm Duyệt → hỏi lại). Việc nhỏ không dùng hộp thoại chặn (9.9).
// Radix AlertDialog lo phần trợ năng: giữ focus trong hộp, Esc để hủy, trả focus về nút đã mở.

import * as AlertDialog from "@radix-ui/react-alert-dialog";
import type { ReactNode } from "react";

import { Icon } from "./icons";
import type { IconName } from "@/lib/icons";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  icon = "approve",
  confirmLabel,
  confirmClass = "btn ok",
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  icon?: IconName;
  confirmLabel: string;
  confirmClass?: string;
  onConfirm: () => void;
  children: ReactNode;
}) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="dialog-overlay" />
        <AlertDialog.Content className="dialog">
          <div className="dialog-icon" aria-hidden>
            <Icon name={icon} size={28} weight="duotone" />
          </div>
          <AlertDialog.Title className="dialog-title">{title}</AlertDialog.Title>
          <AlertDialog.Description asChild>
            <div className="dialog-body">{children}</div>
          </AlertDialog.Description>
          <div className="dialog-actions">
            <AlertDialog.Cancel className="btn">Quay lại</AlertDialog.Cancel>
            <AlertDialog.Action className={confirmClass} onClick={onConfirm}>
              {confirmLabel}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
