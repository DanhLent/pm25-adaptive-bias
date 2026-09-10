# Ngân hàng câu hỏi Q&A

## Vì sao dùng FPGA cho dữ liệu chỉ cập nhật theo giờ?

Mục tiêu là xây dựng một IP có thể tích hợp vào hệ thống nhúng và cho kết quả xác định theo chu kỳ. Nhu cầu hiện tại không đòi hỏi tốc độ cao, nhưng FPGA cho phép kiểm soát latency, fixed-point, tài nguyên và giao tiếp phần cứng. Full top chỉ dùng 6% logic và 5% register trên Tang Nano 9K.

## Vì sao không dùng PurpleAir trực tiếp?

PurpleAir phản ánh vị trí cục bộ nhưng có thể thiếu dữ liệu hoặc lệch A/B. CAMS cung cấp nền liên tục. QC gating ngăn một mẫu PurpleAir kém chất lượng làm thay đổi bias, trong khi CAMS vẫn duy trì đầu ra.

## Vì sao fused dùng bias trước cập nhật?

Quy tắc này giữ tính nhân quả và tránh để PurpleAir hiện tại thay thế ngay CAMS hiện tại. Mẫu hiện tại dạy trạng thái cho tương lai. Python và RTL cùng dùng semantics này.

## Vì sao shift 2 tốt hơn mà phần cứng vẫn dùng shift 3?

Shift 2 là candidate tốt nhất theo MAE trên dữ liệu hiện tại. Shift 3 là cấu hình đã đóng băng và đã qua board validation. Nhóm không tự promote tham số chỉ từ một đợt đánh giá. Thay đổi cần version mới, regression, synthesis và kiểm chứng kit lại.

## Kết quả MAE có chứng minh hệ thống đo chính xác không?

Không. MAE chỉ tính tại các giờ PurpleAir strict trong tập validation đang có. Kết quả chứng minh adaptive bias hữu ích trên phạm vi dữ liệu đã quan sát, không thay thế trạm chuẩn và không phải chứng nhận y tế.

## Tại sao dùng fixed-point x16?

x16 giữ độ phân giải 0,0625 µg/m³ và cho phép dùng số nguyên. Alpha một phần tám trở thành dịch phải số học ba bit, nên core không cần bộ nhân số thực.

## Core có throughput và latency thế nào?

`sample_ready` luôn bằng một, nên core nhận được một mẫu mỗi clock. Output dùng đường register một chu kỳ. Trong demo, UART stop-and-wait mới là nút giới hạn, không phải datapath của core.

## Tại sao không thêm FIFO?

UART 115200 baud chậm hơn nhiều so với clock core 27 MHz và dữ liệu môi trường chỉ cập nhật theo giờ. Stop-and-wait giữ wrapper nhỏ và dễ kiểm chứng. FIFO chỉ cần khi tích hợp vào giao tiếp có lưu lượng cao hơn.

## Vì sao chỉ dùng một bias, không dùng 24 bias theo giờ?

Core v1 giữ một trạng thái toàn cục để nhỏ, dễ kiểm chứng và đúng scope đã đóng băng. Trường `hour` được giữ trong interface và trace để tương thích, nhưng chưa tham gia phép toán.

## 140 giao dịch có đủ không?

Đây là targeted physical validation, gồm replay dữ liệu, QC hold, ngưỡng và bão hòa. Nó chứng minh đường UART và core khớp golden trên các ca đã chạy. Nhóm không gọi đây là formal hoặc exhaustive coverage.

## Nếu PurpleAir mất nhiều giờ thì sao?

CAMS vẫn tạo sample hợp lệ. `qc_ok=0` giữ bias, và fused bằng CAMS cộng bias trước đó. Khi dữ liệu tốt trở lại, core tiếp tục cập nhật từ state hiện có.

## Nếu dữ liệu lịch sử thay đổi sau reconciliation thì sao?

Pipeline phát hiện thay đổi trước giờ đã xử lý và thực hiện deterministic replay. Test xác nhận one-shot và split-run bit-identical, đồng thời replay cập nhật đúng state phía sau.

## Ngưỡng cảnh báo lấy từ đâu?

Ngưỡng là chính sách kỹ thuật đã đóng băng của core v1 và được kiểm thử tại các điểm biên. Báo cáo không trình bày chúng như một khuyến nghị sức khỏe mới. Đổi ngưỡng cần version hóa constants và chạy lại toàn bộ kiểm chứng.
