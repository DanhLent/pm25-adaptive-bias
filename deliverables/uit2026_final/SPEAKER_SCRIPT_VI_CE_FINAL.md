# Kịch bản thuyết trình 7 phút

Mục tiêu diễn tập là 6 phút 30 giây, dành khoảng 30 giây cho nhịp sân khấu. Một thành viên trình bày slide, thành viên còn lại chuẩn bị demo.

## Slide 1 - 0:00-0:20

“Kính thưa Hội đồng, nhóm trình bày IP xử lý và cảnh báo bụi mịn PM2.5 trên FPGA. Sản phẩm trung tâm là lõi RTL dùng số học x16, đã triển khai trên Tang Nano 9K và kiểm chứng qua UART. CAMS cung cấp tín hiệu nền, còn PurpleAir chỉ cập nhật độ lệch khi dữ liệu đạt yêu cầu chất lượng.”

## Slide 2 - 0:20-1:05

“CAMS cung cấp nền theo vùng và theo giờ nhưng có thể chưa phản ánh sát một vị trí cụ thể. PurpleAir gần vị trí hơn và cập nhật mỗi 10 phút, song hai kênh A/B cần được kiểm tra. Thiết kế giữ CAMS làm nền và chỉ dùng PurpleAir để cập nhật độ lệch khi QC cho phép.”

Chuyển: “Từ lựa chọn đó, nhóm phân tách rõ phần chuẩn bị dữ liệu và phần cứng.”

## Slide 3 - 1:05-1:50

“Máy chủ thu thập dữ liệu, kiểm soát chất lượng và lượng tử hóa x16. Mô hình Python tạo kết quả tham chiếu. Cùng một mẫu được gửi qua UART vào FPGA để đối chiếu từng trường. CAMS, PurpleAir và kết quả hiệu chỉnh luôn được giữ thành ba chuỗi độc lập, nên hệ thống không đưa kết quả đã hiệu chỉnh quay lại làm dữ liệu nền.”

## Slide 4 - 1:50-2:50

“Độ lệch quan sát bằng PurpleAir trừ CAMS. Lõi lấy sai số giữa độ lệch quan sát và trạng thái cũ, rồi dịch phải số học ba bit để tạo lượng cập nhật. Đầu ra hiện tại dùng bias_before, vì vậy PurpleAir của mẫu này chỉ tác động đến các mẫu sau. Nếu QC không đạt, lõi vẫn tạo đầu ra từ CAMS và trạng thái cũ nhưng không cập nhật trạng thái.”

## Slide 5 - 2:50-3:40

“Tập dữ liệu chốt có 4.137 mẫu PurpleAir 10 phút. Có 1.309 giờ khớp bản ghi nguồn, 1.226 giờ tạo được giá trị đại diện và 553 giờ đạt QC nghiêm ngặt để cập nhật độ lệch. CAMS giữ 13.704 bản ghi giờ. Trong 12.395 giờ không có bản ghi PurpleAir, lõi vẫn tạo đầu ra bằng CAMS cộng trạng thái độ lệch hiện tại.”

## Slide 6 - 3:40-4:35

“Đánh giá theo bốn phần thời gian cho thấy S bằng 2 có MAE quan sát thấp nhất. Nhóm vẫn giữ S bằng 3 vì đây là cấu hình đã đóng băng và đã qua kiểm chứng phần cứng. Việc thay đổi hệ số cần chạy lại hồi quy, tổng hợp và kiểm chứng bo mạch. Baseline hiện tại có 94 kiểm thử Python đạt và 941 mẫu RTL không lỗi.”

## Slide 7 - 4:35-5:50

“Toàn bộ mô-đun mức cao nhất sử dụng 490 trên 8.640 phần tử logic và 283 trên 6.693 thanh ghi. Tần số cực đại đạt 58,705 MHz so với xung nhịp mục tiêu 27 MHz, không có điểm cuối vi phạm thiết lập hoặc giữ. Năm nhóm kiểm thử vật lý gồm 140 giao dịch đều khớp mô hình tham chiếu.”

## Slide 8 - 5:50-6:30

“Demo gửi lần lượt các ca dữ liệu đạt QC, không đạt QC, độ lệch âm và dương, biên cảnh báo và bão hòa. Với mỗi giao dịch, máy tính hiển thị đầu vào, kết quả tham chiếu và phản hồi thực tế của FPGA. Nhóm kết luận rằng IP có quy mô nhỏ, phép toán xác định và đã được kiểm chứng vật lý trong phạm vi công bố. Xin mời Hội đồng theo dõi phần demo.”

## Quy tắc diễn tập

- Không đọc tiêu đề slide.
- Dừng nửa nhịp trước các số liệu chính trên slide 5, 6 và 7.
- Chỉ dùng thuật ngữ tiếng Anh khi đó là tên chuẩn hoặc tên tín hiệu RTL.
- Không gọi hệ thống là AI hoặc học sâu; dùng “hiệu chỉnh độ lệch thích nghi trực tuyến”.
- Nếu vượt 6 phút 30 giây, rút ngắn phần mô tả máy chủ ở slide 3 trước.
