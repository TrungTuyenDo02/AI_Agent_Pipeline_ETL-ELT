// SINH TỰ ĐỘNG bởi `python scripts/demo_fixtures.py` — không sửa tay.
// Chụp từ luồng thật với LLM_PROVIDER=mock trên dữ liệu nguồn giả lập (không có dữ liệu thật, không có khóa).
// Token/chi phí/thời gian LLM là SỐ LIỆU MẪU; web luôn ghi chú "số liệu mẫu" bên cạnh.
import type { DemoFixtures } from "./types";

export const RUN_TOKEN = "__RUN__";

export const FIXTURES = {
 "request": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
 "stoppedRequest": "Tính doanh thu theo tuần của 3 kênh bán",
 "snapshots": {
  "clarify": {
   "record": {
    "id": "__RUN__",
    "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
    "requester": "khach",
    "status": "waiting_clarification",
    "provider": "demo",
    "model": "mô hình mẫu",
    "created_at": "2026-10-17T15:00:14+00:00",
    "updated_at": "2026-10-17T15:00:16+00:00",
    "summary": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "fix_attempts": 0,
     "rescue_count": 0,
     "review_rounds": 0,
     "optimization": null,
     "improvement_pct": null,
     "llm_calls": 1,
     "tokens": 4540,
     "cost_usd": 0.0213,
     "simulated": false,
     "workspace": null,
     "error": ""
    }
   },
   "busy": false,
   "pending": {
    "kind": "clarify",
    "unknowns": [
     "Trạng thái đơn nào được tính doanh thu",
     "Cách xử lý mã đơn bị trùng trong cùng nguồn"
    ],
    "questions": [
     {
      "id": "q_status",
      "question": "Đơn ở trạng thái nào được tính vào doanh thu?",
      "options": [
       "Chỉ đơn đã giao/hoàn tất",
       "Mọi đơn trừ đơn đã hủy (kể cả đơn hoàn tiền)"
      ],
      "column": "",
      "multiple": false
     },
     {
      "id": "q_duplicates",
      "question": "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao?",
      "options": [
       "Tính một lần (bỏ dòng trùng mã đơn)",
       "Giữ nguyên mọi dòng"
      ],
      "column": "",
      "multiple": false
     }
    ]
   },
   "events": [
    {
     "node": "input_gate",
     "label": "G0 Kiểm tra đầu vào",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.03,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "drift_gate",
     "label": "G1 Kiểm tra cấu trúc nguồn",
     "ok": true,
     "detail": "chưa kiểm (không có cơ sở dữ liệu)",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 1.49,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": false,
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    }
   ],
   "spec": {
    "target": "fct_daily_revenue",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    "grain": [
     "order_date"
    ],
    "output_columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "description": "Ngày đặt đơn",
      "references": ""
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "description": "Số đơn hợp lệ trong ngày",
      "references": ""
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "description": "Tổng doanh thu (VND)",
      "references": ""
     }
    ],
    "metrics": [
     {
      "name": "revenue_vnd",
      "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
     }
    ],
    "filters": [
     "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
    ],
    "assumptions": [],
    "plan_summary": "",
    "plan": [],
    "sources": [
     {
      "name": "san_a_orders",
      "kind": "csv"
     },
     {
      "name": "san_b_orders",
      "kind": "json"
     },
     {
      "name": "website_orders",
      "kind": "sqlite"
     }
    ]
   },
   "answered": [],
   "evidence": {},
   "optimization": {},
   "sandbox": {},
   "code_notes": [],
   "test_notes": [],
   "stages": [
    {
     "id": "input_gate",
     "code": "G0",
     "label": "Kiểm tra đầu vào",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "drift_gate",
     "code": "G1",
     "label": "Kiểm tra cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "chưa kiểm (không có cơ sở dữ liệu)"
    },
    {
     "id": "planner",
     "code": "E1",
     "label": "Lập kế hoạch",
     "kind": "E",
     "state": "passed",
     "detail": "bảng đích fct_daily_revenue, mode ELT"
    },
    {
     "id": "clarify",
     "code": "J1",
     "label": "Hỏi làm rõ",
     "kind": "J",
     "state": "human",
     "detail": "chờ bạn"
    },
    {
     "id": "spec_check",
     "code": "V0",
     "label": "Soát đặc tả",
     "kind": "V",
     "state": "failed",
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn"
    },
    {
     "id": "plan_review",
     "code": "J1b",
     "label": "Duyệt kế hoạch",
     "kind": "J",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "prepare",
     "code": "E0–E2",
     "label": "Nạp và soi dữ liệu",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "schema",
     "code": "Vs",
     "label": "Soát cấu trúc nguồn",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "codegen",
     "code": "E3",
     "label": "Sinh code",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "testgen",
     "code": "E3b",
     "label": "Sinh test",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "safety",
     "code": "V1",
     "label": "Kiểm an toàn",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "sandbox",
     "code": "V2",
     "label": "Chạy thử",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "optimizer",
     "code": "E4",
     "label": "Tối ưu",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "compare",
     "code": "V3",
     "label": "Đối chiếu",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "review",
     "code": "J2",
     "label": "Duyệt code",
     "kind": "J",
     "state": "waiting",
     "detail": ""
    }
   ],
   "usage": {
    "rows": [
     {
      "task": "planner",
      "calls": 1,
      "input_tokens": 3900,
      "output_tokens": 640,
      "cached_tokens": 1170,
      "cost_usd": 0.0213,
      "seconds": 6.2,
      "models": [
       "mô hình mẫu"
      ]
     }
    ],
    "cache_hit_rate": 0.3,
    "simulated": false
   },
   "current": null,
   "queue_position": null,
   "schema_report": {},
   "schema_decision": {},
   "value_filters": [],
   "reconciliation": [],
   "retryable": false,
   "drift": {
    "checked": false,
    "warnings": []
   }
  },
  "plan": {
   "record": {
    "id": "__RUN__",
    "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
    "requester": "khach",
    "status": "waiting_plan_review",
    "provider": "demo",
    "model": "mô hình mẫu",
    "created_at": "2026-10-17T15:00:14+00:00",
    "updated_at": "2026-10-17T15:00:16+00:00",
    "summary": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "fix_attempts": 0,
     "rescue_count": 0,
     "review_rounds": 0,
     "optimization": null,
     "improvement_pct": null,
     "llm_calls": 2,
     "tokens": 9080,
     "cost_usd": 0.0426,
     "simulated": false,
     "workspace": null,
     "error": ""
    }
   },
   "busy": false,
   "pending": {
    "kind": "plan",
    "summary": "Tạo bảng fct_daily_revenue: mỗi ngày một dòng, cho biết số đơn và doanh thu (VND) gộp từ Sàn A, Sàn B và website; chỉ đơn đã giao/hoàn tất.",
    "steps": [
     {
      "title": "Làm sạch đơn Sàn A",
      "detail": "stg_san_a_orders: đọc order_date dạng dd/mm/yyyy lẫn yyyy-mm-dd, total_amount dạng '1.075.000'.",
      "reason": "Mẫu dữ liệu Sàn A có hai kiểu ngày và tiền là chuỗi có dấu chấm."
     },
     {
      "title": "Làm sạch đơn Sàn B và website",
      "detail": "stg_san_b_orders (created_at ISO, grand_total số), stg_website_orders (created_ts, amount_vnd).",
      "reason": "Mỗi nguồn đặt tên cột và trạng thái khác nhau; phải đưa về cùng bộ cột."
     },
     {
      "title": "Gộp 3 nguồn, bỏ đơn trùng",
      "detail": "Ghép các đơn bằng UNION, giữ cột nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
      "reason": "Bạn đã chọn: Tính một lần (bỏ dòng trùng mã đơn)."
     },
     {
      "title": "Tính doanh thu theo ngày",
      "detail": "fct_daily_revenue: order_date, order_count, revenue_vnd; chỉ đơn đã giao/hoàn tất.",
      "reason": "Yêu cầu là doanh thu ngày; trạng thái được tính theo câu trả lời làm rõ."
     }
    ],
    "spec": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
     "grain": [
      "order_date"
     ],
     "output_columns": [
      {
       "name": "order_date",
       "type": "DATE",
       "description": "Ngày đặt đơn",
       "references": ""
      },
      {
       "name": "order_count",
       "type": "BIGINT",
       "description": "Số đơn hợp lệ trong ngày",
       "references": ""
      },
      {
       "name": "revenue_vnd",
       "type": "BIGINT",
       "description": "Tổng doanh thu (VND)",
       "references": ""
      }
     ],
     "metrics": [
      {
       "name": "revenue_vnd",
       "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
      }
     ],
     "filters": [
      "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
     ],
     "assumptions": [
      "q_status: Chỉ đơn đã giao/hoàn tất",
      "q_duplicates: Tính một lần (bỏ dòng trùng mã đơn)",
      "Đơn ở trạng thái nào được tính vào doanh thu? → Chỉ đơn đã giao/hoàn tất",
      "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao? → Tính một lần (bỏ dòng trùng mã đơn)"
     ],
     "options": {
      "load_mode": "full",
      "load_reason": "Dữ liệu còn nhỏ (dưới 100,000 dòng) nên nạp toàn bộ mỗi lần: đơn giản và không bỏ sót dòng bị sửa.",
      "incremental_column": "",
      "schedule": "daily",
      "schedule_reason": "Yêu cầu không nêu tần suất nên chọn mặc định hằng ngày.",
      "connections": [
       {
        "source": "san_a_orders",
        "kind": "file",
        "via": "đọc tệp trong thư mục dữ liệu"
       },
       {
        "source": "san_b_orders",
        "kind": "file",
        "via": "đọc tệp trong thư mục dữ liệu"
       },
       {
        "source": "website_orders",
        "kind": "file",
        "via": "đọc tệp trong thư mục dữ liệu"
       }
      ]
     },
     "glossary_used": [
      {
       "term": "doanh thu theo ngày",
       "definition": "Doanh thu gộp theo ngày đặt đơn; mỗi ngày một dòng."
      },
      {
       "term": "doanh thu",
       "definition": "Tổng tiền VND của các đơn đã hoàn tất; không tính đơn hủy, đơn hoàn tiền và đơn đang xử lý."
      }
     ]
    },
    "sources": [
     "san_a_orders",
     "san_b_orders",
     "website_orders"
    ],
    "next_steps": "Sau khi bạn đồng ý: nạp nguồn vào sandbox → soi dữ liệu → sinh model dbt + DAG → Tester độc lập viết test (không xem code) → chạy thử trong sandbox → tối ưu nếu đáng → bạn duyệt code (J2).",
    "time_columns": [
     "amount_vnd",
     "buyer_email",
     "created_at",
     "created_ts",
     "customer_email",
     "customer_phone",
     "email",
     "grand_total",
     "id",
     "order_date",
     "order_id",
     "phone",
     "state",
     "status",
     "total_amount"
    ],
    "drift_warnings": [],
    "option_choices": {
     "load_mode": [
      {
       "value": "full",
       "label": "Nạp toàn bộ mỗi lần chạy"
      },
      {
       "value": "incremental",
       "label": "Chỉ nạp phần mới (theo cột thời gian)"
      }
     ],
     "schedule": [
      {
       "value": "hourly",
       "label": "Hằng giờ"
      },
      {
       "value": "daily",
       "label": "Hằng ngày"
      },
      {
       "value": "event",
       "label": "Theo sự kiện (kích hoạt từ bên ngoài)"
      }
     ]
    }
   },
   "events": [
    {
     "node": "input_gate",
     "label": "G0 Kiểm tra đầu vào",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.03,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "drift_gate",
     "label": "G1 Kiểm tra cấu trúc nguồn",
     "ok": true,
     "detail": "chưa kiểm (không có cơ sở dữ liệu)",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 1.49,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": false,
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "clarify",
     "label": "J1 Hỏi làm rõ",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 0.04,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    }
   ],
   "spec": {
    "target": "fct_daily_revenue",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    "grain": [
     "order_date"
    ],
    "output_columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "description": "Ngày đặt đơn",
      "references": ""
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "description": "Số đơn hợp lệ trong ngày",
      "references": ""
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "description": "Tổng doanh thu (VND)",
      "references": ""
     }
    ],
    "metrics": [
     {
      "name": "revenue_vnd",
      "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
     }
    ],
    "filters": [
     "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
    ],
    "assumptions": [
     "q_status: Chỉ đơn đã giao/hoàn tất",
     "q_duplicates: Tính một lần (bỏ dòng trùng mã đơn)",
     "Đơn ở trạng thái nào được tính vào doanh thu? → Chỉ đơn đã giao/hoàn tất",
     "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao? → Tính một lần (bỏ dòng trùng mã đơn)"
    ],
    "plan_summary": "Tạo bảng fct_daily_revenue: mỗi ngày một dòng, cho biết số đơn và doanh thu (VND) gộp từ Sàn A, Sàn B và website; chỉ đơn đã giao/hoàn tất.",
    "plan": [
     {
      "title": "Làm sạch đơn Sàn A",
      "detail": "stg_san_a_orders: đọc order_date dạng dd/mm/yyyy lẫn yyyy-mm-dd, total_amount dạng '1.075.000'.",
      "reason": "Mẫu dữ liệu Sàn A có hai kiểu ngày và tiền là chuỗi có dấu chấm."
     },
     {
      "title": "Làm sạch đơn Sàn B và website",
      "detail": "stg_san_b_orders (created_at ISO, grand_total số), stg_website_orders (created_ts, amount_vnd).",
      "reason": "Mỗi nguồn đặt tên cột và trạng thái khác nhau; phải đưa về cùng bộ cột."
     },
     {
      "title": "Gộp 3 nguồn, bỏ đơn trùng",
      "detail": "Ghép các đơn bằng UNION, giữ cột nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
      "reason": "Bạn đã chọn: Tính một lần (bỏ dòng trùng mã đơn)."
     },
     {
      "title": "Tính doanh thu theo ngày",
      "detail": "fct_daily_revenue: order_date, order_count, revenue_vnd; chỉ đơn đã giao/hoàn tất.",
      "reason": "Yêu cầu là doanh thu ngày; trạng thái được tính theo câu trả lời làm rõ."
     }
    ],
    "sources": [
     {
      "name": "san_a_orders",
      "kind": "csv"
     },
     {
      "name": "san_b_orders",
      "kind": "json"
     },
     {
      "name": "website_orders",
      "kind": "sqlite"
     }
    ]
   },
   "answered": [
    {
     "id": "q_status",
     "question": "Đơn ở trạng thái nào được tính vào doanh thu?",
     "answer": "Chỉ đơn đã giao/hoàn tất"
    },
    {
     "id": "q_duplicates",
     "question": "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao?",
     "answer": "Tính một lần (bỏ dòng trùng mã đơn)"
    }
   ],
   "evidence": {},
   "optimization": {},
   "sandbox": {},
   "code_notes": [],
   "test_notes": [],
   "stages": [
    {
     "id": "input_gate",
     "code": "G0",
     "label": "Kiểm tra đầu vào",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "drift_gate",
     "code": "G1",
     "label": "Kiểm tra cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "chưa kiểm (không có cơ sở dữ liệu)"
    },
    {
     "id": "planner",
     "code": "E1",
     "label": "Lập kế hoạch",
     "kind": "E",
     "state": "passed",
     "detail": "bảng đích fct_daily_revenue, mode ELT"
    },
    {
     "id": "clarify",
     "code": "J1",
     "label": "Hỏi làm rõ",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "spec_check",
     "code": "V0",
     "label": "Soát đặc tả",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "plan_review",
     "code": "J1b",
     "label": "Duyệt kế hoạch",
     "kind": "J",
     "state": "human",
     "detail": "chờ bạn"
    },
    {
     "id": "prepare",
     "code": "E0–E2",
     "label": "Nạp và soi dữ liệu",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "schema",
     "code": "Vs",
     "label": "Soát cấu trúc nguồn",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "codegen",
     "code": "E3",
     "label": "Sinh code",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "testgen",
     "code": "E3b",
     "label": "Sinh test",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "safety",
     "code": "V1",
     "label": "Kiểm an toàn",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "sandbox",
     "code": "V2",
     "label": "Chạy thử",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "optimizer",
     "code": "E4",
     "label": "Tối ưu",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "compare",
     "code": "V3",
     "label": "Đối chiếu",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "review",
     "code": "J2",
     "label": "Duyệt code",
     "kind": "J",
     "state": "waiting",
     "detail": ""
    }
   ],
   "usage": {
    "rows": [
     {
      "task": "planner",
      "calls": 2,
      "input_tokens": 7800,
      "output_tokens": 1280,
      "cached_tokens": 2340,
      "cost_usd": 0.0426,
      "seconds": 12.4,
      "models": [
       "mô hình mẫu"
      ]
     }
    ],
    "cache_hit_rate": 0.3,
    "simulated": false
   },
   "current": null,
   "queue_position": null,
   "schema_report": {},
   "schema_decision": {},
   "value_filters": [],
   "reconciliation": [],
   "retryable": false,
   "drift": {
    "checked": false,
    "warnings": []
   }
  },
  "review": {
   "record": {
    "id": "__RUN__",
    "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
    "requester": "khach",
    "status": "waiting_review",
    "provider": "demo",
    "model": "mô hình mẫu",
    "created_at": "2026-10-17T15:00:14+00:00",
    "updated_at": "2026-10-17T15:01:29+00:00",
    "summary": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "fix_attempts": 0,
     "rescue_count": 0,
     "review_rounds": 0,
     "optimization": "applied",
     "improvement_pct": 54.5,
     "llm_calls": 5,
     "tokens": 28530,
     "cost_usd": 0.158,
     "simulated": false,
     "workspace": null,
     "error": ""
    }
   },
   "busy": false,
   "pending": {
    "kind": "review",
    "run_id": "__RUN__",
    "requester": "khach"
   },
   "events": [
    {
     "node": "input_gate",
     "label": "G0 Kiểm tra đầu vào",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.03,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "drift_gate",
     "label": "G1 Kiểm tra cấu trúc nguồn",
     "ok": true,
     "detail": "chưa kiểm (không có cơ sở dữ liệu)",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 1.49,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": false,
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "clarify",
     "label": "J1 Hỏi làm rõ",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 0.04,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "plan_review",
     "label": "J1b Duyệt kế hoạch",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "ingest",
     "label": "E0 Nhận nguồn",
     "ok": true,
     "detail": "san_a_orders: 126 dòng, san_b_orders: 120 dòng, website_orders: 120 dòng",
     "seconds": 0.18,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "profiler",
     "label": "P  Soi dữ liệu",
     "ok": true,
     "detail": "3 bảng",
     "seconds": 0.31,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "schema_guard",
     "label": "Vs Soát cấu trúc nguồn",
     "ok": true,
     "detail": "Không đổi so với bản đã duyệt.",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "mock_data",
     "label": "E2 Dữ liệu thử",
     "ok": true,
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney",
     "seconds": 0.84,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "codegen",
     "label": "E3 Sinh code",
     "ok": true,
     "detail": "5 file",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "testgen",
     "label": "E3b Sinh test",
     "ok": true,
     "detail": "6 file test",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": true,
     "detail": "không phát hiện vấn đề",
     "seconds": 0.63,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "sandbox_run",
     "label": "V2 Chạy sandbox",
     "ok": true,
     "detail": "1/1 model, 17/17 test đạt",
     "seconds": 24.32,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "optimizer",
     "label": "E4 Tối ưu",
     "ok": true,
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ sqlglot",
     "seconds": 4.59,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "compare",
     "label": "V3 Đối chiếu",
     "ok": false,
     "detail": "ứng viên chưa đạt, thử ứng viên kế tiếp",
     "seconds": 2.83,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "optimizer",
     "label": "E4 Tối ưu",
     "ok": true,
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm",
     "seconds": 1.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "compare",
     "label": "V3 Đối chiếu",
     "ok": true,
     "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
     "seconds": 3.71,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": true,
     "detail": "không phát hiện vấn đề",
     "seconds": 1.42,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "sandbox_run",
     "label": "V2 Chạy sandbox",
     "ok": true,
     "detail": "1/1 model, 17/17 test đạt",
     "seconds": 33.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "package",
     "label": "Đóng gói bản duyệt",
     "ok": true,
     "detail": "",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    }
   ],
   "spec": {
    "target": "fct_daily_revenue",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    "grain": [
     "order_date"
    ],
    "output_columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "description": "Ngày đặt đơn",
      "references": ""
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "description": "Số đơn hợp lệ trong ngày",
      "references": ""
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "description": "Tổng doanh thu (VND)",
      "references": ""
     }
    ],
    "metrics": [
     {
      "name": "revenue_vnd",
      "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
     }
    ],
    "filters": [
     "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
    ],
    "assumptions": [
     "q_status: Chỉ đơn đã giao/hoàn tất",
     "q_duplicates: Tính một lần (bỏ dòng trùng mã đơn)",
     "Đơn ở trạng thái nào được tính vào doanh thu? → Chỉ đơn đã giao/hoàn tất",
     "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao? → Tính một lần (bỏ dòng trùng mã đơn)"
    ],
    "plan_summary": "Tạo bảng fct_daily_revenue: mỗi ngày một dòng, cho biết số đơn và doanh thu (VND) gộp từ Sàn A, Sàn B và website; chỉ đơn đã giao/hoàn tất.",
    "plan": [
     {
      "title": "Làm sạch đơn Sàn A",
      "detail": "stg_san_a_orders: đọc order_date dạng dd/mm/yyyy lẫn yyyy-mm-dd, total_amount dạng '1.075.000'.",
      "reason": "Mẫu dữ liệu Sàn A có hai kiểu ngày và tiền là chuỗi có dấu chấm."
     },
     {
      "title": "Làm sạch đơn Sàn B và website",
      "detail": "stg_san_b_orders (created_at ISO, grand_total số), stg_website_orders (created_ts, amount_vnd).",
      "reason": "Mỗi nguồn đặt tên cột và trạng thái khác nhau; phải đưa về cùng bộ cột."
     },
     {
      "title": "Gộp 3 nguồn, bỏ đơn trùng",
      "detail": "Ghép các đơn bằng UNION, giữ cột nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
      "reason": "Bạn đã chọn: Tính một lần (bỏ dòng trùng mã đơn)."
     },
     {
      "title": "Tính doanh thu theo ngày",
      "detail": "fct_daily_revenue: order_date, order_count, revenue_vnd; chỉ đơn đã giao/hoàn tất.",
      "reason": "Yêu cầu là doanh thu ngày; trạng thái được tính theo câu trả lời làm rõ."
     }
    ],
    "sources": [
     {
      "name": "san_a_orders",
      "kind": "csv"
     },
     {
      "name": "san_b_orders",
      "kind": "json"
     },
     {
      "name": "website_orders",
      "kind": "sqlite"
     }
    ]
   },
   "answered": [
    {
     "id": "q_status",
     "question": "Đơn ở trạng thái nào được tính vào doanh thu?",
     "answer": "Chỉ đơn đã giao/hoàn tất"
    },
    {
     "id": "q_duplicates",
     "question": "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao?",
     "answer": "Tính một lần (bỏ dòng trùng mã đơn)"
    }
   ],
   "evidence": {
    "measured": [
     {
      "node": "V0 Soát spec",
      "check": "Đặc tả đủ trường, không còn điểm chưa rõ",
      "result": "Đạt",
      "passed": true
     },
     {
      "node": "V0 Soát spec",
      "check": "Chế độ pipeline",
      "result": "ELT — Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
      "passed": null
     },
     {
      "node": "E0 Nhận nguồn",
      "check": "Số dòng nạp vào sandbox",
      "result": "san_a_orders: 126, san_b_orders: 120, website_orders: 120",
      "passed": null
     },
     {
      "node": "V1 An toàn",
      "check": "Lệnh nguy hiểm, tên bảng/cột bịa",
      "result": "Không phát hiện",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "dbt build (model)",
      "result": "1/1 model chạy được",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "dbt test (đối soát, grain, not_null)",
      "result": "17/17 test đạt",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "Số dòng bảng đích",
      "result": "30",
      "passed": null
     },
     {
      "node": "Vòng sửa",
      "check": "Số lần sửa / cứu hộ",
      "result": "0 lần sửa, 0 lần cứu hộ",
      "passed": null
     },
     {
      "node": "Vs Cấu trúc nguồn",
      "check": "So với bản Reviewer đã duyệt",
      "result": "Không đổi so với bản đã duyệt.",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "san_a_orders → stg_san_a_orders",
      "result": "126 vào → 126 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "san_b_orders → stg_san_b_orders",
      "result": "120 vào → 120 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "website_orders → stg_website_orders",
      "result": "120 vào → 120 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "Điều kiện theo giá trị",
      "check": "So sánh cột với giá trị cụ thể (tô sáng ở màn duyệt)",
      "result": "1 điều kiện, 1 giá trị không có trong đặc tả/câu trả lời",
      "passed": null
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'small'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'dirty'",
      "result": "Giống hệt (29 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'empty'",
      "result": "Giống hệt (0 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'few'",
      "result": "Giống hệt (6 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'dupkeys'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'nullmoney'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'sandbox'",
      "result": "Giống hệt bản gốc trên dữ liệu sandbox (30 dòng)",
      "passed": true
     },
     {
      "node": "E4/V3 Tối ưu",
      "check": "Thời gian trung vị trên bộ large",
      "result": "171.169 ms → 77.862 ms",
      "passed": null
     },
     {
      "node": "E4/V3 Tối ưu",
      "check": "Quyết định",
      "result": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
      "passed": null
     }
    ],
    "claimed": [
     "Mỗi nguồn một model staging chuẩn hóa ngày, tiền VND và trạng thái về cùng một bộ giá trị.",
     "Model đích gộp 3 nguồn, bỏ trùng theo (nguồn, mã đơn), tính theo ngày.",
     "DAG Airflow kiểm cấu trúc nguồn (preflight), chạy dbt run rồi dbt test hằng ngày.",
     "Test tất định: cột grain không rỗng, grain không trùng, giá trị ngày/tiền ép được kiểu (≥ 99%).",
     "Tính lại từ raw: mỗi ngày một dòng, số đơn và tổng tiền các đơn hợp lệ (bỏ dòng trùng nếu được chọn).",
     "Optimizer: Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần."
    ]
   },
   "optimization": {
    "original_sql": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_a_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_b_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_website_orders\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date",
    "proposed_sql": "/* Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần */\nWITH all_orders AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_a_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_b_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_website_orders\n), deduped AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM all_orders\n  QUALIFY\n    ROW_NUMBER() OVER (PARTITION BY source, order_id ORDER BY order_date, amount_vnd DESC, status) = 1\n)\nSELECT\n  order_date,\n  COUNT(*) AS order_count,\n  CAST(COALESCE(SUM(amount_vnd), 0) AS BIGINT) AS revenue_vnd\nFROM deduped\nWHERE\n  status IN ('completed')\nGROUP BY\n  order_date\nORDER BY\n  order_date",
    "findings": [
     {
      "rule": "union_distinct",
      "message": "UNION (khử trùng) thay vì UNION ALL: phải băm toàn bộ dòng để loại trùng."
     },
     {
      "rule": "window_dedupe",
      "message": "row_number() theo PARTITION BY để khử trùng: tốn phân vùng/sắp xếp; thừa nếu khóa đã duy nhất."
     }
    ],
    "before": {
     "median_ms": 171.169,
     "runs": 5,
     "peak_memory_mb": 97.4
    },
    "after": {
     "median_ms": 77.862,
     "runs": 5,
     "peak_memory_mb": 31.9
    },
    "improvement_pct": 54.5,
    "decision": "applied",
    "reason": "Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
    "attempts": 2,
    "equivalence": [
     {
      "dataset": "small",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "dirty",
      "equal": true,
      "detail": "Giống hệt (29 dòng)"
     },
     {
      "dataset": "empty",
      "equal": true,
      "detail": "Giống hệt (0 dòng)"
     },
     {
      "dataset": "few",
      "equal": true,
      "detail": "Giống hệt (6 dòng)"
     },
     {
      "dataset": "dupkeys",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "nullmoney",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "sandbox",
      "equal": true,
      "detail": "Giống hệt bản gốc trên dữ liệu sandbox (30 dòng)"
     }
    ],
    "llm_cost_usd": 0.024,
    "explanation": "Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần.",
    "warehouse_hints": [
     "BigQuery/Snowflake: phân vùng bảng đích theo order_date và cluster theo source (chỉ gợi ý)."
    ]
   },
   "sandbox": {
    "passed": true,
    "error": "",
    "target_rows": 30,
    "sample": [
     {
      "order_date": "2026-09-01",
      "order_count": "2",
      "revenue_vnd": "5168000"
     },
     {
      "order_date": "2026-09-02",
      "order_count": "6",
      "revenue_vnd": "8608000"
     },
     {
      "order_date": "2026-09-03",
      "order_count": "10",
      "revenue_vnd": "16402000"
     },
     {
      "order_date": "2026-09-04",
      "order_count": "6",
      "revenue_vnd": "10088000"
     },
     {
      "order_date": "2026-09-05",
      "order_count": "12",
      "revenue_vnd": "24429000"
     },
     {
      "order_date": "2026-09-06",
      "order_count": "7",
      "revenue_vnd": "9959000"
     },
     {
      "order_date": "2026-09-07",
      "order_count": "6",
      "revenue_vnd": "10250000"
     },
     {
      "order_date": "2026-09-08",
      "order_count": "10",
      "revenue_vnd": "13961000"
     },
     {
      "order_date": "2026-09-09",
      "order_count": "6",
      "revenue_vnd": "9289000"
     },
     {
      "order_date": "2026-09-10",
      "order_count": "10",
      "revenue_vnd": "15045000"
     }
    ],
    "models_ok": 1,
    "models_total": 1,
    "tests_ok": 17,
    "tests_total": 17
   },
   "code_notes": [
    "Mỗi nguồn một model staging chuẩn hóa ngày, tiền VND và trạng thái về cùng một bộ giá trị.",
    "Model đích gộp 3 nguồn, bỏ trùng theo (nguồn, mã đơn), tính theo ngày.",
    "DAG Airflow kiểm cấu trúc nguồn (preflight), chạy dbt run rồi dbt test hằng ngày."
   ],
   "test_notes": [
    "Test tất định: cột grain không rỗng, grain không trùng, giá trị ngày/tiền ép được kiểu (≥ 99%).",
    "Tính lại từ raw: mỗi ngày một dòng, số đơn và tổng tiền các đơn hợp lệ (bỏ dòng trùng nếu được chọn)."
   ],
   "stages": [
    {
     "id": "input_gate",
     "code": "G0",
     "label": "Kiểm tra đầu vào",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "drift_gate",
     "code": "G1",
     "label": "Kiểm tra cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "chưa kiểm (không có cơ sở dữ liệu)"
    },
    {
     "id": "planner",
     "code": "E1",
     "label": "Lập kế hoạch",
     "kind": "E",
     "state": "passed",
     "detail": "bảng đích fct_daily_revenue, mode ELT"
    },
    {
     "id": "clarify",
     "code": "J1",
     "label": "Hỏi làm rõ",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "spec_check",
     "code": "V0",
     "label": "Soát đặc tả",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "plan_review",
     "code": "J1b",
     "label": "Duyệt kế hoạch",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "prepare",
     "code": "E0–E2",
     "label": "Nạp và soi dữ liệu",
     "kind": "E",
     "state": "passed",
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
    },
    {
     "id": "schema",
     "code": "Vs",
     "label": "Soát cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "Không đổi so với bản đã duyệt."
    },
    {
     "id": "codegen",
     "code": "E3",
     "label": "Sinh code",
     "kind": "E",
     "state": "passed",
     "detail": "5 file"
    },
    {
     "id": "testgen",
     "code": "E3b",
     "label": "Sinh test",
     "kind": "E",
     "state": "passed",
     "detail": "6 file test"
    },
    {
     "id": "safety",
     "code": "V1",
     "label": "Kiểm an toàn",
     "kind": "V",
     "state": "passed",
     "detail": "không phát hiện vấn đề"
    },
    {
     "id": "sandbox",
     "code": "V2",
     "label": "Chạy thử",
     "kind": "V",
     "state": "passed",
     "detail": "1/1 model, 17/17 test đạt"
    },
    {
     "id": "optimizer",
     "code": "E4",
     "label": "Tối ưu",
     "kind": "E",
     "state": "passed",
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
    },
    {
     "id": "compare",
     "code": "V3",
     "label": "Đối chiếu",
     "kind": "V",
     "state": "passed",
     "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu."
    },
    {
     "id": "review",
     "code": "J2",
     "label": "Duyệt code",
     "kind": "J",
     "state": "human",
     "detail": "chờ bạn"
    }
   ],
   "usage": {
    "rows": [
     {
      "task": "planner",
      "calls": 2,
      "input_tokens": 7800,
      "output_tokens": 1280,
      "cached_tokens": 2340,
      "cost_usd": 0.0426,
      "seconds": 12.4,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "codegen",
      "calls": 1,
      "input_tokens": 7100,
      "output_tokens": 2480,
      "cached_tokens": 2130,
      "cost_usd": 0.0585,
      "seconds": 14.6,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "testgen",
      "calls": 1,
      "input_tokens": 4200,
      "output_tokens": 1350,
      "cached_tokens": 1260,
      "cost_usd": 0.0329,
      "seconds": 8.1,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "optimizer",
      "calls": 1,
      "input_tokens": 3400,
      "output_tokens": 920,
      "cached_tokens": 1020,
      "cost_usd": 0.024,
      "seconds": 9.3,
      "models": [
       "mô hình mẫu"
      ]
     }
    ],
    "cache_hit_rate": 0.3,
    "simulated": false
   },
   "current": null,
   "queue_position": null,
   "schema_report": {
    "checked": true,
    "note": "",
    "changes": [
     {
      "source": "san_a_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "san_b_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "website_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     }
    ],
    "blocking": false
   },
   "schema_decision": {},
   "value_filters": [
    {
     "file": "models/marts/fct_daily_revenue.sql",
     "line": 44,
     "column": "status",
     "values": [
      "completed"
     ],
     "context": "lọc",
     "expression": "status IN ('completed')",
     "in_spec": false
    }
   ],
   "reconciliation": [
    {
     "model": "stg_san_a_orders",
     "source": "san_a_orders",
     "rows_in": 126,
     "rows_out": 126
    },
    {
     "model": "stg_san_b_orders",
     "source": "san_b_orders",
     "rows_in": 120,
     "rows_out": 120
    },
    {
     "model": "stg_website_orders",
     "source": "website_orders",
     "rows_in": 120,
     "rows_out": 120
    }
   ],
   "retryable": false,
   "drift": {
    "checked": false,
    "warnings": [],
    "recheck": {
     "blocked": false,
     "breaking": [],
     "warnings": []
    }
   }
  },
  "approved": {
   "record": {
    "id": "__RUN__",
    "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
    "requester": "khach",
    "status": "approved",
    "provider": "demo",
    "model": "mô hình mẫu",
    "created_at": "2026-10-17T15:00:14+00:00",
    "updated_at": "2026-10-17T15:01:35+00:00",
    "summary": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "fix_attempts": 0,
     "rescue_count": 0,
     "review_rounds": 0,
     "optimization": "applied",
     "improvement_pct": 54.5,
     "llm_calls": 5,
     "tokens": 28530,
     "cost_usd": 0.158,
     "simulated": false,
     "workspace": null,
     "error": ""
    }
   },
   "busy": false,
   "pending": null,
   "events": [
    {
     "node": "input_gate",
     "label": "G0 Kiểm tra đầu vào",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.03,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "drift_gate",
     "label": "G1 Kiểm tra cấu trúc nguồn",
     "ok": true,
     "detail": "chưa kiểm (không có cơ sở dữ liệu)",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 1.49,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": false,
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "clarify",
     "label": "J1 Hỏi làm rõ",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 0.04,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "plan_review",
     "label": "J1b Duyệt kế hoạch",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "ingest",
     "label": "E0 Nhận nguồn",
     "ok": true,
     "detail": "san_a_orders: 126 dòng, san_b_orders: 120 dòng, website_orders: 120 dòng",
     "seconds": 0.18,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "profiler",
     "label": "P  Soi dữ liệu",
     "ok": true,
     "detail": "3 bảng",
     "seconds": 0.31,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "schema_guard",
     "label": "Vs Soát cấu trúc nguồn",
     "ok": true,
     "detail": "Không đổi so với bản đã duyệt.",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "mock_data",
     "label": "E2 Dữ liệu thử",
     "ok": true,
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney",
     "seconds": 0.84,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "codegen",
     "label": "E3 Sinh code",
     "ok": true,
     "detail": "5 file",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "testgen",
     "label": "E3b Sinh test",
     "ok": true,
     "detail": "6 file test",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": true,
     "detail": "không phát hiện vấn đề",
     "seconds": 0.63,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "sandbox_run",
     "label": "V2 Chạy sandbox",
     "ok": true,
     "detail": "1/1 model, 17/17 test đạt",
     "seconds": 24.32,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "optimizer",
     "label": "E4 Tối ưu",
     "ok": true,
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ sqlglot",
     "seconds": 4.59,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "compare",
     "label": "V3 Đối chiếu",
     "ok": false,
     "detail": "ứng viên chưa đạt, thử ứng viên kế tiếp",
     "seconds": 2.83,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "optimizer",
     "label": "E4 Tối ưu",
     "ok": true,
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm",
     "seconds": 1.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "compare",
     "label": "V3 Đối chiếu",
     "ok": true,
     "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
     "seconds": 3.71,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": true,
     "detail": "không phát hiện vấn đề",
     "seconds": 1.42,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "sandbox_run",
     "label": "V2 Chạy sandbox",
     "ok": true,
     "detail": "1/1 model, 17/17 test đạt",
     "seconds": 33.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "package",
     "label": "Đóng gói bản duyệt",
     "ok": true,
     "detail": "",
     "seconds": 0.02,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "review",
     "label": "J2 Duyệt",
     "ok": true,
     "detail": "",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "finalize",
     "label": "Hoàn tất",
     "ok": true,
     "detail": "",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    }
   ],
   "spec": {
    "target": "fct_daily_revenue",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    "grain": [
     "order_date"
    ],
    "output_columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "description": "Ngày đặt đơn",
      "references": ""
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "description": "Số đơn hợp lệ trong ngày",
      "references": ""
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "description": "Tổng doanh thu (VND)",
      "references": ""
     }
    ],
    "metrics": [
     {
      "name": "revenue_vnd",
      "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
     }
    ],
    "filters": [
     "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
    ],
    "assumptions": [
     "q_status: Chỉ đơn đã giao/hoàn tất",
     "q_duplicates: Tính một lần (bỏ dòng trùng mã đơn)",
     "Đơn ở trạng thái nào được tính vào doanh thu? → Chỉ đơn đã giao/hoàn tất",
     "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao? → Tính một lần (bỏ dòng trùng mã đơn)"
    ],
    "plan_summary": "Tạo bảng fct_daily_revenue: mỗi ngày một dòng, cho biết số đơn và doanh thu (VND) gộp từ Sàn A, Sàn B và website; chỉ đơn đã giao/hoàn tất.",
    "plan": [
     {
      "title": "Làm sạch đơn Sàn A",
      "detail": "stg_san_a_orders: đọc order_date dạng dd/mm/yyyy lẫn yyyy-mm-dd, total_amount dạng '1.075.000'.",
      "reason": "Mẫu dữ liệu Sàn A có hai kiểu ngày và tiền là chuỗi có dấu chấm."
     },
     {
      "title": "Làm sạch đơn Sàn B và website",
      "detail": "stg_san_b_orders (created_at ISO, grand_total số), stg_website_orders (created_ts, amount_vnd).",
      "reason": "Mỗi nguồn đặt tên cột và trạng thái khác nhau; phải đưa về cùng bộ cột."
     },
     {
      "title": "Gộp 3 nguồn, bỏ đơn trùng",
      "detail": "Ghép các đơn bằng UNION, giữ cột nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
      "reason": "Bạn đã chọn: Tính một lần (bỏ dòng trùng mã đơn)."
     },
     {
      "title": "Tính doanh thu theo ngày",
      "detail": "fct_daily_revenue: order_date, order_count, revenue_vnd; chỉ đơn đã giao/hoàn tất.",
      "reason": "Yêu cầu là doanh thu ngày; trạng thái được tính theo câu trả lời làm rõ."
     }
    ],
    "sources": [
     {
      "name": "san_a_orders",
      "kind": "csv"
     },
     {
      "name": "san_b_orders",
      "kind": "json"
     },
     {
      "name": "website_orders",
      "kind": "sqlite"
     }
    ]
   },
   "answered": [
    {
     "id": "q_status",
     "question": "Đơn ở trạng thái nào được tính vào doanh thu?",
     "answer": "Chỉ đơn đã giao/hoàn tất"
    },
    {
     "id": "q_duplicates",
     "question": "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao?",
     "answer": "Tính một lần (bỏ dòng trùng mã đơn)"
    }
   ],
   "evidence": {
    "measured": [
     {
      "node": "V0 Soát spec",
      "check": "Đặc tả đủ trường, không còn điểm chưa rõ",
      "result": "Đạt",
      "passed": true
     },
     {
      "node": "V0 Soát spec",
      "check": "Chế độ pipeline",
      "result": "ELT — Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
      "passed": null
     },
     {
      "node": "E0 Nhận nguồn",
      "check": "Số dòng nạp vào sandbox",
      "result": "san_a_orders: 126, san_b_orders: 120, website_orders: 120",
      "passed": null
     },
     {
      "node": "V1 An toàn",
      "check": "Lệnh nguy hiểm, tên bảng/cột bịa",
      "result": "Không phát hiện",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "dbt build (model)",
      "result": "1/1 model chạy được",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "dbt test (đối soát, grain, not_null)",
      "result": "17/17 test đạt",
      "passed": true
     },
     {
      "node": "V2 Sandbox",
      "check": "Số dòng bảng đích",
      "result": "30",
      "passed": null
     },
     {
      "node": "Vòng sửa",
      "check": "Số lần sửa / cứu hộ",
      "result": "0 lần sửa, 0 lần cứu hộ",
      "passed": null
     },
     {
      "node": "Vs Cấu trúc nguồn",
      "check": "So với bản Reviewer đã duyệt",
      "result": "Không đổi so với bản đã duyệt.",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "san_a_orders → stg_san_a_orders",
      "result": "126 vào → 126 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "san_b_orders → stg_san_b_orders",
      "result": "120 vào → 120 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "V2 Đối chiếu số dòng",
      "check": "website_orders → stg_website_orders",
      "result": "120 vào → 120 ra (khớp; cần lý do ghi rõ nếu khác)",
      "passed": true
     },
     {
      "node": "Điều kiện theo giá trị",
      "check": "So sánh cột với giá trị cụ thể (tô sáng ở màn duyệt)",
      "result": "1 điều kiện, 1 giá trị không có trong đặc tả/câu trả lời",
      "passed": null
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'small'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'dirty'",
      "result": "Giống hệt (29 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'empty'",
      "result": "Giống hệt (0 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'few'",
      "result": "Giống hệt (6 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'dupkeys'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'nullmoney'",
      "result": "Giống hệt (30 dòng)",
      "passed": true
     },
     {
      "node": "V3 Đối chiếu",
      "check": "Kết quả bộ 'sandbox'",
      "result": "Giống hệt bản gốc trên dữ liệu sandbox (30 dòng)",
      "passed": true
     },
     {
      "node": "E4/V3 Tối ưu",
      "check": "Thời gian trung vị trên bộ large",
      "result": "171.169 ms → 77.862 ms",
      "passed": null
     },
     {
      "node": "E4/V3 Tối ưu",
      "check": "Quyết định",
      "result": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
      "passed": null
     }
    ],
    "claimed": [
     "Mỗi nguồn một model staging chuẩn hóa ngày, tiền VND và trạng thái về cùng một bộ giá trị.",
     "Model đích gộp 3 nguồn, bỏ trùng theo (nguồn, mã đơn), tính theo ngày.",
     "DAG Airflow kiểm cấu trúc nguồn (preflight), chạy dbt run rồi dbt test hằng ngày.",
     "Test tất định: cột grain không rỗng, grain không trùng, giá trị ngày/tiền ép được kiểu (≥ 99%).",
     "Tính lại từ raw: mỗi ngày một dòng, số đơn và tổng tiền các đơn hợp lệ (bỏ dòng trùng nếu được chọn).",
     "Optimizer: Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần."
    ]
   },
   "optimization": {
    "original_sql": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_a_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_b_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_website_orders\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date",
    "proposed_sql": "/* Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần */\nWITH all_orders AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_a_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_b_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_website_orders\n), deduped AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM all_orders\n  QUALIFY\n    ROW_NUMBER() OVER (PARTITION BY source, order_id ORDER BY order_date, amount_vnd DESC, status) = 1\n)\nSELECT\n  order_date,\n  COUNT(*) AS order_count,\n  CAST(COALESCE(SUM(amount_vnd), 0) AS BIGINT) AS revenue_vnd\nFROM deduped\nWHERE\n  status IN ('completed')\nGROUP BY\n  order_date\nORDER BY\n  order_date",
    "findings": [
     {
      "rule": "union_distinct",
      "message": "UNION (khử trùng) thay vì UNION ALL: phải băm toàn bộ dòng để loại trùng."
     },
     {
      "rule": "window_dedupe",
      "message": "row_number() theo PARTITION BY để khử trùng: tốn phân vùng/sắp xếp; thừa nếu khóa đã duy nhất."
     }
    ],
    "before": {
     "median_ms": 171.169,
     "runs": 5,
     "peak_memory_mb": 97.4
    },
    "after": {
     "median_ms": 77.862,
     "runs": 5,
     "peak_memory_mb": 31.9
    },
    "improvement_pct": 54.5,
    "decision": "applied",
    "reason": "Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
    "attempts": 2,
    "equivalence": [
     {
      "dataset": "small",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "dirty",
      "equal": true,
      "detail": "Giống hệt (29 dòng)"
     },
     {
      "dataset": "empty",
      "equal": true,
      "detail": "Giống hệt (0 dòng)"
     },
     {
      "dataset": "few",
      "equal": true,
      "detail": "Giống hệt (6 dòng)"
     },
     {
      "dataset": "dupkeys",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "nullmoney",
      "equal": true,
      "detail": "Giống hệt (30 dòng)"
     },
     {
      "dataset": "sandbox",
      "equal": true,
      "detail": "Giống hệt bản gốc trên dữ liệu sandbox (30 dòng)"
     }
    ],
    "llm_cost_usd": 0.024,
    "explanation": "Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần.",
    "warehouse_hints": [
     "BigQuery/Snowflake: phân vùng bảng đích theo order_date và cluster theo source (chỉ gợi ý)."
    ]
   },
   "sandbox": {
    "passed": true,
    "error": "",
    "target_rows": 30,
    "sample": [
     {
      "order_date": "2026-09-01",
      "order_count": "2",
      "revenue_vnd": "5168000"
     },
     {
      "order_date": "2026-09-02",
      "order_count": "6",
      "revenue_vnd": "8608000"
     },
     {
      "order_date": "2026-09-03",
      "order_count": "10",
      "revenue_vnd": "16402000"
     },
     {
      "order_date": "2026-09-04",
      "order_count": "6",
      "revenue_vnd": "10088000"
     },
     {
      "order_date": "2026-09-05",
      "order_count": "12",
      "revenue_vnd": "24429000"
     },
     {
      "order_date": "2026-09-06",
      "order_count": "7",
      "revenue_vnd": "9959000"
     },
     {
      "order_date": "2026-09-07",
      "order_count": "6",
      "revenue_vnd": "10250000"
     },
     {
      "order_date": "2026-09-08",
      "order_count": "10",
      "revenue_vnd": "13961000"
     },
     {
      "order_date": "2026-09-09",
      "order_count": "6",
      "revenue_vnd": "9289000"
     },
     {
      "order_date": "2026-09-10",
      "order_count": "10",
      "revenue_vnd": "15045000"
     }
    ],
    "models_ok": 1,
    "models_total": 1,
    "tests_ok": 17,
    "tests_total": 17
   },
   "code_notes": [
    "Mỗi nguồn một model staging chuẩn hóa ngày, tiền VND và trạng thái về cùng một bộ giá trị.",
    "Model đích gộp 3 nguồn, bỏ trùng theo (nguồn, mã đơn), tính theo ngày.",
    "DAG Airflow kiểm cấu trúc nguồn (preflight), chạy dbt run rồi dbt test hằng ngày."
   ],
   "test_notes": [
    "Test tất định: cột grain không rỗng, grain không trùng, giá trị ngày/tiền ép được kiểu (≥ 99%).",
    "Tính lại từ raw: mỗi ngày một dòng, số đơn và tổng tiền các đơn hợp lệ (bỏ dòng trùng nếu được chọn)."
   ],
   "stages": [
    {
     "id": "input_gate",
     "code": "G0",
     "label": "Kiểm tra đầu vào",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "drift_gate",
     "code": "G1",
     "label": "Kiểm tra cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "chưa kiểm (không có cơ sở dữ liệu)"
    },
    {
     "id": "planner",
     "code": "E1",
     "label": "Lập kế hoạch",
     "kind": "E",
     "state": "passed",
     "detail": "bảng đích fct_daily_revenue, mode ELT"
    },
    {
     "id": "clarify",
     "code": "J1",
     "label": "Hỏi làm rõ",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "spec_check",
     "code": "V0",
     "label": "Soát đặc tả",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "plan_review",
     "code": "J1b",
     "label": "Duyệt kế hoạch",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "prepare",
     "code": "E0–E2",
     "label": "Nạp và soi dữ liệu",
     "kind": "E",
     "state": "passed",
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
    },
    {
     "id": "schema",
     "code": "Vs",
     "label": "Soát cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "Không đổi so với bản đã duyệt."
    },
    {
     "id": "codegen",
     "code": "E3",
     "label": "Sinh code",
     "kind": "E",
     "state": "passed",
     "detail": "5 file"
    },
    {
     "id": "testgen",
     "code": "E3b",
     "label": "Sinh test",
     "kind": "E",
     "state": "passed",
     "detail": "6 file test"
    },
    {
     "id": "safety",
     "code": "V1",
     "label": "Kiểm an toàn",
     "kind": "V",
     "state": "passed",
     "detail": "không phát hiện vấn đề"
    },
    {
     "id": "sandbox",
     "code": "V2",
     "label": "Chạy thử",
     "kind": "V",
     "state": "passed",
     "detail": "1/1 model, 17/17 test đạt"
    },
    {
     "id": "optimizer",
     "code": "E4",
     "label": "Tối ưu",
     "kind": "E",
     "state": "passed",
     "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
    },
    {
     "id": "compare",
     "code": "V3",
     "label": "Đối chiếu",
     "kind": "V",
     "state": "passed",
     "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu."
    },
    {
     "id": "review",
     "code": "J2",
     "label": "Duyệt code",
     "kind": "J",
     "state": "passed",
     "detail": ""
    }
   ],
   "usage": {
    "rows": [
     {
      "task": "planner",
      "calls": 2,
      "input_tokens": 7800,
      "output_tokens": 1280,
      "cached_tokens": 2340,
      "cost_usd": 0.0426,
      "seconds": 12.4,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "codegen",
      "calls": 1,
      "input_tokens": 7100,
      "output_tokens": 2480,
      "cached_tokens": 2130,
      "cost_usd": 0.0585,
      "seconds": 14.6,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "testgen",
      "calls": 1,
      "input_tokens": 4200,
      "output_tokens": 1350,
      "cached_tokens": 1260,
      "cost_usd": 0.0329,
      "seconds": 8.1,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "optimizer",
      "calls": 1,
      "input_tokens": 3400,
      "output_tokens": 920,
      "cached_tokens": 1020,
      "cost_usd": 0.024,
      "seconds": 9.3,
      "models": [
       "mô hình mẫu"
      ]
     }
    ],
    "cache_hit_rate": 0.3,
    "simulated": false
   },
   "current": null,
   "queue_position": null,
   "schema_report": {
    "checked": true,
    "note": "",
    "changes": [
     {
      "source": "san_a_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "san_b_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "website_orders",
      "has_baseline": false,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     }
    ],
    "blocking": false
   },
   "schema_decision": {},
   "value_filters": [
    {
     "file": "models/marts/fct_daily_revenue.sql",
     "line": 44,
     "column": "status",
     "values": [
      "completed"
     ],
     "context": "lọc",
     "expression": "status IN ('completed')",
     "in_spec": false
    }
   ],
   "reconciliation": [
    {
     "model": "stg_san_a_orders",
     "source": "san_a_orders",
     "rows_in": 126,
     "rows_out": 126
    },
    {
     "model": "stg_san_b_orders",
     "source": "san_b_orders",
     "rows_in": 120,
     "rows_out": 120
    },
    {
     "model": "stg_website_orders",
     "source": "website_orders",
     "rows_in": 120,
     "rows_out": 120
    }
   ],
   "retryable": false,
   "drift": {
    "checked": false,
    "warnings": []
   }
  }
 },
 "phases": {
  "intake": [
   {
    "dur": 1.2,
    "events_count": 0,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:14+00:00",
      "summary": {
       "tokens": 0,
       "cost_usd": 0,
       "llm_calls": 0,
       "simulated": false,
       "workspace": null
      }
     },
     "busy": true,
     "pending": null,
     "spec": {
      "sources": []
     },
     "stages": [
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [],
      "cache_hit_rate": null,
      "simulated": false
     },
     "queue_position": 0
    }
   },
   {
    "dur": 1.5,
    "events_count": 2,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:14+00:00",
      "summary": {
       "tokens": 0,
       "cost_usd": 0,
       "llm_calls": 0,
       "simulated": false,
       "workspace": null
      }
     },
     "busy": true,
     "pending": null,
     "spec": {
      "sources": []
     },
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [],
      "cache_hit_rate": null,
      "simulated": false
     },
     "current": {
      "node": "planner",
      "label": "E1 Lập kế hoạch",
      "started_at": 0,
      "activity": [
       "Đọc yêu cầu “Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày”",
       "Xem cấu trúc và thống kê (không có dòng dữ liệu thật) của 3 bảng nguồn: san_a_orders, san_b_orders, website_orders",
       "Chọn bảng đích, mỗi dòng là gì (grain), cột đầu ra và chỉ số",
       "Quyết định ELT hay ETL; điểm nào chưa rõ thì soạn câu hỏi cho bạn",
       "Viết kế hoạch từng bước kèm lý do để bạn duyệt (J1b)"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "planner"
     },
     "queue_position": 0
    }
   }
  ],
  "plan": [
   {
    "dur": 1.2,
    "events_count": 4,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 1,
       "tokens": 4540,
       "cost_usd": 0.0213,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "spec": {
      "target": "fct_daily_revenue",
      "mode": "ELT",
      "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
      "grain": [
       "order_date"
      ],
      "output_columns": [
       {
        "name": "order_date",
        "type": "DATE",
        "description": "Ngày đặt đơn",
        "references": ""
       },
       {
        "name": "order_count",
        "type": "BIGINT",
        "description": "Số đơn hợp lệ trong ngày",
        "references": ""
       },
       {
        "name": "revenue_vnd",
        "type": "BIGINT",
        "description": "Tổng doanh thu (VND)",
        "references": ""
       }
      ],
      "metrics": [
       {
        "name": "revenue_vnd",
        "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
       }
      ],
      "filters": [
       "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
      ],
      "assumptions": [],
      "plan_summary": "",
      "plan": [],
      "sources": [
       {
        "name": "san_a_orders",
        "kind": "csv"
       },
       {
        "name": "san_b_orders",
        "kind": "json"
       },
       {
        "name": "website_orders",
        "kind": "sqlite"
       }
      ]
     },
     "answered": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "failed",
       "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 1,
        "input_tokens": 3900,
        "output_tokens": 640,
        "cached_tokens": 1170,
        "cost_usd": 0.0213,
        "seconds": 6.2,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "queue_position": 0
    }
   },
   {
    "dur": 1.2,
    "events_count": 5,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 1,
       "tokens": 4540,
       "cost_usd": 0.0213,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "spec": {
      "target": "fct_daily_revenue",
      "mode": "ELT",
      "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
      "grain": [
       "order_date"
      ],
      "output_columns": [
       {
        "name": "order_date",
        "type": "DATE",
        "description": "Ngày đặt đơn",
        "references": ""
       },
       {
        "name": "order_count",
        "type": "BIGINT",
        "description": "Số đơn hợp lệ trong ngày",
        "references": ""
       },
       {
        "name": "revenue_vnd",
        "type": "BIGINT",
        "description": "Tổng doanh thu (VND)",
        "references": ""
       }
      ],
      "metrics": [
       {
        "name": "revenue_vnd",
        "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
       }
      ],
      "filters": [
       "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
      ],
      "assumptions": [],
      "plan_summary": "",
      "plan": [],
      "sources": [
       {
        "name": "san_a_orders",
        "kind": "csv"
       },
       {
        "name": "san_b_orders",
        "kind": "json"
       },
       {
        "name": "website_orders",
        "kind": "sqlite"
       }
      ]
     },
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "failed",
       "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 1,
        "input_tokens": 3900,
        "output_tokens": 640,
        "cached_tokens": 1170,
        "cost_usd": 0.0213,
        "seconds": 6.2,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "planner",
      "label": "E1 Lập kế hoạch",
      "started_at": 0,
      "activity": [
       "Đọc yêu cầu “Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày”",
       "Xem cấu trúc và thống kê (không có dòng dữ liệu thật) của 3 bảng nguồn: san_a_orders, san_b_orders, website_orders",
       "Dùng 2 câu trả lời làm rõ của bạn",
       "Chọn bảng đích, mỗi dòng là gì (grain), cột đầu ra và chỉ số",
       "Quyết định ELT hay ETL; điểm nào chưa rõ thì soạn câu hỏi cho bạn",
       "Viết kế hoạch từng bước kèm lý do để bạn duyệt (J1b)"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 1,
      "stage": "planner"
     },
     "queue_position": 0
    }
   }
  ],
  "build": [
   {
    "dur": 1.2,
    "events_count": 7,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 2,
       "tokens": 9080,
       "cost_usd": 0.0426,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "code_notes": [],
     "test_notes": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "queue_position": 0,
     "schema_report": {},
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 8,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 2,
       "tokens": 9080,
       "cost_usd": 0.0426,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "code_notes": [],
     "test_notes": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "ingest",
      "label": "E0 Nhận nguồn",
      "started_at": 0,
      "activity": [
       "Nạp 3 nguồn vào sandbox DuckDB"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "prepare"
     },
     "queue_position": 0,
     "schema_report": {},
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 9,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 2,
       "tokens": 9080,
       "cost_usd": 0.0426,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "code_notes": [],
     "test_notes": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "profiler",
      "label": "P  Soi dữ liệu",
      "started_at": 0,
      "activity": [
       "Soi dữ liệu nguồn bằng code: kiểu cột, % rỗng, khóa trùng, định dạng ngày/tiền"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "prepare"
     },
     "queue_position": 0,
     "schema_report": {},
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 11,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 2,
       "tokens": 9080,
       "cost_usd": 0.0426,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "code_notes": [],
     "test_notes": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "mock_data",
      "label": "E2 Dữ liệu thử",
      "started_at": 0,
      "activity": [
       "Tạo 7 bộ dữ liệu thử (seed cố định): small, large, dirty, empty, few, dupkeys, nullmoney"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "prepare"
     },
     "queue_position": 0,
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 12,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 2,
       "tokens": 9080,
       "cost_usd": 0.0426,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "code_notes": [],
     "test_notes": [],
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "codegen",
      "label": "E3 Sinh code",
      "started_at": 0,
      "activity": [
       "Viết model staging cho 3 nguồn: san_a_orders, san_b_orders, website_orders",
       "Viết model mart `fct_daily_revenue` với 3 cột: order_date, order_count, revenue_vnd",
       "Mỗi dòng của mart là một giá trị của order_date",
       "Viết DAG Airflow chạy `dbt build`"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "codegen"
     },
     "queue_position": 0,
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 14,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 4,
       "tokens": 24210,
       "cost_usd": 0.134,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "codegen",
        "calls": 1,
        "input_tokens": 7100,
        "output_tokens": 2480,
        "cached_tokens": 2130,
        "cost_usd": 0.0585,
        "seconds": 14.6,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "testgen",
        "calls": 1,
        "input_tokens": 4200,
        "output_tokens": 1350,
        "cached_tokens": 1260,
        "cost_usd": 0.0329,
        "seconds": 8.1,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "safety",
      "label": "V1 An toàn",
      "started_at": 0,
      "activity": [
       "Kiểm an toàn bằng code: chặn lệnh ghi, hàm hệ thống, DAG gọi shell"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "safety"
     },
     "queue_position": 0,
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 4.0,
    "events_count": 15,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 4,
       "tokens": 24210,
       "cost_usd": 0.134,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "sandbox": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "codegen",
        "calls": 1,
        "input_tokens": 7100,
        "output_tokens": 2480,
        "cached_tokens": 2130,
        "cost_usd": 0.0585,
        "seconds": 14.6,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "testgen",
        "calls": 1,
        "input_tokens": 4200,
        "output_tokens": 1350,
        "cached_tokens": 1260,
        "cost_usd": 0.0329,
        "seconds": 8.1,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "sandbox_run",
      "label": "V2 Chạy sandbox",
      "started_at": 0,
      "activity": [
       "Ghi file đã qua V1 vào workspace, chạy `dbt build` + test trên DuckDB local"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "sandbox"
     },
     "queue_position": 0,
     "value_filters": [],
     "reconciliation": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 4.0,
    "events_count": 16,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 4,
       "tokens": 24210,
       "cost_usd": 0.134,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "waiting",
       "detail": ""
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "codegen",
        "calls": 1,
        "input_tokens": 7100,
        "output_tokens": 2480,
        "cached_tokens": 2130,
        "cost_usd": 0.0585,
        "seconds": 14.6,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "testgen",
        "calls": 1,
        "input_tokens": 4200,
        "output_tokens": 1350,
        "cached_tokens": 1260,
        "cost_usd": 0.0329,
        "seconds": 8.1,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "optimizer",
      "label": "E4 Tối ưu",
      "started_at": 0,
      "activity": [
       "Tìm dấu hiệu chậm bằng code: SELECT *, UNION, hàm trong WHERE, truy vấn con tương quan…",
       "Đo thời gian query gốc của `fct_daily_revenue` trên bộ dữ liệu lớn",
       "LLM đề xuất bản viết lại; V3 sẽ chạy cả hai và so kết quả bằng code"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "optimizer"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 2.8,
    "events_count": 17,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 4,
       "tokens": 24210,
       "cost_usd": 0.134,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "passed",
       "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ sqlglot"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "codegen",
        "calls": 1,
        "input_tokens": 7100,
        "output_tokens": 2480,
        "cached_tokens": 2130,
        "cost_usd": 0.0585,
        "seconds": 14.6,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "testgen",
        "calls": 1,
        "input_tokens": 4200,
        "output_tokens": 1350,
        "cached_tokens": 1260,
        "cost_usd": 0.0329,
        "seconds": 8.1,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "compare",
      "label": "V3 Đối chiếu",
      "started_at": 0,
      "activity": [
       "Chạy SQL gốc và SQL tối ưu trên nhiều bộ dữ liệu, so kết quả từng dòng"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "compare"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 18,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 4,
       "tokens": 24210,
       "cost_usd": 0.134,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "failed",
       "detail": "ứng viên chưa đạt, thử ứng viên kế tiếp"
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "usage": {
      "rows": [
       {
        "task": "planner",
        "calls": 2,
        "input_tokens": 7800,
        "output_tokens": 1280,
        "cached_tokens": 2340,
        "cost_usd": 0.0426,
        "seconds": 12.4,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "codegen",
        "calls": 1,
        "input_tokens": 7100,
        "output_tokens": 2480,
        "cached_tokens": 2130,
        "cost_usd": 0.0585,
        "seconds": 14.6,
        "models": [
         "mô hình mẫu"
        ]
       },
       {
        "task": "testgen",
        "calls": 1,
        "input_tokens": 4200,
        "output_tokens": 1350,
        "cached_tokens": 1260,
        "cost_usd": 0.0329,
        "seconds": 8.1,
        "models": [
         "mô hình mẫu"
        ]
       }
      ],
      "cache_hit_rate": 0.3,
      "simulated": false
     },
     "current": {
      "node": "optimizer",
      "label": "E4 Tối ưu",
      "started_at": 0,
      "activity": [
       "Tìm dấu hiệu chậm bằng code: SELECT *, UNION, hàm trong WHERE, truy vấn con tương quan…",
       "Đo thời gian query gốc của `fct_daily_revenue` trên bộ dữ liệu lớn",
       "Đề xuất lần 2: ứng viên trước chưa qua V3",
       "LLM đề xuất bản viết lại; V3 sẽ chạy cả hai và so kết quả bằng code"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 1,
      "stage": "optimizer"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 3.7,
    "events_count": 19,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 5,
       "tokens": 28530,
       "cost_usd": 0.158,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {},
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "passed",
       "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "current": {
      "node": "compare",
      "label": "V3 Đối chiếu",
      "started_at": 0,
      "activity": [
       "Chạy SQL gốc và SQL tối ưu trên nhiều bộ dữ liệu, so kết quả từng dòng"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 1,
      "stage": "compare"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.4,
    "events_count": 20,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 5,
       "tokens": 28530,
       "cost_usd": 0.158,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {
      "original_sql": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_a_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_b_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_website_orders\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date",
      "proposed_sql": "/* Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần */\nWITH all_orders AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_a_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_b_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_website_orders\n), deduped AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM all_orders\n  QUALIFY\n    ROW_NUMBER() OVER (PARTITION BY source, order_id ORDER BY order_date, amount_vnd DESC, status) = 1\n)\nSELECT\n  order_date,\n  COUNT(*) AS order_count,\n  CAST(COALESCE(SUM(amount_vnd), 0) AS BIGINT) AS revenue_vnd\nFROM deduped\nWHERE\n  status IN ('completed')\nGROUP BY\n  order_date\nORDER BY\n  order_date",
      "findings": [
       {
        "rule": "union_distinct",
        "message": "UNION (khử trùng) thay vì UNION ALL: phải băm toàn bộ dòng để loại trùng."
       },
       {
        "rule": "window_dedupe",
        "message": "row_number() theo PARTITION BY để khử trùng: tốn phân vùng/sắp xếp; thừa nếu khóa đã duy nhất."
       }
      ],
      "before": {
       "median_ms": 171.169,
       "runs": 5,
       "peak_memory_mb": 97.4
      },
      "after": {
       "median_ms": 77.862,
       "runs": 5,
       "peak_memory_mb": 31.9
      },
      "improvement_pct": 54.5,
      "decision": "applied",
      "reason": "Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
      "attempts": 2,
      "equivalence": [
       {
        "dataset": "small",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       },
       {
        "dataset": "dirty",
        "equal": true,
        "detail": "Giống hệt (29 dòng)"
       },
       {
        "dataset": "empty",
        "equal": true,
        "detail": "Giống hệt (0 dòng)"
       },
       {
        "dataset": "few",
        "equal": true,
        "detail": "Giống hệt (6 dòng)"
       },
       {
        "dataset": "dupkeys",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       },
       {
        "dataset": "nullmoney",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       }
      ],
      "llm_cost_usd": 0.024,
      "explanation": "Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần.",
      "warehouse_hints": [
       "BigQuery/Snowflake: phân vùng bảng đích theo order_date và cluster theo source (chỉ gợi ý)."
      ]
     },
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "passed",
       "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "passed",
       "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu."
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "current": {
      "node": "safety",
      "label": "V1 An toàn",
      "started_at": 0,
      "activity": [
       "Kiểm an toàn bằng code: chặn lệnh ghi, hàm hệ thống, DAG gọi shell"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 1,
      "stage": "safety"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 4.0,
    "events_count": 21,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 5,
       "tokens": 28530,
       "cost_usd": 0.158,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "evidence": {},
     "optimization": {
      "original_sql": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_a_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_san_b_orders\n    union\n    select source, order_id, order_date, status, amount_vnd from main.stg_website_orders\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date",
      "proposed_sql": "/* Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần */\nWITH all_orders AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_a_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_san_b_orders\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM main.stg_website_orders\n), deduped AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM all_orders\n  QUALIFY\n    ROW_NUMBER() OVER (PARTITION BY source, order_id ORDER BY order_date, amount_vnd DESC, status) = 1\n)\nSELECT\n  order_date,\n  COUNT(*) AS order_count,\n  CAST(COALESCE(SUM(amount_vnd), 0) AS BIGINT) AS revenue_vnd\nFROM deduped\nWHERE\n  status IN ('completed')\nGROUP BY\n  order_date\nORDER BY\n  order_date",
      "findings": [
       {
        "rule": "union_distinct",
        "message": "UNION (khử trùng) thay vì UNION ALL: phải băm toàn bộ dòng để loại trùng."
       },
       {
        "rule": "window_dedupe",
        "message": "row_number() theo PARTITION BY để khử trùng: tốn phân vùng/sắp xếp; thừa nếu khóa đã duy nhất."
       }
      ],
      "before": {
       "median_ms": 171.169,
       "runs": 5,
       "peak_memory_mb": 97.4
      },
      "after": {
       "median_ms": 77.862,
       "runs": 5,
       "peak_memory_mb": 31.9
      },
      "improvement_pct": 54.5,
      "decision": "applied",
      "reason": "Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.",
      "attempts": 2,
      "equivalence": [
       {
        "dataset": "small",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       },
       {
        "dataset": "dirty",
        "equal": true,
        "detail": "Giống hệt (29 dòng)"
       },
       {
        "dataset": "empty",
        "equal": true,
        "detail": "Giống hệt (0 dòng)"
       },
       {
        "dataset": "few",
        "equal": true,
        "detail": "Giống hệt (6 dòng)"
       },
       {
        "dataset": "dupkeys",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       },
       {
        "dataset": "nullmoney",
        "equal": true,
        "detail": "Giống hệt (30 dòng)"
       }
      ],
      "llm_cost_usd": 0.024,
      "explanation": "Đổi UNION thành UNION ALL: bước bỏ trùng theo (nguồn, mã đơn) phía sau đã xử lý trùng, nên không cần băm toàn bộ dữ liệu thêm một lần.",
      "warehouse_hints": [
       "BigQuery/Snowflake: phân vùng bảng đích theo order_date và cluster theo source (chỉ gợi ý)."
      ]
     },
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "running",
       "detail": "đang chạy"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "passed",
       "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "passed",
       "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu."
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "waiting",
       "detail": ""
      }
     ],
     "current": {
      "node": "sandbox_run",
      "label": "V2 Chạy sandbox",
      "started_at": 0,
      "activity": [
       "Ghi file đã qua V1 vào workspace, chạy `dbt build` + test trên DuckDB local"
      ],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 1,
      "stage": "sandbox"
     },
     "queue_position": 0,
     "value_filters": [],
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   },
   {
    "dur": 1.2,
    "events_count": 23,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:00:16+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": null,
       "improvement_pct": null,
       "llm_calls": 5,
       "tokens": 28530,
       "cost_usd": 0.158,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "pending": null,
     "stages": [
      {
       "id": "input_gate",
       "code": "G0",
       "label": "Kiểm tra đầu vào",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "drift_gate",
       "code": "G1",
       "label": "Kiểm tra cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "chưa kiểm (không có cơ sở dữ liệu)"
      },
      {
       "id": "planner",
       "code": "E1",
       "label": "Lập kế hoạch",
       "kind": "E",
       "state": "passed",
       "detail": "bảng đích fct_daily_revenue, mode ELT"
      },
      {
       "id": "clarify",
       "code": "J1",
       "label": "Hỏi làm rõ",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "spec_check",
       "code": "V0",
       "label": "Soát đặc tả",
       "kind": "V",
       "state": "passed",
       "detail": "đạt"
      },
      {
       "id": "plan_review",
       "code": "J1b",
       "label": "Duyệt kế hoạch",
       "kind": "J",
       "state": "passed",
       "detail": ""
      },
      {
       "id": "prepare",
       "code": "E0–E2",
       "label": "Nạp và soi dữ liệu",
       "kind": "E",
       "state": "passed",
       "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
      },
      {
       "id": "schema",
       "code": "Vs",
       "label": "Soát cấu trúc nguồn",
       "kind": "V",
       "state": "passed",
       "detail": "Không đổi so với bản đã duyệt."
      },
      {
       "id": "codegen",
       "code": "E3",
       "label": "Sinh code",
       "kind": "E",
       "state": "passed",
       "detail": "5 file"
      },
      {
       "id": "testgen",
       "code": "E3b",
       "label": "Sinh test",
       "kind": "E",
       "state": "passed",
       "detail": "6 file test"
      },
      {
       "id": "safety",
       "code": "V1",
       "label": "Kiểm an toàn",
       "kind": "V",
       "state": "passed",
       "detail": "không phát hiện vấn đề"
      },
      {
       "id": "sandbox",
       "code": "V2",
       "label": "Chạy thử",
       "kind": "V",
       "state": "passed",
       "detail": "1/1 model, 17/17 test đạt"
      },
      {
       "id": "optimizer",
       "code": "E4",
       "label": "Tối ưu",
       "kind": "E",
       "state": "passed",
       "detail": "2 dấu hiệu chậm, baseline 171.169 ms, ứng viên từ llm"
      },
      {
       "id": "compare",
       "code": "V3",
       "label": "Đối chiếu",
       "kind": "V",
       "state": "passed",
       "detail": "applied: Nhanh hơn 54.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu."
      },
      {
       "id": "review",
       "code": "J2",
       "label": "Duyệt code",
       "kind": "J",
       "state": "running",
       "detail": "đang chạy"
      }
     ],
     "current": {
      "node": "review",
      "label": "J2 Duyệt",
      "started_at": 0,
      "activity": [],
      "elapsed_s": 0,
      "typical_s": null,
      "samples": 0,
      "stage": "review"
     },
     "queue_position": 0,
     "drift": {
      "checked": false,
      "warnings": []
     }
    }
   }
  ],
  "approve": [
   {
    "dur": 1.2,
    "events_count": 23,
    "patch": {
     "record": {
      "id": "__RUN__",
      "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày",
      "requester": "khach",
      "status": "running",
      "provider": "demo",
      "model": "mô hình mẫu",
      "created_at": "2026-10-17T15:00:14+00:00",
      "updated_at": "2026-10-17T15:01:35+00:00",
      "summary": {
       "target": "fct_daily_revenue",
       "mode": "ELT",
       "fix_attempts": 0,
       "rescue_count": 0,
       "review_rounds": 0,
       "optimization": "applied",
       "improvement_pct": 54.5,
       "llm_calls": 5,
       "tokens": 28530,
       "cost_usd": 0.158,
       "simulated": false,
       "workspace": null,
       "error": ""
      }
     },
     "busy": true,
     "queue_position": 0
    }
   }
  ]
 },
 "files": {
  "code_files": {
   "models/staging/stg_san_a_orders.sql": "-- Chuẩn hóa đơn Sàn A: ngày dd/mm/yyyy hoặc yyyy-mm-dd, tiền VND dạng chuỗi \"1.075.000\"\nselect\n    'san_a' as source,\n    cast(order_id as varchar) as order_id,\n    coalesce(\n        try_strptime(cast(order_date as varchar), '%d/%m/%Y'),\n        try_strptime(cast(order_date as varchar), '%Y-%m-%d')\n    )::date as order_date,\n    case upper(status)\n        when 'COMPLETED' then 'completed'\n        when 'CANCELLED' then 'cancelled'\n        when 'RETURNED' then 'refunded'\n        else 'other'\n    end as status,\n    try_cast(nullif(replace(cast(total_amount as varchar), '.', ''), '') as bigint) as amount_vnd\nfrom {{ source('raw', 'san_a_orders') }}\n",
   "models/staging/stg_san_b_orders.sql": "-- Chuẩn hóa đơn Sàn B (JSON từ API): created_at ISO 8601, grand_total số thực\nselect\n    'san_b' as source,\n    cast(id as varchar) as order_id,\n    cast(created_at as timestamp)::date as order_date,\n    case lower(state)\n        when 'delivered' then 'completed'\n        when 'canceled' then 'cancelled'\n        when 'refunded' then 'refunded'\n        else 'other'\n    end as status,\n    cast(round(grand_total) as bigint) as amount_vnd\nfrom {{ source('raw', 'san_b_orders') }}\n",
   "models/staging/stg_website_orders.sql": "-- Chuẩn hóa đơn website (SQLite): created_ts dạng 'YYYY-MM-DD HH:MM:SS'\nselect\n    'website' as source,\n    cast(order_id as varchar) as order_id,\n    cast(created_ts as timestamp)::date as order_date,\n    case lower(status)\n        when 'paid' then 'completed'\n        when 'cancelled' then 'cancelled'\n        when 'refunded' then 'refunded'\n        else 'other'\n    end as status,\n    cast(amount_vnd as bigint) as amount_vnd\nfrom {{ source('raw', 'website_orders') }}\n",
   "models/marts/fct_daily_revenue.sql": "-- Bản đã tối ưu (E4), đối chiếu giống hệt bản gốc (V3)\n/* Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần */\nWITH all_orders AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM {{ ref('stg_san_a_orders') }}\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM {{ ref('stg_san_b_orders') }}\n  UNION ALL\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM {{ ref('stg_website_orders') }}\n), deduped AS (\n  SELECT\n    source,\n    order_id,\n    order_date,\n    status,\n    amount_vnd\n  FROM all_orders\n  QUALIFY\n    ROW_NUMBER() OVER (PARTITION BY source, order_id ORDER BY order_date, amount_vnd DESC, status) = 1\n)\nSELECT\n  order_date,\n  COUNT(*) AS order_count,\n  CAST(COALESCE(SUM(amount_vnd), 0) AS BIGINT) AS revenue_vnd\nFROM deduped\nWHERE\n  status IN ('completed')\nGROUP BY\n  order_date\nORDER BY\n  order_date\n",
   "dags/fct_daily_revenue_dag.py": "\"\"\"DAG Airflow chạy pipeline dbt `fct_daily_revenue` hằng ngày (agent sinh, Engineer duyệt trước khi merge).\"\"\"\n\nfrom datetime import datetime\n\nfrom airflow import DAG\nfrom airflow.operators.bash import BashOperator\n\nDBT_CMD = \"cd {{ var.value.p113_dbt_project_dir }} && dbt\"\n\nwith DAG(\n    dag_id=\"p113_fct_daily_revenue\",\n    start_date=datetime(2026, 1, 1),\n    schedule=\"@daily\",\n    catchup=False,\n    tags=[\"p113\", \"dbt\"],\n) as dag:\n    preflight = BashOperator(task_id=\"check_source_schema\", bash_command=DBT_CMD + \" run-operation check_source_schema\")\n    build_models = BashOperator(task_id=\"dbt_run\", bash_command=DBT_CMD + \" run --select +fct_daily_revenue\")\n    run_tests = BashOperator(task_id=\"dbt_test\", bash_command=DBT_CMD + \" test --select +fct_daily_revenue\")\n\n    preflight >> build_models >> run_tests\n"
  },
  "test_files": {
   "models/marts/fct_daily_revenue.yml": "version: 2\nmodels:\n- name: fct_daily_revenue\n  columns:\n  - name: order_date\n    data_tests:\n    - not_null\n",
   "tests/assert_grain_unique.sql": "-- Mỗi giá trị grain (order_date) chỉ có một dòng\nselect order_date, count(*) as n\nfrom {{ ref('fct_daily_revenue') }}\ngroup by order_date\nhaving count(*) > 1\n",
   "tests/assert_san_a_orders_order_date_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của san_a_orders.order_date không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'san_a_orders') }} where \"order_date\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'san_a_orders') }}\n    where \"order_date\" is not null and (coalesce(try_strptime(\"order_date\", '%d/%m/%Y'), try_cast(\"order_date\" as timestamp))::date) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
   "tests/assert_san_a_orders_total_amount_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của san_a_orders.total_amount không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'san_a_orders') }} where \"total_amount\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'san_a_orders') }}\n    where \"total_amount\" is not null and (try_cast(replace(\"total_amount\", '.', '') as bigint)) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
   "tests/assert_website_orders_created_ts_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của website_orders.created_ts không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'website_orders') }} where \"created_ts\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'website_orders') }}\n    where \"created_ts\" is not null and (try_cast(\"created_ts\" as timestamp)) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
   "tests/assert_fct_daily_revenue_reconciles.sql": "-- Đối soát (code dựng): kết quả kỳ vọng do Testgen tính độc lập từ raw, so hai chiều với bảng đích\nwith expected as (\n    -- Kỳ vọng tính độc lập từ raw: mỗi ngày một dòng, số đơn hợp lệ và tổng tiền\n    select\n        order_date,\n        count(*) as order_count,\n        cast(coalesce(sum(amount), 0) as bigint) as revenue_vnd\n    from (\n        select distinct\n            'san_a' as source,\n            cast(order_id as varchar) as order_id,\n            coalesce(\n                try_strptime(cast(order_date as varchar), '%d/%m/%Y'),\n                try_strptime(cast(order_date as varchar), '%Y-%m-%d')\n            )::date as order_date,\n            try_cast(nullif(replace(cast(total_amount as varchar), '.', ''), '') as bigint) as amount\n        from {{ source('raw', 'san_a_orders') }} where upper(status) in ('COMPLETED')\n        union all\n        select distinct 'san_b', cast(id as varchar), cast(created_at as timestamp)::date, cast(round(grand_total) as bigint)\n        from {{ source('raw', 'san_b_orders') }} where lower(state) in ('delivered')\n        union all\n        select distinct 'website', cast(order_id as varchar), cast(created_ts as timestamp)::date, cast(amount_vnd as bigint)\n        from {{ source('raw', 'website_orders') }} where lower(status) in ('paid')\n    ) as src\n    group by order_date\n),\n\nexpected_rows as (select order_date, order_count, revenue_vnd, true as _found from expected),\n\nactual_rows as (select order_date, order_count, revenue_vnd, true as _found from {{ ref('fct_daily_revenue') }})\n\nselect coalesce(e.order_date, a.order_date) as order_date, e.order_count as expected_order_count, a.order_count as actual_order_count, e.revenue_vnd as expected_revenue_vnd, a.revenue_vnd as actual_revenue_vnd\nfrom expected_rows as e\nfull outer join actual_rows as a on e.order_date is not distinct from a.order_date\nwhere e._found is null or a._found is null\n    or abs(coalesce(e.order_count, 0) - coalesce(a.order_count, 0)) > 1e-06 + 1e-09 * abs(coalesce(a.order_count, 0))\n    or abs(coalesce(e.revenue_vnd, 0) - coalesce(a.revenue_vnd, 0)) > 1e-06 + 1e-09 * abs(coalesce(a.revenue_vnd, 0))\n"
  },
  "previous_files": {}
 },
 "catalog": {
  "tables": [
   {
    "id": "raw.san_a_orders",
    "name": "san_a_orders",
    "layer": "source",
    "columns": [
     {
      "name": "order_id",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "order_date",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "customer_email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "customer_phone",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "total_amount",
      "type": "VARCHAR",
      "null_pct": 2.38,
      "is_key": false
     }
    ],
    "rows": 126,
    "duplicate_keys": 6,
    "file": "",
    "group": "",
    "description": ""
   },
   {
    "id": "raw.san_b_orders",
    "name": "san_b_orders",
    "layer": "source",
    "columns": [
     {
      "name": "id",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "created_at",
      "type": "TIMESTAMP",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "state",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "grand_total",
      "type": "DOUBLE",
      "null_pct": 1.67,
      "is_key": false
     },
     {
      "name": "buyer_email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     }
    ],
    "rows": 120,
    "duplicate_keys": 0,
    "file": "",
    "group": "",
    "description": ""
   },
   {
    "id": "raw.website_orders",
    "name": "website_orders",
    "layer": "source",
    "columns": [
     {
      "name": "order_id",
      "type": "BIGINT",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "created_ts",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "amount_vnd",
      "type": "BIGINT",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "phone",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     }
    ],
    "rows": 120,
    "duplicate_keys": 0,
    "file": "",
    "group": "",
    "description": ""
   },
   {
    "id": "main.stg_san_a_orders",
    "name": "stg_san_a_orders",
    "layer": "staging",
    "columns": [
     {
      "name": "source",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_id",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_date",
      "type": "DATE",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "amount_vnd",
      "type": "BIGINT",
      "null_pct": null,
      "is_key": false
     }
    ],
    "rows": null,
    "duplicate_keys": null,
    "file": "models/staging/stg_san_a_orders.sql",
    "group": "",
    "description": ""
   },
   {
    "id": "main.stg_san_b_orders",
    "name": "stg_san_b_orders",
    "layer": "staging",
    "columns": [
     {
      "name": "source",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_id",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_date",
      "type": "DATE",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "amount_vnd",
      "type": "BIGINT",
      "null_pct": null,
      "is_key": false
     }
    ],
    "rows": null,
    "duplicate_keys": null,
    "file": "models/staging/stg_san_b_orders.sql",
    "group": "",
    "description": ""
   },
   {
    "id": "main.stg_website_orders",
    "name": "stg_website_orders",
    "layer": "staging",
    "columns": [
     {
      "name": "source",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_id",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "order_date",
      "type": "DATE",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "amount_vnd",
      "type": "BIGINT",
      "null_pct": null,
      "is_key": false
     }
    ],
    "rows": null,
    "duplicate_keys": null,
    "file": "models/staging/stg_website_orders.sql",
    "group": "",
    "description": ""
   },
   {
    "id": "main.fct_daily_revenue",
    "name": "fct_daily_revenue",
    "layer": "mart",
    "columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "null_pct": null,
      "is_key": true
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "null_pct": null,
      "is_key": false
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "null_pct": null,
      "is_key": false
     }
    ],
    "rows": 30,
    "duplicate_keys": null,
    "file": "models/marts/fct_daily_revenue.sql",
    "group": "",
    "description": ""
   }
  ],
  "lineage": [
   {
    "source": "raw.san_a_orders",
    "target": "main.stg_san_a_orders"
   },
   {
    "source": "raw.san_b_orders",
    "target": "main.stg_san_b_orders"
   },
   {
    "source": "raw.website_orders",
    "target": "main.stg_website_orders"
   },
   {
    "source": "main.stg_website_orders",
    "target": "main.fct_daily_revenue"
   },
   {
    "source": "main.stg_san_a_orders",
    "target": "main.fct_daily_revenue"
   },
   {
    "source": "main.stg_san_b_orders",
    "target": "main.fct_daily_revenue"
   }
  ],
  "joins": []
 },
 "profiles": {
  "raw.san_a_orders": {
   "id": "raw.san_a_orders",
   "name": "san_a_orders",
   "layer": "source",
   "rows": 126,
   "columns": [
    {
     "name": "order_id",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": true,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "order_date",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [
      "dd/mm/yyyy",
      "yyyy-mm-dd"
     ],
     "distinct": 33,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "18/09/2026",
       "count": 8
      },
      {
       "label": "28/09/2026",
       "count": 8
      },
      {
       "label": "20/09/2026",
       "count": 7
      },
      {
       "label": "25/09/2026",
       "count": 7
      },
      {
       "label": "08/09/2026",
       "count": 6
      },
      {
       "label": "22/09/2026",
       "count": 6
      }
     ],
     "other": 84,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "customer_email",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "customer_phone",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "status",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "COMPLETED",
       "count": 88
      },
      {
       "label": "CANCELLED",
       "count": 24
      },
      {
       "label": "RETURNED",
       "count": 14
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "total_amount",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 123,
     "nulls": 3,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [
      "vnd_dot (1.075.000)"
     ],
     "distinct": 114,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "SP00001",
     "21/09/2026",
     "k***@example.com",
     "094******10",
     "CANCELLED",
     "2.283.000"
    ],
    [
     "SP00002",
     "2026-09-03",
     "k***@example.com",
     "091******99",
     "CANCELLED",
     "158.000"
    ],
    [
     "SP00003",
     "18/09/2026",
     "k***@example.com",
     "099******12",
     "COMPLETED",
     "1.189.000"
    ],
    [
     "SP00004",
     "26/09/2026",
     "k***@example.com",
     "093******10",
     "COMPLETED",
     "1.428.000"
    ],
    [
     "SP00005",
     "04/09/2026",
     "k***@example.com",
     "092******52",
     "COMPLETED",
     "227.000"
    ],
    [
     "SP00006",
     "24/09/2026",
     "k***@example.com",
     "092******83",
     "COMPLETED",
     "2.624.000"
    ],
    [
     "SP00007",
     "20/09/2026",
     "k***@example.com",
     "095******31",
     "COMPLETED",
     "983.000"
    ],
    [
     "SP00008",
     "25/09/2026",
     "k***@example.com",
     "094******63",
     "COMPLETED",
     "1.544.000"
    ],
    [
     "SP00009",
     "06/09/2026",
     "k***@example.com",
     "093******57",
     "COMPLETED",
     "342.000"
    ],
    [
     "SP00010",
     "20/09/2026",
     "k***@example.com",
     "098******40",
     "CANCELLED",
     "2.671.000"
    ],
    [
     "SP00011",
     "23/09/2026",
     "k***@example.com",
     "095******91",
     "COMPLETED",
     "181.000"
    ],
    [
     "SP00012",
     "26/09/2026",
     "k***@example.com",
     "094******72",
     "COMPLETED",
     "2.990.000"
    ],
    [
     "SP00013",
     "11/09/2026",
     "k***@example.com",
     "097******85",
     "COMPLETED",
     "1.134.000"
    ],
    [
     "SP00014",
     "05/09/2026",
     "k***@example.com",
     "098******55",
     "COMPLETED",
     "2.440.000"
    ],
    [
     "SP00015",
     "13/09/2026",
     "k***@example.com",
     "092******72",
     "RETURNED",
     "499.000"
    ],
    [
     "SP00016",
     "05/09/2026",
     "k***@example.com",
     "096******51",
     "COMPLETED",
     "1.967.000"
    ],
    [
     "SP00017",
     "17/09/2026",
     "k***@example.com",
     "091******56",
     "CANCELLED",
     "1.142.000"
    ],
    [
     "SP00018",
     "25/09/2026",
     "k***@example.com",
     "092******79",
     "CANCELLED",
     null
    ],
    [
     "SP00019",
     "24/09/2026",
     "k***@example.com",
     "094******79",
     "COMPLETED",
     "485.000"
    ],
    [
     "SP00020",
     "28/09/2026",
     "k***@example.com",
     "099******49",
     "CANCELLED",
     "711.000"
    ],
    [
     "SP00021",
     "18/09/2026",
     "k***@example.com",
     "098******64",
     "COMPLETED",
     "508.000"
    ],
    [
     "SP00022",
     "30/09/2026",
     "k***@example.com",
     "095******47",
     "CANCELLED",
     "372.000"
    ],
    [
     "SP00023",
     "03/09/2026",
     "k***@example.com",
     "091******46",
     "COMPLETED",
     "2.752.000"
    ],
    [
     "SP00024",
     "16/09/2026",
     "k***@example.com",
     "094******98",
     "COMPLETED",
     "2.258.000"
    ],
    [
     "SP00025",
     "25/09/2026",
     "k***@example.com",
     "093******38",
     "COMPLETED",
     "1.579.000"
    ],
    [
     "SP00026",
     "15/09/2026",
     "k***@example.com",
     "097******44",
     "CANCELLED",
     "2.459.000"
    ],
    [
     "SP00027",
     "2026-09-18",
     "k***@example.com",
     "093******77",
     "COMPLETED",
     "326.000"
    ],
    [
     "SP00028",
     "29/09/2026",
     "k***@example.com",
     "095******61",
     "CANCELLED",
     "927.000"
    ],
    [
     "SP00029",
     "18/09/2026",
     "k***@example.com",
     "098******06",
     "CANCELLED",
     "1.717.000"
    ],
    [
     "SP00030",
     "07/09/2026",
     "k***@example.com",
     "099******67",
     "COMPLETED",
     "271.000"
    ],
    [
     "SP00031",
     "22/09/2026",
     "k***@example.com",
     "092******23",
     "COMPLETED",
     "497.000"
    ],
    [
     "SP00032",
     "08/09/2026",
     "k***@example.com",
     "098******55",
     "COMPLETED",
     "1.073.000"
    ],
    [
     "SP00033",
     "28/09/2026",
     "k***@example.com",
     "096******01",
     "COMPLETED",
     "2.721.000"
    ],
    [
     "SP00034",
     "18/09/2026",
     "k***@example.com",
     "092******17",
     "COMPLETED",
     "2.039.000"
    ],
    [
     "SP00035",
     "16/09/2026",
     "k***@example.com",
     "096******16",
     "CANCELLED",
     null
    ],
    [
     "SP00036",
     "13/09/2026",
     "k***@example.com",
     "097******89",
     "COMPLETED",
     "2.326.000"
    ],
    [
     "SP00037",
     "22/09/2026",
     "k***@example.com",
     "093******78",
     "CANCELLED",
     "2.270.000"
    ],
    [
     "SP00038",
     "02/09/2026",
     "k***@example.com",
     "091******93",
     "COMPLETED",
     "2.225.000"
    ],
    [
     "SP00039",
     "06/09/2026",
     "k***@example.com",
     "092******78",
     "RETURNED",
     "1.013.000"
    ],
    [
     "SP00040",
     "13/09/2026",
     "k***@example.com",
     "098******39",
     "COMPLETED",
     "1.767.000"
    ],
    [
     "SP00041",
     "22/09/2026",
     "k***@example.com",
     "098******08",
     "COMPLETED",
     "1.336.000"
    ],
    [
     "SP00042",
     "08/09/2026",
     "k***@example.com",
     "092******85",
     "COMPLETED",
     "347.000"
    ],
    [
     "SP00043",
     "01/09/2026",
     "k***@example.com",
     "098******27",
     "RETURNED",
     "1.136.000"
    ],
    [
     "SP00044",
     "05/09/2026",
     "k***@example.com",
     "091******13",
     "COMPLETED",
     "2.275.000"
    ],
    [
     "SP00045",
     "23/09/2026",
     "k***@example.com",
     "099******15",
     "COMPLETED",
     "2.767.000"
    ],
    [
     "SP00046",
     "04/09/2026",
     "k***@example.com",
     "094******15",
     "CANCELLED",
     "1.165.000"
    ],
    [
     "SP00047",
     "10/09/2026",
     "k***@example.com",
     "095******13",
     "COMPLETED",
     "2.051.000"
    ],
    [
     "SP00048",
     "09/09/2026",
     "k***@example.com",
     "091******12",
     "COMPLETED",
     "64.000"
    ],
    [
     "SP00049",
     "11/09/2026",
     "k***@example.com",
     "099******09",
     "CANCELLED",
     "2.940.000"
    ],
    [
     "SP00050",
     "14/09/2026",
     "k***@example.com",
     "092******58",
     "COMPLETED",
     "2.284.000"
    ]
   ],
   "issues": [
    {
     "level": "fail",
     "column": "",
     "text": "6 dòng trùng khóa (order_id)."
    },
    {
     "level": "info",
     "column": "order_date",
     "text": "Lẫn 2 cách viết: dd/mm/yyyy, yyyy-mm-dd — đã có biểu thức đọc từ bộ soi P."
    }
   ],
   "duplicate_keys": 6,
   "keys": [
    "order_id"
   ],
   "rows_in": null,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": ""
  },
  "raw.san_b_orders": {
   "id": "raw.san_b_orders",
   "name": "san_b_orders",
   "layer": "source",
   "rows": 120,
   "columns": [
    {
     "name": "id",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": true,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "created_at",
     "type": "TIMESTAMP",
     "kind": "date",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 118,
     "minimum": "2026-09-01 10:55:00",
     "maximum": "2026-09-30 19:19:00",
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "2026-09-01",
       "count": 5
      },
      {
       "label": "2026-09-04",
       "count": 14
      },
      {
       "label": "2026-09-06",
       "count": 3
      },
      {
       "label": "2026-09-09",
       "count": 8
      },
      {
       "label": "2026-09-11",
       "count": 14
      },
      {
       "label": "2026-09-13",
       "count": 12
      },
      {
       "label": "2026-09-16",
       "count": 10
      },
      {
       "label": "2026-09-18",
       "count": 15
      },
      {
       "label": "2026-09-21",
       "count": 10
      },
      {
       "label": "2026-09-23",
       "count": 10
      },
      {
       "label": "2026-09-26",
       "count": 5
      },
      {
       "label": "2026-09-28",
       "count": 14
      }
     ],
     "near_unique": true
    },
    {
     "name": "state",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "delivered",
       "count": 93
      },
      {
       "label": "canceled",
       "count": 17
      },
      {
       "label": "refunded",
       "count": 10
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "grand_total",
     "type": "DOUBLE",
     "kind": "number",
     "is_key": false,
     "filled": 118,
     "nulls": 2,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 118,
     "minimum": "54000.0",
     "maximum": "2933000.0",
     "mean": 1585686.4407,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "54,000",
       "count": 9
      },
      {
       "label": "293,917",
       "count": 9
      },
      {
       "label": "533,833",
       "count": 10
      },
      {
       "label": "773,750",
       "count": 6
      },
      {
       "label": "1.01367e+06",
       "count": 13
      },
      {
       "label": "1.25358e+06",
       "count": 8
      },
      {
       "label": "1.4935e+06",
       "count": 7
      },
      {
       "label": "1.73342e+06",
       "count": 10
      },
      {
       "label": "1.97333e+06",
       "count": 10
      },
      {
       "label": "2.21325e+06",
       "count": 13
      },
      {
       "label": "2.45317e+06",
       "count": 12
      },
      {
       "label": "2.69308e+06",
       "count": 11
      }
     ],
     "near_unique": true
    },
    {
     "name": "buyer_email",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "TK00001",
     "2026-09-19 08:48:00",
     "delivered",
     "2406000.0",
     "k***@example.com"
    ],
    [
     "TK00002",
     "2026-09-16 16:41:00",
     "delivered",
     "767000.0",
     "k***@example.com"
    ],
    [
     "TK00003",
     "2026-09-14 18:52:00",
     "delivered",
     "2447000.0",
     "k***@example.com"
    ],
    [
     "TK00004",
     "2026-09-11 13:42:00",
     "canceled",
     "1722000.0",
     "k***@example.com"
    ],
    [
     "TK00005",
     "2026-09-16 12:42:00",
     "delivered",
     "2891000.0",
     "k***@example.com"
    ],
    [
     "TK00006",
     "2026-09-11 12:20:00",
     "canceled",
     "410000.0",
     "k***@example.com"
    ],
    [
     "TK00007",
     "2026-09-22 21:34:00",
     "delivered",
     "54000.0",
     "k***@example.com"
    ],
    [
     "TK00008",
     "2026-09-20 20:31:00",
     "delivered",
     "1531000.0",
     "k***@example.com"
    ],
    [
     "TK00009",
     "2026-09-05 22:18:00",
     "delivered",
     "2299000.0",
     "k***@example.com"
    ],
    [
     "TK00010",
     "2026-09-20 20:15:00",
     "delivered",
     "2630000.0",
     "k***@example.com"
    ],
    [
     "TK00011",
     "2026-09-14 09:14:00",
     "delivered",
     "2312000.0",
     "k***@example.com"
    ],
    [
     "TK00012",
     "2026-09-21 21:09:00",
     "delivered",
     "531000.0",
     "k***@example.com"
    ],
    [
     "TK00013",
     "2026-09-14 21:30:00",
     "delivered",
     "1169000.0",
     "k***@example.com"
    ],
    [
     "TK00014",
     "2026-09-13 11:58:00",
     "delivered",
     "642000.0",
     "k***@example.com"
    ],
    [
     "TK00015",
     "2026-09-25 20:54:00",
     "delivered",
     "1181000.0",
     "k***@example.com"
    ],
    [
     "TK00016",
     "2026-09-10 19:19:00",
     "delivered",
     "60000.0",
     "k***@example.com"
    ],
    [
     "TK00017",
     "2026-09-28 10:28:00",
     "delivered",
     "2055000.0",
     "k***@example.com"
    ],
    [
     "TK00018",
     "2026-09-13 15:59:00",
     "delivered",
     "2275000.0",
     "k***@example.com"
    ],
    [
     "TK00019",
     "2026-09-19 14:14:00",
     "delivered",
     "1028000.0",
     "k***@example.com"
    ],
    [
     "TK00020",
     "2026-09-23 22:51:00",
     "delivered",
     "1987000.0",
     "k***@example.com"
    ],
    [
     "TK00021",
     "2026-09-05 15:02:00",
     "canceled",
     "2720000.0",
     "k***@example.com"
    ],
    [
     "TK00022",
     "2026-09-28 21:28:00",
     "refunded",
     "461000.0",
     "k***@example.com"
    ],
    [
     "TK00023",
     "2026-09-05 14:55:00",
     "delivered",
     null,
     "k***@example.com"
    ],
    [
     "TK00024",
     "2026-09-11 17:44:00",
     "delivered",
     "1135000.0",
     "k***@example.com"
    ],
    [
     "TK00025",
     "2026-09-28 16:24:00",
     "delivered",
     "2812000.0",
     "k***@example.com"
    ],
    [
     "TK00026",
     "2026-09-28 16:02:00",
     "delivered",
     "2048000.0",
     "k***@example.com"
    ],
    [
     "TK00027",
     "2026-09-08 19:05:00",
     "delivered",
     "1227000.0",
     "k***@example.com"
    ],
    [
     "TK00028",
     "2026-09-28 09:28:00",
     "canceled",
     "2933000.0",
     "k***@example.com"
    ],
    [
     "TK00029",
     "2026-09-11 20:03:00",
     "delivered",
     "238000.0",
     "k***@example.com"
    ],
    [
     "TK00030",
     "2026-09-17 14:36:00",
     "delivered",
     "1050000.0",
     "k***@example.com"
    ],
    [
     "TK00031",
     "2026-09-20 21:24:00",
     "delivered",
     "373000.0",
     "k***@example.com"
    ],
    [
     "TK00032",
     "2026-09-05 11:29:00",
     "delivered",
     "2438000.0",
     "k***@example.com"
    ],
    [
     "TK00033",
     "2026-09-29 20:29:00",
     "delivered",
     "88000.0",
     "k***@example.com"
    ],
    [
     "TK00034",
     "2026-09-12 17:19:00",
     "delivered",
     "1859000.0",
     "k***@example.com"
    ],
    [
     "TK00035",
     "2026-09-28 12:12:00",
     "delivered",
     "1921000.0",
     "k***@example.com"
    ],
    [
     "TK00036",
     "2026-09-19 13:36:00",
     "delivered",
     "1612000.0",
     "k***@example.com"
    ],
    [
     "TK00037",
     "2026-09-27 18:25:00",
     "delivered",
     null,
     "k***@example.com"
    ],
    [
     "TK00038",
     "2026-09-30 17:47:00",
     "delivered",
     "250000.0",
     "k***@example.com"
    ],
    [
     "TK00039",
     "2026-09-20 20:22:00",
     "canceled",
     "992000.0",
     "k***@example.com"
    ],
    [
     "TK00040",
     "2026-09-25 19:49:00",
     "delivered",
     "2826000.0",
     "k***@example.com"
    ],
    [
     "TK00041",
     "2026-09-21 08:19:00",
     "delivered",
     "2620000.0",
     "k***@example.com"
    ],
    [
     "TK00042",
     "2026-09-03 22:18:00",
     "delivered",
     "588000.0",
     "k***@example.com"
    ],
    [
     "TK00043",
     "2026-09-26 16:56:00",
     "delivered",
     "591000.0",
     "k***@example.com"
    ],
    [
     "TK00044",
     "2026-09-27 10:16:00",
     "delivered",
     "1166000.0",
     "k***@example.com"
    ],
    [
     "TK00045",
     "2026-09-24 21:21:00",
     "delivered",
     "1258000.0",
     "k***@example.com"
    ],
    [
     "TK00046",
     "2026-09-25 11:55:00",
     "delivered",
     "626000.0",
     "k***@example.com"
    ],
    [
     "TK00047",
     "2026-09-12 09:50:00",
     "delivered",
     "2332000.0",
     "k***@example.com"
    ],
    [
     "TK00048",
     "2026-09-12 18:47:00",
     "delivered",
     "1912000.0",
     "k***@example.com"
    ],
    [
     "TK00049",
     "2026-09-12 09:43:00",
     "canceled",
     "2665000.0",
     "k***@example.com"
    ],
    [
     "TK00050",
     "2026-09-11 22:39:00",
     "canceled",
     "2349000.0",
     "k***@example.com"
    ]
   ],
   "issues": [],
   "duplicate_keys": 0,
   "keys": [
    "id"
   ],
   "rows_in": null,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": ""
  },
  "raw.website_orders": {
   "id": "raw.website_orders",
   "name": "website_orders",
   "layer": "source",
   "rows": 120,
   "columns": [
    {
     "name": "order_id",
     "type": "BIGINT",
     "kind": "number",
     "is_key": true,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": "1",
     "maximum": "120",
     "mean": 60.5,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "1",
       "count": 10
      },
      {
       "label": "10.9167",
       "count": 10
      },
      {
       "label": "20.8333",
       "count": 10
      },
      {
       "label": "30.75",
       "count": 10
      },
      {
       "label": "40.6667",
       "count": 10
      },
      {
       "label": "50.5833",
       "count": 10
      },
      {
       "label": "60.5",
       "count": 10
      },
      {
       "label": "70.4167",
       "count": 10
      },
      {
       "label": "80.3333",
       "count": 10
      },
      {
       "label": "90.25",
       "count": 10
      },
      {
       "label": "100.167",
       "count": 10
      },
      {
       "label": "110.083",
       "count": 10
      }
     ],
     "near_unique": true
    },
    {
     "name": "created_ts",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [
      "yyyy-mm-dd hh:mm:ss"
     ],
     "distinct": 118,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "status",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "paid",
       "count": 92
      },
      {
       "label": "cancelled",
       "count": 19
      },
      {
       "label": "refunded",
       "count": 9
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "amount_vnd",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": "144000",
     "maximum": "2977000",
     "mean": 1689250.0,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "144,000",
       "count": 7
      },
      {
       "label": "380,083",
       "count": 10
      },
      {
       "label": "616,167",
       "count": 13
      },
      {
       "label": "852,250",
       "count": 6
      },
      {
       "label": "1.08833e+06",
       "count": 7
      },
      {
       "label": "1.32442e+06",
       "count": 10
      },
      {
       "label": "1.5605e+06",
       "count": 6
      },
      {
       "label": "1.79658e+06",
       "count": 12
      },
      {
       "label": "2.03267e+06",
       "count": 11
      },
      {
       "label": "2.26875e+06",
       "count": 11
      },
      {
       "label": "2.50483e+06",
       "count": 12
      },
      {
       "label": "2.74092e+06",
       "count": 15
      }
     ],
     "near_unique": true
    },
    {
     "name": "email",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "phone",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "1",
     "2026-09-11 22:49:00",
     "refunded",
     "2581000",
     "k***@example.com",
     "098******79"
    ],
    [
     "2",
     "2026-09-05 10:11:00",
     "paid",
     "2887000",
     "k***@example.com",
     "092******04"
    ],
    [
     "3",
     "2026-09-06 19:28:00",
     "paid",
     "228000",
     "k***@example.com",
     "099******47"
    ],
    [
     "4",
     "2026-09-24 11:28:00",
     "paid",
     "2550000",
     "k***@example.com",
     "096******09"
    ],
    [
     "5",
     "2026-09-26 15:14:00",
     "paid",
     "2237000",
     "k***@example.com",
     "094******79"
    ],
    [
     "6",
     "2026-09-26 20:30:00",
     "paid",
     "844000",
     "k***@example.com",
     "094******52"
    ],
    [
     "7",
     "2026-09-19 15:29:00",
     "paid",
     "1204000",
     "k***@example.com",
     "095******77"
    ],
    [
     "8",
     "2026-09-14 10:52:00",
     "paid",
     "867000",
     "k***@example.com",
     "096******50"
    ],
    [
     "9",
     "2026-09-09 08:41:00",
     "cancelled",
     "2018000",
     "k***@example.com",
     "099******54"
    ],
    [
     "10",
     "2026-09-04 19:54:00",
     "paid",
     "2163000",
     "k***@example.com",
     "095******45"
    ],
    [
     "11",
     "2026-09-25 10:17:00",
     "paid",
     "1890000",
     "k***@example.com",
     "092******67"
    ],
    [
     "12",
     "2026-09-14 09:58:00",
     "cancelled",
     "959000",
     "k***@example.com",
     "097******38"
    ],
    [
     "13",
     "2026-09-30 08:26:00",
     "paid",
     "268000",
     "k***@example.com",
     "097******73"
    ],
    [
     "14",
     "2026-09-08 14:05:00",
     "paid",
     "1585000",
     "k***@example.com",
     "096******50"
    ],
    [
     "15",
     "2026-09-30 09:53:00",
     "refunded",
     "2977000",
     "k***@example.com",
     "094******82"
    ],
    [
     "16",
     "2026-09-05 10:02:00",
     "paid",
     "1225000",
     "k***@example.com",
     "099******46"
    ],
    [
     "17",
     "2026-09-05 20:45:00",
     "paid",
     "1971000",
     "k***@example.com",
     "097******27"
    ],
    [
     "18",
     "2026-09-29 09:01:00",
     "paid",
     "1098000",
     "k***@example.com",
     "097******70"
    ],
    [
     "19",
     "2026-09-18 19:38:00",
     "paid",
     "2211000",
     "k***@example.com",
     "093******89"
    ],
    [
     "20",
     "2026-09-10 11:19:00",
     "cancelled",
     "549000",
     "k***@example.com",
     "096******92"
    ],
    [
     "21",
     "2026-09-21 20:39:00",
     "cancelled",
     "1922000",
     "k***@example.com",
     "091******22"
    ],
    [
     "22",
     "2026-09-29 15:38:00",
     "cancelled",
     "2245000",
     "k***@example.com",
     "091******33"
    ],
    [
     "23",
     "2026-09-19 11:45:00",
     "paid",
     "638000",
     "k***@example.com",
     "091******15"
    ],
    [
     "24",
     "2026-09-20 13:15:00",
     "paid",
     "2387000",
     "k***@example.com",
     "094******64"
    ],
    [
     "25",
     "2026-09-22 09:33:00",
     "cancelled",
     "1527000",
     "k***@example.com",
     "096******56"
    ],
    [
     "26",
     "2026-09-18 16:50:00",
     "paid",
     "2129000",
     "k***@example.com",
     "091******64"
    ],
    [
     "27",
     "2026-09-28 15:02:00",
     "refunded",
     "2653000",
     "k***@example.com",
     "098******16"
    ],
    [
     "28",
     "2026-09-09 19:01:00",
     "paid",
     "1512000",
     "k***@example.com",
     "096******31"
    ],
    [
     "29",
     "2026-09-24 18:40:00",
     "paid",
     "474000",
     "k***@example.com",
     "091******90"
    ],
    [
     "30",
     "2026-09-11 10:02:00",
     "paid",
     "1493000",
     "k***@example.com",
     "098******41"
    ],
    [
     "31",
     "2026-09-21 10:53:00",
     "paid",
     "2854000",
     "k***@example.com",
     "098******24"
    ],
    [
     "32",
     "2026-09-16 18:11:00",
     "paid",
     "602000",
     "k***@example.com",
     "097******29"
    ],
    [
     "33",
     "2026-09-15 08:18:00",
     "paid",
     "875000",
     "k***@example.com",
     "091******10"
    ],
    [
     "34",
     "2026-09-29 08:20:00",
     "paid",
     "1320000",
     "k***@example.com",
     "091******78"
    ],
    [
     "35",
     "2026-09-27 16:30:00",
     "paid",
     "1087000",
     "k***@example.com",
     "097******14"
    ],
    [
     "36",
     "2026-09-07 12:22:00",
     "paid",
     "245000",
     "k***@example.com",
     "091******56"
    ],
    [
     "37",
     "2026-09-04 20:23:00",
     "paid",
     "1839000",
     "k***@example.com",
     "099******74"
    ],
    [
     "38",
     "2026-09-29 14:21:00",
     "paid",
     "815000",
     "k***@example.com",
     "096******13"
    ],
    [
     "39",
     "2026-09-12 22:51:00",
     "paid",
     "2176000",
     "k***@example.com",
     "097******69"
    ],
    [
     "40",
     "2026-09-24 14:05:00",
     "paid",
     "1813000",
     "k***@example.com",
     "094******45"
    ],
    [
     "41",
     "2026-09-06 16:18:00",
     "paid",
     "1365000",
     "k***@example.com",
     "099******12"
    ],
    [
     "42",
     "2026-09-22 12:19:00",
     "refunded",
     "1876000",
     "k***@example.com",
     "092******58"
    ],
    [
     "43",
     "2026-09-06 19:28:00",
     "paid",
     "1489000",
     "k***@example.com",
     "099******05"
    ],
    [
     "44",
     "2026-09-28 22:22:00",
     "refunded",
     "2568000",
     "k***@example.com",
     "097******27"
    ],
    [
     "45",
     "2026-09-26 08:04:00",
     "paid",
     "2799000",
     "k***@example.com",
     "096******26"
    ],
    [
     "46",
     "2026-09-17 20:47:00",
     "paid",
     "2832000",
     "k***@example.com",
     "099******84"
    ],
    [
     "47",
     "2026-09-05 21:38:00",
     "paid",
     "2827000",
     "k***@example.com",
     "093******54"
    ],
    [
     "48",
     "2026-09-03 11:49:00",
     "refunded",
     "2692000",
     "k***@example.com",
     "096******61"
    ],
    [
     "49",
     "2026-09-19 08:38:00",
     "paid",
     "678000",
     "k***@example.com",
     "095******75"
    ],
    [
     "50",
     "2026-09-12 15:48:00",
     "paid",
     "364000",
     "k***@example.com",
     "097******84"
    ]
   ],
   "issues": [],
   "duplicate_keys": 0,
   "keys": [
    "order_id"
   ],
   "rows_in": null,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": ""
  },
  "main.stg_san_a_orders": {
   "id": "main.stg_san_a_orders",
   "name": "stg_san_a_orders",
   "layer": "staging",
   "rows": 126,
   "columns": [
    {
     "name": "source",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 1,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "san_a",
       "count": 126
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "order_id",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "order_date",
     "type": "DATE",
     "kind": "date",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 30,
     "minimum": "2026-09-01",
     "maximum": "2026-09-30",
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "2026-09-01",
       "count": 9
      },
      {
       "label": "2026-09-03",
       "count": 7
      },
      {
       "label": "2026-09-06",
       "count": 12
      },
      {
       "label": "2026-09-08",
       "count": 8
      },
      {
       "label": "2026-09-10",
       "count": 11
      },
      {
       "label": "2026-09-13",
       "count": 5
      },
      {
       "label": "2026-09-15",
       "count": 6
      },
      {
       "label": "2026-09-18",
       "count": 20
      },
      {
       "label": "2026-09-20",
       "count": 10
      },
      {
       "label": "2026-09-23",
       "count": 16
      },
      {
       "label": "2026-09-25",
       "count": 8
      },
      {
       "label": "2026-09-27",
       "count": 14
      }
     ],
     "near_unique": false
    },
    {
     "name": "status",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 126,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "completed",
       "count": 88
      },
      {
       "label": "cancelled",
       "count": 24
      },
      {
       "label": "refunded",
       "count": 14
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "amount_vnd",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 123,
     "nulls": 3,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 114,
     "minimum": "51000",
     "maximum": "2996000",
     "mean": 1548219.5122,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "51,000",
       "count": 11
      },
      {
       "label": "296,417",
       "count": 13
      },
      {
       "label": "541,833",
       "count": 5
      },
      {
       "label": "787,250",
       "count": 8
      },
      {
       "label": "1.03267e+06",
       "count": 14
      },
      {
       "label": "1.27808e+06",
       "count": 8
      },
      {
       "label": "1.5235e+06",
       "count": 15
      },
      {
       "label": "1.76892e+06",
       "count": 7
      },
      {
       "label": "2.01433e+06",
       "count": 8
      },
      {
       "label": "2.25975e+06",
       "count": 14
      },
      {
       "label": "2.50517e+06",
       "count": 8
      },
      {
       "label": "2.75058e+06",
       "count": 12
      }
     ],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "san_a",
     "SP00001",
     "2026-09-21",
     "cancelled",
     "2283000"
    ],
    [
     "san_a",
     "SP00002",
     "2026-09-03",
     "cancelled",
     "158000"
    ],
    [
     "san_a",
     "SP00003",
     "2026-09-18",
     "completed",
     "1189000"
    ],
    [
     "san_a",
     "SP00004",
     "2026-09-26",
     "completed",
     "1428000"
    ],
    [
     "san_a",
     "SP00005",
     "2026-09-04",
     "completed",
     "227000"
    ],
    [
     "san_a",
     "SP00006",
     "2026-09-24",
     "completed",
     "2624000"
    ],
    [
     "san_a",
     "SP00007",
     "2026-09-20",
     "completed",
     "983000"
    ],
    [
     "san_a",
     "SP00008",
     "2026-09-25",
     "completed",
     "1544000"
    ],
    [
     "san_a",
     "SP00009",
     "2026-09-06",
     "completed",
     "342000"
    ],
    [
     "san_a",
     "SP00010",
     "2026-09-20",
     "cancelled",
     "2671000"
    ],
    [
     "san_a",
     "SP00011",
     "2026-09-23",
     "completed",
     "181000"
    ],
    [
     "san_a",
     "SP00012",
     "2026-09-26",
     "completed",
     "2990000"
    ],
    [
     "san_a",
     "SP00013",
     "2026-09-11",
     "completed",
     "1134000"
    ],
    [
     "san_a",
     "SP00014",
     "2026-09-05",
     "completed",
     "2440000"
    ],
    [
     "san_a",
     "SP00015",
     "2026-09-13",
     "refunded",
     "499000"
    ],
    [
     "san_a",
     "SP00016",
     "2026-09-05",
     "completed",
     "1967000"
    ],
    [
     "san_a",
     "SP00017",
     "2026-09-17",
     "cancelled",
     "1142000"
    ],
    [
     "san_a",
     "SP00018",
     "2026-09-25",
     "cancelled",
     null
    ],
    [
     "san_a",
     "SP00019",
     "2026-09-24",
     "completed",
     "485000"
    ],
    [
     "san_a",
     "SP00020",
     "2026-09-28",
     "cancelled",
     "711000"
    ],
    [
     "san_a",
     "SP00021",
     "2026-09-18",
     "completed",
     "508000"
    ],
    [
     "san_a",
     "SP00022",
     "2026-09-30",
     "cancelled",
     "372000"
    ],
    [
     "san_a",
     "SP00023",
     "2026-09-03",
     "completed",
     "2752000"
    ],
    [
     "san_a",
     "SP00024",
     "2026-09-16",
     "completed",
     "2258000"
    ],
    [
     "san_a",
     "SP00025",
     "2026-09-25",
     "completed",
     "1579000"
    ],
    [
     "san_a",
     "SP00026",
     "2026-09-15",
     "cancelled",
     "2459000"
    ],
    [
     "san_a",
     "SP00027",
     "2026-09-18",
     "completed",
     "326000"
    ],
    [
     "san_a",
     "SP00028",
     "2026-09-29",
     "cancelled",
     "927000"
    ],
    [
     "san_a",
     "SP00029",
     "2026-09-18",
     "cancelled",
     "1717000"
    ],
    [
     "san_a",
     "SP00030",
     "2026-09-07",
     "completed",
     "271000"
    ],
    [
     "san_a",
     "SP00031",
     "2026-09-22",
     "completed",
     "497000"
    ],
    [
     "san_a",
     "SP00032",
     "2026-09-08",
     "completed",
     "1073000"
    ],
    [
     "san_a",
     "SP00033",
     "2026-09-28",
     "completed",
     "2721000"
    ],
    [
     "san_a",
     "SP00034",
     "2026-09-18",
     "completed",
     "2039000"
    ],
    [
     "san_a",
     "SP00035",
     "2026-09-16",
     "cancelled",
     null
    ],
    [
     "san_a",
     "SP00036",
     "2026-09-13",
     "completed",
     "2326000"
    ],
    [
     "san_a",
     "SP00037",
     "2026-09-22",
     "cancelled",
     "2270000"
    ],
    [
     "san_a",
     "SP00038",
     "2026-09-02",
     "completed",
     "2225000"
    ],
    [
     "san_a",
     "SP00039",
     "2026-09-06",
     "refunded",
     "1013000"
    ],
    [
     "san_a",
     "SP00040",
     "2026-09-13",
     "completed",
     "1767000"
    ],
    [
     "san_a",
     "SP00041",
     "2026-09-22",
     "completed",
     "1336000"
    ],
    [
     "san_a",
     "SP00042",
     "2026-09-08",
     "completed",
     "347000"
    ],
    [
     "san_a",
     "SP00043",
     "2026-09-01",
     "refunded",
     "1136000"
    ],
    [
     "san_a",
     "SP00044",
     "2026-09-05",
     "completed",
     "2275000"
    ],
    [
     "san_a",
     "SP00045",
     "2026-09-23",
     "completed",
     "2767000"
    ],
    [
     "san_a",
     "SP00046",
     "2026-09-04",
     "cancelled",
     "1165000"
    ],
    [
     "san_a",
     "SP00047",
     "2026-09-10",
     "completed",
     "2051000"
    ],
    [
     "san_a",
     "SP00048",
     "2026-09-09",
     "completed",
     "64000"
    ],
    [
     "san_a",
     "SP00049",
     "2026-09-11",
     "cancelled",
     "2940000"
    ],
    [
     "san_a",
     "SP00050",
     "2026-09-14",
     "completed",
     "2284000"
    ]
   ],
   "issues": [],
   "duplicate_keys": null,
   "keys": [],
   "rows_in": 126,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": "models/staging/stg_san_a_orders.sql"
  },
  "main.stg_san_b_orders": {
   "id": "main.stg_san_b_orders",
   "name": "stg_san_b_orders",
   "layer": "staging",
   "rows": 120,
   "columns": [
    {
     "name": "source",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 1,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "san_b",
       "count": 120
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "order_id",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "order_date",
     "type": "DATE",
     "kind": "date",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 29,
     "minimum": "2026-09-01",
     "maximum": "2026-09-30",
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "2026-09-01",
       "count": 7
      },
      {
       "label": "2026-09-03",
       "count": 12
      },
      {
       "label": "2026-09-06",
       "count": 5
      },
      {
       "label": "2026-09-08",
       "count": 6
      },
      {
       "label": "2026-09-10",
       "count": 15
      },
      {
       "label": "2026-09-13",
       "count": 11
      },
      {
       "label": "2026-09-15",
       "count": 10
      },
      {
       "label": "2026-09-18",
       "count": 15
      },
      {
       "label": "2026-09-20",
       "count": 9
      },
      {
       "label": "2026-09-23",
       "count": 11
      },
      {
       "label": "2026-09-25",
       "count": 5
      },
      {
       "label": "2026-09-27",
       "count": 14
      }
     ],
     "near_unique": false
    },
    {
     "name": "status",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "completed",
       "count": 93
      },
      {
       "label": "cancelled",
       "count": 17
      },
      {
       "label": "refunded",
       "count": 10
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "amount_vnd",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 118,
     "nulls": 2,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 118,
     "minimum": "54000",
     "maximum": "2933000",
     "mean": 1585686.4407,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "54,000",
       "count": 9
      },
      {
       "label": "293,917",
       "count": 9
      },
      {
       "label": "533,833",
       "count": 10
      },
      {
       "label": "773,750",
       "count": 6
      },
      {
       "label": "1.01367e+06",
       "count": 13
      },
      {
       "label": "1.25358e+06",
       "count": 8
      },
      {
       "label": "1.4935e+06",
       "count": 7
      },
      {
       "label": "1.73342e+06",
       "count": 10
      },
      {
       "label": "1.97333e+06",
       "count": 10
      },
      {
       "label": "2.21325e+06",
       "count": 13
      },
      {
       "label": "2.45317e+06",
       "count": 12
      },
      {
       "label": "2.69308e+06",
       "count": 11
      }
     ],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "san_b",
     "TK00001",
     "2026-09-19",
     "completed",
     "2406000"
    ],
    [
     "san_b",
     "TK00002",
     "2026-09-16",
     "completed",
     "767000"
    ],
    [
     "san_b",
     "TK00003",
     "2026-09-14",
     "completed",
     "2447000"
    ],
    [
     "san_b",
     "TK00004",
     "2026-09-11",
     "cancelled",
     "1722000"
    ],
    [
     "san_b",
     "TK00005",
     "2026-09-16",
     "completed",
     "2891000"
    ],
    [
     "san_b",
     "TK00006",
     "2026-09-11",
     "cancelled",
     "410000"
    ],
    [
     "san_b",
     "TK00007",
     "2026-09-22",
     "completed",
     "54000"
    ],
    [
     "san_b",
     "TK00008",
     "2026-09-20",
     "completed",
     "1531000"
    ],
    [
     "san_b",
     "TK00009",
     "2026-09-05",
     "completed",
     "2299000"
    ],
    [
     "san_b",
     "TK00010",
     "2026-09-20",
     "completed",
     "2630000"
    ],
    [
     "san_b",
     "TK00011",
     "2026-09-14",
     "completed",
     "2312000"
    ],
    [
     "san_b",
     "TK00012",
     "2026-09-21",
     "completed",
     "531000"
    ],
    [
     "san_b",
     "TK00013",
     "2026-09-14",
     "completed",
     "1169000"
    ],
    [
     "san_b",
     "TK00014",
     "2026-09-13",
     "completed",
     "642000"
    ],
    [
     "san_b",
     "TK00015",
     "2026-09-25",
     "completed",
     "1181000"
    ],
    [
     "san_b",
     "TK00016",
     "2026-09-10",
     "completed",
     "60000"
    ],
    [
     "san_b",
     "TK00017",
     "2026-09-28",
     "completed",
     "2055000"
    ],
    [
     "san_b",
     "TK00018",
     "2026-09-13",
     "completed",
     "2275000"
    ],
    [
     "san_b",
     "TK00019",
     "2026-09-19",
     "completed",
     "1028000"
    ],
    [
     "san_b",
     "TK00020",
     "2026-09-23",
     "completed",
     "1987000"
    ],
    [
     "san_b",
     "TK00021",
     "2026-09-05",
     "cancelled",
     "2720000"
    ],
    [
     "san_b",
     "TK00022",
     "2026-09-28",
     "refunded",
     "461000"
    ],
    [
     "san_b",
     "TK00023",
     "2026-09-05",
     "completed",
     null
    ],
    [
     "san_b",
     "TK00024",
     "2026-09-11",
     "completed",
     "1135000"
    ],
    [
     "san_b",
     "TK00025",
     "2026-09-28",
     "completed",
     "2812000"
    ],
    [
     "san_b",
     "TK00026",
     "2026-09-28",
     "completed",
     "2048000"
    ],
    [
     "san_b",
     "TK00027",
     "2026-09-08",
     "completed",
     "1227000"
    ],
    [
     "san_b",
     "TK00028",
     "2026-09-28",
     "cancelled",
     "2933000"
    ],
    [
     "san_b",
     "TK00029",
     "2026-09-11",
     "completed",
     "238000"
    ],
    [
     "san_b",
     "TK00030",
     "2026-09-17",
     "completed",
     "1050000"
    ],
    [
     "san_b",
     "TK00031",
     "2026-09-20",
     "completed",
     "373000"
    ],
    [
     "san_b",
     "TK00032",
     "2026-09-05",
     "completed",
     "2438000"
    ],
    [
     "san_b",
     "TK00033",
     "2026-09-29",
     "completed",
     "88000"
    ],
    [
     "san_b",
     "TK00034",
     "2026-09-12",
     "completed",
     "1859000"
    ],
    [
     "san_b",
     "TK00035",
     "2026-09-28",
     "completed",
     "1921000"
    ],
    [
     "san_b",
     "TK00036",
     "2026-09-19",
     "completed",
     "1612000"
    ],
    [
     "san_b",
     "TK00037",
     "2026-09-27",
     "completed",
     null
    ],
    [
     "san_b",
     "TK00038",
     "2026-09-30",
     "completed",
     "250000"
    ],
    [
     "san_b",
     "TK00039",
     "2026-09-20",
     "cancelled",
     "992000"
    ],
    [
     "san_b",
     "TK00040",
     "2026-09-25",
     "completed",
     "2826000"
    ],
    [
     "san_b",
     "TK00041",
     "2026-09-21",
     "completed",
     "2620000"
    ],
    [
     "san_b",
     "TK00042",
     "2026-09-03",
     "completed",
     "588000"
    ],
    [
     "san_b",
     "TK00043",
     "2026-09-26",
     "completed",
     "591000"
    ],
    [
     "san_b",
     "TK00044",
     "2026-09-27",
     "completed",
     "1166000"
    ],
    [
     "san_b",
     "TK00045",
     "2026-09-24",
     "completed",
     "1258000"
    ],
    [
     "san_b",
     "TK00046",
     "2026-09-25",
     "completed",
     "626000"
    ],
    [
     "san_b",
     "TK00047",
     "2026-09-12",
     "completed",
     "2332000"
    ],
    [
     "san_b",
     "TK00048",
     "2026-09-12",
     "completed",
     "1912000"
    ],
    [
     "san_b",
     "TK00049",
     "2026-09-12",
     "cancelled",
     "2665000"
    ],
    [
     "san_b",
     "TK00050",
     "2026-09-11",
     "cancelled",
     "2349000"
    ]
   ],
   "issues": [],
   "duplicate_keys": null,
   "keys": [],
   "rows_in": 120,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": "models/staging/stg_san_b_orders.sql"
  },
  "main.stg_website_orders": {
   "id": "main.stg_website_orders",
   "name": "stg_website_orders",
   "layer": "staging",
   "rows": 120,
   "columns": [
    {
     "name": "source",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 1,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "website",
       "count": 120
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "order_id",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [],
     "near_unique": true
    },
    {
     "name": "order_date",
     "type": "DATE",
     "kind": "date",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 30,
     "minimum": "2026-09-01",
     "maximum": "2026-09-30",
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "2026-09-01",
       "count": 10
      },
      {
       "label": "2026-09-03",
       "count": 9
      },
      {
       "label": "2026-09-06",
       "count": 11
      },
      {
       "label": "2026-09-08",
       "count": 11
      },
      {
       "label": "2026-09-10",
       "count": 11
      },
      {
       "label": "2026-09-13",
       "count": 7
      },
      {
       "label": "2026-09-15",
       "count": 10
      },
      {
       "label": "2026-09-18",
       "count": 12
      },
      {
       "label": "2026-09-20",
       "count": 5
      },
      {
       "label": "2026-09-23",
       "count": 13
      },
      {
       "label": "2026-09-25",
       "count": 7
      },
      {
       "label": "2026-09-27",
       "count": 14
      }
     ],
     "near_unique": false
    },
    {
     "name": "status",
     "type": "VARCHAR",
     "kind": "text",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 3,
     "minimum": null,
     "maximum": null,
     "mean": null,
     "zeros": 0,
     "top": [
      {
       "label": "completed",
       "count": 92
      },
      {
       "label": "cancelled",
       "count": 19
      },
      {
       "label": "refunded",
       "count": 9
      }
     ],
     "other": 0,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "amount_vnd",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 120,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 120,
     "minimum": "144000",
     "maximum": "2977000",
     "mean": 1689250.0,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "144,000",
       "count": 7
      },
      {
       "label": "380,083",
       "count": 10
      },
      {
       "label": "616,167",
       "count": 13
      },
      {
       "label": "852,250",
       "count": 6
      },
      {
       "label": "1.08833e+06",
       "count": 7
      },
      {
       "label": "1.32442e+06",
       "count": 10
      },
      {
       "label": "1.5605e+06",
       "count": 6
      },
      {
       "label": "1.79658e+06",
       "count": 12
      },
      {
       "label": "2.03267e+06",
       "count": 11
      },
      {
       "label": "2.26875e+06",
       "count": 11
      },
      {
       "label": "2.50483e+06",
       "count": 12
      },
      {
       "label": "2.74092e+06",
       "count": 15
      }
     ],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "website",
     "1",
     "2026-09-11",
     "refunded",
     "2581000"
    ],
    [
     "website",
     "2",
     "2026-09-05",
     "completed",
     "2887000"
    ],
    [
     "website",
     "3",
     "2026-09-06",
     "completed",
     "228000"
    ],
    [
     "website",
     "4",
     "2026-09-24",
     "completed",
     "2550000"
    ],
    [
     "website",
     "5",
     "2026-09-26",
     "completed",
     "2237000"
    ],
    [
     "website",
     "6",
     "2026-09-26",
     "completed",
     "844000"
    ],
    [
     "website",
     "7",
     "2026-09-19",
     "completed",
     "1204000"
    ],
    [
     "website",
     "8",
     "2026-09-14",
     "completed",
     "867000"
    ],
    [
     "website",
     "9",
     "2026-09-09",
     "cancelled",
     "2018000"
    ],
    [
     "website",
     "10",
     "2026-09-04",
     "completed",
     "2163000"
    ],
    [
     "website",
     "11",
     "2026-09-25",
     "completed",
     "1890000"
    ],
    [
     "website",
     "12",
     "2026-09-14",
     "cancelled",
     "959000"
    ],
    [
     "website",
     "13",
     "2026-09-30",
     "completed",
     "268000"
    ],
    [
     "website",
     "14",
     "2026-09-08",
     "completed",
     "1585000"
    ],
    [
     "website",
     "15",
     "2026-09-30",
     "refunded",
     "2977000"
    ],
    [
     "website",
     "16",
     "2026-09-05",
     "completed",
     "1225000"
    ],
    [
     "website",
     "17",
     "2026-09-05",
     "completed",
     "1971000"
    ],
    [
     "website",
     "18",
     "2026-09-29",
     "completed",
     "1098000"
    ],
    [
     "website",
     "19",
     "2026-09-18",
     "completed",
     "2211000"
    ],
    [
     "website",
     "20",
     "2026-09-10",
     "cancelled",
     "549000"
    ],
    [
     "website",
     "21",
     "2026-09-21",
     "cancelled",
     "1922000"
    ],
    [
     "website",
     "22",
     "2026-09-29",
     "cancelled",
     "2245000"
    ],
    [
     "website",
     "23",
     "2026-09-19",
     "completed",
     "638000"
    ],
    [
     "website",
     "24",
     "2026-09-20",
     "completed",
     "2387000"
    ],
    [
     "website",
     "25",
     "2026-09-22",
     "cancelled",
     "1527000"
    ],
    [
     "website",
     "26",
     "2026-09-18",
     "completed",
     "2129000"
    ],
    [
     "website",
     "27",
     "2026-09-28",
     "refunded",
     "2653000"
    ],
    [
     "website",
     "28",
     "2026-09-09",
     "completed",
     "1512000"
    ],
    [
     "website",
     "29",
     "2026-09-24",
     "completed",
     "474000"
    ],
    [
     "website",
     "30",
     "2026-09-11",
     "completed",
     "1493000"
    ],
    [
     "website",
     "31",
     "2026-09-21",
     "completed",
     "2854000"
    ],
    [
     "website",
     "32",
     "2026-09-16",
     "completed",
     "602000"
    ],
    [
     "website",
     "33",
     "2026-09-15",
     "completed",
     "875000"
    ],
    [
     "website",
     "34",
     "2026-09-29",
     "completed",
     "1320000"
    ],
    [
     "website",
     "35",
     "2026-09-27",
     "completed",
     "1087000"
    ],
    [
     "website",
     "36",
     "2026-09-07",
     "completed",
     "245000"
    ],
    [
     "website",
     "37",
     "2026-09-04",
     "completed",
     "1839000"
    ],
    [
     "website",
     "38",
     "2026-09-29",
     "completed",
     "815000"
    ],
    [
     "website",
     "39",
     "2026-09-12",
     "completed",
     "2176000"
    ],
    [
     "website",
     "40",
     "2026-09-24",
     "completed",
     "1813000"
    ],
    [
     "website",
     "41",
     "2026-09-06",
     "completed",
     "1365000"
    ],
    [
     "website",
     "42",
     "2026-09-22",
     "refunded",
     "1876000"
    ],
    [
     "website",
     "43",
     "2026-09-06",
     "completed",
     "1489000"
    ],
    [
     "website",
     "44",
     "2026-09-28",
     "refunded",
     "2568000"
    ],
    [
     "website",
     "45",
     "2026-09-26",
     "completed",
     "2799000"
    ],
    [
     "website",
     "46",
     "2026-09-17",
     "completed",
     "2832000"
    ],
    [
     "website",
     "47",
     "2026-09-05",
     "completed",
     "2827000"
    ],
    [
     "website",
     "48",
     "2026-09-03",
     "refunded",
     "2692000"
    ],
    [
     "website",
     "49",
     "2026-09-19",
     "completed",
     "678000"
    ],
    [
     "website",
     "50",
     "2026-09-12",
     "completed",
     "364000"
    ]
   ],
   "issues": [],
   "duplicate_keys": null,
   "keys": [],
   "rows_in": 120,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": "models/staging/stg_website_orders.sql"
  },
  "main.fct_daily_revenue": {
   "id": "main.fct_daily_revenue",
   "name": "fct_daily_revenue",
   "layer": "mart",
   "rows": 30,
   "columns": [
    {
     "name": "order_date",
     "type": "DATE",
     "kind": "date",
     "is_key": true,
     "filled": 30,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 30,
     "minimum": "2026-09-01",
     "maximum": "2026-09-30",
     "mean": null,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "2026-09-01",
       "count": 3
      },
      {
       "label": "2026-09-03",
       "count": 2
      },
      {
       "label": "2026-09-06",
       "count": 3
      },
      {
       "label": "2026-09-08",
       "count": 2
      },
      {
       "label": "2026-09-10",
       "count": 3
      },
      {
       "label": "2026-09-13",
       "count": 2
      },
      {
       "label": "2026-09-15",
       "count": 2
      },
      {
       "label": "2026-09-18",
       "count": 3
      },
      {
       "label": "2026-09-20",
       "count": 2
      },
      {
       "label": "2026-09-23",
       "count": 3
      },
      {
       "label": "2026-09-25",
       "count": 2
      },
      {
       "label": "2026-09-27",
       "count": 3
      }
     ],
     "near_unique": true
    },
    {
     "name": "order_count",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 30,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 12,
     "minimum": "2",
     "maximum": "15",
     "mean": 8.9,
     "zeros": 0,
     "top": [
      {
       "label": "10",
       "count": 10
      },
      {
       "label": "6",
       "count": 6
      },
      {
       "label": "7",
       "count": 3
      },
      {
       "label": "13",
       "count": 2
      },
      {
       "label": "8",
       "count": 2
      },
      {
       "label": "11",
       "count": 1
      }
     ],
     "other": 6,
     "bins": [],
     "near_unique": false
    },
    {
     "name": "revenue_vnd",
     "type": "BIGINT",
     "kind": "number",
     "is_key": false,
     "filled": 30,
     "nulls": 0,
     "blank": 0,
     "invalid": 0,
     "case_variants": 0,
     "formats": [],
     "distinct": 30,
     "minimum": "4494000",
     "maximum": "27498000",
     "mean": 14344366.6667,
     "zeros": 0,
     "top": [],
     "other": 0,
     "bins": [
      {
       "label": "4.494e+06",
       "count": 3
      },
      {
       "label": "6.411e+06",
       "count": 3
      },
      {
       "label": "8.328e+06",
       "count": 4
      },
      {
       "label": "1.0245e+07",
       "count": 3
      },
      {
       "label": "1.2162e+07",
       "count": 2
      },
      {
       "label": "1.4079e+07",
       "count": 2
      },
      {
       "label": "1.5996e+07",
       "count": 5
      },
      {
       "label": "1.7913e+07",
       "count": 3
      },
      {
       "label": "1.983e+07",
       "count": 1
      },
      {
       "label": "2.1747e+07",
       "count": 0
      },
      {
       "label": "2.3664e+07",
       "count": 2
      },
      {
       "label": "2.5581e+07",
       "count": 2
      }
     ],
     "near_unique": true
    }
   ],
   "preview": [
    [
     "2026-09-01",
     "2",
     "5168000"
    ],
    [
     "2026-09-02",
     "6",
     "8608000"
    ],
    [
     "2026-09-03",
     "10",
     "16402000"
    ],
    [
     "2026-09-04",
     "6",
     "10088000"
    ],
    [
     "2026-09-05",
     "12",
     "24429000"
    ],
    [
     "2026-09-06",
     "7",
     "9959000"
    ],
    [
     "2026-09-07",
     "6",
     "10250000"
    ],
    [
     "2026-09-08",
     "10",
     "13961000"
    ],
    [
     "2026-09-09",
     "6",
     "9289000"
    ],
    [
     "2026-09-10",
     "10",
     "15045000"
    ],
    [
     "2026-09-11",
     "5",
     "4494000"
    ],
    [
     "2026-09-12",
     "10",
     "17378000"
    ],
    [
     "2026-09-13",
     "8",
     "13458000"
    ],
    [
     "2026-09-14",
     "10",
     "15830000"
    ],
    [
     "2026-09-15",
     "8",
     "10571000"
    ],
    [
     "2026-09-16",
     "10",
     "16984000"
    ],
    [
     "2026-09-17",
     "10",
     "19953000"
    ],
    [
     "2026-09-18",
     "13",
     "19280000"
    ],
    [
     "2026-09-19",
     "13",
     "19338000"
    ],
    [
     "2026-09-20",
     "14",
     "25672000"
    ],
    [
     "2026-09-21",
     "6",
     "11676000"
    ],
    [
     "2026-09-22",
     "9",
     "8049000"
    ],
    [
     "2026-09-23",
     "10",
     "18191000"
    ],
    [
     "2026-09-24",
     "10",
     "17608000"
    ],
    [
     "2026-09-25",
     "15",
     "27498000"
    ],
    [
     "2026-09-26",
     "10",
     "17383000"
    ],
    [
     "2026-09-27",
     "7",
     "7519000"
    ],
    [
     "2026-09-28",
     "11",
     "23886000"
    ],
    [
     "2026-09-29",
     "7",
     "6979000"
    ],
    [
     "2026-09-30",
     "6",
     "5385000"
    ]
   ],
   "issues": [],
   "duplicate_keys": 0,
   "keys": [
    "order_date"
   ],
   "rows_in": null,
   "dataset": "sandbox",
   "datasets": [
    "sandbox",
    "small",
    "dirty",
    "empty",
    "few",
    "dupkeys",
    "nullmoney"
   ],
   "file": "models/marts/fct_daily_revenue.sql"
  }
 },
 "stopped": {
  "detail": {
   "record": {
    "id": "__RUN__",
    "request_text": "Tính doanh thu theo tuần của 3 kênh bán",
    "requester": "khach",
    "status": "failed",
    "provider": "demo",
    "model": "mô hình mẫu",
    "created_at": "2026-10-17T15:01:35+00:00",
    "updated_at": "2026-10-17T15:01:40+00:00",
    "summary": {
     "target": "fct_daily_revenue",
     "mode": "ELT",
     "fix_attempts": 2,
     "rescue_count": 0,
     "review_rounds": 0,
     "optimization": null,
     "improvement_pct": null,
     "llm_calls": 5,
     "tokens": 33790,
     "cost_usd": 0.1925,
     "simulated": false,
     "workspace": null,
     "error": "Đã dừng ở bước cứu hộ theo yêu cầu của người dùng."
    }
   },
   "busy": false,
   "pending": null,
   "events": [
    {
     "node": "input_gate",
     "label": "G0 Kiểm tra đầu vào",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "drift_gate",
     "label": "G1 Kiểm tra cấu trúc nguồn",
     "ok": true,
     "detail": "chưa kiểm (không có cơ sở dữ liệu)",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 0.64,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": false,
     "detail": "Còn 2 điểm chưa rõ: Trạng thái đơn nào được tính doanh thu; Cách xử lý mã đơn bị trùng trong cùng nguồn",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "clarify",
     "label": "J1 Hỏi làm rõ",
     "ok": true,
     "detail": "",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "planner",
     "label": "E1 Lập kế hoạch",
     "ok": true,
     "detail": "bảng đích fct_daily_revenue, mode ELT",
     "seconds": 0.03,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "spec_check",
     "label": "V0 Soát đặc tả",
     "ok": true,
     "detail": "đạt",
     "seconds": 0.0,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "plan_review",
     "label": "J1b Duyệt kế hoạch",
     "ok": true,
     "detail": "",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "ingest",
     "label": "E0 Nhận nguồn",
     "ok": true,
     "detail": "san_a_orders: 126 dòng, san_b_orders: 120 dòng, website_orders: 120 dòng",
     "seconds": 0.86,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "profiler",
     "label": "P  Soi dữ liệu",
     "ok": true,
     "detail": "3 bảng",
     "seconds": 1.06,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "schema_guard",
     "label": "Vs Soát cấu trúc nguồn",
     "ok": true,
     "detail": "Không đổi so với bản đã duyệt.",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "mock_data",
     "label": "E2 Dữ liệu thử",
     "ok": true,
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney",
     "seconds": 1.27,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "codegen",
     "label": "E3 Sinh code",
     "ok": true,
     "detail": "5 file",
     "seconds": 0.16,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "testgen",
     "label": "E3b Sinh test",
     "ok": true,
     "detail": "6 file test",
     "seconds": 0.24,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": false,
     "detail": "1 vấn đề: models/marts/fct_daily_revenue.sql: Bảng 'main.stg_khuyen_mai_quy' không có trong danh mục dữ liệu t",
     "seconds": 0.34,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "codegen",
     "label": "E3 Sinh code",
     "ok": true,
     "detail": "5 file",
     "seconds": 0.04,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "testgen",
     "label": "E3b Sinh test",
     "ok": true,
     "detail": "6 file test",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "safety",
     "label": "V1 An toàn",
     "ok": false,
     "detail": "1 vấn đề: models/marts/fct_daily_revenue.sql: Bảng 'main.stg_khuyen_mai_quy' không có trong danh mục dữ liệu t",
     "seconds": 0.29,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "rescue",
     "label": "J  Cứu hộ",
     "ok": false,
     "detail": "Đã dừng ở bước cứu hộ theo yêu cầu của người dùng.",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    },
    {
     "node": "fail",
     "label": "Dừng",
     "ok": false,
     "detail": "Đã dừng ở bước cứu hộ theo yêu cầu của người dùng.",
     "seconds": 0.01,
     "tokens": 0,
     "finished_at": 0
    }
   ],
   "spec": {
    "target": "fct_daily_revenue",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    "grain": [
     "order_date"
    ],
    "output_columns": [
     {
      "name": "order_date",
      "type": "DATE",
      "description": "Ngày đặt đơn",
      "references": ""
     },
     {
      "name": "order_count",
      "type": "BIGINT",
      "description": "Số đơn hợp lệ trong ngày",
      "references": ""
     },
     {
      "name": "revenue_vnd",
      "type": "BIGINT",
      "description": "Tổng doanh thu (VND)",
      "references": ""
     }
    ],
    "metrics": [
     {
      "name": "revenue_vnd",
      "description": "Tổng tiền các đơn hợp lệ theo ngày, đơn vị VND"
     }
    ],
    "filters": [
     "Chỉ tính đơn có trạng thái hợp lệ theo câu trả lời làm rõ"
    ],
    "assumptions": [
     "q_status: Chỉ đơn đã giao/hoàn tất",
     "q_duplicates: Tính một lần (bỏ dòng trùng mã đơn)",
     "Đơn ở trạng thái nào được tính vào doanh thu? → Chỉ đơn đã giao/hoàn tất",
     "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao? → Tính một lần (bỏ dòng trùng mã đơn)"
    ],
    "plan_summary": "Tạo bảng fct_daily_revenue: mỗi ngày một dòng, cho biết số đơn và doanh thu (VND) gộp từ Sàn A, Sàn B và website; chỉ đơn đã giao/hoàn tất.",
    "plan": [
     {
      "title": "Làm sạch đơn Sàn A",
      "detail": "stg_san_a_orders: đọc order_date dạng dd/mm/yyyy lẫn yyyy-mm-dd, total_amount dạng '1.075.000'.",
      "reason": "Mẫu dữ liệu Sàn A có hai kiểu ngày và tiền là chuỗi có dấu chấm."
     },
     {
      "title": "Làm sạch đơn Sàn B và website",
      "detail": "stg_san_b_orders (created_at ISO, grand_total số), stg_website_orders (created_ts, amount_vnd).",
      "reason": "Mỗi nguồn đặt tên cột và trạng thái khác nhau; phải đưa về cùng bộ cột."
     },
     {
      "title": "Gộp 3 nguồn, bỏ đơn trùng",
      "detail": "Ghép các đơn bằng UNION, giữ cột nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
      "reason": "Bạn đã chọn: Tính một lần (bỏ dòng trùng mã đơn)."
     },
     {
      "title": "Tính doanh thu theo ngày",
      "detail": "fct_daily_revenue: order_date, order_count, revenue_vnd; chỉ đơn đã giao/hoàn tất.",
      "reason": "Yêu cầu là doanh thu ngày; trạng thái được tính theo câu trả lời làm rõ."
     }
    ],
    "sources": [
     {
      "name": "san_a_orders",
      "kind": "csv"
     },
     {
      "name": "san_b_orders",
      "kind": "json"
     },
     {
      "name": "website_orders",
      "kind": "sqlite"
     }
    ]
   },
   "answered": [
    {
     "id": "q_status",
     "question": "Đơn ở trạng thái nào được tính vào doanh thu?",
     "answer": "Chỉ đơn đã giao/hoàn tất"
    },
    {
     "id": "q_duplicates",
     "question": "Một mã đơn xuất hiện nhiều lần trong cùng nguồn thì sao?",
     "answer": "Tính một lần (bỏ dòng trùng mã đơn)"
    }
   ],
   "evidence": {},
   "optimization": {},
   "sandbox": {},
   "code_notes": [
    "Mỗi nguồn một model staging chuẩn hóa ngày, tiền VND và trạng thái về cùng một bộ giá trị.",
    "Model đích gộp 3 nguồn, bỏ trùng theo (nguồn, mã đơn), tính theo ngày.",
    "DAG Airflow kiểm cấu trúc nguồn (preflight), chạy dbt run rồi dbt test hằng ngày."
   ],
   "test_notes": [
    "Test tất định: cột grain không rỗng, grain không trùng, giá trị ngày/tiền ép được kiểu (≥ 99%).",
    "Tính lại từ raw: mỗi ngày một dòng, số đơn và tổng tiền các đơn hợp lệ (bỏ dòng trùng nếu được chọn)."
   ],
   "stages": [
    {
     "id": "input_gate",
     "code": "G0",
     "label": "Kiểm tra đầu vào",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "drift_gate",
     "code": "G1",
     "label": "Kiểm tra cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "chưa kiểm (không có cơ sở dữ liệu)"
    },
    {
     "id": "planner",
     "code": "E1",
     "label": "Lập kế hoạch",
     "kind": "E",
     "state": "passed",
     "detail": "bảng đích fct_daily_revenue, mode ELT"
    },
    {
     "id": "clarify",
     "code": "J1",
     "label": "Hỏi làm rõ",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "spec_check",
     "code": "V0",
     "label": "Soát đặc tả",
     "kind": "V",
     "state": "passed",
     "detail": "đạt"
    },
    {
     "id": "plan_review",
     "code": "J1b",
     "label": "Duyệt kế hoạch",
     "kind": "J",
     "state": "passed",
     "detail": ""
    },
    {
     "id": "prepare",
     "code": "E0–E2",
     "label": "Nạp và soi dữ liệu",
     "kind": "E",
     "state": "passed",
     "detail": "small, large, dirty, empty, few, dupkeys, nullmoney"
    },
    {
     "id": "schema",
     "code": "Vs",
     "label": "Soát cấu trúc nguồn",
     "kind": "V",
     "state": "passed",
     "detail": "Không đổi so với bản đã duyệt."
    },
    {
     "id": "codegen",
     "code": "E3",
     "label": "Sinh code",
     "kind": "E",
     "state": "passed",
     "detail": "5 file"
    },
    {
     "id": "testgen",
     "code": "E3b",
     "label": "Sinh test",
     "kind": "E",
     "state": "passed",
     "detail": "6 file test"
    },
    {
     "id": "safety",
     "code": "V1",
     "label": "Kiểm an toàn",
     "kind": "V",
     "state": "failed",
     "detail": "1 vấn đề: models/marts/fct_daily_revenue.sql: Bảng 'main.stg_khuyen_mai_quy' không có trong danh mục dữ liệu t"
    },
    {
     "id": "sandbox",
     "code": "V2",
     "label": "Chạy thử",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "rescue",
     "code": "J",
     "label": "Cứu hộ",
     "kind": "J",
     "state": "failed",
     "detail": "Đã dừng ở bước cứu hộ theo yêu cầu của người dùng."
    },
    {
     "id": "optimizer",
     "code": "E4",
     "label": "Tối ưu",
     "kind": "E",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "compare",
     "code": "V3",
     "label": "Đối chiếu",
     "kind": "V",
     "state": "waiting",
     "detail": ""
    },
    {
     "id": "review",
     "code": "J2",
     "label": "Duyệt code",
     "kind": "J",
     "state": "waiting",
     "detail": ""
    }
   ],
   "usage": {
    "rows": [
     {
      "task": "planner",
      "calls": 2,
      "input_tokens": 7800,
      "output_tokens": 1280,
      "cached_tokens": 2340,
      "cost_usd": 0.0426,
      "seconds": 12.4,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "codegen",
      "calls": 2,
      "input_tokens": 14200,
      "output_tokens": 4960,
      "cached_tokens": 4260,
      "cost_usd": 0.117,
      "seconds": 29.2,
      "models": [
       "mô hình mẫu"
      ]
     },
     {
      "task": "testgen",
      "calls": 1,
      "input_tokens": 4200,
      "output_tokens": 1350,
      "cached_tokens": 1260,
      "cost_usd": 0.0329,
      "seconds": 8.1,
      "models": [
       "mô hình mẫu"
      ]
     }
    ],
    "cache_hit_rate": 0.3,
    "simulated": false
   },
   "current": null,
   "queue_position": null,
   "schema_report": {
    "checked": true,
    "note": "",
    "changes": [
     {
      "source": "san_a_orders",
      "has_baseline": true,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "san_b_orders",
      "has_baseline": true,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     },
     {
      "source": "website_orders",
      "has_baseline": true,
      "added": {},
      "removed": {},
      "type_changed": {},
      "rename_candidates": [],
      "new_values": {},
      "proposals": []
     }
    ],
    "blocking": false
   },
   "schema_decision": {},
   "value_filters": [],
   "reconciliation": [],
   "retryable": false,
   "drift": {
    "checked": false,
    "warnings": []
   }
  },
  "eventOffsets": [
   0.01,
   0.01,
   0.65,
   0.65,
   0.73,
   0.75,
   0.75,
   0.85,
   1.71,
   2.77,
   2.79,
   4.06,
   4.25,
   4.47,
   4.81,
   4.85,
   4.86,
   5.16,
   5.27,
   5.27
  ],
  "files": {
   "code_files": {
    "models/staging/stg_san_a_orders.sql": "-- Chuẩn hóa đơn Sàn A: ngày dd/mm/yyyy hoặc yyyy-mm-dd, tiền VND dạng chuỗi \"1.075.000\"\nselect\n    'san_a' as source,\n    cast(order_id as varchar) as order_id,\n    coalesce(\n        try_strptime(cast(order_date as varchar), '%d/%m/%Y'),\n        try_strptime(cast(order_date as varchar), '%Y-%m-%d')\n    )::date as order_date,\n    case upper(status)\n        when 'COMPLETED' then 'completed'\n        when 'CANCELLED' then 'cancelled'\n        when 'RETURNED' then 'refunded'\n        else 'other'\n    end as status,\n    try_cast(nullif(replace(cast(total_amount as varchar), '.', ''), '') as bigint) as amount_vnd\nfrom {{ source('raw', 'san_a_orders') }}\n",
    "models/staging/stg_san_b_orders.sql": "-- Chuẩn hóa đơn Sàn B (JSON từ API): created_at ISO 8601, grand_total số thực\nselect\n    'san_b' as source,\n    cast(id as varchar) as order_id,\n    cast(created_at as timestamp)::date as order_date,\n    case lower(state)\n        when 'delivered' then 'completed'\n        when 'canceled' then 'cancelled'\n        when 'refunded' then 'refunded'\n        else 'other'\n    end as status,\n    cast(round(grand_total) as bigint) as amount_vnd\nfrom {{ source('raw', 'san_b_orders') }}\n",
    "models/staging/stg_website_orders.sql": "-- Chuẩn hóa đơn website (SQLite): created_ts dạng 'YYYY-MM-DD HH:MM:SS'\nselect\n    'website' as source,\n    cast(order_id as varchar) as order_id,\n    cast(created_ts as timestamp)::date as order_date,\n    case lower(status)\n        when 'paid' then 'completed'\n        when 'cancelled' then 'cancelled'\n        when 'refunded' then 'refunded'\n        else 'other'\n    end as status,\n    cast(amount_vnd as bigint) as amount_vnd\nfrom {{ source('raw', 'website_orders') }}\n",
    "models/marts/fct_daily_revenue.sql": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_san_a_orders') }}\n    union\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_san_b_orders') }} join {{ ref('stg_khuyen_mai_quy') }} using (order_id)\n    union\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_website_orders') }}\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date\n",
    "dags/fct_daily_revenue_dag.py": "\"\"\"DAG Airflow chạy pipeline dbt `fct_daily_revenue` hằng ngày (agent sinh, Engineer duyệt trước khi merge).\"\"\"\n\nfrom datetime import datetime\n\nfrom airflow import DAG\nfrom airflow.operators.bash import BashOperator\n\nDBT_CMD = \"cd {{ var.value.p113_dbt_project_dir }} && dbt\"\n\nwith DAG(\n    dag_id=\"p113_fct_daily_revenue\",\n    start_date=datetime(2026, 1, 1),\n    schedule=\"@daily\",\n    catchup=False,\n    tags=[\"p113\", \"dbt\"],\n) as dag:\n    preflight = BashOperator(task_id=\"check_source_schema\", bash_command=DBT_CMD + \" run-operation check_source_schema\")\n    build_models = BashOperator(task_id=\"dbt_run\", bash_command=DBT_CMD + \" run --select +fct_daily_revenue\")\n    run_tests = BashOperator(task_id=\"dbt_test\", bash_command=DBT_CMD + \" test --select +fct_daily_revenue\")\n\n    preflight >> build_models >> run_tests\n"
   },
   "test_files": {
    "models/marts/fct_daily_revenue.yml": "version: 2\nmodels:\n- name: fct_daily_revenue\n  columns:\n  - name: order_date\n    data_tests:\n    - not_null\n",
    "tests/assert_grain_unique.sql": "-- Mỗi giá trị grain (order_date) chỉ có một dòng\nselect order_date, count(*) as n\nfrom {{ ref('fct_daily_revenue') }}\ngroup by order_date\nhaving count(*) > 1\n",
    "tests/assert_san_a_orders_order_date_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của san_a_orders.order_date không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'san_a_orders') }} where \"order_date\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'san_a_orders') }}\n    where \"order_date\" is not null and (coalesce(try_strptime(\"order_date\", '%d/%m/%Y'), try_cast(\"order_date\" as timestamp))::date) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
    "tests/assert_san_a_orders_total_amount_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của san_a_orders.total_amount không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'san_a_orders') }} where \"total_amount\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'san_a_orders') }}\n    where \"total_amount\" is not null and (try_cast(replace(\"total_amount\", '.', '') as bigint)) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
    "tests/assert_website_orders_created_ts_castable.sql": "-- Chống mất dữ liệu lặng lẽ: quá 1% giá trị không rỗng của website_orders.created_ts không ép được kiểu thì test thất bại\nwith total as (select count(*) as n from {{ source('raw', 'website_orders') }} where \"created_ts\" is not null),\nfailed as (\n    select count(*) as n from {{ source('raw', 'website_orders') }}\n    where \"created_ts\" is not null and (try_cast(\"created_ts\" as timestamp)) is null\n)\nselect failed.n as failed_rows, total.n as total_rows\nfrom failed, total\nwhere total.n > 0 and failed.n * 1.0 / total.n > 0.01\n",
    "tests/assert_fct_daily_revenue_reconciles.sql": "-- Đối soát (code dựng): kết quả kỳ vọng do Testgen tính độc lập từ raw, so hai chiều với bảng đích\nwith expected as (\n    -- Kỳ vọng tính độc lập từ raw: mỗi ngày một dòng, số đơn hợp lệ và tổng tiền\n    select\n        order_date,\n        count(*) as order_count,\n        cast(coalesce(sum(amount), 0) as bigint) as revenue_vnd\n    from (\n        select distinct\n            'san_a' as source,\n            cast(order_id as varchar) as order_id,\n            coalesce(\n                try_strptime(cast(order_date as varchar), '%d/%m/%Y'),\n                try_strptime(cast(order_date as varchar), '%Y-%m-%d')\n            )::date as order_date,\n            try_cast(nullif(replace(cast(total_amount as varchar), '.', ''), '') as bigint) as amount\n        from {{ source('raw', 'san_a_orders') }} where upper(status) in ('COMPLETED')\n        union all\n        select distinct 'san_b', cast(id as varchar), cast(created_at as timestamp)::date, cast(round(grand_total) as bigint)\n        from {{ source('raw', 'san_b_orders') }} where lower(state) in ('delivered')\n        union all\n        select distinct 'website', cast(order_id as varchar), cast(created_ts as timestamp)::date, cast(amount_vnd as bigint)\n        from {{ source('raw', 'website_orders') }} where lower(status) in ('paid')\n    ) as src\n    group by order_date\n),\n\nexpected_rows as (select order_date, order_count, revenue_vnd, true as _found from expected),\n\nactual_rows as (select order_date, order_count, revenue_vnd, true as _found from {{ ref('fct_daily_revenue') }})\n\nselect coalesce(e.order_date, a.order_date) as order_date, e.order_count as expected_order_count, a.order_count as actual_order_count, e.revenue_vnd as expected_revenue_vnd, a.revenue_vnd as actual_revenue_vnd\nfrom expected_rows as e\nfull outer join actual_rows as a on e.order_date is not distinct from a.order_date\nwhere e._found is null or a._found is null\n    or abs(coalesce(e.order_count, 0) - coalesce(a.order_count, 0)) > 1e-06 + 1e-09 * abs(coalesce(a.order_count, 0))\n    or abs(coalesce(e.revenue_vnd, 0) - coalesce(a.revenue_vnd, 0)) > 1e-06 + 1e-09 * abs(coalesce(a.revenue_vnd, 0))\n"
   },
   "previous_files": {}
  }
 },
 "status": {
  "status": "ready",
  "agent": "P-113 Pipeline Agent v0.1.0",
  "llm_provider": "demo",
  "models": "mô hình mẫu",
  "simulated": false,
  "breakers": []
 },
 "sourcesCatalog": {
  "tables": [
   {
    "id": "raw.san_a_orders",
    "name": "san_a_orders",
    "layer": "source",
    "columns": [
     {
      "name": "order_id",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "order_date",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "customer_email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "customer_phone",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "total_amount",
      "type": "VARCHAR",
      "null_pct": 2.38,
      "is_key": false
     }
    ],
    "rows": 126,
    "duplicate_keys": 6,
    "file": "",
    "group": "",
    "description": ""
   },
   {
    "id": "raw.san_b_orders",
    "name": "san_b_orders",
    "layer": "source",
    "columns": [
     {
      "name": "id",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "created_at",
      "type": "TIMESTAMP",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "state",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "grand_total",
      "type": "DOUBLE",
      "null_pct": 1.67,
      "is_key": false
     },
     {
      "name": "buyer_email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     }
    ],
    "rows": 120,
    "duplicate_keys": 0,
    "file": "",
    "group": "",
    "description": ""
   },
   {
    "id": "raw.website_orders",
    "name": "website_orders",
    "layer": "source",
    "columns": [
     {
      "name": "order_id",
      "type": "BIGINT",
      "null_pct": 0.0,
      "is_key": true
     },
     {
      "name": "created_ts",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "status",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "amount_vnd",
      "type": "BIGINT",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "email",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     },
     {
      "name": "phone",
      "type": "VARCHAR",
      "null_pct": 0.0,
      "is_key": false
     }
    ],
    "rows": 120,
    "duplicate_keys": 0,
    "file": "",
    "group": "",
    "description": ""
   }
  ],
  "lineage": [],
  "joins": []
 },
 "schemaReport": {
  "checked": true,
  "note": "",
  "changes": [
   {
    "source": "san_a_orders",
    "has_baseline": true,
    "added": {},
    "removed": {},
    "type_changed": {},
    "rename_candidates": [],
    "new_values": {},
    "proposals": []
   },
   {
    "source": "san_b_orders",
    "has_baseline": true,
    "added": {},
    "removed": {},
    "type_changed": {},
    "rename_candidates": [],
    "new_values": {},
    "proposals": []
   },
   {
    "source": "website_orders",
    "has_baseline": true,
    "added": {},
    "removed": {},
    "type_changed": {},
    "rename_candidates": [],
    "new_values": {},
    "proposals": []
   }
  ],
  "blocking": false
 },
 "errors": [
  {
   "id": 1,
   "code": "SAFETY_BLOCKED",
   "signature": "77a2b47d8f60",
   "description": "models/marts/fct_daily_revenue.sql: Bảng <đã che> không có trong danh mục dữ liệu thật.",
   "cause": "",
   "fix": "",
   "sql_before": "-- Doanh thu theo ngày từ 3 nguồn; mỗi (nguồn, mã đơn) tính một lần\nwith all_orders as (\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_san_a_orders') }}\n    union\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_san_b_orders') }} join {{ ref('stg_khuyen_mai_quy') }} using (order_id)\n    union\n    select source, order_id, order_date, status, amount_vnd from {{ ref('stg_website_orders') }}\n),\n\ndeduped as (\n    select source, order_id, order_date, status, amount_vnd\n    from all_orders\n    qualify row_number() over (\n        partition by source, order_id\n        order by order_date, amount_vnd desc nulls last, status\n    ) = 1\n)\n\nselect\n    order_date,\n    count(*) as order_count,\n    cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd\nfrom deduped\nwhere status in ('completed')\ngroup by order_date\norder by order_date\n",
   "sql_after": "",
   "occurrences": 2,
   "approved": false,
   "warnings": []
  }
 ],
 "glossary": [
  {
   "id": 1,
   "term": "doanh thu",
   "synonyms": [
    "doanh thu thuần",
    "revenue",
    "net revenue"
   ],
   "definition": "Tổng tiền VND của các đơn đã hoàn tất; không tính đơn hủy, đơn hoàn tiền và đơn đang xử lý.",
   "maps_to": "SUM(tiền đơn) với đơn hoàn tất; san_a_orders.total_amount, san_b_orders.grand_total, website_orders.amount_vnd",
   "department_id": null
  },
  {
   "id": 13,
   "term": "doanh thu theo ngày",
   "synonyms": [
    "doanh thu hằng ngày",
    "daily revenue"
   ],
   "definition": "Doanh thu gộp theo ngày đặt đơn; mỗi ngày một dòng.",
   "maps_to": "GROUP BY ngày đặt đơn",
   "department_id": null
  },
  {
   "id": 14,
   "term": "doanh thu theo tháng",
   "synonyms": [
    "doanh thu hằng tháng",
    "monthly revenue"
   ],
   "definition": "Doanh thu gộp theo tháng dương lịch của ngày đặt đơn; cột tháng là ngày đầu tháng.",
   "maps_to": "GROUP BY date_trunc('month', ngày đặt đơn)",
   "department_id": null
  },
  {
   "id": 9,
   "term": "giá trị đơn trung bình",
   "synonyms": [
    "giá trị trung bình mỗi đơn",
    "AOV",
    "average order value"
   ],
   "definition": "Doanh thu chia số đơn hoàn tất trong cùng kỳ.",
   "maps_to": "SUM(tiền đơn) / COUNT(đơn) với đơn hoàn tất",
   "department_id": null
  },
  {
   "id": 4,
   "term": "hoàn tiền",
   "synonyms": [
    "đơn hoàn tiền",
    "trả hàng",
    "đơn trả hàng",
    "refund"
   ],
   "definition": "Đơn đã giao nhưng khách trả hàng và được hoàn tiền. Sàn A RETURNED, Sàn B refunded, website refunded.",
   "maps_to": "san_a_orders.status = RETURNED; san_b_orders.state = refunded; website_orders.status = refunded",
   "department_id": null
  },
  {
   "id": 16,
   "term": "khách hàng",
   "synonyms": [
    "khách",
    "người mua",
    "customer"
   ],
   "definition": "Người mua hàng, nhận diện bằng email trong bảng khách hàng; một khách có thể có nhiều đơn.",
   "maps_to": "customers.email, customers.customer_id",
   "department_id": null
  },
  {
   "id": 11,
   "term": "kênh bán",
   "synonyms": [
    "kênh",
    "nguồn bán",
    "sàn",
    "channel"
   ],
   "definition": "Nơi phát sinh đơn: san_a, san_b hoặc website; mỗi bảng nguồn là một kênh.",
   "maps_to": "san_a_orders, san_b_orders, website_orders",
   "department_id": null
  },
  {
   "id": 6,
   "term": "mã đơn",
   "synonyms": [
    "order id",
    "mã đơn hàng",
    "order_id"
   ],
   "definition": "Khóa của đơn trong từng nguồn; hai nguồn khác nhau có thể dùng cùng một mã cho hai đơn khác nhau.",
   "maps_to": "san_a_orders.order_id, san_b_orders.id, website_orders.order_id",
   "department_id": null
  },
  {
   "id": 7,
   "term": "ngày đặt đơn",
   "synonyms": [
    "ngày đơn",
    "ngày đặt hàng",
    "order date"
   ],
   "definition": "Ngày khách đặt đơn, lấy theo ngày lưu trong dữ liệu (không đổi múi giờ).",
   "maps_to": "san_a_orders.order_date, san_b_orders.created_at, website_orders.created_ts",
   "department_id": null
  },
  {
   "id": 8,
   "term": "số đơn",
   "synonyms": [
    "số lượng đơn",
    "tổng số đơn",
    "order count"
   ],
   "definition": "Số đơn hợp lệ theo điều kiện lọc của yêu cầu, mỗi đơn đếm một lần.",
   "maps_to": "COUNT(đơn) sau khi bỏ trùng",
   "department_id": null
  },
  {
   "id": 12,
   "term": "tiền VND",
   "synonyms": [
    "số tiền",
    "đơn vị tiền",
    "đồng",
    "vnd"
   ],
   "definition": "Mọi số tiền tính bằng đồng Việt Nam, số nguyên. Sàn A ghi chuỗi có dấu chấm ngăn nghìn, Sàn B ghi số thực.",
   "maps_to": "san_a_orders.total_amount (chuỗi), san_b_orders.grand_total (số thực), website_orders.amount_vnd (số nguyên)",
   "department_id": null
  },
  {
   "id": 5,
   "term": "trùng đơn",
   "synonyms": [
    "đơn trùng",
    "đơn lặp",
    "dòng lặp",
    "dòng trùng",
    "duplicate order"
   ],
   "definition": "Cùng một mã đơn xuất hiện nhiều dòng trong một nguồn; mỗi (nguồn, mã đơn) chỉ tính một lần.",
   "maps_to": "san_a_orders.order_id, san_b_orders.id, website_orders.order_id",
   "department_id": null
  },
  {
   "id": 10,
   "term": "tỷ lệ hoàn tiền",
   "synonyms": [
    "tỉ lệ hoàn tiền",
    "tỷ lệ trả hàng",
    "refund rate"
   ],
   "definition": "Số đơn hoàn tiền chia tổng số đơn đã giao hoặc đã hoàn tiền, sau khi bỏ trùng.",
   "maps_to": "COUNT(đơn hoàn tiền) / COUNT(đơn hoàn tất + đơn hoàn tiền)",
   "department_id": null
  },
  {
   "id": 2,
   "term": "đơn hoàn tất",
   "synonyms": [
    "đơn thành công",
    "đơn đã giao",
    "đơn đã thanh toán",
    "completed order"
   ],
   "definition": "Đơn đã giao hoặc đã thanh toán xong. Sàn A COMPLETED, Sàn B delivered, website paid.",
   "maps_to": "san_a_orders.status = COMPLETED; san_b_orders.state = delivered; website_orders.status = paid",
   "department_id": null
  },
  {
   "id": 3,
   "term": "đơn hủy",
   "synonyms": [
    "đơn bị hủy",
    "đơn huỷ",
    "cancelled order",
    "canceled order"
   ],
   "definition": "Đơn bị hủy trước khi hoàn tất. Sàn A CANCELLED, Sàn B canceled, website cancelled.",
   "maps_to": "san_a_orders.status = CANCELLED; san_b_orders.state = canceled; website_orders.status = cancelled",
   "department_id": null
  },
  {
   "id": 17,
   "term": "đơn thiếu số tiền",
   "synonyms": [
    "đơn rỗng tiền",
    "đơn không có số tiền"
   ],
   "definition": "Đơn có ô số tiền rỗng; vẫn đếm vào số đơn nhưng doanh thu của đơn đó là 0.",
   "maps_to": "tiền đơn IS NULL",
   "department_id": null
  },
  {
   "id": 15,
   "term": "đơn đang xử lý",
   "synonyms": [
    "đơn chờ",
    "đơn chưa hoàn tất",
    "pending order"
   ],
   "definition": "Đơn chưa hoàn tất, chưa hủy và chưa hoàn tiền (mọi trạng thái còn lại). Không tính vào doanh thu.",
   "maps_to": "trạng thái khác hoàn tất, hủy, hoàn tiền",
   "department_id": null
  }
 ],
 "sources": [
  {
   "id": 1,
   "name": "P113 Retail",
   "department_id": 1,
   "kind": "file",
   "secret_ref": "",
   "allowed_tables": [
    "*"
   ],
   "sensitivity": "medium",
   "llm_access": "profile",
   "restricted_columns": [],
   "enabled": true,
   "department_name": "Mặc định",
   "access_text": "AI thấy thống kê, không thấy dòng thật",
   "llm_access_effective": "profile"
  }
 ]
} satisfies DemoFixtures;
