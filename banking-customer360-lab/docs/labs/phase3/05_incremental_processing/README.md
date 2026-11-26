# Lab 05 – Incremental Processing

## 1. Bối cảnh nghiệp vụ
Batch 02 chứa insert, update, delivery duplicate và có thể có transaction đến muộn.

## 2. Mục tiêu học tập
Áp dụng Delta MERGE, bảo vệ bản mới và replay an toàn.

## 3. Dữ liệu đầu vào
Batch 02 đã được generator tạo; không sinh dữ liệu mới trong DAG.

## 4. Kết quả mong đợi
Small đạt 10.020 customers, 20.040 accounts, 41.000 transactions và 10.020 loans ở current state.

## 5. Logic xử lý
Bronze thay batch_02; facts MERGE theo key khi source.updated_at mới hơn; customer_master rebuild từ mọi batch.

## 6. Code Spark liên quan
`build_silver_facts.py`, `writers.merge_silver`, `build_customer_master.py`.

## 7. Chạy bằng Airflow
Sau Full Load, trigger pipeline với `load_type=incremental`, `batch_id=batch_02`.

## 8. SQL kiểm tra
Chạy `05_incremental_validation.sql` và xem `quality.pipeline_batches`.

## 9. Quan sát Spark UI
Tìm Window, Join và các scan Delta; so application Full với Incremental.

## 10. Câu hỏi thảo luận
Vì sao late transaction mới vẫn insert dù transaction_time cũ? Vì sao updated_at mới là điều kiện update?

## 11. Lỗi thường gặp
Chỉ join hai change batch cho customer_master hoặc dùng transaction_time làm watermark duy nhất.

## 12. Bài tập học viên
Replay Batch 02 và so count; đưa một update cũ vào pure test để chứng minh target không đổi.

