# Lab 02 – Full Load vào Bronze

## 1. Bối cảnh nghiệp vụ
Nhiều nguồn phải được đưa vào một lớp lưu trữ chung nhưng vẫn giữ đúng nội dung delivery gốc.

## 2. Mục tiêu học tập
Hiểu metadata ingestion, Delta location rõ ràng và retry idempotent theo batch.

## 3. Dữ liệu đầu vào
Batch 01 của năm bảng; transactions đọc raw delivery chứ không ghép thêm canonical dataset.

## 4. Kết quả mong đợi
Năm bảng `lab02_bronze.*`; small transactions có 40.400 dòng và 40.000 business key.

## 5. Logic xử lý
Đọc schema tường minh, thêm `_source_system`, `_batch_id`, `_ingested_at`, ghi `replaceWhere` theo batch.

## 6. Code Spark liên quan
`ingest_bronze.py`, `customer360/readers.py`, `customer360/writers.py`.

## 7. Chạy bằng Airflow
Trigger `lab_02_bronze_ingestion`; DAG dùng namespace cô lập và không sửa bảng pipeline chính.

## 8. SQL kiểm tra
Đổi schema trong `02_bronze_validation.sql` thành `lab02_bronze` rồi kiểm tra count/duplicate.

## 9. Quan sát Spark UI
Tìm FileScan và Project thêm metadata; xem event log sau khi container đã bị xóa.

## 10. Câu hỏi thảo luận
Tại sao retry pipeline phải khác duplicate delivery? Tại sao không overwrite toàn bảng?

## 11. Lỗi thường gặp
Khử transaction duplicate ở Bronze, điền income NULL bằng 0 hoặc ingest cả canonical lẫn raw delivery.

## 12. Bài tập học viên
Thêm metadata `_source_file` trong exercise riêng; chạy lại batch và chứng minh count không đổi.

