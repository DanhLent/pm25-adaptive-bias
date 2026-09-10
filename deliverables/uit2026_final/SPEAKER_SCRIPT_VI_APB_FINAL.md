# Kịch bản thuyết trình PM2.5 FPGA — bản APB3

Mục tiêu: kết thúc phần slide ở **6 phút 30 giây**, chừa 30 giây an toàn trước phần demo. Một thành viên trình bày xuyên suốt; thành viên còn lại chuẩn bị sẵn kết nối và cửa sổ demo.

## Slide 1 — Trang bìa — 0:00–0:20

“Kính thưa Hội đồng, nhóm xin trình bày IP xử lý và cảnh báo PM2.5 trên FPGA. Giải pháp kết hợp CAMS với PurpleAir, thực hiện hiệu chỉnh thích nghi bằng lõi RTL nhỏ và có thể tích hợp vào SoC qua APB3.”

## Slide 2 — Bài toán và lựa chọn dữ liệu — 0:20–1:00

“CAMS cung cấp tín hiệu nền liên tục nhưng đại diện cho vùng rộng. PurpleAir gần vị trí quan sát hơn, song có thể thiếu mẫu hoặc lệch giữa hai kênh A và B. Vì vậy, CAMS luôn tạo đầu ra nền; PurpleAir chỉ cập nhật trạng thái hiệu chỉnh khi vượt qua kiểm soát chất lượng. Hệ thống vẫn hoạt động khi dữ liệu cục bộ gián đoạn.”

## Slide 3 — Kiến trúc IP hoàn chỉnh — 1:00–1:50

“Thiết kế đặt toàn bộ phép hiệu chỉnh trong một lõi độc lập với giao tiếp. Khi tích hợp SoC, bộ xử lý dùng APB3 32 bit; khi kiểm chứng trên Tang Nano 9K, máy tính dùng UART. Hai đường này cùng sử dụng một lõi và không nối tiếp nhau. Thiết bị chủ chịu trách nhiệm QC và chuyển dữ liệu sang số nguyên x16. FPGA thực hiện hiệu chỉnh và ổn định cảnh báo.”

## Slide 4 — Lõi xử lý PM2.5 — 1:50–2:40

“Lõi lấy chênh lệch giữa PurpleAir và CAMS, so với trạng thái hiệu chỉnh hiện tại rồi điều chỉnh một phần tám sai số. Giá trị PM2.5 của mẫu hiện tại dùng trạng thái đã có; phần cập nhật chỉ áp dụng từ mẫu kế tiếp. Khi QC không đạt, trạng thái được giữ nguyên nhưng hệ thống vẫn tạo đầu ra từ CAMS. Cuối cùng, giá trị được giới hạn trong dải hợp lệ, phân mức và đưa qua vùng trễ để tránh cảnh báo dao động sát ngưỡng.”

## Slide 5 — Giao diện APB3 cho tích hợp SoC — 2:40–3:30

“Qua APB3, phần mềm nạp dữ liệu, phát `PROCESS`, theo dõi `BUSY/DONE` rồi đọc kết quả. Giao diện có 10 thanh ghi 32 bit và hoạt động trong một miền clock. Mỗi giao dịch bus hoàn tất không chèn chu kỳ đợi, còn phép xử lý được theo dõi riêng. Khi nhận lệnh, khối giao tiếp chốt đồng thời toàn bộ đầu vào nên lần ghi sau không thể đổi mẫu đang xử lý. Truy cập không hợp lệ được báo bằng `PSLVERR`.”

## Slide 6 — Dữ liệu và kiểm soát chất lượng — 3:30–4:10

“Tập dữ liệu chốt có 4.137 mẫu PurpleAir mười phút. Sau khi gom giờ, 1.309 giờ có bản ghi nguồn, 1.226 giờ có giá trị đại diện và 553 giờ đạt QC để cập nhật trạng thái. Trục thời gian có 13.704 giờ CAMS, trong đó 12.395 giờ không có bản ghi nguồn PurpleAir. PurpleAir cập nhật trạng thái khi đủ tin cậy; CAMS duy trì đầu ra liên tục.”

## Slide 7 — Đánh giá hệ số thích nghi — 4:10–5:05

“Biểu đồ so sánh năm giá trị S trên bốn đoạn kiểm định theo thời gian. Cấu hình IP v1 dùng `S=3`, tức alpha bằng một phần tám. Trên tập dữ liệu hiện tại, `S=2` giảm MAE từ 4,7259 xuống 4,2633 microgam trên mét khối, nhưng độ biến động trạng thái tăng từ 51,75 lên 71,23 x16. Đây là đánh đổi giữa tốc độ thích nghi và độ ổn định.”

## Slide 8 — Kết quả triển khai và mức sẵn sàng — 5:05–6:30

“Trên Tang Nano 9K, đường UART vật lý đạt 140 trên 140 giao dịch khớp mô hình tham chiếu. Toàn bộ cấu hình dùng 6 phần trăm logic và 5 phần trăm thanh ghi. Tần số cực đại là 58,705 MHz, cao hơn mục tiêu 27 MHz, với 0 điểm cuối vi phạm thiết lập và 0 điểm cuối vi phạm giữ.

Giao tiếp APB3 đạt 89 giao dịch và 325 phép kiểm ở mô phỏng RTL. Hai lớp bằng chứng được tách rõ: UART chứng minh đường dữ liệu trên FPGA vật lý; APB3 chứng minh hành vi giao tiếp ở mức RTL.

Sản phẩm đã có lõi độc lập với giao tiếp, APB3 để tích hợp SoC và UART để kiểm chứng trên kit. Xin mời Hội đồng theo dõi phần demo trực tiếp.”

## Nhịp trình bày

- Không đọc lại tiêu đề hoặc toàn bộ con số trên slide.
- Dừng ngắn sau ba ý: lõi độc lập với giao tiếp, chốt đồng thời dữ liệu đầu vào và hai phạm vi bằng chứng.
- Nếu vượt 6:30, rút một câu diễn giải ở slide 6 và một câu kết ở slide 7; không rút phần phân biệt APB3 với UART.
- Khi chuyển sang demo, người trình bày giữ lời dẫn; thành viên phụ trách demo chỉ thao tác và xác nhận kết quả trên màn hình.
