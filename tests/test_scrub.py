"""scrub_error (CLAUDE.md bản 2, mục 3.4): lỗi của DuckDB/dbt/Postgres chứa giá trị thật → vào prompt chỉ còn `<đã che>`."""

import pytest

from src.agents.tools.scrub import MASK, prompt_error, scrub_error

SECRETS = [
    "abc@x.com",
    "an.nguyen@congty.vn",
    "Nguyễn Văn A",
    "0987654321",
    "1.075.000",
    "9876543210123",
    "DELL",
    "an@congty.vn",
    "Trần Thị B",
]

ERRORS = {
    "duckdb_convert": "Conversion Error: Could not convert string 'abc@x.com' to INT32\nLINE 3: select cast(email as int)",
    "duckdb_parse": 'Invalid Input Error: Could not parse string "Nguyễn Văn A" according to format specifier "%d/%m/%Y"',
    "duckdb_money": "Conversion Error: Could not convert string '1.075.000' to INT64 when casting column total_amount",
    "duckdb_phone": "Invalid Input Error: value 0987654321 is out of range for type INTEGER",
    "dbt": (
        "Database Error in model stg_shopee_orders (models/staging/stg_shopee_orders.sql)\n"
        "  Conversion Error: Could not convert string 'an.nguyen@congty.vn' to DOUBLE\n"
        "  compiled code at C:\\Users\\DELL\\AppData\\Local\\Temp\\p113\\target\\run\\stg.sql"
    ),
    "pg_key": 'ERROR: duplicate key value violates unique constraint "users_email_key"\nDETAIL: Key (email)=(an@congty.vn) already exists.',
    "pg_row": "DETAIL: Failing row contains (1, an@congty.vn, Trần Thị B, 9876543210123).",
    "pg_syntax": 'ERROR: invalid input syntax for type integer: "Nguyễn Văn A"',
}


@pytest.mark.parametrize("name", ERRORS)
def test_values_are_removed_but_error_shape_is_kept(name: str):
    cleaned = scrub_error(ERRORS[name])
    for secret in SECRETS:
        assert secret not in cleaned, f"{secret!r} còn trong: {cleaned}"
    assert MASK in cleaned


def test_error_kind_and_column_names_survive_so_llm_can_still_fix_the_code():
    cleaned = scrub_error(ERRORS["duckdb_convert"])
    assert cleaned.startswith("Conversion Error: Could not convert string") and "INT32" in cleaned
    assert "Key (email)=(<đã che>)" in scrub_error(ERRORS["pg_key"])
    assert 'constraint "users_email_key"' in scrub_error(
        ERRORS["pg_key"]
    )  # tên ràng buộc là cấu trúc, không phải dữ liệu
    assert "stg_shopee_orders" in scrub_error(ERRORS["dbt"])


def test_binder_errors_keep_identifiers():
    error = 'Binder Error: Referenced column "order_dt" not found in FROM clause! Candidate bindings: "order_date", "status"'
    assert scrub_error(error) == error


def test_sql_echo_and_format_strings_are_code_not_data():
    error = "Parser Error: bad\nLINE 12: where status = 'completed' and d = strptime(x, '%d/%m/%Y')"
    assert scrub_error(error) == error
    assert scrub_error("could not parse format '%d/%m/%Y'") == "could not parse format '%d/%m/%Y'"


def test_username_in_absolute_path_is_masked_but_location_is_kept():
    cleaned = scrub_error(
        "IO Error: cannot open C:\\Users\\DELL\\data\\x.csv and /home/dell/data/y.csv and /Users/an/z.csv"
    )
    assert "DELL" not in cleaned and "dell" not in cleaned and "/an/" not in cleaned
    assert "data\\x.csv" in cleaned and "data/y.csv" in cleaned


def test_long_numbers_money_phone_and_email_anywhere_in_text():
    cleaned = scrub_error("row 5: amount 1,075,000 phone +84 91 234 5678 id 12345678901 mail nguyen.van@a.vn end")
    assert cleaned.count(MASK) >= 4 and "@" not in cleaned and "12345678901" not in cleaned
    assert "row 5" in cleaned  # số nhỏ (số dòng, mã dòng) giữ nguyên


def test_empty_and_non_string_input():
    assert scrub_error("") == "" and scrub_error(None) == ""  # type: ignore[arg-type]


def test_prompt_error_truncates_after_scrubbing():
    cleaned = prompt_error("Could not convert string 'abc@x.com' " + "x" * 5000, limit=100)
    assert len(cleaned) <= 100 and "abc@x.com" not in cleaned


def test_codegen_prompt_gets_scrubbed_error():
    from src.agents.nodes.codegen import codegen_variables

    state = {"sandbox": {"passed": False, "error": "Could not convert string 'an@x.vn' to INT32"}, "code_files": {}}
    assert codegen_variables(state)["last_error"] == f"Could not convert string {MASK} to INT32"


def test_error_book_and_memory_keep_only_scrubbed_text():
    from src.agents.nodes.common import register_failure
    from src.services.error_memory import get_error_memory

    update = register_failure({}, "Conversion Error: Could not convert string 'Nguyễn Văn Canary' to INT32")
    assert all("Canary" not in note for note in update["error_notes"])
    entries = get_error_memory().pending()
    assert entries and all("Canary" not in e.description for e in entries)
