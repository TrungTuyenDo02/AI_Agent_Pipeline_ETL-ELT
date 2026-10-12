# Chính sách bảo mật

## Báo cáo lỗ hổng

**Không** mở public issue cho lỗ hổng bảo mật.

Dùng [GitHub Security Advisories](https://github.com/AI20K-Build-Phase/starter-code-template/security/advisories/new)
để báo cáo riêng tư. Vui lòng mô tả: loại lỗ hổng, file/dòng liên quan, các bước
tái hiện, và tác động bạn đánh giá.

Chúng tôi sẽ phản hồi trong vòng 7 ngày làm việc.

## Nếu bạn lỡ commit một API key

Xoá key khỏi file rồi commit tiếp là **chưa đủ** — giá trị cũ vẫn nằm trong git
history và trong mọi bản clone/fork đã tồn tại. Coi như key đã lộ hoàn toàn.

Làm theo thứ tự này:

1. **Xoay key ngay (rotate).** Đây là bước duy nhất thật sự vô hiệu hoá key cũ.
   Mọi bước còn lại chỉ là dọn dẹp.
2. Thay bằng placeholder trong file, commit.
3. Nếu cần xoá khỏi history, dùng
   [git-filter-repo](https://github.com/newren/git-filter-repo) rồi force-push.
   Lưu ý việc này viết lại history, mọi người phải re-clone.
4. Báo maintainer để kiểm tra fork và cache của GitHub.

## Các lớp bảo vệ agent (prompt injection, bí mật)

| Lớp | Chặn gì | Ở đâu | Test |
|---|---|---|---|
| Thẻ `<data>` không đóng sớm được | Dữ liệu chứa `</data>` giả làm chỉ dẫn | `src/services/llm.py` (`neutralize_data_tags`) | `tests/test_prompts/test_prompt_injection.py` |
| Câu dặn trong 4 prompt | Chữ trong dữ liệu đòi đổi luật | `src/prompts/*.md` | `tests/test_prompts/test_budget.py` |
| Quét từ khóa, **chỉ cảnh báo** | Ô dữ liệu nguồn / mục sổ lỗi giống lệnh cài cắm hoặc bí mật | `src/agents/tools/injection_scan.py` | `tests/test_verifiers/test_injection_scan.py` |
| V1 kiểm code sinh ra | Lệnh ghi/xóa, đọc file, Jinja lạ, hàm lộ cấu hình | `src/agents/nodes/safety.py` | `tests/test_verifiers/test_v1_redteam.py` |
| Môi trường dbt sạch | dbt đọc khóa/mật khẩu qua biến môi trường | `src/agents/tools/dbt_tools.py` (`is_secret_env`) | `tests/test_agents/test_dbt_workspace.py` |

Quét từ khóa dễ né và có thể báo nhầm, nên chỉ để người duyệt chú ý. Chốt chặn thật là hai lớp code (thẻ dữ liệu, V1) và người duyệt.
Chưa kiểm chứng: hiệu quả của câu dặn trong prompt với LLM thật (cần khóa API, chưa có bộ eval injection).

## Bảo mật khi dùng template này

- **Không bao giờ** đặt key thật vào `.env.example` — file đó được commit.
  Key thật đặt trong `.env` (đã có trong `.gitignore`).
- `AI_LOG_API_KEY` là key **riêng của từng đội**, lấy từ link mời của BTC.
  Không chia sẻ, không commit.
- Trước khi push, tự kiểm tra nhanh:
  ```bash
  git diff --cached | grep -iE "api[_-]?key|secret|token|password"
  ```
- Thư mục `.ai-log/` chứa nội dung prompt của bạn. Kiểm tra trước khi public
  một repo có sẵn log — prompt có thể vô tình chứa dữ liệu nhạy cảm.
