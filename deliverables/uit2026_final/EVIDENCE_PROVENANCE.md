# Nguồn gốc các số liệu trong báo cáo

Thời điểm khóa số liệu: 12:18 ngày 07/09/2026, múi giờ
Asia/Ho_Chi_Minh. Các tệp dưới đây được đọc tại chỗ; không gọi API và không
sửa dữ liệu nguồn. Dữ liệu vận hành có thể tiếp tục tăng sau thời điểm này, vì
vậy báo cáo dùng snapshot có hash và số đếm được lưu trong hồ sơ audit cuối.

## Tệp bằng chứng đã đối chiếu

| Tệp | Thời điểm sửa | SHA-256 |
| --- | --- | --- |
| `archive/reports/final_codex_review/audit_evidence/final_claim_snapshot.json` | 07/09/2026 12:18 +07:00 | `dbe595907f3735a1f9aec51c3259067381d1864277f6cbf8f51b1e1028d9e9f2` |
| `archive/reports/final_codex_review/audit_evidence/alpha_recomputed/latest_alpha_candidate.json` | 07/09/2026 12:18 +07:00 | `e2ba2c2799a2228a445b869e129dc2d45c3f171213b90c05e8f50c621592774f` |
| `reports/fpga/gowin_implementation_summary.json` | 14/08/2026 15:42:44 +07:00 | `e7ebbf5bebf4494ca65637a66759cd6a702ab1710240d1841f6caf58a9321306` |
| `reports/fpga/hardware_validation.json` | 14/08/2026 15:42:44 +07:00 | `6d96d3b7eb21e4273f38e49c40e249aac1eb5eda8ad3f15ea9a3f4b0600f40c1` |

## Số liệu vận hành

Tập PurpleAir dùng trong báo cáo kết thúc lúc 11:50 ngày 07/09/2026 theo giờ
Việt Nam. Trục thời gian CAMS kết thúc lúc 23:00 cùng ngày.

| Số liệu | Giá trị | Trường nguồn |
| --- | ---: | --- |
| Mẫu PurpleAir 10 phút | 4.137 | `purpleair_10min.rows` |
| Giờ có bản ghi nguồn PurpleAir | 1.309 | `purpleair_hourly.matched_source_hours` |
| Giờ có giá trị PurpleAir đại diện | 1.226 | `purpleair_hourly.hours_with_representative_value` |
| Giờ PurpleAir đủ điều kiện cập nhật | 553 | `purpleair_hourly.strict_qc_hours` |
| Khoảng thiếu dữ liệu 10 phút | 6 | `purpleair_10min.gap_count` |
| Bản ghi giờ CAMS hiện có | 13.704 | `cams.rows` |
| Giờ CAMS không có bản ghi nguồn PurpleAir | 12.395 | `left_join_timeline.unmatched_purpleair_source_hours` |
| Giờ thiếu trong hai quãng CAMS | 1.056 | `cams.missing_hours_total` |

## Đánh giá hệ số thích nghi

Đánh giá được chạy lại trên cùng snapshot chốt. Trong 553 giờ đạt QC, 138 giờ
được dùng để khởi động trạng thái và 415 giờ thuộc bốn phần kiểm định nối tiếp
theo thời gian.

| S | Hệ số | MAE CAMS | MAE hiệu chỉnh | RMSE hiệu chỉnh | Độ lệch chuẩn trạng thái x16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1/4 | 15,8884 | 4,2633 | 6,0729 | 71,23 |
| 3 | 1/8 | 15,8884 | 4,7259 | 6,7801 | 51,75 |
| 4 | 1/16 | 15,8884 | 4,9440 | 7,1817 | 36,46 |
| 5 | 1/32 | 15,8884 | 5,3190 | 7,4608 | 26,64 |
| 6 | 1/64 | 15,8884 | 6,0211 | 7,9180 | 18,63 |

Cấu hình đang dùng trước và sau đánh giá đều là S=3. S=2 là cấu hình có MAE quan sát thấp nhất nhưng không được tự động đưa vào thiết kế.

## Triển khai và kiểm chứng

| Số liệu | Giá trị | Nguồn |
| --- | ---: | --- |
| Phần tử logic | 490/8.640 (6%) | `gowin_implementation_summary.json` |
| Thanh ghi | 283/6.693 (5%) | `gowin_implementation_summary.json` |
| Tần số cực đại | 58,705 MHz | `gowin_implementation_summary.json` |
| Độ dư thiết lập / giữ nhỏ nhất | +20,003 / +0,572 ns | `gowin_implementation_summary.json` |
| Điểm cuối vi phạm thiết lập / giữ | 0/0 | `gowin_implementation_summary.json` |
| Giao dịch UART vật lý | 140 | `hardware_validation.json` |
| Sai khác vật lý | 0 | `hardware_validation.json` |
| Kiểm thử Python | 94 phép kiểm tra đạt | `.venv-ubuntu24/bin/python -m pytest -q` |
| Hồi quy lõi RTL | 18 bộ véc-tơ, 941 mẫu, 0 lỗi | `bash sim/scripts/run_all_core_tests.sh` |
| Kiểm thử gói tin UART | RX đạt, TX đạt | `bash sim/scripts/run_uart_packet_tests.sh` |

140 giao dịch chỉ chứng minh các trường hợp vật lý đã chọn; báo cáo không tuyên bố bao phủ hình thức, bao phủ UVM hoặc bao phủ toàn bộ không gian trạng thái.
