# Lab 03 – Làm sạch Silver

## 1. Bối cảnh nghiệp vụ
Bronze chứa delivery event; Silver cần current state duy nhất cho mỗi business key.

## 2. Mục tiêu học tập
Khử trùng có thứ tự, chuẩn hóa kiểu/category và phát hiện conflict thay vì chọn ngẫu nhiên.

## 3. Dữ liệu đầu vào
`bronze.accounts`, `bronze.transactions`, `bronze.loans` từ Batch 01.

## 4. Kết quả mong đợi
`lab03_silver` có business key duy nhất; SUCCESS/FAILED và hot accounts đều được giữ.

## 5. Logic xử lý
Window theo key, sort `updated_at DESC`; cùng timestamp và payload giống nhau được gộp, payload khác làm fail.

## 6. Code Spark liên quan
`build_silver_facts.py` và `customer360/transformations.py`.

## 7. Chạy bằng Airflow
Sau Full Load Bronze chính, trigger `lab_03_silver_transformation`.

## 8. SQL kiểm tra
Đổi schema trong `03_silver_validation.sql` thành `lab03_silver`.

## 9. Quan sát Spark UI
Tìm Exchange, Sort, Window và Project; giải thích vì sao Window cần shuffle theo key.

## 10. Câu hỏi thảo luận
Vì sao `dropDuplicates([transaction_id])` không an toàn khi status được cập nhật?

## 11. Lỗi thường gặp
Dùng transaction_time thay updated_at, đổi Decimal sang Double hoặc lọc FAILED.

## 12. Bài tập học viên
Sửa hàm dedup không an toàn trong `exercises/deduplication_todo.py`; thêm test conflict.

