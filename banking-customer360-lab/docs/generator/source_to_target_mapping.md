# Ánh xạ nguồn sang đích

## Bronze: ánh xạ từng cột

| Bảng | Cột đích | Nguồn / công thức |
|---|---|---|
| bronze.customers | customer_id | core_banking.customers.customer_id; giữ giá trị và kiểu. |
| bronze.customers | full_name | core_banking.customers.full_name; giữ giá trị và kiểu. |
| bronze.customers | identity_number | core_banking.customers.identity_number; giữ giá trị và kiểu. |
| bronze.customers | date_of_birth | core_banking.customers.date_of_birth; giữ giá trị và kiểu. |
| bronze.customers | gender | core_banking.customers.gender; giữ giá trị và kiểu. |
| bronze.customers | customer_type | core_banking.customers.customer_type; giữ giá trị và kiểu. |
| bronze.customers | created_at | core_banking.customers.created_at; giữ giá trị và kiểu. |
| bronze.customers | updated_at | core_banking.customers.updated_at; giữ giá trị và kiểu. |
| bronze.customers | _source_system | core_banking |
| bronze.customers | _ingested_at | Thời điểm nhận UTC |
| bronze.customers | _batch_id | Định danh batch do bộ nạp cấp |
| bronze.accounts | account_id | core_banking.accounts.account_id; giữ giá trị và kiểu. |
| bronze.accounts | customer_id | core_banking.accounts.customer_id; giữ giá trị và kiểu. |
| bronze.accounts | account_type | core_banking.accounts.account_type; giữ giá trị và kiểu. |
| bronze.accounts | balance | core_banking.accounts.balance; giữ giá trị và kiểu. |
| bronze.accounts | status | core_banking.accounts.status; giữ giá trị và kiểu. |
| bronze.accounts | created_at | core_banking.accounts.created_at; giữ giá trị và kiểu. |
| bronze.accounts | updated_at | core_banking.accounts.updated_at; giữ giá trị và kiểu. |
| bronze.accounts | _source_system | core_banking |
| bronze.accounts | _ingested_at | Thời điểm nhận UTC |
| bronze.accounts | _batch_id | Định danh batch do bộ nạp cấp |
| bronze.transactions | transaction_id | core_banking.transactions.transaction_id; giữ giá trị và kiểu. |
| bronze.transactions | account_id | core_banking.transactions.account_id; giữ giá trị và kiểu. |
| bronze.transactions | transaction_type | core_banking.transactions.transaction_type; giữ giá trị và kiểu. |
| bronze.transactions | amount | core_banking.transactions.amount; giữ giá trị và kiểu. |
| bronze.transactions | transaction_time | core_banking.transactions.transaction_time; giữ giá trị và kiểu. |
| bronze.transactions | channel | core_banking.transactions.channel; giữ giá trị và kiểu. |
| bronze.transactions | merchant_category | core_banking.transactions.merchant_category; giữ giá trị và kiểu. |
| bronze.transactions | merchant_name | core_banking.transactions.merchant_name; giữ giá trị và kiểu. |
| bronze.transactions | description | core_banking.transactions.description; giữ giá trị và kiểu. |
| bronze.transactions | reference_number | core_banking.transactions.reference_number; giữ giá trị và kiểu. |
| bronze.transactions | status | core_banking.transactions.status; giữ giá trị và kiểu. |
| bronze.transactions | updated_at | core_banking.transactions.updated_at; giữ giá trị và kiểu. |
| bronze.transactions | _source_system | core_banking |
| bronze.transactions | _ingested_at | Thời điểm nhận UTC |
| bronze.transactions | _batch_id | Định danh batch do bộ nạp cấp |
| bronze.customer_profiles | profile_id | crm.customer_profiles.profile_id; giữ giá trị và kiểu. |
| bronze.customer_profiles | identity_number | crm.customer_profiles.identity_number; giữ giá trị và kiểu. |
| bronze.customer_profiles | phone | crm.customer_profiles.phone; giữ giá trị và kiểu. |
| bronze.customer_profiles | email | crm.customer_profiles.email; giữ giá trị và kiểu. |
| bronze.customer_profiles | address | crm.customer_profiles.address; giữ giá trị và kiểu. |
| bronze.customer_profiles | occupation | crm.customer_profiles.occupation; giữ giá trị và kiểu. |
| bronze.customer_profiles | monthly_income | crm.customer_profiles.monthly_income; giữ giá trị và kiểu. |
| bronze.customer_profiles | updated_at | crm.customer_profiles.updated_at; giữ giá trị và kiểu. |
| bronze.customer_profiles | _source_system | crm |
| bronze.customer_profiles | _ingested_at | Thời điểm nhận UTC |
| bronze.customer_profiles | _batch_id | Định danh batch do bộ nạp cấp |
| bronze.loans | loan_id | loan_system.loans.loan_id; giữ giá trị và kiểu. |
| bronze.loans | customer_id | loan_system.loans.customer_id; giữ giá trị và kiểu. |
| bronze.loans | loan_type | loan_system.loans.loan_type; giữ giá trị và kiểu. |
| bronze.loans | loan_amount | loan_system.loans.loan_amount; giữ giá trị và kiểu. |
| bronze.loans | outstanding | loan_system.loans.outstanding; giữ giá trị và kiểu. |
| bronze.loans | overdue_days | loan_system.loans.overdue_days; giữ giá trị và kiểu. |
| bronze.loans | loan_date | loan_system.loans.loan_date; giữ giá trị và kiểu. |
| bronze.loans | status | loan_system.loans.status; giữ giá trị và kiểu. |
| bronze.loans | updated_at | loan_system.loans.updated_at; giữ giá trị và kiểu. |
| bronze.loans | _source_system | loan_system |
| bronze.loans | _ingested_at | Thời điểm nhận UTC |
| bronze.loans | _batch_id | Định danh batch do bộ nạp cấp |

## Silver: ánh xạ từng cột

| Bảng đích | Cột | Nguồn / xử lý |
|---|---|---|
| silver.accounts | account_id | bronze.accounts.account_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | customer_id | bronze.accounts.customer_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | account_type | bronze.accounts.account_type; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | balance | bronze.accounts.balance; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | status | bronze.accounts.status; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | created_at | bronze.accounts.created_at; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.accounts | updated_at | bronze.accounts.updated_at; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | transaction_id | bronze.transactions.transaction_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | account_id | bronze.transactions.account_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | transaction_type | bronze.transactions.transaction_type; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | amount | bronze.transactions.amount; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | transaction_time | bronze.transactions.transaction_time; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | channel | bronze.transactions.channel; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | merchant_category | bronze.transactions.merchant_category; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | merchant_name | bronze.transactions.merchant_name; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | description | bronze.transactions.description; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | reference_number | bronze.transactions.reference_number; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | status | bronze.transactions.status; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.transactions | updated_at | bronze.transactions.updated_at; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | loan_id | bronze.loans.loan_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | customer_id | bronze.loans.customer_id; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | loan_type | bronze.loans.loan_type; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | loan_amount | bronze.loans.loan_amount; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | outstanding | bronze.loans.outstanding; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | overdue_days | bronze.loans.overdue_days; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | loan_date | bronze.loans.loan_date; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | status | bronze.loans.status; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.loans | updated_at | bronze.loans.updated_at; khử trùng theo PK, chọn updated_at mới nhất. |
| silver.customer_master | customer_id | bronze.customers.customer_id; giữ nguyên. |
| silver.customer_master | full_name | bronze.customers.full_name; giữ nguyên. |
| silver.customer_master | identity_number | bronze.customers.identity_number; giữ nguyên. |
| silver.customer_master | date_of_birth | bronze.customers.date_of_birth; giữ nguyên. |
| silver.customer_master | gender | bronze.customers.gender; giữ nguyên. |
| silver.customer_master | customer_type | bronze.customers.customer_type; giữ nguyên. |
| silver.customer_master | created_at | bronze.customers.created_at; giữ nguyên. |
| silver.customer_master | updated_at | bronze.customers.updated_at; max với CRM.updated_at. |
| silver.customer_master | phone | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.phone; chuẩn hóa định dạng; không khớp → NULL. |
| silver.customer_master | email | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.email; chuẩn hóa định dạng; không khớp → NULL. |
| silver.customer_master | address | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.address; chuẩn hóa định dạng; không khớp → NULL. |
| silver.customer_master | occupation | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.occupation; giữ nguyên; không khớp → NULL. |
| silver.customer_master | monthly_income | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.monthly_income; giữ nguyên; không khớp → NULL. |
| silver.customer_master | profile_updated_at | LEFT JOIN CRM theo identity_number; bronze.customer_profiles.updated_at; giữ nguyên; không khớp → NULL. |
| silver.transactions | transaction_month | YYYY-MM UTC từ transaction_time. |

Khóa CRM identity_number phải duy nhất trước khi nối. Batch có cập nhật dùng ảnh dòng mới nhất theo updated_at; tie cần quy tắc ổn định ở pha triển khai. _ingested_at, _source_system, _batch_id là lineage Bronze; có thể giữ bổ sung nhưng không nằm schema nghiệp vụ Silver tối thiểu.

## Gold: ánh xạ toàn bộ cột

| Cột customer_360 | Nguồn Silver / chỉ tiêu | Quy tắc |
|---|---|---|
| customer_id | customer_master.customer_id | Khóa duy nhất; giữ mọi khách. |
| full_name | customer_master.full_name | Tên nguồn. |
| age | customer_master.date_of_birth | Số năm tròn tại snapshot_date, NULL nếu ngày sinh NULL. |
| gender | customer_master.gender | Giữ NULL pháp nhân. |
| customer_type | customer_master.customer_type | Loại khách nguồn. |
| phone | customer_master.phone | Chuẩn hóa +84-SYN-...; NULL nếu thiếu hồ sơ. |
| email | customer_master.email | Email sau chuẩn hóa chữ thường. |
| address | customer_master.address | Cắt khoảng trắng thừa. |
| occupation | customer_master.occupation | Nghề nghiệp nguồn. |
| monthly_income | customer_master.monthly_income | Giữ NULL; không mặc định thành 0. |
| customer_since | customer_master.created_at | Ngày UTC tạo khách. |
| total_accounts | accounts.account_id | Đếm tài khoản mọi trạng thái theo khách; mặc định 0. |
| total_balance | accounts.balance, status | Tổng số dư ACTIVE theo khách; mặc định 0. |
| total_loans | loans.loan_id | Đếm khoản vay mọi trạng thái; mặc định 0. |
| total_loan_amount | loans.loan_amount | Tổng gốc mọi trạng thái; mặc định 0. |
| total_outstanding | loans.outstanding, status | Tổng dư nợ ACTIVE; mặc định 0. |
| max_overdue_days | loans.overdue_days, status | Max ACTIVE; mặc định 0. |
| total_transactions_30d | transactions.transaction_id, status, transaction_time; accounts.customer_id | Đếm SUCCESS trong [reference_time-30d, reference_time); mặc định 0. |
| total_credit_30d | transactions.amount, transaction_type, status, transaction_time; accounts.customer_id | Tổng CREDIT SUCCESS trong 30 ngày; mặc định 0. |
| total_debit_30d | transactions.amount, transaction_type, status, transaction_time; accounts.customer_id | Tổng DEBIT SUCCESS trong 30 ngày; mặc định 0. |
| avg_transaction_amount_30d | transactions.amount, status, transaction_time; accounts.customer_id | Trung bình SUCCESS trong 30 ngày; làm tròn HALF_UP đến 2 số lẻ; NULL nếu đếm 0. |
| last_transaction_date | transactions.transaction_time, status; accounts.customer_id | Ngày UTC của SUCCESS cuối trước reference_time; NULL nếu chưa có. |
| days_since_last_transaction | last_transaction_date, snapshot_date | Chênh lệch ngày lịch UTC; NULL nếu chưa có. |
| customer_segment | total_balance | VIP >= 1 tỷ; PRIORITY >= 200 triệu; còn lại MASS. |
| inactivity_flag | transactions.transaction_time, status; accounts.customer_id | Không có SUCCESS trong [reference_time-90d,reference_time), kể cả chưa từng giao dịch. |
| overdue_flag | loans.status, overdue_days | Có ít nhất một ACTIVE với overdue_days > 0. |
| credit_card_candidate | customer_type, monthly_income, overdue_flag | INDIVIDUAL và income >= 20 triệu và không overdue; NULL income cho FALSE. |
| snapshot_date | reference_time | Ngày UTC của mốc báo cáo; reference_time được xem là biên phải loại trừ. |
| updated_at | reference_time / thời điểm tính snapshot | Thời điểm tạo/cập nhật snapshot ở giai đoạn tương lai, không phải thời gian chạy generator. |

Tổng hợp các bảng con riêng về customer_id trước khi LEFT JOIN customer_master. Khử delivery trùng transaction_id trước khi đếm. Không nối chi tiết accounts × transactions × loans rồi SUM. Chỉ đặc tả, không thực thi.
