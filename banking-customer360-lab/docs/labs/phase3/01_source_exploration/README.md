# Lab 01 – Khám phá dữ liệu nguồn

## 1. Bối cảnh nghiệp vụ
Core Banking, CRM và Loan System dùng khóa và chất lượng dữ liệu khác nhau; giao dịch còn có phân bố lệch hợp lệ.

## 2. Mục tiêu học tập
Đọc schema/count/NULL, quan hệ cardinality và đối chiếu manifest mà không thu dữ liệu lớn về driver.

## 3. Dữ liệu đầu vào
Năm dataset tại `s3a://raw/small/batch_01` và raw transaction delivery.

## 4. Kết quả mong đợi
Count khớp manifest; thấy CRM phone/income anomaly, hot accounts và 400 event giao dịch lặp ở bộ small.

## 5. Logic xử lý
Mỗi bảng được cache trong một application; dùng aggregate Spark, chỉ lấy ba sample và top 20 nhỏ.

## 6. Code Spark liên quan
`infra/spark/jobs/phase3/profile_sources.py`; chú ý `countDistinct`, aggregate NULL và group theo tháng.

## 7. Chạy bằng Airflow
Trigger `lab_01_source_exploration` với profile `small`, batch `batch_01`, source mode `file`.

## 8. SQL kiểm tra
Chạy `infra/sql/phase3/01_source_profiling.sql` sau khi Bronze đã có dữ liệu.

## 9. Quan sát Spark UI
Tìm FileScan, HashAggregate, Exchange và AdaptiveSparkPlan; so số job với các action trong code.

## 10. Câu hỏi thảo luận
Vì sao transaction skew không phải lỗi? Vì sao CRM không thể join bằng profile_id với customer_id?

## 11. Lỗi thường gặp
Dùng `toPandas()`, hiển thị quá nhiều dòng hoặc coi event delivery lặp là dữ liệu nguồn hỏng.

## 12. Bài tập học viên
Thêm một chỉ tiêu NULL; đổi số JDBC partition trong config và giải thích số connection tối đa.

