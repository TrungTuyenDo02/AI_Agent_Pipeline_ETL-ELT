# Windows không có `make`: dùng `python scripts/tasks.py <đích>` (cùng tên đích).
PYTHON ?= python
DEMO_REQUEST = Gộp dữ liệu đơn hàng 3 nguồn (Shopee CSV, Tiki JSON, website SQLite), tính doanh thu theo ngày

.PHONY: run test lint format typecheck check ci doctor seed demo eval eval-llm frontend-dev frontend-build frontend-check docker-up docker-down clean

run:
	$(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

# Cần cài thêm mypy (chưa có trong requirements.txt)
typecheck:
	$(PYTHON) -m mypy src/

check: lint format test

# Giống hệt CI: lint → kiểm tra định dạng → test + độ phủ
ci:
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m ruff format --check src/ tests/
	$(PYTHON) -m pytest

doctor:
	$(PYTHON) -m src.cli doctor

seed:
	$(PYTHON) -m src.cli seed

# Kịch bản mẫu trọn vẹn bằng mock: Engineer "an" tạo yêu cầu, Reviewer "binh" duyệt
demo: seed
	$(PYTHON) -m src.cli --provider mock run --request "$(DEMO_REQUEST)" --as engineer --user an --auto-answer
	$(PYTHON) -m src.cli --provider mock review latest --as reviewer --user binh --approve

# Đánh giá không cần LLM (pytest, golden reference, mutation) → eval/results/report.md
eval:
	$(PYTHON) eval/run_eval.py

# Thêm golden chạy bằng LLM thật (tốn token; cần khóa trong .env)
eval-llm:
	$(PYTHON) eval/run_eval.py --with-llm

# Giao diện web (Next.js) ở http://localhost:3000, gọi API ở NEXT_PUBLIC_API_URL (mặc định http://localhost:8000)
frontend-dev:
	npm --prefix frontend run dev

frontend-build:
	npm --prefix frontend run build

# Giống job frontend của CI: ESLint, Prettier, tsc, next build
frontend-check:
	npm --prefix frontend run lint
	npm --prefix frontend run format:check
	npm --prefix frontend run typecheck
	npm --prefix frontend run build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache htmlcov coverage.xml .coverage
