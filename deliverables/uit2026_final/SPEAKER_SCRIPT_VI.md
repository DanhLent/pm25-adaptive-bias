# Kịch bản thuyết trình 7 phút

Mục tiêu diễn tập là 6 phút 30 giây, dành 30 giây cho nhịp sân khấu hoặc câu chuyển chậm hơn dự kiến. Một người trình bày toàn bộ; thành viên còn lại chuẩn bị demo.

## Slide 1 — 0:00–0:20

“Kính thưa Hội đồng, nhóm trình bày IP tự hiệu chỉnh cho hệ thống cảnh báo PM2.5 trên FPGA. Sản phẩm trung tâm là lõi RTL fixed-point đã được triển khai trên Tang Nano 9K và kiểm chứng qua UART. CAMS và PurpleAir cung cấp dữ liệu cho cơ chế hiệu chỉnh có kiểm soát chất lượng.”

## Slide 2 — 0:20–1:05

“CAMS cung cấp tín hiệu nền theo vùng và theo giờ, nhưng có thể chưa phản ánh sát một vị trí cụ thể. PurpleAir gần vị trí hơn và cập nhật nhanh hơn, nhưng cần kiểm tra chất lượng hai kênh A/B. Thiết kế dùng CAMS làm nền và chỉ dùng PurpleAir để cập nhật sai lệch khi dữ liệu đạt QC.”

Chuyển: “Từ lựa chọn đó, nhóm tách rõ phần xử lý dữ liệu và phần cứng.”

## Slide 3 — 1:05–1:55

“Host thu thập dữ liệu, QC và lượng tử hóa x16. Golden model Python tạo kết quả tham chiếu. Cùng một mẫu được gửi qua UART vào FPGA, sau đó host đối chiếu phản hồi theo từng trường. CAMS, PurpleAir và fused hardware-aligned luôn là ba chuỗi độc lập, nên hệ thống không đưa fused quay lại làm dữ liệu nền.”

## Slide 4 — 1:55–2:55

“Residual bằng PurpleAir trừ CAMS. Core lấy sai số giữa residual và bias cũ, rồi dịch phải ba bit để tạo delta. Fused hiện tại dùng bias trước cập nhật, nên PurpleAir của mẫu này chỉ dạy bias cho các mẫu sau. Khi QC fail, core vẫn tạo fused từ CAMS và bias cũ nhưng không cập nhật state. Scale x16 và alpha một phần tám giúp đường dữ liệu chỉ cần cộng, trừ, dịch số học, bão hòa và so sánh.”

## Slide 5 — 2:55–3:45

“PurpleAir được thu theo chu kỳ 10 phút. Một giờ strict cần ít nhất bốn mẫu tốt và coverage 30 phút. Dữ liệu hiện có 4.037 mẫu, tạo 536 giờ strict. Timeline CAMS giữ 13.680 giờ; trong 12.387 giờ thiếu PurpleAir, hệ thống vẫn sinh fused bằng bias đã học. State có version, lock và replay để nhiều lần scheduler chạy cho kết quả giống one-shot.”

## Slide 6 — 3:45–4:45

“Đánh giá theo bốn fold thời gian cho thấy shift 2 có MAE quan sát thấp nhất. Nhóm vẫn giữ shift 3 vì đây là cấu hình đã đóng băng và đã chạy trên phần cứng. Việc promote cần chạy lại regression, synthesis và board validation. Baseline vừa chạy lại có 94 test Python pass và 18 vector RTL với 941 mẫu, không có sai khác.”

## Slide 7 — 4:45–5:50

“Đây là kết quả phần cứng chính. Full UART top sử dụng 490 trên 8.640 logic, tương đương 6 phần trăm, và 283 register, tương đương 5 phần trăm. Fmax đạt 58,705 MHz so với clock mục tiêu 27 MHz. Báo cáo không ghi nhận endpoint setup hoặc hold vi phạm. Sau khi tạo bitstream và nạp SRAM, năm nhóm kiểm thử gồm 140 giao dịch đều khớp golden model.”

## Slide 8 — 5:50–6:30

“Demo sau đây gửi các ca QC tốt, QC fail, residual âm và dương, ngưỡng cảnh báo cùng bão hòa. Host hiển thị đầu vào, golden expected và phản hồi thực tế của FPGA. Kết luận của nhóm là một IP nhỏ, xác định và đã được kiểm chứng vật lý trong phạm vi công bố. Xin mời Hội đồng theo dõi demo.”

## Quy tắc diễn tập

- Không đọc tiêu đề slide.
- Không giải thích chi tiết pipeline Python ngoài vai trò QC, golden model và state.
- Dừng nửa nhịp trước bốn số trên slide 7.
- Không nói “AI” hoặc “deep learning”. Dùng “online adaptive bias” hoặc “hiệu chỉnh thích nghi trực tuyến”.
- Nếu vượt 6:30 ở lần tập thứ ba, rút ngắn slide 3 và slide 5 trước.
