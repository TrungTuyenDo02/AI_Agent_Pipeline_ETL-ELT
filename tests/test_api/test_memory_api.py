"""Bộ nhớ agent nối vào lần chạy: ghi (chờ duyệt) khi tự sửa xong, đọc lại chỉ mục đã duyệt của đúng tài khoản, Reviewer duyệt."""

from httpx import AsyncClient

from src.agents.nodes.common import memory_notes, register_failure, remember_fixes
from src.services.agent_memory import get_agent_memory

API = "/api/v1"


def test_remember_fixes_only_after_a_fix_and_stays_pending():
    failed = register_failure({"requester": "an", "fix_attempts": 0}, "Binder Error: column 'amt' not found 1.075.000")
    values = {"requester": "an", "fix_attempts": 1, **failed}
    assert remember_fixes("r1", {"requester": "an", "fix_attempts": 0, "error_notes": ["x"]}) == 0  # chưa sửa gì
    assert remember_fixes("r1", values) == 1
    assert memory_notes({"requester": "an", "request_text": "doanh thu"}) == []  # chờ duyệt thì chưa vào prompt
    item = get_agent_memory().pending("an")[0]
    assert "tự sửa được sau 1 lần" in item.content and "r1" == item.source_run_id


def test_only_approved_items_of_same_account_reach_the_prompt():
    memory = get_agent_memory()
    mine = memory.add("an", "error_fix", "Lỗi cột amt không có; đã sửa", "r1")
    other = memory.add("binh", "error_fix", "Lỗi của người khác", "r2")
    memory.approve("an", mine.id)
    memory.approve("binh", other.id)
    assert memory_notes({"requester": "an", "request_text": "doanh thu"}) == ["Lỗi cột amt không có; đã sửa"]
    assert memory_notes({"requester": ""}) == []


async def test_reviewer_approves_and_engineer_cannot(client: AsyncClient, login):
    item = get_agent_memory().add("an", "error_fix", "Lỗi ngày sai định dạng; đã sửa", "r9")
    engineer = await login("engineer")
    assert (await engineer.get(f"{API}/memory")).status_code == 403
    reviewer = await login("reviewer")
    listed = (await reviewer.get(f"{API}/memory")).json()
    assert item.id in [i["id"] for i in listed]  # kho dùng chung giữa các test: không đòi danh sách chỉ có một mục
    assert (await reviewer.post(f"{API}/memory/{item.id}/approve")).status_code == 200
    assert get_agent_memory().approved("an")[0].id == item.id
    assert (await reviewer.post(f"{API}/memory/999/discard")).status_code == 404
