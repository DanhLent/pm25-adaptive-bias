# Giải thích tổng quan project PM2.5 CAMS + PurpleAir

Tài liệu này giải thích project bằng tiếng Việt, theo cách dễ đọc cho người mới làm quen với xử lý tín hiệu và học máy. Nội dung chỉ mô tả trạng thái hiện tại của project, không thêm thuật toán mới và không thay đổi pipeline lõi.

## 1. Tóm tắt ngắn gọn đề tài

Đề tài này xây dựng một hệ thống xử lý, kết hợp và cảnh báo nồng độ bụi mịn PM2.5 quanh khu vực ký túc xá ĐHQG TP.HCM. PM2.5 là loại bụi rất nhỏ trong không khí, có đường kính khoảng 2.5 micromet hoặc nhỏ hơn. Khi nồng độ PM2.5 cao, chất lượng không khí xấu hơn và có thể ảnh hưởng sức khỏe.

Project đang dùng hai nguồn dữ liệu chính:

- CAMS/Open-Meteo: nguồn dữ liệu PM2.5 theo giờ, có chuỗi dài hơn. Có thể xem CAMS như tín hiệu nền dài hạn, phản ánh tình hình ô nhiễm theo mô hình/lưới khí quyển, không phải đo trực tiếp ngay tại cảm biến.
- PurpleAir: dữ liệu cảm biến cục bộ/realtime, phản ứng nhanh hơn với môi trường gần điểm đo. Tuy nhiên cảm biến này nhiễu hơn, dữ liệu hiện tại ngắn hơn, và hai kênh A/B đang lệch khá mạnh.

Lý do cần kết hợp hai nguồn là: CAMS ổn định và có dữ liệu dài, nhưng có thể chưa phản ánh thật sát điều kiện cục bộ; PurpleAir gần vị trí đo hơn và cập nhật nhanh hơn, nhưng cần kiểm tra chất lượng kỹ. Project dùng CAMS làm nền, dùng PurpleAir để hiệu chỉnh phần sai lệch cục bộ, sau đó tạo tín hiệu PM2.5 đã hiệu chỉnh.

Mục tiêu cuối cùng là tạo một hệ thống có thể:

- ước lượng PM2.5 đã kết hợp từ CAMS và PurpleAir;
- phân mức cảnh báo hiện tại;
- cảnh báo sớm khả năng vượt ngưỡng trong 1 giờ, 3 giờ và 6 giờ.

Hiện tại project nên được hiểu là proof-of-concept, tức là bản chứng minh ý tưởng và pipeline. Chưa nên xem đây là một mô hình dự báo đã được kiểm chứng mạnh, vì phần dữ liệu PurpleAir trùng với CAMS còn rất ngắn.

## 2. Hiện tại project đã làm tới đâu?

| Stage | Mục tiêu | Đã tạo ra gì | Ý nghĩa thực tế |
| --- | --- | --- | --- |
| Stage 1 | Đọc dữ liệu, kiểm tra dữ liệu, chuẩn hóa thời gian, đồng bộ CAMS và PurpleAir. | Các script xử lý ban đầu, dataset hourly đã ghép, báo cáo kiểm tra dữ liệu, báo cáo tiền xử lý, mô hình baseline và hình minh họa. | Chứng minh dữ liệu thô có thể được đưa về một timeline chung để phân tích. |
| Stage 1.5 | Review lại dữ liệu và QC, tránh báo cáo quá lạc quan. | QC strict/loose cho PurpleAir, cảnh báo về metric classification, hình kiểm tra A/B channel, `reports/STAGE_1_REVIEW.md`. | Làm project trung thực hơn: dữ liệu cảm biến không được tin mù quáng. |
| Stage 2 | Xây thuật toán fusion và cảnh báo nhẹ, thân thiện với phần cứng. | `src/fusion_alert.py`, timeline fusion, metric Stage 2, hình Stage 2, báo cáo thiết kế và đánh giá. | Có được thuật toán chính: residual, EMA, Dual-EMA, confidence gating, hysteresis alert, early warning. |
| Stage 2.1 | Polish thuật toán và báo cáo. | Thêm confidence diagnostics, sửa forecast âm bằng cách chặn dưới tại 0, thêm cờ metric có ý nghĩa hay không, thêm executive summary. | Giúp kết quả dễ giải thích hơn và tránh hiểu nhầm về độ mạnh của metric. |
| Stage 3 | Tạo nền tảng thu thập/cập nhật dữ liệu. | Fetcher Open-Meteo, fetcher PurpleAir, append/deduplicate, incremental update, latest snapshot. | Chuẩn bị để tích lũy dữ liệu thật theo thời gian, thay vì chỉ chạy trên file có sẵn. |
| Stage 3.1 | Polish API fetch. | Chế độ dry-run rõ hơn, PurpleAir exact sensor endpoint, bounding-box search, xử lý timezone cho history fetch, test request construction. | Giúp bước lấy dữ liệu thật sau này an toàn và dễ kiểm tra hơn trước khi gọi API thật. |

Tóm lại, project hiện đã có pipeline xử lý dữ liệu, thuật toán fusion/cảnh báo, các báo cáo chính, hình minh họa và nền tảng cập nhật dữ liệu. Chưa có Stage 4 thật sự về vận hành live dài hạn hoặc học máy nâng cao.

## 3. Dữ liệu đang có

### CAMS/Open-Meteo

CAMS/Open-Meteo là dữ liệu PM2.5 theo giờ. Trong project này, nó được dùng làm tín hiệu nền dài hạn. Dữ liệu hiện tại có chuỗi từ khoảng `2025-01-01 00:00:00+07:00` đến `2026-05-14 23:00:00+07:00`.

Cần hiểu rõ: CAMS/Open-Meteo không phải cảm biến đo trực tiếp tại đúng vị trí PurpleAir. Đây là dữ liệu từ mô hình/lưới khí quyển, nên phù hợp làm nền nhưng có thể bỏ sót sai lệch cục bộ quanh điểm đo.

### PurpleAir

PurpleAir là dữ liệu từ cảm biến cục bộ/realtime. Dữ liệu hiện tại chỉ nằm trong khoảng `2026-05-12 10:20:32+07:00` đến `2026-05-14 10:17:19+07:00`. Ban đầu dữ liệu có tần suất vài phút/lần, sau đó được gom về hourly để ghép với CAMS.

PurpleAir có hai kênh A/B. Hai kênh này đang lệch mạnh: theo working state, A/B disagreement là `1069 / 1435` dòng, tương đương `74.49%`, với mean absolute difference khoảng `11.344 ug/m3`. Vì vậy project phải có QC, tức kiểm tra chất lượng dữ liệu, thay vì tin tuyệt đối vào cảm biến.

Overlap hiện tại giữa CAMS và PurpleAir chỉ khoảng 49 giờ. Trong đó strict valid hourly rows của PurpleAir là 22 giờ, còn loose fallback hourly rows là 27 giờ. Vì overlap quá ngắn, project chưa thể claim mạnh về học máy hoặc khả năng dự báo vận hành thực tế.

## 4. Các thuật toán chính đang có

### 4.1 QC PurpleAir

QC nghĩa là kiểm tra chất lượng dữ liệu. Với PurpleAir, project kiểm tra các điểm như:

- giá trị âm hoặc bất thường;
- số mẫu hợp lệ trong mỗi giờ;
- tỷ lệ mẫu xấu trong mỗi giờ;
- độ lệch giữa kênh A và kênh B.

Nếu A/B lệch quá mạnh, hệ thống giảm độ tin cậy của PurpleAir. Project có hai mức sử dụng dữ liệu:

- strict valid: dữ liệu đạt điều kiện chặt hơn;
- loose fallback: dữ liệu chưa lý tưởng nhưng vẫn có thể dùng có kiểm soát khi thiếu strict valid.

Điểm quan trọng là project không âm thầm bỏ qua vấn đề dữ liệu. Nó ghi nhận rõ chất lượng cảm biến để phần fusion biết nên tin PurpleAir nhiều hay ít.

### 4.2 Đồng bộ thời gian

CAMS là dữ liệu theo giờ. PurpleAir là dữ liệu realtime/few-minute, tức là vài phút có thể có một bản ghi. Để ghép hai nguồn, PurpleAir được gom về hourly. Sau đó CAMS và PurpleAir được merge theo cùng mốc giờ.

Việc đồng bộ này giúp mỗi dòng dữ liệu đại diện cho một giờ, trong đó có PM2.5 nền từ CAMS và PM2.5 cục bộ từ PurpleAir.

### 4.3 Residual

Residual là phần sai lệch giữa PurpleAir và CAMS:

```text
residual = PurpleAir_PM25 - CAMS_PM25
```

Nếu residual dương, PurpleAir đang cao hơn CAMS. Nếu residual âm, PurpleAir đang thấp hơn CAMS. Residual cho biết sai lệch cục bộ giữa cảm biến và tín hiệu nền.

Trong project này, residual rất quan trọng vì hệ thống không chỉ lọc trực tiếp PM2.5 thô. Thay vào đó, nó học/cập nhật phần sai lệch giữa PurpleAir và CAMS, rồi cộng phần hiệu chỉnh đó trở lại CAMS.

### 4.4 Single EMA

EMA là bộ lọc trung bình mũ. Có thể hiểu đơn giản: EMA làm mượt tín hiệu bằng cách kết hợp giá trị mới với giá trị quá khứ. Công thức thường dùng là:

```text
ema[t] = alpha * x[t] + (1 - alpha) * ema[t-1]
```

Trong đó `x[t]` là giá trị hiện tại, `ema[t-1]` là giá trị EMA trước đó, còn `alpha` quyết định hệ thống phản ứng nhanh hay chậm. Alpha lớn thì phản ứng nhanh hơn nhưng dễ nhiễu hơn. Alpha nhỏ thì mượt hơn nhưng chậm hơn.

Single EMA trong project dùng để làm mượt residual, giúp giảm nhiễu từ PurpleAir.

### 4.5 Dual-EMA

Dual-EMA dùng hai EMA:

- EMA nhanh: bắt biến động nhanh hơn;
- EMA chậm: giữ xu hướng nền ổn định hơn.

Hiệu giữa EMA nhanh và EMA chậm cho biết xu hướng residual đang tăng hay giảm. Trong project, ý tưởng được viết như sau:

```text
residual_fast_ema = EMA nhanh của residual
residual_slow_ema = EMA chậm của residual
trend = residual_fast_ema - residual_slow_ema
fused_pm25 = CAMS + residual_slow_ema + beta * trend
```

Lý do lọc residual thay vì lọc PM2.5 thô là vì CAMS đã đóng vai trò nền. PurpleAir chỉ nên hiệu chỉnh sai lệch cục bộ, nhất là khi dữ liệu cảm biến có nhiễu. Cách này hợp lý hơn cho fusion và cũng thân thiện với phần cứng vì EMA chỉ cần phép cộng, nhân hệ số và lưu trạng thái trước đó.

### 4.6 Confidence gating

Confidence gating nghĩa là điều chỉnh mức độ tin vào PurpleAir. Không phải lúc nào hệ thống cũng tin PurpleAir như nhau.

Nếu dữ liệu cảm biến tốt, có đủ mẫu, ít mẫu xấu và A/B đồng thuận, PurpleAir được cho ảnh hưởng nhiều hơn. Nếu A/B lệch mạnh, dữ liệu ít hoặc nhiều mẫu xấu, hệ thống giảm trọng số của PurpleAir. Khi PurpleAir không đáng tin, hệ thống quay về dựa nhiều hơn vào CAMS.

Đây là phần rất quan trọng vì dữ liệu PurpleAir hiện tại đang có vấn đề A/B disagreement cao.

### 4.7 Fused PM2.5

Fused PM2.5 là tín hiệu PM2.5 cuối cùng sau khi kết hợp CAMS và phần hiệu chỉnh từ PurpleAir:

```text
fused_pm25 = CAMS + correction_from_PurpleAir
```

Trong Stage 2, correction được tính từ residual đã qua Dual-EMA và confidence gating. Fused PM2.5 là tín hiệu được dùng để đánh giá mức cảnh báo và cảnh báo sớm.

### 4.8 Hysteresis alert

Nếu chỉ dùng một ngưỡng duy nhất, cảnh báo có thể bật/tắt liên tục khi PM2.5 dao động quanh ngưỡng. Hysteresis giải quyết vấn đề này bằng cách dùng ngưỡng bật và ngưỡng tắt khác nhau.

Ví dụ: bật cảnh báo khi PM2.5 vượt `35.4 ug/m3`, nhưng chỉ tắt cảnh báo khi PM2.5 giảm xuống thấp hơn một mức an toàn. Nhờ vậy cảnh báo ổn định hơn và ít nhấp nháy hơn.

### 4.9 Early warning 1h/3h/6h

Project không chỉ cảnh báo trạng thái hiện tại. Nó còn tạo cảnh báo sớm cho 1 giờ, 3 giờ và 6 giờ. Ý tưởng là nhìn xu hướng ngắn hạn của fused PM2.5; nếu có khả năng vượt ngưỡng trong các mốc đó thì bật cờ cảnh báo sớm.

Đây vẫn là cảnh báo proof-of-concept, chưa phải dự báo vận hành đã được kiểm chứng trên dữ liệu dài.

### 4.10 Self-learning hiện tại tới đâu?

Hiện tại project chưa có online learning hoặc deep learning thật sự. Không có mô hình học sâu mới nào được thêm vào ở giai đoạn này.

Tuy vậy, project đã có nền cho khả năng tự thích nghi nhẹ thông qua residual EMA/Dual-EMA. Nghĩa là hệ thống có thể cập nhật sai lệch giữa PurpleAir và CAMS theo thời gian. Khi residual thay đổi, bộ lọc EMA cập nhật dần phần hiệu chỉnh.

Muốn self-learning mạnh hơn thì cần thu thập PurpleAir dài hơn, ổn định hơn, và xử lý rõ vấn đề A/B channel trước.

## 5. Các file output quan trọng

### Báo cáo nên đọc

- `reports/STAGE_1_REVIEW.md`: đọc để hiểu các vấn đề dữ liệu ban đầu, đặc biệt là QC PurpleAir và cảnh báo không nên hiểu sai metric.
- `reports/STAGE_2_EXECUTIVE_SUMMARY.md`: đọc để nắm nhanh Stage 2 đã làm gì, kết quả chính là gì và giới hạn là gì.
- `reports/STAGE_2_FUSION_ALERT_DESIGN.md`: đọc để hiểu thiết kế thuật toán fusion/cảnh báo: residual, EMA, Dual-EMA, confidence gating, hysteresis.
- `reports/STAGE_2_EVALUATION.md`: đọc để xem đánh giá Stage 2, nhưng cần nhớ các metric chỉ mang tính diagnostic vì dữ liệu overlap ngắn.
- `reports/STAGE_3_STATUS.md`: đọc để biết trạng thái Stage 3, file nào đã tạo, latest snapshot hiện tại là gì.
- `reports/STAGE_3_RUNBOOK.md`: đọc để biết cách chạy fetch, incremental update và tạo latest snapshot.

### Dữ liệu và kết quả để demo

- `data/processed/pm25_fused_hourly_dataset.csv`: dataset hourly đã ghép CAMS và PurpleAir, có feature, residual và target dự báo. Dùng để chứng minh pipeline xử lý dữ liệu đã chạy được.
- `outputs/predictions/fusion_alert_timeline.csv`: timeline chính của Stage 2, chứa CAMS, PurpleAir, confidence, residual, EMA, fused PM2.5, cảnh báo hiện tại và cảnh báo sớm. Đây là file quan trọng nhất để demo thuật toán.
- `outputs/metrics/fusion_alert_metrics.csv`: metric Stage 2 cho 1h/3h/6h. Dùng để xem kết quả diagnostic, không dùng để claim mô hình mạnh.
- `outputs/latest/latest_alert_summary.json`: bản tóm tắt cảnh báo mới nhất, rất phù hợp để demo nhanh trạng thái hệ thống.
- `outputs/latest/latest_fusion_alert_snapshot.csv`: một dòng snapshot mới nhất với nhiều cột hơn JSON, dùng khi cần xem chi tiết dữ liệu tại thời điểm mới nhất.

Tất cả các file bắt buộc ở trên hiện có trong project.

## 6. Các hình ảnh output và cách đọc

Các hình hiện có trong `outputs/figures/`:

- `outputs/figures/01_cams_pm25_full_timeseries.png`: vẽ chuỗi CAMS PM2.5 toàn bộ giai đoạn. Nên nhìn xu hướng dài hạn. Có thể demo rằng CAMS là tín hiệu nền có chuỗi dài.
- `outputs/figures/02_purpleair_raw_pm25_timeseries.png`: vẽ PM2.5 PurpleAir thô. Nên nhìn độ dao động nhanh. Có thể demo rằng cảm biến cục bộ phản ứng nhanh nhưng nhiễu hơn.
- `outputs/figures/03_purpleair_ab_channel_comparison.png`: so sánh kênh A/B của PurpleAir. Nên nhìn độ lệch giữa hai kênh. Có thể demo vì sao cần QC.
- `outputs/figures/04_purpleair_hourly_pm25.png`: vẽ PurpleAir sau khi gom về hourly. Nên nhìn dữ liệu đã được đưa về cùng tần suất với CAMS.
- `outputs/figures/05_cams_vs_purpleair_overlap.png`: so sánh CAMS và PurpleAir trong vùng overlap. Nên nhìn khoảng thời gian trùng rất ngắn. Có thể demo giới hạn dữ liệu hiện tại.
- `outputs/figures/06_residual_over_time.png`: vẽ residual theo thời gian. Nên nhìn PurpleAir cao/thấp hơn CAMS ra sao.
- `outputs/figures/07_residual_ema_over_time.png`: vẽ residual sau EMA. Nên nhìn tín hiệu được làm mượt hơn. Có thể demo ý tưởng lọc nhiễu.
- `outputs/figures/08_fused_vs_cams_vs_purpleair.png`: so sánh CAMS, PurpleAir và fused PM2.5. Nên nhìn fused nằm như tín hiệu đã hiệu chỉnh.
- `outputs/figures/09_alert_level_timeline.png`: vẽ mức cảnh báo theo thời gian. Có thể demo phần phân mức cảnh báo.
- `outputs/figures/10_prediction_vs_actual_1h.png`: so sánh dự báo 1h và giá trị thực trong dữ liệu test. Nên đọc như hình diagnostic.
- `outputs/figures/10_prediction_vs_actual_3h.png`: so sánh dự báo 3h và giá trị thực. Không nên dùng để claim mạnh vì dữ liệu ít.
- `outputs/figures/10_prediction_vs_actual_6h.png`: so sánh dự báo 6h và giá trị thực. Nên nhấn mạnh đây là baseline/diagnostic.
- `outputs/figures/11_purpleair_ab_difference.png`: vẽ độ lệch A/B. Có thể demo rõ vấn đề cảm biến.
- `outputs/figures/12_purpleair_bad_fraction_hourly.png`: vẽ tỷ lệ mẫu xấu theo giờ. Nên nhìn giờ nào dữ liệu kém tin cậy.
- `outputs/figures/13_loose_vs_strict_purpleair_hourly.png`: so sánh strict và loose PurpleAir hourly. Có thể demo chính sách dùng strict trước, loose fallback khi cần.

Các hình Stage 2 quan trọng:

- `outputs/figures/14_stage2_fusion_timeline.png`: vẽ timeline fusion Stage 2. Nên nhìn CAMS, PurpleAir và fused PM2.5 thay đổi theo thời gian. Ý nghĩa: đây là hình chính để nói “hệ thống kết hợp tín hiệu nền và cảm biến cục bộ”. Khi demo với giảng viên, có thể nói: “Đường fused là kết quả sau khi CAMS được hiệu chỉnh bằng PurpleAir có kiểm soát.”
- `outputs/figures/15_stage2_residual_filters.png`: vẽ residual và các bộ lọc residual. Nên nhìn Single EMA/Dual-EMA làm mượt sai lệch như thế nào. Ý nghĩa: minh họa phần xử lý tín hiệu chính, thân thiện với phần cứng. Khi demo, có thể nói: “Thay vì tin ngay vào cảm biến nhiễu, hệ thống lọc phần sai lệch giữa cảm biến và CAMS.”
- `outputs/figures/16_stage2_sensor_confidence.png`: vẽ độ tin cậy cảm biến. Nên nhìn confidence thấp khi dữ liệu xấu hoặc A/B lệch. Ý nghĩa: giải thích vì sao PurpleAir không phải lúc nào cũng được tin như nhau. Khi demo, có thể nói: “Kênh A/B lệch thì hệ thống tự giảm mức ảnh hưởng của PurpleAir.”
- `outputs/figures/17_stage2_alert_hysteresis.png`: vẽ cảnh báo với hysteresis. Nên nhìn trạng thái cảnh báo bật/tắt ổn định hơn quanh ngưỡng. Ý nghĩa: tránh cảnh báo nhấp nháy. Khi demo, có thể nói: “Hệ thống dùng ngưỡng bật và ngưỡng tắt khác nhau để cảnh báo không dao động liên tục.”
- `outputs/figures/18_stage2_early_warning_forecasts.png`: vẽ cảnh báo sớm 1h/3h/6h. Nên nhìn các dự báo ngắn hạn và cờ vượt ngưỡng. Ý nghĩa: project không chỉ đọc hiện tại mà còn có cảnh báo sớm proof-of-concept. Khi demo, có thể nói: “Đây là phần dự báo xu hướng ngắn hạn, nhưng hiện chưa claim mạnh vì dữ liệu overlap còn ngắn.”

Không có hình bắt buộc nào ở trên bị thiếu tại thời điểm kiểm tra tài liệu này.

## 7. Thành tựu hiện tại

Project hiện đã có một pipeline khá đầy đủ cho proof-of-concept: đọc dữ liệu thô, kiểm tra dữ liệu, QC cảm biến PurpleAir, đồng bộ CAMS và PurpleAir theo giờ, tạo residual, áp dụng Single EMA và Dual-EMA, dùng confidence gating để giảm ảnh hưởng của dữ liệu cảm biến kém tin cậy, tạo fused PM2.5, phân mức cảnh báo bằng hysteresis, cảnh báo sớm 1h/3h/6h, cập nhật dữ liệu incremental và tạo latest alert snapshot.

Điểm mạnh của project là hướng đi giải thích được và thân thiện với phần cứng. Các phép tính chính như residual, EMA, gating và FSM cảnh báo đều có thể mô tả rõ ràng, không phải “hộp đen”.

Về test: tài liệu handoff trước đó ghi nhận `16 passed` trong môi trường đã có đủ thư viện. Trong lần kiểm tra hiện tại, chưa chạy lại được test vì môi trường Python hiện thiếu `pytest` và `pandas`. Cụ thể, `python -m pytest tests -q` báo không có module `pytest`, còn chạy trực tiếp các file test báo thiếu `pandas`.

## 8. Giới hạn hiện tại

Các giới hạn cần nói thẳng:

- PurpleAir overlap với CAMS còn ngắn, chỉ khoảng 49 giờ.
- Strict valid PurpleAir hourly rows chỉ có 22 giờ.
- A/B channel của PurpleAir lệch cao, khoảng 74.49% dòng có disagreement.
- Metrics classification có thể gây hiểu nhầm vì test set thiếu hoặc không có nhiều mẫu vượt ngưỡng.
- Chưa nên claim mô hình dự đoán tốt.
- Chưa nên claim self-learning mạnh.
- Chưa có dữ liệu PurpleAir dài hạn để đánh giá ổn định nhiều ngày/tuần.
- Fetcher đã được test ở mức dry-run/request construction, nhưng live API vẫn cần API key thật và kiểm tra vận hành thật.

Vì vậy, cách trình bày đúng là: project đã chứng minh được kiến trúc, pipeline và thuật toán cảnh báo có thể chạy; nhưng chưa chứng minh được hiệu năng dự báo vận hành.

## 9. Có cần Colab/ML ngay không?

Hiện tại chưa cần Colab để train mô hình nặng. Codex/local project đã đủ để xử lý pipeline, tạo report, tạo demo, chạy thuật toán nhẹ và kiểm tra snapshot.

Colab có thể hữu ích sau này nếu muốn làm notebook demo đẹp hơn, chia sẻ với giảng viên, hoặc train model khi đã có nhiều dữ liệu PurpleAir hơn. Nhưng chưa nên train deep learning lúc này vì dữ liệu PurpleAir quá ngắn. Nếu train mô hình nặng bây giờ, kết quả dễ bị overfit, tức là học thuộc đoạn dữ liệu ngắn thay vì học quy luật thật.

## 10. Hướng đi tiếp theo

### Hướng A: Demo/report

- Tạo `DEMO_GUIDE.md`.
- Tạo notebook demo.
- Gom hình, bảng, snapshot để trình bày với thầy.
- Chuẩn bị câu chuyện thuyết trình: dữ liệu, QC, fusion, cảnh báo, giới hạn.

### Hướng B: Thu thập dữ liệu thật

- Chạy fetch CAMS/PurpleAir định kỳ.
- Tích lũy dữ liệu nhiều ngày hoặc nhiều tuần.
- Khóa đúng `sensor_index` của PurpleAir gần khu vực mục tiêu.
- Sau đó mới đánh giá ML/self-learning nghiêm túc hơn.

### Hướng C: Hướng vi mạch/hardware

- Chuyển Dual-EMA sang fixed-point, tức biểu diễn số phù hợp với phần cứng.
- Thiết kế alert FSM, tức máy trạng thái cho cảnh báo bật/tắt.
- Viết mô tả block diagram.
- Có thể tạo Verilog skeleton sau khi đặc tả thuật toán đã ổn.

Khuyến nghị: với cuộc thi thiết kế vi mạch, nên ưu tiên demo/report và hardware-oriented design trước. ML nâng cao nên để sau khi có dữ liệu PurpleAir dài hơn và đáng tin hơn.

## 11. Script demo 5 phút bằng tiếng Việt

“Em xin trình bày project dự báo và cảnh báo bụi mịn PM2.5 quanh khu vực ký túc xá ĐHQG TP.HCM.

Bài toán của tụi em là: làm sao kết hợp được một nguồn dữ liệu nền có sẵn lâu dài với một cảm biến cục bộ để tạo ra tín hiệu PM2.5 gần thực tế hơn, rồi từ đó đưa ra cảnh báo hiện tại và cảnh báo sớm.

Project dùng hai nguồn dữ liệu. Nguồn thứ nhất là CAMS/Open-Meteo. Đây là dữ liệu PM2.5 theo giờ, có chuỗi dài từ năm 2025 đến tháng 5 năm 2026 trong bộ dữ liệu hiện tại. CAMS phù hợp làm tín hiệu nền, nhưng nó là dữ liệu mô hình/lưới, không phải đo trực tiếp tại đúng cảm biến.

Nguồn thứ hai là PurpleAir. Đây là cảm biến cục bộ, cập nhật nhanh hơn và phản ánh môi trường gần điểm đo hơn. Tuy nhiên dữ liệu PurpleAir hiện tại chỉ có khoảng hai ngày, và hai kênh A/B của cảm biến đang lệch khá mạnh. Vì vậy bước đầu tiên là phải QC, tức kiểm tra chất lượng cảm biến. Project kiểm tra giá trị bất thường, số mẫu hợp lệ, tỷ lệ mẫu xấu và độ lệch A/B. Nếu cảm biến không đáng tin thì hệ thống giảm độ ảnh hưởng của PurpleAir.

Sau khi đồng bộ thời gian, CAMS và PurpleAir đều được đưa về cùng mốc hourly. Thuật toán chính dùng khái niệm residual. Residual bằng PurpleAir trừ CAMS. Nếu residual dương thì cảm biến cục bộ đang cao hơn tín hiệu nền; nếu residual âm thì cảm biến thấp hơn tín hiệu nền. Thay vì lọc PM2.5 thô, project lọc residual để học phần sai lệch cục bộ giữa PurpleAir và CAMS.

Để lọc residual, project dùng EMA và Dual-EMA. EMA là trung bình mũ, giúp làm mượt tín hiệu. Dual-EMA dùng một EMA nhanh và một EMA chậm. EMA nhanh bắt biến động ngắn hạn, EMA chậm giữ xu hướng nền. Hiệu giữa hai EMA cho biết residual đang có xu hướng tăng hay giảm. Cách này nhẹ, dễ giải thích và phù hợp nếu sau này chuyển sang thiết kế phần cứng.

Project còn có confidence gating. Nghĩa là hệ thống không tin PurpleAir như nhau trong mọi thời điểm. Nếu dữ liệu tốt thì PurpleAir ảnh hưởng nhiều hơn vào fused PM2.5. Nếu A/B lệch, ít mẫu hoặc nhiều mẫu xấu thì hệ thống giảm trọng số của PurpleAir và dựa nhiều hơn vào CAMS.

Tín hiệu cuối cùng gọi là fused PM2.5, bằng CAMS cộng với phần hiệu chỉnh từ PurpleAir. Từ fused PM2.5, hệ thống tạo cảnh báo bằng hysteresis. Hysteresis dùng ngưỡng bật và ngưỡng tắt khác nhau, giúp cảnh báo không bị bật tắt liên tục khi PM2.5 dao động quanh ngưỡng.

Ngoài cảnh báo hiện tại, project còn có cảnh báo sớm 1 giờ, 3 giờ và 6 giờ. Đây là dự báo xu hướng ngắn hạn để xem PM2.5 có khả năng vượt ngưỡng hay không.

File snapshot mới nhất nằm ở `outputs/latest/latest_alert_summary.json`. Theo snapshot hiện tại, thời điểm mới nhất là `2026-05-14 10:00:00+07:00`, CAMS khoảng `26.0`, PurpleAir hourly khoảng `12.18`, fused PM2.5 Stage 2 khoảng `21.59`, mức cảnh báo là moderate, và chưa bật cảnh báo vượt ngưỡng 1h/3h/6h.

Giới hạn lớn nhất hiện tại là dữ liệu PurpleAir trùng với CAMS chỉ khoảng 49 giờ, quá ngắn để claim mô hình dự báo mạnh. Ngoài ra A/B channel của PurpleAir đang lệch cao, nên project hiện nên được xem là proof-of-concept: đã chứng minh pipeline và thuật toán có thể chạy, nhưng chưa chứng minh hiệu năng vận hành dài hạn.

Hướng tiếp theo là một trong ba hướng. Một là làm demo/report để trình bày rõ với giảng viên. Hai là thu thập dữ liệu thật nhiều ngày hoặc nhiều tuần bằng API. Ba là chuyển thuật toán Dual-EMA và cảnh báo hysteresis sang đặc tả phần cứng như fixed-point và FSM. Với cuộc thi thiết kế vi mạch, em đề xuất ưu tiên demo/report và thiết kế hướng phần cứng trước, còn ML nâng cao để sau khi có dữ liệu PurpleAir dài hơn.”

## 12. Danh sách “mở file nào để xem thành quả”

```text
[ ] Mở reports/PROJECT_EXPLANATION_VI.md
[ ] Mở reports/STAGE_2_EXECUTIVE_SUMMARY.md
[ ] Mở outputs/figures/14_stage2_fusion_timeline.png
[ ] Mở outputs/figures/15_stage2_residual_filters.png
[ ] Mở outputs/figures/16_stage2_sensor_confidence.png
[ ] Mở outputs/figures/17_stage2_alert_hysteresis.png
[ ] Mở outputs/figures/18_stage2_early_warning_forecasts.png
[ ] Mở outputs/latest/latest_alert_summary.json
[ ] Mở outputs/predictions/fusion_alert_timeline.csv
```

## 13. Ghi chú kiểm tra cuối cùng

Tài liệu này chỉ tạo file giải thích tiếng Việt và không chạy API thật. Không cần API key cho bước này. Không thêm ML model mới. Không sửa file CSV gốc. Không thay đổi thuật toán lõi.

Các đường dẫn bắt buộc được nhắc trong tài liệu đã được kiểm tra ở mức tồn tại trong project, gồm các báo cáo Stage 1/2/3, dataset processed, timeline Stage 2, metric Stage 2, latest snapshot và các hình Stage 2.
