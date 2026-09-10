# Manifest khóa bản Chung kết UIT 2026 — APB3

Ngày kiểm tra: 10/09/2026, múi giờ Asia/Ho_Chi_Minh.

| Artifact | Thuộc tính | Kích thước | SHA-256 |
| --- | --- | ---: | --- |
| `report/UIT2026_PM25_FPGA_FINAL_REPORT.pdf` | Bản báo cáo đã khóa; không chỉnh sửa trong lượt hoàn thiện slide APB3 | 266.365 byte | `b8f2dd5a79dcb0b88be3d5a0a9135fca29ee9577c6fb16d230bb9fc3c6f104b4` |
| `report/UIT2026_PM25_FPGA_FINAL_REPORT_SOURCE.zip` | Gói nguồn LaTeX bàn giao hiện có | 645.487 byte | `0678c8d004936100e2d5f287e7411589347f285a7ee5022e7fa647e7e735d02a` |
| `slides/UIT2026_PM25_FPGA_FINAL_APB.pptx` | 12 slide 16:9; 8 slide trình bày + 4 slide kỹ thuật ẩn; 12 speaker notes | 1.398.103 byte | `ac52279a4edcac42e6b2b80acf2f41f484f0562408b9b0f4ea8d4199f16aff7b` |
| `SPEAKER_SCRIPT_VI_APB_FINAL.md` | Kịch bản một người trình bày, mốc 0:00–6:30 | 5.222 byte | `57bc2ff7e484c27f6504d2928751059e65ff0ad461f8d9f4e5ef5a014b3ccf75` |
| `QNA_BANK_VI_APB_FINAL.md` | Ngân hàng Q&A, gồm tích hợp APB3 và giới hạn bằng chứng | 8.440 byte | `b7a984dc715bede66699be55e109cc2971a617238ed413421bbab61fed54aa2f` |
| `demo/UIT2026_PM25_DEMO_FALLBACK.mp4` | 60 giây, 1280×720, H.264 | 280.621 byte | `83309d0c15cdab8a453902b4cd0b3aa513c9781c1c9d668bcf2b772f588d2905` |

Các artifact dự kiến nộp đều nhỏ hơn giới hạn 10 MB mỗi file.

## Kiểm tra đã hoàn tất

- Baseline repository trước khi sửa: 96 pytest pass. Đây là kiểm tra đóng gói hiện tại; deck không dùng con số này để thay mốc 94 kiểm thử chức năng đã công bố trong báo cáo.
- RTL core: 18 bộ véc-tơ, 941 mẫu, 0 lỗi; năm giá trị shift, 450 mẫu, 0 lỗi.
- UART RTL: packet RX/TX, wrapper và serial regression pass.
- APB3 RTL: 89 giao dịch, 325 phép kiểm, 0 lỗi.
- Bằng chứng FPGA được giữ đúng phạm vi: UART vật lý 140/140 giao dịch; full UART top dùng 6% logic, 5% thanh ghi; Fmax 58,705 MHz tại mục tiêu 27 MHz; 0/0 endpoint vi phạm setup/hold.
- PPTX: package integrity pass; khổ 13,333 × 7,5 inch; 12 slide và 12 speaker notes; slide 9–12 có trạng thái ẩn.
- Đối tượng native: biểu đồ slide 7 chỉnh sửa được; bốn bảng native trên slide 9–11.
- Font: chỉ dùng Noto Sans và DejaVu Sans Mono; kiểm tra heading fit, overflow, overlap và geometry không có finding.
- Toàn bộ 12 slide đã được render riêng ở kích thước đầy đủ và kiểm tra lại bằng contact sheet.
- Nội dung hiển thị và speaker notes không còn nhãn hậu trường, câu phòng thủ hoặc đường dẫn nguồn lịch sử đã bị loại bỏ.
- Slide 1–8 dùng tên chức năng dễ hiểu; tên module RTL chỉ còn trong nguồn của speaker notes hoặc câu trả lời kỹ thuật cần truy vết.

## Bảo toàn nguồn

- Hai bản `UIT2026_PM25_FPGA_FINAL_REPORT.pdf` ở repository root và thư mục bàn giao đều giữ SHA-256 `b8f2dd5a79dcb0b88be3d5a0a9135fca29ee9577c6fb16d230bb9fc3c6f104b4`.
- Deck nguồn `slides/UIT2026_PM25_FPGA_FINAL_CE_REFINED.pptx` giữ SHA-256 `104c584eddc565fe5a32112bcef53787d904cad50dec591d5b974c08bb17b5b0`.
- Bản rollback `slides/UIT2026_PM25_FPGA_FINAL_APB_R1.pptx` giữ SHA-256 `b5b20a93167ebc81226c94bd854841058a65873de6f35fe4717ac9303c616d8c` và không nằm trong danh sách file nộp.
- Không thay đổi RTL, register map, thuật toán, ngưỡng, `ALPHA_SHIFT=3`, định dạng gói UART, pin board hoặc constraints.

## Giới hạn xác nhận

- Không tạo một lần chạy FPGA vật lý mới. Số liệu UART 140/140 và kết quả Gowin được dẫn từ bằng chứng đã lưu trong `reports/fpga/`.
- APB3 đã được kiểm chứng ở mô phỏng RTL; chưa có bằng chứng tích hợp CPU/SoC vật lý trong phạm vi bàn giao này.
- Tệp PPTX đã qua kiểm tra cấu trúc, render và kiểm tra thị giác trong môi trường bàn giao; chưa được mở lại bằng Microsoft PowerPoint bản desktop trong lượt khóa này.
