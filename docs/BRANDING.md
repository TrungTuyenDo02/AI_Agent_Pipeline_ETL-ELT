# PipeSmith và Pip

PipeSmith là tên hiển thị của dự án P-113. Chữ thương hiệu dùng component `PipeSmithWordmark`; nội dung tiếng Việt tiếp tục dùng Be Vietnam Pro, code tiếp tục dùng JetBrains Mono.

## Galey Sans

Chủ dự án cung cấp file `prestigetype-studio-galey-semi-bold.ttf`; metadata của font là `Galey SemBd`, PostScript `Galey-SemiBold`. Bản dùng trong ứng dụng nằm ở `frontend/public/fonts/galey/galey-semi-bold.ttf`, được phục vụ cùng ứng dụng qua `@font-face` trong `frontend/styles/pipesmith-brand.css`, trọng lượng 600. Không cần cài font trên máy người xem. Bản Rounded Extra Light không được dùng cho wordmark.

Giữ nguyên giấy phép đi kèm ở `frontend/public/fonts/galey/Befonts-License.txt`: “Personal Use Only”. Bản font được cung cấp phục vụ bản xem thử; trước khi triển khai thương mại cần có giấy phép phù hợp.

**File font không có trong repo.** Giấy phép “Personal Use Only” không cho phát tán, nên `.gitignore` chặn file `.ttf`/`.otf`/`.woff*` trong `frontend/public/fonts/galey/`; repo chỉ giữ file giấy phép. Máy có file font thì wordmark dùng Galey; bản clone mới và bản deploy (Vercel) tự dùng font dự phòng Be Vietnam Pro, giao diện không vỡ. Khi có giấy phép dùng cho web: đặt file vào đường dẫn trên rồi bỏ dòng tương ứng trong `.gitignore`. Nguồn thông tin font: [Galey của Prestigetype Studio](https://www.myfonts.com/collections/galey-font-prestigetype-studio).

## Pip

- Mèo pixel trắng/cam/nâu, khăn xanh ngọc, dựa trên bảng sáu tư thế đã được chủ dự án chọn trong chat.
- Asset dùng thật: `frontend/public/brand/pip-atlas.webp`, lưới 3 × 2, sáu ô 512 × 512 pixel, nền trong suốt. File WebP được mã hóa lossless từ kết quả imagegen, giữ nguyên pixel và alpha.
- Tư thế: nghỉ, ghi chép, gõ code, chờ duyệt, cần sửa lỗi, hoàn tất.
- `frontend/lib/pip.ts` ánh xạ trạng thái thật của `RunDetail` sang tư thế và lời nhắn. Không có tiến độ hay kết quả được linh vật tự dựng.
- `PipSprite` vẽ một ô của atlas; `PipCompanion` bám mép viewport qua portal vào `document.body`. Trên Trang chủ và các trang ứng dụng, `AppShell` hiển thị Pip nghỉ cùng lời chào; trong trang chi tiết, `RunHeader` hiển thị Pip theo dữ liệu lần chạy. Hai vị trí loại trừ nhau để luôn chỉ có một Pip. Áp dụng cho người đăng nhập và chế độ khách; các trang công khai đăng nhập/giới thiệu giữ hình Pip trong nội dung. Mặc định góc dưới phải, hình mèo nền trong suốt, không chiếm ô trong nội dung. Kéo để bám một trong bốn góc; các nút chọn góc hỗ trợ bàn phím. Vị trí và lựa chọn ẩn được lưu ở `p113.pip.position`; nếu storage bị chặn vẫn dùng được trong phiên hiện tại.
- Bấm mèo để mở lời nhắn và tùy chọn. Trạng thái cần xử lý tự hiện lời nhắn tối đa 9 giây; hoàn tất tối đa 5 giây. Người dùng mở thủ công thì lời nhắn giữ đến khi đóng, bấm ra ngoài hoặc nhấn Escape. Liên kết đưa tới phần công việc hoặc màn duyệt của đúng lần chạy; linh vật không tự gửi quyết định. Có nút ẩn và nút nhỏ để hiện lại.
- Bong bóng ở chế độ sáng có nền xanh ngọc nhạt, tiêu đề xanh đậm và chữ phụ cùng tông; màu được tách thành các token `--pip-bubble-*`. Chế độ tối giữ nền trung tính. Các cặp tiêu đề/nội dung/liên kết trên nền bong bóng được kiểm trong `check:contrast`; tỷ lệ thấp nhất 4,76:1. Kiểm trình duyệt sáng/tối ở 1310 và 390 px: đúng màu, không tràn màn hình (`out/pip-bubble-qa/`).
- Khi đang chạy, mỗi chu kỳ 28 giây có một lượt đi và về dài tối đa 112 px. Dùng asset bổ sung `frontend/public/brand/pip-walk.webp`: bốn khung bước chân trong lưới 2 × 2, mỗi ô 627 × 627 px, alpha thật, mã hóa WebP lossless; CSS bù chênh lệch vị trí chân giữa các ô. Dừng đường đi khi rê chuột, nhận focus, mở lời nhắn hoặc kéo. Các tư thế làm việc vẫn dùng chuyển động CSS nhẹ; ăn mừng và biểu cảm lỗi chạy một lần khi đổi tư thế.
- Dưới 640 px, Pip thu còn khung 64 px (hình mèo khoảng 48–56 px), đứng yên phía trên điều hướng dưới, chọn được mép trái/phải. Tắt mọi hoạt ảnh với `prefers-reduced-motion`. Linh vật tạm khuất khi toast hoặc hộp thoại đang mở để nhường tương tác.
- Chờ hàng đợi dùng tư thế nghỉ; yêu cầu pause chưa hoàn tất vẫn là đang làm. Chỉ nghỉ khi backend báo `paused`. Chỉ ăn mừng khi trạng thái là `approved`; chế độ khách có lời nhắn riêng cho kết quả mẫu.

## Nguồn hình và prompt

Tạo bằng công cụ imagegen tích hợp, dùng bảng Pip sáu hành động đã duyệt làm ảnh tham chiếu. Không dùng API key của dự án.

Prompt sản xuất:

> Convert the approved Pip action board into a transparent 3-column × 2-row sprite atlas. Preserve the exact six calico kitten designs, teal neckerchief, props and crisp chunky pixel style. Remove all captions and cream background. Center one full pose in each equal square cell with padding and aligned baselines. Positions: resting, taking notes, typing on a teal laptop, holding an approval clipboard, repairing a disconnected pipe, celebrating with a connected pipe. No labels, dividers or new poses.

Prompt bổ sung cho `pip-walk.webp` (công cụ imagegen tích hợp, lấy atlas cũ làm tham chiếu nhận diện):

> Create one production pixel-art walk-cycle sprite sheet for Pip, the calico kitten mascot in the reference. The reference is an identity reference: preserve white fur, orange patch on left of face, dark brown right ear, dark brown pixel outline, tiny pink nose and cheeks, teal neckerchief. New poses only: the exact same kitten walking on four paws facing LEFT, no props. FOUR animation frames in an exact 2-column by 2-row grid, each square exactly same size and ground baseline, in chronological row-major order. All frames show same identity/scale and a small readable alternating front/back paw gait. Frame1 front left extended; frame2 passing pose; frame3 opposite paws extended; frame4 passing alternate pose. Side view with face slightly towards viewer, cute consistent proportions and crisp square pixels. Each full kitten occupies central 75% of its cell, with transparent padding. Truly transparent background; hard clean alpha cutout, no shadow, no glow, no colored translucent artifacts, no ground, no grid, no labels or text, no border. Deliver square sprite atlas.

Mã backend, tên node, checkpoint, khóa lưu trình duyệt `p113.*` và hợp đồng API giữ nguyên để không ảnh hưởng dữ liệu cũ.

## Kiểm tra

`python scripts/tasks.py frontend-check` đạt cho đợt thêm thương hiệu và Pip: lint, định dạng, typecheck, tương phản và build. Kiểm Chromium headless ở 1366 px và 390 px, sáng/tối: tên và sprite hiển thị, không tràn ngang; ẩn/hiện Pip và giảm chuyển động hoạt động. Ánh xạ trạng thái đã kiểm 13 tình huống. Chế độ khách dùng dữ liệu mẫu; chưa kiểm lần chạy LLM thật.

Sau khi thêm file font, kiểm riêng định dạng CSS và Chromium: `/login` ở 1366/390 px và `/docs` ở 1366 px đều tải font thành công, không tràn ngang, không lỗi JavaScript. DevTools xác nhận cả 9 ký tự `PipeSmith` dùng font thực `Galey-SemiBold`, không phải font dự phòng. Báo cáo local: `out/pipesmith-qa/galey-report.json`.

Đợt chuyển Pip sang bám mép: 26 kiểm tra Chromium headless đạt ở 1366/390/320 px, sáng/tối; gồm Pointer Events kéo thật, tải lại giữ vị trí và ẩn/hiện, Escape trả focus, thời gian tự đóng, liên kết xử lý, giới hạn đường đi, giảm chuyển động, điều hướng dưới và bong bóng không tràn màn hình. Lần chạy mẫu đang làm được giữ đồng hồ trong script QA để tránh chuyển trạng thái giữa lúc kiểm. Báo cáo và ảnh local: `out/pip-edge-qa/`.

Chạy lại `python scripts/tasks.py frontend-check` sau thay đổi bám mép: lint, định dạng, typecheck, tương phản, lint:text và build đều đạt.

Bổ sung hiển thị trên Trang chủ: frontend-check đạt toàn bộ; 12 kiểm tra Chromium đạt cho khách Engineer/Reviewer, danh sách và chi tiết, chuyển trang không trùng linh vật, ẩn/hiện xuyên trang, desktop 1310 × 655 và điện thoại 390 × 844. Ảnh tái hiện đúng kích thước màn hình người dùng: `out/pip-home-qa/home-desktop.png`; báo cáo `out/pip-home-qa/report.json`.
