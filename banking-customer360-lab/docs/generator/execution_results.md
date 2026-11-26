# Kết quả thực thi và nghiệm thu

Ngày kiểm tra: **26/11/2026** (Asia/Ho_Chi_Minh). Mốc nghiệp vụ cố định của dữ liệu: **2027-01-01T00:00:00Z**. Đây là số đo thật của lần chạy trên máy hiện tại, không phải ước tính hoặc benchmark Spark.

## Môi trường

- macOS-26.6.2-arm64-arm-64bit, Python 3.12.14.
- numpy 2.3.5, pyarrow 26.0.1, yaml 6.0.4, pytest 9.2.0, psutil 7.2.2.
- Môi trường ảo của phiên làm việc đặt tại `../.venv`; không chỉnh Python hệ thống.

## Kiểm thử tự động

Lệnh `python -m pytest -q`: **16 passed in 5.03s**. Bao gồm tái sinh với cùng seed nhưng batch khác; seed khác tạo fingerprint khác; chạy đầy đủ cả bảy lựa chọn scenario; thiếu hồ sơ CRM; giao dịch đến muộn; delivery lặp; rows_per_file; hot IDs/ratios tùy chỉnh; phát hiện sửa sai mô tả trong biến thể; từ chối quota vượt volume, cập nhật khóa được bảo vệ, và raw lặp từ batch rỗng.

## Số đo sinh và kiểm định

| Chỉ tiêu | Small | Standard |
|---|---:|---:|
| Thời gian sinh (giây) | 0.645 | 20.896 |
| RSS đỉnh sinh lấy mẫu (byte) | 220463104 | 1017004032 |
| RSS đỉnh tiến trình sinh, ru_maxrss (byte) | 223772672 | 1018314752 |
| Thời gian kiểm định cuối (giây) | 0.974 | 26.579 |
| RSS đỉnh kiểm định lấy mẫu (byte) | 269352960 | 1228587008 |
| Tổng dung lượng sau profiling (byte) | 49912629 | 2439385286 |
| Tổng số file | 72 | 211 |
| Số file Parquet | 63 | 202 |
| File giao dịch canonical | 8 | 24 |
| Số kiểm tra đạt | 193/193 | 193/193 |
| Số tháng giao dịch | 12 | 12 |

Bộ sinh standard đạt RSS đỉnh khoảng **971 MiB**, dưới mục tiêu 2 GB. RSS lấy mẫu bằng psutil mỗi 20 ms; ru_maxrss đo đỉnh toàn tiến trình. Sinh và kiểm định là hai tiến trình riêng. Dung lượng gồm full load, incremental, raw, cả ba biến thể và báo cáo; bản thân dữ liệu chuẩn nhỏ hơn tổng này. Thời lượng phụ thuộc cache, phần cứng và các tiến trình khác. Đồng hồ pha sinh bắt đầu sau đọc YAML và cấp phát/kiểm tra quan hệ, bao gồm sinh giá trị, ghi mọi biến thể, raw và metadata; ru_maxrss vẫn bao gồm cấp phát đầu tiến trình.

## Số dòng chuẩn thực tế

| Bảng | Small batch 1 | Standard batch 1 | Small sau batch 2 | Standard sau batch 2 |
|---|---:|---:|---:|---:|
| customers | 10000 | 500000 | 10020 | 501000 |
| accounts | 20000 | 1000000 | 20040 | 1002000 |
| transactions | 40000 | 2000000 | 41000 | 2050000 |
| customer_profiles | 10000 | 500000 | 10020 | 501000 |
| loans | 10000 | 500000 | 10020 | 501000 |

Counts sau batch 2 là kết quả kỳ vọng từ miền PK insert/update đã kiểm định, không phải bảng MERGE đã được vật chất hóa.

## Tình huống được xác nhận

- Standard: hot account 1/2/3 có chính xác **600000 / 200000 / 100000** giao dịch (30%/10%/5%). Phần còn lại **1100000**. Mỗi khóa nóng trải trên **24 file**, lần lượt **218 / 217 / 218 row group**. Ba chủ tài khoản là ba pháp nhân khác nhau.
- Small: tương ứng **12000 / 4000 / 2000**, trải đủ 8 file, mỗi khóa xuất hiện trong 40 row group.
- Cohort standard: 100 khách × 5 tài khoản ACTIVE × 100 SUCCESS mỗi tài khoản × 10 khoản vay ACTIVE. Cardinality ghép chi tiết sai **500000**; mỗi khách có đúng số tiền và chỉ tiêu trong expected_customer_metrics.parquet. Small giữ cùng cấu trúc cho 10 khách, cardinality 50000.
- Standard: đúng **5000 khoản quá hạn / 5000 khách riêng biệt**, tỷ lệ 1%; bản chọn distinct customer_id Arrow có **40000 byte**. Toàn bộ dòng khoản vay sau lọc chiếm **419862 byte** Arrow theo cách đọc batch hiện tại. Small là 100 khoản/100 khách.
- CRM standard: **25000** monthly_income NULL và **50000** phone không chuẩn. Small: 500 và 1000. identity_number vẫn duy nhất, mọi hồ sơ khớp khách nguồn.
- Raw full-load standard: **2020000** dòng = 2000000 chuẩn + 20000 giao lại. Raw batch 2: **51510** dòng = 51000 ảnh dòng chuẩn + 510 giao lại. Small: 40400 và 1030 dòng. Mọi bản giao lại giữ nguyên giá trị.
- Hai bản scan giữ cùng ID và toàn bộ giá trị với canonical; cả 12 tháng tồn tại. Baseline uniform là tập riêng, không được coi là tương đương tổng hợp khách.
- Batch 2 standard: thêm 1000 khách, 1000 CRM, 2000 tài khoản, 50000 giao dịch, 1000 vay; sửa 10000 tài khoản, 1000 trạng thái giao dịch, 5000 CRM, 5000 vay. Khóa dành được bảo vệ.

## Phân loại nghiệp vụ quan sát được (standard)

| Nhóm | Số khách |
|---|---:|
| VIP | 61078 |
| PRIORITY | 87100 |
| MASS | 351822 |
| Chưa có giao dịch thành công | 117285 |
| Inactive theo cửa sổ 90 ngày | 346483 |
| Không có khoản vay | 255008 |
| Có khoản quá hạn | 5000 |
| Thiếu thu nhập | 25000 |
| Ứng viên thẻ | 156547 |

Nhóm nghiệp vụ có thể giao nhau. Tỷ lệ 15% cấu hình là quần thể bị buộc giao dịch cũ; tỷ lệ Inactive quan sát lớn hơn do nhiều khách ít hoặc không giao dịch. Đây là phân bố minh họa, không phải số liệu ngân hàng thực.

## Quyết định triển khai

- Cấp phát miền hot/cohort/quá hạn trước, chỉ điền nền vào dung lượng còn lại; không tăng số dòng âm thầm.
- Dùng NumPy cho quan hệ và hàm băm theo seed/ID; sinh các cột rộng bằng batch. Tiền lưu decimal Arrow, timestamp UTC.
- Hot records được rải vật lý bằng hoán vị rank giao dịch; phần nền loại tuyệt đối hot keys và cohort.
- Dùng bộ ghi nhiều file có thống kê Parquet. Bản pushdown quét nguồn theo hai status, tránh sort toàn bộ dữ liệu rộng trong RAM.
- Kiểm định giá trị từng hàng với bộ sinh stateless, đồng thời đếm/tổng hợp nghiệp vụ độc lập. Fingerprint IPC chuẩn hóa theo PK phục vụ test tái sinh.
- Bật cả uniform và hai biến thể scan mặc định để lab có đủ dữ liệu; có thể tắt riêng để giảm ổ đĩa.

## Vị trí dữ liệu và báo cáo

### small

Dữ liệu: `data/small`.

- Manifest: `data/small/metadata/dataset_manifest.json`
- Kiểm định: `data/small/reports/validation_report.json`
- Profiling: `data/small/reports/profiling_report.md`

### standard

Dữ liệu: `data/standard`.

- Manifest: `data/standard/metadata/dataset_manifest.json`
- Kiểm định: `data/standard/reports/validation_report.json`
- Profiling: `data/standard/reports/profiling_report.md`

## Giới hạn và phần còn lại

- **Không còn phần triển khai bắt buộc của Phase 1 chưa hoàn thành.** Stress đã có cấu hình nhưng chưa chạy vì yêu cầu phải được chọn rõ ràng.
- Đã chạy trên macOS arm64/Python 3.12.14; chưa thực thi trên Windows/Linux hoặc mọi phiên bản tối thiểu trong requirements. DDL PostgreSQL/MySQL được cung cấp nhưng chưa chạy trên máy chủ DB vì pha này không yêu cầu DB.
- Test tái sinh độc lập dùng hồ sơ test nhỏ. Standard được kiểm định từng dòng với bộ sinh stateless; không ghi lại toàn bộ standard lần thứ hai.
- Baseline giữ quota cohort cố định, do đó tính đồng đều áp dụng cho phần tài khoản nền đủ điều kiện. Nó cố ý không có cùng tổng hợp khách với skew.
- Row group có thể nhỏ hơn cấu hình ở biên batch/file. Kích thước lọc Arrow là theo cột và batch đã ghi rõ, không phải kích thước broadcast thực của Spark.
- Bộ kiểm định dùng chung hàm sinh cho so sánh từng giá trị; các kiểm tra khóa, tài chính, quota, tổng hợp cohort và thử sửa sai giúp bổ sung kiểm tra độc lập. Fingerprint IPC chỉ nên so trong cùng môi trường thư viện; không cam kết byte Parquet giống giữa các phiên bản Arrow.
- Chưa và không triển khai Spark ETL, Delta MERGE, tối ưu hiệu năng, Airflow, Docker, notebook, dashboard hoặc API. Các phần đó thuộc pha sau. Không tuyên bố dữ liệu mặc định đảm bảo spill, AQE, broadcast tự động hay một mức cải thiện hiệu năng cụ thể.

## Cấu trúc nguồn sau khi tổ chức lại

```text
.gitignore
README.md
docs/generator/*.md
synthetic_data_generator/configs/{small,standard,stress}.yaml
synthetic_data_generator/requirements.txt
synthetic_data_generator/schemas/mysql/crm.sql
synthetic_data_generator/schemas/parquet/{schema_manifest.json,schemas.py}
synthetic_data_generator/schemas/postgres/{core_banking,loan_system}.sql
synthetic_data_generator/scripts/{generate_data,profile_data,validate_data}.py
synthetic_data_generator/src/**
synthetic_data_generator/tests/{conftest,test_integration}.py
```

Nội dung sinh ra nằm dưới `data/`. Dữ liệu, môi trường và cache đều được Git bỏ qua.
