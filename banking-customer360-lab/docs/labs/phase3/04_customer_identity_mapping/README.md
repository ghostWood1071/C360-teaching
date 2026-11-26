# Lab 04 – Ánh xạ định danh khách hàng

## 1. Bối cảnh nghiệp vụ
Core Banking và CRM không dùng cùng customer key; `identity_number` là khóa liên kết được kiểm soát.

## 2. Mục tiêu học tập
LEFT JOIN an toàn, giữ khách không khớp và phân biệt income 0 với NULL.

## 3. Dữ liệu đầu vào
Bronze customers và customer_profiles đã giải quyết bản mới nhất.

## 4. Kết quả mong đợi
Một dòng mỗi customer_id; số customer_master bằng số khách hợp lệ của Core Banking.

## 5. Logic xử lý
Kiểm tra CRM identity duy nhất, LEFT JOIN, trim chuỗi, email chữ thường, chuẩn hóa phone, giữ NULL income.

## 6. Code Spark liên quan
`build_customer_master.py` và hàm `build_customer_master`/`normalized_phone_expression`.

## 7. Chạy bằng Airflow
Task `build_customer_master` nằm trong DAG Lab 03 và pipeline chính.

## 8. SQL kiểm tra
Chạy `04_identity_mapping.sql`; so customers, unique identities và missing income.

## 9. Quan sát Spark UI
Xem SortMergeJoin hoặc BroadcastHashJoin do AQE chọn tự nhiên; không ép hint trong pipeline.

## 10. Câu hỏi thảo luận
INNER JOIN làm mất gì? Tại sao income NULL không được đổi thành 0?

## 11. Lỗi thường gặp
Join trước khi kiểm tra CRM uniqueness, tự bịa phone hoặc dùng profile_id làm customer_id.

## 12. Bài tập học viên
Hoàn thiện `phone_normalization_todo.py`; so count LEFT JOIN với INNER JOIN.

