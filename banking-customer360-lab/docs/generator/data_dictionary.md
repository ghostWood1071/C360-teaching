# Từ điển dữ liệu nguồn và đích

Mọi giá trị tiền là VND. BIGINT dùng số nguyên 64 bit; TIMESTAMP có độ chính xác microsecond, UTC. PK không NULL. Các cột STRING được mã hóa UTF-8.

## Nguồn

### core_banking.customers

| Cột | Kiểu | NULL | Ý nghĩa / ràng buộc |
|---|---|---|---|
| customer_id | BIGINT | Không | Khóa khách hàng dương; FK tại tài khoản và vay. |
| full_name | STRING | Không | Tên cá nhân Việt Nam ghép giả lập hoặc công ty giả lập. |
| identity_number | STRING | Không | Mã FICTIONAL-ABC- duy nhất, khóa ánh xạ khách và CRM. |
| date_of_birth | DATE | Có | Ngày sinh; NULL cho pháp nhân. |
| gender | STRING | Có | M hoặc F; NULL cho pháp nhân. |
| customer_type | STRING | Không | INDIVIDUAL hoặc CORPORATE. |
| created_at | TIMESTAMP UTC | Không | Thời điểm tạo; không sau updated_at. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm sửa nguồn; UTC; batch đầu trước reference_time, batch sau muộn hơn. |

### core_banking.accounts

| Cột | Kiểu | NULL | Ý nghĩa / ràng buộc |
|---|---|---|---|
| account_id | BIGINT | Không | Khóa tài khoản dương; FK của giao dịch. |
| customer_id | BIGINT | Không | Khóa khách hàng dương; FK tại tài khoản và vay. |
| account_type | STRING | Không | SAVING hoặc CURRENT. |
| balance | DECIMAL(18,2) | Không | Số dư hiện tại VND không âm; CLOSED bằng 0. |
| status | STRING | Không | Tài khoản/vay: ACTIVE hoặc CLOSED; giao dịch: SUCCESS hoặc FAILED. |
| created_at | TIMESTAMP UTC | Không | Thời điểm tạo; không sau updated_at. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm sửa nguồn; UTC; batch đầu trước reference_time, batch sau muộn hơn. |

### core_banking.transactions

| Cột | Kiểu | NULL | Ý nghĩa / ràng buộc |
|---|---|---|---|
| transaction_id | BIGINT | Không | Khóa giao dịch chuẩn duy nhất; có thể lặp trong raw_delivery. |
| account_id | BIGINT | Không | Khóa tài khoản dương; FK của giao dịch. |
| transaction_type | STRING | Không | CREDIT hoặc DEBIT. |
| amount | DECIMAL(18,2) | Không | Số tiền VND dương; không dùng FLOAT. |
| transaction_time | TIMESTAMP UTC | Không | Thời điểm sự kiện UTC, 12 tháng lịch liên tiếp; có thể cũ trong batch muộn. |
| channel | STRING | Không | ATM, MOBILE, INTERNET hoặc BRANCH. |
| merchant_category | STRING | Không | Nhóm thương nhân giả lập bắt đầu SYN_. |
| merchant_name | STRING | Không | Tên thương nhân giả lập, chiều rộng ký tự cấu hình. |
| description | STRING | Không | Mô tả giả lập có entropy theo khóa, chiều rộng cấu hình. |
| reference_number | STRING | Không | Mã tham chiếu ABC-SYN-TX- duy nhất. |
| status | STRING | Không | Tài khoản/vay: ACTIVE hoặc CLOSED; giao dịch: SUCCESS hoặc FAILED. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm sửa nguồn; UTC; batch đầu trước reference_time, batch sau muộn hơn. |

### crm.customer_profiles

| Cột | Kiểu | NULL | Ý nghĩa / ràng buộc |
|---|---|---|---|
| profile_id | BIGINT | Không | Khóa CRM riêng, bắt đầu 1000000001; không chứa customer_id. |
| identity_number | STRING | Không | Mã FICTIONAL-ABC- duy nhất, khóa ánh xạ khách và CRM. |
| phone | STRING | Có | Số giả lập chứa SYN, có bốn kiểu không chuẩn khi tiêm lỗi. |
| email | STRING | Có | Email giả lập thuộc example.com. |
| address | STRING | Có | Địa chỉ có nhãn giả lập. |
| occupation | STRING | Có | Nghề nghiệp giả lập thuộc từ điển SYNTHETIC_. |
| monthly_income | DECIMAL(18,2) | Có | Thu nhập VND không âm hoặc NULL; mặc định thiếu đúng 5%. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm sửa nguồn; UTC; batch đầu trước reference_time, batch sau muộn hơn. |

### loan_system.loans

| Cột | Kiểu | NULL | Ý nghĩa / ràng buộc |
|---|---|---|---|
| loan_id | BIGINT | Không | Khóa khoản vay dương. |
| customer_id | BIGINT | Không | Khóa khách hàng dương; FK tại tài khoản và vay. |
| loan_type | STRING | Không | HOME, CAR, PERSONAL hoặc BUSINESS. |
| loan_amount | DECIMAL(18,2) | Không | Số gốc VND dương. |
| outstanding | DECIMAL(18,2) | Không | Dư nợ VND: 0 <= outstanding <= loan_amount; CLOSED bằng 0. |
| overdue_days | INT | Không | Số ngày quá hạn không âm; CLOSED bằng 0; quá hạn phải ACTIVE và dư nợ dương. |
| loan_date | DATE | Không | Ngày giải ngân giả lập, không sau updated_at. |
| status | STRING | Không | Tài khoản/vay: ACTIVE hoặc CLOSED; giao dịch: SUCCESS hoặc FAILED. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm sửa nguồn; UTC; batch đầu trước reference_time, batch sau muộn hơn. |

## Bronze

Năm bảng giữ nguyên toàn bộ cột, kiểu và quy tắc nguồn nêu trên, thêm:

| Cột | Kiểu | NULL | Ý nghĩa |
|---|---|---|---|
| _source_system | STRING | Không | core_banking, crm hoặc loan_system. |
| _ingested_at | TIMESTAMP UTC | Không | Thời điểm nhận batch. |
| _batch_id | STRING | Không | Định danh batch nhận. |

## Silver

accounts và loans giữ toàn bộ cột nguồn. transactions giữ toàn bộ cột nguồn và thêm transaction_month STRING NOT NULL (YYYY-MM theo UTC). customer_master gồm toàn bộ customers và các cột phone, email, address, occupation, monthly_income của CRM (đều nullable khi không khớp), thêm profile_updated_at TIMESTAMP UTC nullable; updated_at lấy max hai nguồn. PK là customer_id; identity_number duy nhất. Không mang profile_id vào khóa Customer 360.

## Gold customer_360

| Cột | Kiểu | NULL | Ý nghĩa / quy tắc |
|---|---|---|---|
| customer_id | BIGINT | Không | Khóa duy nhất; giữ mọi khách. |
| full_name | STRING | Không | Tên nguồn. |
| age | INT | Có | Số năm tròn tại snapshot_date, NULL nếu ngày sinh NULL. |
| gender | STRING | Có | Giữ NULL pháp nhân. |
| customer_type | STRING | Không | Loại khách nguồn. |
| phone | STRING | Có | Chuẩn hóa +84-SYN-...; NULL nếu thiếu hồ sơ. |
| email | STRING | Có | Email sau chuẩn hóa chữ thường. |
| address | STRING | Có | Cắt khoảng trắng thừa. |
| occupation | STRING | Có | Nghề nghiệp nguồn. |
| monthly_income | DECIMAL(18,2) | Có | Giữ NULL; không mặc định thành 0. |
| customer_since | DATE | Không | Ngày UTC tạo khách. |
| total_accounts | BIGINT | Không | Đếm tài khoản mọi trạng thái theo khách; mặc định 0. |
| total_balance | DECIMAL(18,2) | Không | Tổng số dư ACTIVE theo khách; mặc định 0. |
| total_loans | BIGINT | Không | Đếm khoản vay mọi trạng thái; mặc định 0. |
| total_loan_amount | DECIMAL(18,2) | Không | Tổng gốc mọi trạng thái; mặc định 0. |
| total_outstanding | DECIMAL(18,2) | Không | Tổng dư nợ ACTIVE; mặc định 0. |
| max_overdue_days | INT | Không | Max ACTIVE; mặc định 0. |
| total_transactions_30d | BIGINT | Không | Đếm SUCCESS trong [reference_time-30d, reference_time); mặc định 0. |
| total_credit_30d | DECIMAL(18,2) | Không | Tổng CREDIT SUCCESS trong 30 ngày; mặc định 0. |
| total_debit_30d | DECIMAL(18,2) | Không | Tổng DEBIT SUCCESS trong 30 ngày; mặc định 0. |
| avg_transaction_amount_30d | DECIMAL(18,2) | Có | Trung bình SUCCESS trong 30 ngày; làm tròn HALF_UP đến 2 số lẻ; NULL nếu đếm 0. |
| last_transaction_date | DATE | Có | Ngày UTC của SUCCESS cuối trước reference_time; NULL nếu chưa có. |
| days_since_last_transaction | INT | Có | Chênh lệch ngày lịch UTC; NULL nếu chưa có. |
| customer_segment | STRING | Không | VIP >= 1 tỷ; PRIORITY >= 200 triệu; còn lại MASS. |
| inactivity_flag | BOOLEAN | Không | Không có SUCCESS trong [reference_time-90d,reference_time), kể cả chưa từng giao dịch. |
| overdue_flag | BOOLEAN | Không | Có ít nhất một ACTIVE với overdue_days > 0. |
| credit_card_candidate | BOOLEAN | Không | INDIVIDUAL và income >= 20 triệu và không overdue; NULL income cho FALSE. |
| snapshot_date | DATE | Không | Ngày UTC của mốc báo cáo; reference_time được xem là biên phải loại trừ. |
| updated_at | TIMESTAMP UTC | Không | Thời điểm tạo/cập nhật snapshot ở giai đoạn tương lai, không phải thời gian chạy generator. |
