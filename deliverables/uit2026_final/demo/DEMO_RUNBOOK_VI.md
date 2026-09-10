# Kịch bản demo 3 phút

## Mục tiêu

Chứng minh Tang Nano 9K nhận packet UART, chạy đúng core fixed-point và trả kết quả khớp golden model Python theo từng giao dịch. Demo không cần Internet hoặc cảm biến ngoài.

## Chuẩn bị trước khi lên sân khấu

- Nạp đúng bitstream cho `pm25_uart_demo_top`.
- Xác nhận board dùng clock 27 MHz và UART 115200 baud.
- Mở Device Manager và ghi lại đúng cổng COM của board.
- Cắm nguồn laptop, tắt sleep và tắt các tiến trình scheduler PM2.5 trong thời gian demo.
- Đặt PowerShell ở project root và chạy dry-run:

```powershell
powershell -ExecutionPolicy Bypass -File .\deliverables\uit2026_final\demo\run_demo_windows.ps1 -DryRun
```

- Chạy thử live với cổng thực tế, ví dụ `COM4`:

```powershell
powershell -ExecutionPolicy Bypass -File .\deliverables\uit2026_final\demo\run_demo_windows.ps1 -Port COM4
```

## Nhịp demo

### 0:00–0:20 — Thiết lập

Nói: “Laptop gửi packet nhị phân qua USB-UART. FPGA trả fused PM2.5, bias và trạng thái cảnh báo. Python chỉ tính golden để đối chiếu.”

Chỉ vào tiêu đề các cột `cams`, `pa`, `fused`, `bias`, `level`, `accepted`, `state` và `check`.

### 0:20–1:35 — Tám giao dịch hỗn hợp

Chạy lượt đầu. Chỉ ra:

- Dòng `qc=1` có `accepted=1` và bias thay đổi.
- Dòng `qc=0` có `accepted=0`, nhưng fused vẫn hợp lệ và bias được giữ.
- Alert state bật khi fused vượt ngưỡng bật và chỉ tắt khi xuống dưới ngưỡng hysteresis.
- Mỗi dòng phải kết thúc bằng `PASS`.

### 1:35–2:25 — Bão hòa hai phía

Reset board theo prompt và chạy lượt hai. Hai mẫu đầu đưa bias tới biên dương. Hai mẫu sau đưa bias tới biên âm. Các giá trị đầu vào nằm trong int16 của packet UART.

Nói: “Core bão hòa bias ở cả hai phía, nên phép cập nhật lớn không gây wrap-around.”

### 2:25–2:50 — Kết quả

Chỉ vào hai dòng `SUMMARY` và thư mục log. Yêu cầu kết quả:

```text
SUMMARY rows=8 mismatches=0 mode=serial
SUMMARY rows=4 mismatches=0 mode=serial
```

Nói: “Demo hiện tại có 12 giao dịch. Bộ bằng chứng lưu trong repository gồm 140 giao dịch và 0 mismatch.”

### 2:50–3:00 — Chuyển sang Q&A

Nói: “Nhóm xin kết thúc phần demo và sẵn sàng trả lời câu hỏi của Hội đồng.”

## Khi demo gặp lỗi

1. Không thử sửa cổng COM quá 20 giây trên sân khấu.
2. Chuyển sang video `UIT2026_PM25_DEMO_FALLBACK.mp4` và nói rõ đây là bản phát lại bằng chứng đã lưu.
3. Nếu video không phát, mở `UIT2026_PM25_HARDWARE_RESULT.png`, slide phụ lục 10 để giải thích packet và slide 7 để trình bày kết quả 140/140.
4. Có thể chạy `-DryRun` để minh họa packet và golden model. Phải nói rõ dry-run không giao tiếp với FPGA.

## Checklist mang đến hội trường

- Tang Nano 9K đã nạp và một bản bitstream dự phòng.
- Laptop và bộ sạc.
- Hai cáp USB đã thử data, không chỉ sạc.
- USB hub nếu laptop thiếu cổng.
- Bản PPTX, PDF của slide và video dự phòng lưu cục bộ.
- Môi trường `.venv` có `pyserial`.
- File CSV demo và script PowerShell.
- Ảnh chụp kết quả 140/140 và report Gowin.
- Tắt sleep, update, notification và ứng dụng có thể chiếm cổng COM.
