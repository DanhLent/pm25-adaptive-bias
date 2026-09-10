# Kịch bản thuyết trình Chung kết CE

Thời lượng mục tiêu: 6 phút 30 giây. Một thành viên trình bày, thành viên còn lại chuẩn bị phần demo.

## Slide 1 - 0:00-0:20

“Kính thưa Hội đồng, nhóm trình bày đề tài Thiết kế IP xử lý và cảnh báo bụi mịn PM2.5 trên FPGA. Nhóm tập trung vào lõi RTL hiệu chỉnh độ lệch thích nghi, triển khai trên Tang Nano 9K và kiểm chứng qua UART.”

## Slide 2 - 0:20-1:05

“CAMS cung cấp tín hiệu nền theo giờ và có khoảng thời gian bao phủ dài, nhưng có thể lệch so với điều kiện tại vị trí đo. PurpleAir quan sát cục bộ mỗi 10 phút, song hai kênh A và B cần được kiểm tra. Hệ thống giữ CAMS làm nền và chỉ dùng PurpleAir để cập nhật độ lệch khi QC đạt.”

Chuyển: “Từ lựa chọn dữ liệu này, nhóm phân tách rõ phần chuẩn bị dữ liệu và phần xử lý trên FPGA.”

## Slide 3 - 1:05-1:50

“Máy chủ thu thập dữ liệu, kiểm soát chất lượng và lượng tử hóa x16. Mô hình Python tạo kết quả tham chiếu. Cùng một mẫu được gửi qua UART vào FPGA để đối chiếu. CAMS, PurpleAir và kết quả hiệu chỉnh được lưu thành ba chuỗi độc lập, nên hệ thống không đưa kết quả hiệu chỉnh quay lại làm dữ liệu nền.”

## Slide 4 - 1:50-2:50

“Độ lệch quan sát bằng PurpleAir trừ CAMS. Lõi lấy sai số giữa độ lệch quan sát và bias trước cập nhật, rồi dịch phải số học ba bit. Đầu ra của mẫu hiện tại dùng `bias_before`, vì vậy quan sát của mẫu này chỉ ảnh hưởng đến các mẫu sau. Khi `qc_ok` bằng không, lõi vẫn tạo đầu ra nhưng giữ nguyên bias.”

## Slide 5 - 2:50-3:40

“Tập dữ liệu chốt đến 11 giờ 50 ngày 7 tháng 9 năm 2026 có 4.137 mẫu PurpleAir 10 phút. Có 1.309 giờ khớp bản ghi nguồn, 1.226 giờ tạo được giá trị đại diện và 553 giờ đạt QC nghiêm ngặt. CAMS có 13.704 bản ghi giờ. Trong 12.395 giờ thiếu bản ghi PurpleAir, lõi vẫn tạo đầu ra bằng CAMS cộng trạng thái độ lệch hiện tại.”

## Slide 6 - 3:40-4:35

“Kết quả trên 415 giờ kiểm định cho thấy S bằng 2 có MAE thấp nhất. Nhóm vẫn dùng S bằng 3 vì đây là cấu hình đã đóng băng và đã được kiểm chứng trên phần cứng. Việc đổi hệ số cần chạy lại hồi quy, tổng hợp và kiểm chứng bo mạch. Baseline hiện tại có 94 kiểm thử Python đạt và 941 mẫu RTL không lỗi.”

## Slide 7 - 4:35-5:50

“Thiết kế sử dụng 490 trên 8.640 phần tử logic và 283 trên 6.693 thanh ghi. Tần số cực đại đạt 58,705 MHz so với mục tiêu 27 MHz. Báo cáo timing không có vi phạm thiết lập hoặc giữ, với độ dư thiết lập đại diện là 20,003 ns. Cả 140 giao dịch UART trên Tang Nano 9K đều khớp mô hình tham chiếu.”

## Slide 8 - 5:50-6:30

“Demo lần lượt kiểm tra dữ liệu đạt QC, dữ liệu không đạt QC, độ lệch âm và dương, các biên cảnh báo và bão hòa. Với mỗi giao dịch, máy tính so sánh phản hồi FPGA với mô hình tham chiếu theo từng trường. Trong phạm vi công bố, kết quả cho thấy lõi hoạt động đúng trên các ca đã kiểm tra. Xin mời Hội đồng theo dõi phần demo.”

## Quy tắc diễn tập

- Không đọc tiêu đề slide.
- Dừng ngắn trước các số liệu chính trên slide 5, 6 và 7.
- Chỉ giữ tiếng Anh khi đó là tên chuẩn hoặc tín hiệu RTL.
- Dùng cụm “hiệu chỉnh độ lệch thích nghi”, không gọi hệ thống là AI hoặc học sâu.
- Nếu vượt 6 phút 30 giây, rút ngắn phần mô tả máy chủ ở slide 3.
