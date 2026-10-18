import { Fragment } from "react";

/** Hiện chuỗi có đánh dấu `**ý chính**` thành chữ đậm (chữ nội dung nằm ở content/, không viết JSX trong đó). */
export function Rich({ text }: { text: string }) {
  return text
    .split("**")
    .map((part, index) =>
      index % 2 === 1 ? <strong key={index}>{part}</strong> : <Fragment key={index}>{part}</Fragment>,
    );
}
