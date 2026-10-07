# ELT-Bench-Verified — chế độ `agent`

- Ngày chạy: 2026-10-02 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- Dữ liệu: 10 pipeline nhẹ nhất (eval/benchmarks/eltbench/tasks.yaml); ELT-Bench-Verified, CC BY-SA 4.0.
- Đầu ra đã lưu: `eval/results/eltbench_runs/2026-10-02_1327/` • chấm bằng bộ chấm hiện tại ngày 2026-10-07

**Khớp bảng kết quả đúng: 11/34 model**

- **Gồm** 2 model lỗi benchmark (chấm nghiêm, như benchmark gốc): 11/34
- **Không gồm** (bỏ 2 model ở known_issues.yaml khỏi mẫu số): 11/32
- Nếu bỏ qua cột lỗi benchmark thay vì bỏ model: 11/34
- Độ tin cậy thấp: 17/34 bảng đúng có ≤ 5 dòng (khớp trong số đó: 8/17). Cột `gt_rows` = số dòng bảng đúng.
- Câu hỏi làm rõ (J1): bộ chạy tự chọn **đáp án đầu tiên** (`options[0]`) cho mọi câu (cột `auto_answers`). Đây là đo *agent khi người trả lời bừa*, không phải *agent có người thật trả lời*.

| Task | Model | run_id | status | auto_answers | fix_attempts | rescue | tokens | cost_usd | seconds | gt_rows | ok | known_issue | ok_if_issue_ignored | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| human_resources | positions | cd3954f49e | approved | 2 | 0 | 0 | 17057 | 0.00952 | 85.6 | 4 | True | False | True | Khớp 4 dòng |
| human_resources | locations | db3a93df61 | approved | 1 | 0 | 0 | 18374 | 0.010066 | 113.8 | 8 | True | False | True | Khớp 8 dòng |
| amplitude | amplitude__event_enhanced | 1406360252 | failed | 2 | 3 | 0 | 69942 | 0.031503 | 197.0 | 10 | False | True | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| amplitude | amplitude__sessions | c7b83ae6ea | approved | 1 | 1 | 0 | 41117 | 0.035848 | 110.6 | 7 | False | False | False | 7/7 dòng khác bảng đúng — cột lệch ['unique_session_id']; mẫu: đúng=(11dc34b7c4be945c700770158de5113e) / agent=(a@gmail.com--1); đúng=(4f8dd535b6095749049460fba0fcfb69) / agent=(b@gmail.com--1); đúng=(54a0ffaa694132def0268898fc5e3cfa) / agent=(beyonce@gmail.com--1) |
| amplitude | amplitude__user_enhanced | 27b49e45a7 | approved | 2 | 0 | 0 | 25141 | 0.010437 | 64.3 | 7 | False | False | False | 1/7 dòng khác bảng đúng — cột lệch ['user_created_at']; mẫu: đúng=(2021-04-01 19:42:58.123) / agent=(2021-12-10 05:51:07) |
| computer_student | courses | 10305622f2 | approved | 2 | 0 | 0 | 21658 | 0.032517000000000004 | 96.9 | 132 | False | False | False | 15/132 dòng khác bảng đúng — cột lệch ['number_of_professors', 'number_of_professors_not_faculty', 'number_of_professors_faculty', 'taught_by_more_than_4_people']; mẫu: đúng=(1.0, 0.0, 1.0, 0.0) / agent=(1.0, 1.0, 0.0, 0.0); đúng=(3.0, 0.0, 2.0, 0.0) / agent=(2.0, 0.0, 2.0, 0.0); đúng=(2.0, 0.0, 1.0, 0.0) / agent=(1.0, 0.0, 1.0, 0.0) |
| cs_semester | students | c638fef272 | approved | 3 | 0 | 0 | 23257 | 0.012858999999999999 | 89.1 | 38 | False | True | False | Khác cột — thiếu [], thừa ['gpa_based_on_registration'] |
| cs_semester | professors | 13f688668e | approved | 3 | 0 | 0 | 20449 | 0.011465 | 80.7 | 10 | False | False | False | 5/10 dòng khác bảng đúng — cột lệch ['num_students_with_the_highest_research_ability']; mẫu: đúng=(0.0) / agent=(1.0); đúng=(0.0) / agent=(3.0); đúng=(0.0) / agent=(1.0) |
| cs_semester | courses | 4f752fc5ff | approved | 3 | 0 | 0 | 17917 | 0.009172000000000001 | 65.7 | 13 | False | False | False | 11/13 dòng khác bảng đúng — cột lệch ['number_of_students_fail', 'percentage_of_ug']; mẫu: đúng=(0.0, 14.285714) / agent=(0.0, 28.571428571428573); đúng=(1.0, 37.5) / agent=(0.0, 0.0); đúng=(0.0, 30.0) / agent=(0.0, 40.0) |
| pinterest | pinterest_ads__ad_group_report | 0121e18a16 | failed | 1 | 3 | 0 | 59027 | 0.023905000000000003 | 134.1 | 5 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| pinterest | pinterest_ads__campaign_report | 6c035839bd | approved | 0 | 0 | 0 | 21434 | 0.008919 | 57.3 | 5 | True | False | True | Khớp 5 dòng |
| pinterest | pinterest_ads__advertiser_report | 3fb1bb496f | approved | 0 | 0 | 0 | 21400 | 0.00912 | 60.9 | 5 | True | False | True | Khớp 5 dòng |
| pinterest | pinterest_ads__keyword_report | 4e2acc5f84 | approved | 2 | 0 | 0 | 51813 | 0.021709 | 118.7 | 6 | False | False | False | 6/6 dòng khác bảng đúng — cột lệch ['match_type', 'parent_type']; mẫu: đúng=(BROAD, AD_GROUP) / agent=(Broad, Ad group); đúng=(BROAD, AD_GROUP) / agent=(Broad, Ad group); đúng=(BROAD, AD_GROUP) / agent=(Broad, Ad group) |
| asana | asana__task | 01492cc965 | approved | 3 | 0 | 0 | 31800 | 0.015035999999999999 | 101.2 | 1 | False | False | False | 1/1 dòng khác bảng đúng — cột lệch ['task_description', 'has_been_assigned']; mẫu: đúng=(many notes, 0.0) / agent=(cool name, 1.0) |
| asana | asana__user | 64581c12de | approved | 3 | 0 | 0 | 28709 | 0.012552999999999998 | 78.8 | 20 | True | False | True | Khớp 20 dòng |
| asana | asana__project | b6e0767f2b | approved | 2 | 0 | 0 | 29921 | 0.013406 | 83.3 | 16 | False | False | False | 13/16 dòng khác bảng đúng — cột lệch ['due_date', 'number_of_users_involved']; mẫu: đúng=(NULL, 1.0) / agent=(NULL, 0.0); đúng=(NULL, 1.0) / agent=(NULL, 0.0); đúng=(NULL, 1.0) / agent=(NULL, 0.0) |
| asana | asana__team | e869faae19 | approved | 2 | 0 | 0 | 36087 | 0.041224000000000004 | 100.9 | 25 | False | False | False | 1/25 dòng khác bảng đúng — cột lệch ['active_projects']; mẫu: đúng=(35a0789351b1e8bea1efce4b7e1b6d58, 3a704…) / agent=(35a0789351b1e8bea1efce4b7e1b6d58, 3a704…) |
| asana | asana__tag | 0331ed198e | approved | 1 | 0 | 0 | 23353 | 0.009344 | 55.6 | 17 | True | False | True | Khớp 17 dòng |
| mailchimp | mailchimp__lists | 7d5cf37d71 | approved | 3 | 0 | 0 | 79699 | 0.083065 | 207.1 | 2 | False | False | False | 2/2 dòng khác bảng đúng — cột lệch ['date_created', 'most_recent_signup_timestamp', 'automation_unsubscribes']; mẫu: đúng=(2019-10-01 21:39:58, 2020-04-21 14:52:25, 1.0) / agent=(2019-10-01, 2020-04-21, 0.0); đúng=(2019-10-01 21:39:58, 2020-04-21 14:52:25, 0.0) / agent=(2019-10-01, 2020-04-21, 0.0) |
| mailchimp | mailchimp__members | a103fe222f | approved | 2 | 0 | 0 | 47015 | 0.020382 | 105.4 | 9 | False | False | False | 1/9 dòng khác bảng đúng — cột lệch ['automation_unsubscribes']; mẫu: đúng=(1.0) / agent=(0.0) |
| mailchimp | mailchimp__campaigns | 10f5dcacf2 | approved | 0 | 0 | 0 | 33102 | 0.013377 | 73.9 | 1 | True | False | True | Khớp 1 dòng |
| mailchimp | mailchimp__campaign_recipients | 5b155bb261 | failed | 1 | 2 | 0 | 54660 | 0.022967 | 134.2 | 10 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| mailchimp | mailchimp__campaign_activities | a0667b092d | failed | 1 | 3 | 0 | 53985 | 0.021782 | 144.0 | 17 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| mailchimp | mailchimp__automations | 5b940ac859 | approved | 1 | 0 | 0 | 49048 | 0.04887899999999999 | 137.0 | 2 | True | False | True | Khớp 2 dòng |
| mailchimp | mailchimp__automation_emails | 5ef54b7d85 | approved | 0 | 0 | 0 | 41994 | 0.046738 | 154.0 | 2 | True | False | True | Khớp 2 dòng |
| mailchimp | mailchimp__automation_activities | 860e2f5150 | approved | 1 | 1 | 0 | 37124 | 0.01379 | 88.3 | 8 | False | False | False | 8/8 dòng khác bảng đúng — cột lệch ['activity_id']; mẫu: đúng=(40967cab629427f1ad45d17dc22cb92a) / agent=(NULL); đúng=(fadbbda0a5bc4f1525cc0244b4ca83b0) / agent=(NULL); đúng=(b31cae1f1d145b07e8ce85f60e442aba) / agent=(NULL) |
| mailchimp | mailchimp__segments | 0e2f3b45bc | approved | 3 | 0 | 0 | 89254 | 0.08781900000000001 | 222.3 | 1 | True | False | True | Khớp 1 dòng |
| twilio | twilio__account_overview | d591da820f | approved | 4 | 0 | 0 | 45587 | 0.034248 | 132.6 | 1 | True | False | True | Khớp 1 dòng |
| tiktok_ads | tiktok_ads__advertiser_report | 3bea8dfc50 | approved | 3 | 0 | 0 | 81150 | 0.049291 | 147.4 | 4 | False | False | False | Khác số dòng: 2 ≠ 4 (đúng) |
| tiktok_ads | tiktok_ads__ad_report | 9ea77184a7 | failed | 3 | 3 | 0 | 120048 | 0.042712 | 209.6 | 4 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| tiktok_ads | tiktok_ads__ad_group_report | 2eb9cfff2a | approved | 3 | 0 | 0 | 66226 | 0.052617 | 148.5 | 4 | False | False | False | 3/4 dòng khác bảng đúng — cột lệch ['budget', 'daily_cpc', 'daily_cpm', 'daily_ctr']; mẫu: đúng=(500.0, 3.8, 237.5, 6.25) / agent=(0.0, 3.8, 237.5, 6.25); đúng=(900.0, 0.7675757575757576, 7.829984544049458, 1.0201) / agent=(0.0, 0.7675757575757576, 7.829984544049458, 1.0200927357032459); đúng=(500.0, NULL, NULL, NULL) / agent=(0.0, 0.0, 0.0, 0.0) |
| tiktok_ads | tiktok_ads__campaign_report | 5d089955ef | failed | 3 | 3 | 0 | 90044 | 0.035951000000000004 | 204.4 | 4 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
| lever | lever__posting_enhanced | 4a5636e364 | approved | 3 | 0 | 0 | 68521 | 0.023902000000000003 | 130.3 | 3 | False | False | False | 3/3 dòng khác bảng đúng — cột lệch ['created_at', 'updated_at']; mẫu: đúng=(2018-10-31 08:00:00, 2018-10-31 08:00:00) / agent=(2018-10-31, 2018-10-31); đúng=(2020-09-25 11:14:31, 2020-10-28 14:28:37) / agent=(2020-09-25, 2020-10-28); đúng=(2019-10-14 17:49:37, 2019-10-22 20:00:09) / agent=(2019-10-14, 2019-10-22) |
| lever | lever__requisition_enhanced | adbd61371d | failed | 1 | 2 | 0 | 62831 | 0.023927 | 125.3 | 3 | False | False | False | Đã dừng ở bước cứu hộ theo yêu cầu của người dùng. |
