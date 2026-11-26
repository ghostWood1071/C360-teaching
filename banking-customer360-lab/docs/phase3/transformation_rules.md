# Quy tắc chuyển đổi Silver

- Chọn bản mới nhất theo business key và `updated_at` bằng Window + `row_number`.
- Event trùng có cùng payload được thu gọn; payload khác nhau ở cùng key/timestamp làm task thất bại.
- `dropDuplicates([business_key])` không được dùng vì có thể giữ ngẫu nhiên bản cũ.
- Chuỗi được trim; category chuẩn hóa chữ hoa; email chữ thường.
- Tiền giữ `DECIMAL(18,2)`, không đổi sang FLOAT/DOUBLE; NULL income được giữ nguyên.
- Phone Việt Nam hợp lệ về `0xxxxxxxxx`; phone giả lập Phase 1 về `+84-SYN-xxxxxxxxxx`. Giá trị không nhận diện được được giữ để kiểm tra, không tự bịa số.
- customer_master dùng LEFT JOIN từ Core Banking sang CRM qua `identity_number`; Core Banking là nguồn có thẩm quyền.
- transactions giữ SUCCESS/FAILED, CREDIT/DEBIT và thêm `transaction_month` theo UTC.
- Không loại hot account, cohort join explosion, overdue loans hay cột mô tả.

Session Phase 3 đặt timezone UTC vì timestamp nguồn được định nghĩa UTC. Cấu hình mặc định Phase 2 có thể hiển thị Asia/Ho_Chi_Minh, nhưng job Phase 3 chủ động override để việc tạo `transaction_month` không đổi ngày tại biên tháng.
