# Ngân hàng Q&A PM2.5 FPGA — bản APB3

Các câu trả lời dưới đây được viết để nói trong khoảng 20–40 giây. Slide 9–12 cung cấp số liệu và giao thức chi tiết khi Hội đồng cần đối chiếu.

## Vì sao dùng FPGA khi dữ liệu chỉ cập nhật theo giờ?

Mục tiêu của đề tài là một IP nhúng có hành vi xác định, tài nguyên nhỏ và giao diện tích hợp rõ ràng. Tốc độ dữ liệu hiện tại không phải lý do chính. FPGA cho phép xác định chính xác độ trễ, kiểm chứng số học fixed-point và đưa cùng lõi xử lý vào SoC. Toàn bộ cấu hình UART hiện chỉ dùng 6% logic và 5% thanh ghi trên Tang Nano 9K.

## Vì sao phải kết hợp CAMS và PurpleAir?

CAMS cung cấp tín hiệu nền liên tục nhưng đại diện cho vùng rộng. PurpleAir phản ánh quan sát cục bộ hơn nhưng có thể thiếu dữ liệu hoặc không đạt kiểm tra hai kênh A/B. Thiết kế dùng CAMS làm nền và chỉ cho PurpleAir cập nhật trạng thái hiệu chỉnh khi `qc_ok=1`, nhờ đó một mẫu cục bộ kém chất lượng không làm đổi trạng thái.

## Vì sao kết quả dùng trạng thái trước cập nhật?

Quy tắc này giữ quan hệ nhân quả: quan sát PurpleAir ở mẫu hiện tại cập nhật trạng thái cho tương lai, không sửa ngược ngay chính mẫu đang quan sát. Mô hình tham chiếu và RTL dùng cùng một thứ tự, nên kết quả có thể đối chiếu chính xác từng bit.

## Vì sao dùng fixed-point x16?

Thang x16 cho độ phân giải 0,0625 µg/m³ nhưng vẫn chỉ cần số nguyên. Với `S=3`, phép nhân alpha bằng một phần tám trở thành dịch phải số học ba bit, giúp datapath nhỏ và dễ kiểm chứng.

## Vì sao IP v1 dùng S=3 khi S=2 có MAE thấp hơn?

Hai giá trị thể hiện một đánh đổi. Trên tập dữ liệu đánh giá, `S=2` giảm MAE hiệu chỉnh từ 4,7259 xuống 4,2633 µg/m³ nhưng độ biến động trạng thái tăng từ 51,75 lên 71,23 x16. Cấu hình IP v1 và bằng chứng triển khai hiện tại dùng `S=3`. Kết quả `S=2` chỉ phản ánh phép đánh giá trên tập dữ liệu này.

## Kết quả MAE có chứng minh thiết bị đo chính xác không?

Không. MAE được tính tại các giờ PurpleAir đạt QC trong tập kiểm định theo thời gian. Kết quả cho thấy cơ chế hiệu chỉnh thích nghi cải thiện sai số quan sát trong phạm vi dữ liệu đó. PurpleAir không thay thế trạm chuẩn và kết quả không phải chứng nhận y tế.

## Lõi có thông lượng và độ trễ như thế nào?

Lõi xử lý trung tâm (`pm25_alert_core`) có thể nhận một mẫu ở mỗi chu kỳ khi `sample_valid` được chấp nhận. Kết quả đi qua một tầng thanh ghi. Trong đường demo, UART 115200 baud và cơ chế gửi một yêu cầu rồi chờ phản hồi mới là giới hạn tốc độ thực tế.

## Vì sao tách APB3 và UART thành hai khối giao tiếp?

APB3 phục vụ tích hợp theo ánh xạ bộ nhớ với CPU trong SoC. UART phục vụ kiểm chứng vật lý từ máy tính trên Tang Nano 9K. Hai khối giao tiếp độc lập cùng sử dụng lõi hiệu chỉnh (`pm25_alert_core`), vì vậy thuật toán không phụ thuộc phương tiện kiểm chứng. APB3 không đi qua UART.

## Một lần xử lý qua APB3 diễn ra thế nào?

CPU ghi các thanh ghi đầu vào, phát lệnh `PROCESS`, đọc `STATUS` để theo dõi `BUSY/DONE`, sau đó đọc kết quả và trạng thái hiệu chỉnh. `PROCESS` là lệnh ghi một để kích hoạt rồi tự xóa. `DONE` được giữ lại để phần mềm không bỏ lỡ kết quả.

## Zero-wait-state có mâu thuẫn với BUSY không?

Không. `PREADY=1` mô tả thời gian hoàn thành của từng giao dịch đọc/ghi APB. `BUSY` mô tả trạng thái của phép xử lý được khởi động bởi giao dịch đó. Bus không bị giữ chờ, còn phần mềm dùng `BUSY/DONE` để biết khi nào kết quả sẵn sàng.

## Việc chốt đồng thời dữ liệu đầu vào giải quyết vấn đề gì?

Khi `PROCESS` được chấp nhận, khối giao tiếp APB3 (`pm25_apb_wrapper`) chốt đồng thời toàn bộ dữ liệu đầu vào. Vì vậy, các lần ghi sau đó không thể trộn dữ liệu mới vào mẫu đang xử lý. Nếu phát `PROCESS` khi `BUSY=1`, khối giao tiếp báo lỗi thay vì bắt đầu một mẫu chồng lấn.

## APB3 phản hồi lỗi trong trường hợp nào?

`PSLVERR` được dùng cho truy cập lệch hàng 32 bit, địa chỉ ngoài bản đồ, ghi vào thanh ghi chỉ đọc và phát `PROCESS` khi lõi đang bận. Điều này giúp phần mềm phát hiện lỗi ngay tại giao dịch bus.

## Vì sao chỉ có 10 thanh ghi?

Bản đồ được chia thành bốn nhóm: điều khiển và trạng thái, dữ liệu đầu vào, kết quả, cùng trạng thái hiệu chỉnh. Mục tiêu là đủ cho một lần xử lý nhất quán mà không đưa thuật toán vào khối giao tiếp. Slide 9 giữ ánh xạ đầy đủ để tra cứu khi cần.

## Phạm vi kiểm chứng APB3 đến đâu?

Khối giao tiếp APB3 đã đạt 89 giao dịch và 325 phép kiểm ở mô phỏng RTL, bao gồm luồng hợp lệ và các phản hồi lỗi. Chưa có bằng chứng APB3 chạy trên CPU/SoC vật lý trong phạm vi bàn giao này. Bằng chứng vật lý 140/140 thuộc đường UART trên Tang Nano 9K.

## Vì sao UART không cần FIFO?

UART 115200 baud chậm hơn nhiều so với clock 27 MHz của lõi. Máy tính gửi một yêu cầu, chờ đủ phản hồi rồi mới gửi yêu cầu tiếp theo. FIFO chỉ cần khi hệ thống yêu cầu thông lượng hoặc mức đồng thời cao hơn. Trong phiên bản này, FIFO sẽ tăng trạng thái và phạm vi kiểm chứng nhưng không giải quyết một nút thắt hiện hữu.

## 140 giao dịch vật lý có đủ không?

Đây là kiểm chứng vật lý có chủ đích, gồm phát lại dữ liệu, giữ trạng thái khi QC không đạt, các điểm biên cảnh báo và bão hòa. Các ca đã chạy qua toàn bộ đường UART và lõi đều khớp mô hình tham chiếu. Con số này không đại diện cho kiểm chứng hình thức hoặc bao phủ toàn bộ không gian trạng thái.

## Vì sao lõi chỉ giữ một trạng thái hiệu chỉnh thay vì một trạng thái cho từng giờ?

Phiên bản một dùng một trạng thái chung để giữ đường dữ liệu nhỏ và phạm vi kiểm chứng rõ. Trường `hour` vẫn có trong giao diện và dữ liệu truy vết để bảo toàn định dạng, nhưng chưa tham gia phép tính. Trạng thái hiệu chỉnh theo từng giờ sẽ là một mở rộng kiến trúc, không phải thay đổi nhỏ của bản đồ thanh ghi.

## Điều gì xảy ra khi PurpleAir mất dữ liệu trong thời gian dài?

CAMS vẫn cung cấp mẫu nền. Với `qc_ok=0`, trạng thái hiệu chỉnh được giữ nguyên và đầu ra tiếp tục bằng CAMS cộng độ lệch đã học. Khi quan sát cục bộ đạt QC trở lại, lõi tiếp tục cập nhật từ trạng thái hiện có.

## Ngưỡng cảnh báo được chọn như thế nào?

Đó là bộ hằng kỹ thuật đã đóng băng cho lõi v1 và đã được kiểm thử tại các điểm biên cùng vùng trễ cảnh báo. Tài liệu không trình bày các ngưỡng này như một khuyến nghị sức khỏe mới. Nếu thay đổi, nhóm phải tạo phiên bản hằng mới và chạy lại hồi quy, tổng hợp cùng các bước kiểm chứng liên quan.

## Giới hạn bằng chứng quan trọng nhất là gì?

Ba giới hạn cần nói rõ: PurpleAir không phải trạm chuẩn; đánh giá hệ số chỉ áp dụng cho tập dữ liệu đã khóa; và APB3 mới có bằng chứng mô phỏng RTL, chưa có kiểm chứng tích hợp SoC vật lý. Các kết quả UART, tài nguyên và timing thuộc cấu hình Tang Nano 9K đã lưu, không đại diện cho mọi nền tảng.
