# Bộ tài liệu Chung kết Thiết kế Vi mạch UIT III 2026

Tên đề tài: **Thiết kế IP xử lý và cảnh báo bụi mịn PM2.5 trên FPGA**.

## File nộp chính

- `report/UIT2026_PM25_FPGA_FINAL_REPORT.pdf`
- `slides/UIT2026_PM25_FPGA_FINAL_APB.pptx`
- `demo/UIT2026_PM25_DEMO_FALLBACK.mp4` nếu BTC cho phép nộp kèm file dự phòng.

## File hỗ trợ

- `SPEAKER_SCRIPT_VI_APB_FINAL.md`: lời nói cho 8 slide chính, mốc 0:00–6:30.
- `QNA_BANK_VI_APB_FINAL.md`: câu trả lời ngắn, gồm các câu hỏi tích hợp APB3 và phạm vi bằng chứng.
- `slides/UIT2026_PM25_FPGA_FINAL_APB_R1.pptx`: bản trước lượt tinh chỉnh ngôn ngữ, chỉ dùng để rollback và không đưa vào bộ file nộp.
- `EVIDENCE_PROVENANCE.md`: nguồn của từng số liệu chính.
- `DELIVERY_MANIFEST.md`: kích thước, checksum và kết quả kiểm tra khóa cuối.
- `report/UIT2026_PM25_FPGA_FINAL_REPORT_SOURCE.zip`: mã nguồn LaTeX tự chứa, kèm trang bìa chính thức và các hình dùng trong báo cáo.
- `demo/DEMO_RUNBOOK_VI.md`: kịch bản demo 3 phút và checklist hội trường.
- `demo/run_demo_windows.ps1`: chạy 8 giao dịch hỗn hợp và 4 giao dịch bão hòa.
- `demo/UIT2026_PM25_DEMO_FALLBACK.mp4`: bản phát lại bằng chứng dự phòng, không thay thế demo live.
- `demo/UIT2026_PM25_HARDWARE_RESULT.png`: ảnh tóm tắt bằng chứng 140/140 để mở nhanh khi Q&A.
- `demo/logs/*_dryrun.csv`: log kiểm tra luồng demo không dùng COM; không phải log phần cứng mới.

## Biên dịch báo cáo

Báo cáo dùng XeLaTeX, khổ A4, phông Times New Roman (có phông thay thế tương thích), cỡ chữ 13 pt và giãn dòng 1,5. Bố cục đen--trắng gồm 5 trang đầu không đánh số và 12 trang đánh số từ Tóm tắt đến Tài liệu tham khảo. Các bảng có viền kín, khoảng đệm và quy tắc căn lề thống nhất.

Có thể biên dịch bằng Tectonic; tệp `preamble.tex` phải nằm cùng thư mục với `main.tex`:

```bash
cd deliverables/uit2026_final/report
../build/tools/tectonic -X compile main.tex --outdir ../build/report
```

Hoặc dùng XeLaTeX trong Overleaf. Tài liệu tham khảo được khai báo trực tiếp bằng môi trường `thebibliography`, không cần chạy BibTeX.

## Lưu ý trình chiếu

- Chỉ trình bày slide 1–8; kịch bản kết thúc ở 6:30 để chừa 30 giây an toàn trong phần slide 7 phút.
- Slide 9–12 đã được đặt trạng thái ẩn, chỉ mở khi cần trả lời Q&A kỹ thuật.
- PowerPoint là định dạng chính. Nên xuất thêm PDF từ PowerPoint trên chính laptop trình chiếu để dự phòng font.
- Video dự phòng là bản phát lại tĩnh từ bằng chứng đã lưu và được gắn nhãn rõ, không được mô tả như một lần chạy live mới.
- Không nộp thư mục `build/`; thư mục này chứa công cụ biên dịch và ảnh QA nội bộ.
