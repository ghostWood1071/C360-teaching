# Lab 06 – Data Quality và Reconciliation

## 1. Bối cảnh nghiệp vụ
Pipeline chỉ READY khi dữ liệu, quan hệ và số tiền đã được kiểm tra thật.

## 2. Mục tiêu học tập
Phân biệt expected anomaly với corruption và lưu evidence kiểm tra bền vững.

## 3. Dữ liệu đầu vào
Bronze, Silver và các manifest Phase 1 trên MinIO.

## 4. Kết quả mong đợi
Các check PASSED được ghi vào `quality.validation_results`; critical failure làm task fail.

## 5. Logic xử lý
Kiểm tra schema/count/metadata, uniqueness/FK/category/financial, rồi đối soát latest Bronze với Silver bằng Decimal.

## 6. Code Spark liên quan
`validate_bronze.py`, `validate_silver.py`, `reconcile_data.py`, `customer360/quality.py`.

## 7. Chạy bằng Airflow
Để `enable_quality_checks=true` trong pipeline; không đánh dấu READY trước reconciliation.

## 8. SQL kiểm tra
Chạy `02_bronze_validation.sql` và `03_silver_validation.sql` bằng identity có quyền.

## 9. Quan sát Spark UI
Tìm HashAggregate cho count/sum, BroadcastHashJoin hoặc SortMergeJoin cho FK.

## 10. Câu hỏi thảo luận
Vì sao không so tổng tiền Silver trực tiếp với raw delivery có duplicate?

## 11. Lỗi thường gặp
Báo PASSED khi check chưa chạy, so tiền bằng float hoặc xóa hot accounts vì tưởng là anomaly.

## 12. Bài tập học viên
Thêm check descriptive columns; viết query tìm FK mồ côi; kiểm tra lịch sử 12 tháng còn đủ.

