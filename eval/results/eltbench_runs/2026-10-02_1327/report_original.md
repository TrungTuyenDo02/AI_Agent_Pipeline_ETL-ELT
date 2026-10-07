# ELT-Bench-Verified — chế độ `agent`

- Ngày chạy: 2026-10-02 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- Dữ liệu: 10 pipeline nhẹ nhất (eval/benchmarks/eltbench/tasks.yaml); ELT-Bench-Verified, CC BY-SA 4.0.

**Khớp bảng kết quả đúng: 7/34 model**

| Task | Model | status | auto_answers | fix_attempts | rescue | tokens | cost_usd | seconds | ok | detail |
|---|---|---|---|---|---|---|---|---|---|---|
| human_resources | positions | approved | 2 | 0 | 0 | 17057 | 0.00952 | 85.6 | True | Khớp 4 dòng |
| human_resources | locations | approved | 1 | 0 | 0 | 18374 | 0.010066 | 113.8 | True | Khớp 8 dòng |
| amplitude | amplitude__event_enhanced | failed | 2 | 3 | 0 | 69942 | 0.031503 | 197.0 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| amplitude | amplitude__sessions | approved | 1 | 1 | 0 | 41117 | 0.035848 | 110.6 | False | 7/7 dòng khác bảng đúng |
| amplitude | amplitude__user_enhanced | approved | 2 | 0 | 0 | 25141 | 0.010437 | 64.3 | False | 1/7 dòng khác bảng đúng |
| computer_student | courses | approved | 2 | 0 | 0 | 21658 | 0.032517000000000004 | 96.9 | False | 15/132 dòng khác bảng đúng |
| cs_semester | students | approved | 3 | 0 | 0 | 23257 | 0.012858999999999999 | 89.1 | False | Khác cột — thiếu [], thừa ['gpa_based_on_registration'] |
| cs_semester | professors | approved | 3 | 0 | 0 | 20449 | 0.011465 | 80.7 | False | 5/10 dòng khác bảng đúng |
| cs_semester | courses | approved | 3 | 0 | 0 | 17917 | 0.009172000000000001 | 65.7 | False | 11/13 dòng khác bảng đúng |
| pinterest | pinterest_ads__ad_group_report | failed | 1 | 3 | 0 | 59027 | 0.023905000000000003 | 134.1 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| pinterest | pinterest_ads__campaign_report | approved | 0 | 0 | 0 | 21434 | 0.008919 | 57.3 | True | Khớp 5 dòng |
| pinterest | pinterest_ads__advertiser_report | approved | 0 | 0 | 0 | 21400 | 0.00912 | 60.9 | True | Khớp 5 dòng |
| pinterest | pinterest_ads__keyword_report | approved | 2 | 0 | 0 | 51813 | 0.021709 | 118.7 | False | 6/6 dòng khác bảng đúng |
| asana | asana__task | approved | 3 | 0 | 0 | 31800 | 0.015035999999999999 | 101.2 | False | 1/1 dòng khác bảng đúng |
| asana | asana__user | approved | 3 | 0 | 0 | 28709 | 0.012552999999999998 | 78.8 | True | Khớp 20 dòng |
| asana | asana__project | approved | 2 | 0 | 0 | 29921 | 0.013406 | 83.3 | False | 13/16 dòng khác bảng đúng |
| asana | asana__team | approved | 2 | 0 | 0 | 36087 | 0.041224000000000004 | 100.9 | False | 1/25 dòng khác bảng đúng |
| asana | asana__tag | approved | 1 | 0 | 0 | 23353 | 0.009344 | 55.6 | True | Khớp 17 dòng |
| mailchimp | mailchimp__lists | approved | 3 | 0 | 0 | 79699 | 0.083065 | 207.1 | False | 2/2 dòng khác bảng đúng |
| mailchimp | mailchimp__members | approved | 2 | 0 | 0 | 47015 | 0.020382 | 105.4 | False | 1/9 dòng khác bảng đúng |
| mailchimp | mailchimp__campaigns | approved | 0 | 0 | 0 | 33102 | 0.013377 | 73.9 | False | 1/1 dòng khác bảng đúng |
| mailchimp | mailchimp__campaign_recipients | failed | 1 | 2 | 0 | 54660 | 0.022967 | 134.2 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| mailchimp | mailchimp__campaign_activities | failed | 1 | 3 | 0 | 53985 | 0.021782 | 144.0 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| mailchimp | mailchimp__automations | approved | 1 | 0 | 0 | 49048 | 0.04887899999999999 | 137.0 | False | 2/2 dòng khác bảng đúng |
| mailchimp | mailchimp__automation_emails | approved | 0 | 0 | 0 | 41994 | 0.046738 | 154.0 | False | 2/2 dòng khác bảng đúng |
| mailchimp | mailchimp__automation_activities | approved | 1 | 1 | 0 | 37124 | 0.01379 | 88.3 | False | 8/8 dòng khác bảng đúng |
| mailchimp | mailchimp__segments | approved | 3 | 0 | 0 | 89254 | 0.08781900000000001 | 222.3 | True | Khớp 1 dòng |
| twilio | twilio__account_overview | approved | 4 | 0 | 0 | 45587 | 0.034248 | 132.6 | False | 1/1 dòng khác bảng đúng |
| tiktok_ads | tiktok_ads__advertiser_report | approved | 3 | 0 | 0 | 81150 | 0.049291 | 147.4 | False | Khác số dòng: 2 ≠ 4 (đúng) |
| tiktok_ads | tiktok_ads__ad_report | failed | 3 | 3 | 0 | 120048 | 0.042712 | 209.6 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| tiktok_ads | tiktok_ads__ad_group_report | approved | 3 | 0 | 0 | 66226 | 0.052617 | 148.5 | False | 3/4 dòng khác bảng đúng |
| tiktok_ads | tiktok_ads__campaign_report | failed | 3 | 3 | 0 | 90044 | 0.035951000000000004 | 204.4 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| lever | lever__posting_enhanced | approved | 3 | 0 | 0 | 68521 | 0.023902000000000003 | 130.3 | False | 3/3 dòng khác bảng đúng |
| lever | lever__requisition_enhanced | failed | 1 | 2 | 0 | 62831 | 0.023927 | 125.3 | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
