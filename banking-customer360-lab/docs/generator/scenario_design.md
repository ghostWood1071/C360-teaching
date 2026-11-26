# Phân bố dữ liệu và thiết kế tình huống

## Phân bố nghiệp vụ

Các hàm băm số nguyên theo seed và khóa tạo phân bố tái lập, không phụ thuộc batch size. Khoảng 5% pháp nhân; ba chủ tài khoản nóng luôn là ba pháp nhân khác nhau. Nhóm tài chính theo khóa: khoảng 10% có số dư mỗi tài khoản 1,2–2 tỷ, 25% khoảng 220–400 triệu, phần còn lại khoảng 1–50 triệu. Số tài khoản của khách biến thiên, có khách không có tài khoản. Thu nhập theo tầng tương ứng, có NULL. Khoảng 10% khách nền được loại khỏi tập tài khoản có giao dịch; 15% tiếp theo chỉ có giao dịch cũ hơn 90 ngày. Khách còn lại được rải theo 12 tháng; không hứa mọi khách đều có giao dịch gần đây. Khoản vay nền chọn một tập khách đủ nhỏ để có cả khách không vay và khách nhiều khoản. Khoản đóng có dư nợ và quá hạn bằng 0. Manifest và profiling báo số thực tế thay vì coi các tỷ lệ thiết kế là tỷ lệ quan sát chắc chắn.

## 01. Skew

Bối cảnh: pháp nhân tập trung thanh toán. Dành trước account_id 1,2,3 với customer_id 1,2,3 khi bật skew; không trùng cohort. Standard phân bổ chính xác 600000/200000/100000, còn lại 1100000 bao gồm giao dịch cohort. Các ID giao dịch được hoán vị affine để trải khóa nóng qua nhiều file và row group. Số lượng nóng cấu hình bằng count hoặc ratio (floor của tổng * ratio); phần nền tuyệt đối không chọn ba khóa này. Baseline tùy chọn giữ cohort, cùng schema và số dòng nhưng chia đều trên tập tài khoản đủ điều kiện. Đếm theo account và file để kiểm chứng. Dự kiến shuffle join có phân vùng lệch và task chậm; AQE/salting/tổng hợp trước là chủ đề tương lai. Baseline không có cùng tổng hợp khách với skew; chỉ so thuật toán trên cùng biến thể. Không triển khai tối ưu.

## 02. Join Explosion

Bối cảnh: ghép nhiều quan hệ một-nhiều. Standard dành 100 khách ngay sau khóa khách nóng, mỗi khách 5 tài khoản ACTIVE, 100 SUCCESS mỗi tài khoản (50 CREDIT/50 DEBIT), 10 khoản ACTIVE. Số dư 100 triệu, giao dịch 1 triệu, gốc vay 30 triệu, dư nợ 20 triệu, quá hạn 0. Tất cả giao dịch thuộc cửa sổ 30 ngày. Không có bản ghi nền thêm vào các khóa đã dành. Small dùng 10 khách với cùng cấu trúc mỗi khách. Đếm quan hệ, kiểm tra tổng tiền và cardinality 1→5→500→5000 mỗi khách; standard là 500000 dòng sau ghép sai. File expected_customer_metrics.parquet chứa kết quả đúng. Phép join chi tiết nhân số dư và gốc vay, không được dùng làm Gold. Kiểm định chỉ dùng tổng hợp cột trong NumPy, không tạo pipeline đích.

## 03. Broadcast Join

Bối cảnh: tìm khách quá hạn từ tập vay lớn. Dành đúng 5000 khoản ACTIVE standard, 100 small (hoặc floor(loans*ratio)), mỗi khoản cho một khách khác nhau, loại cohort và khóa nóng. overdue_days > 0, outstanding > 0, các khoản khác overdue_days = 0. Manifest chứa miền khóa; báo số dòng, số khách, tỷ lệ và kích thước Arrow sau lọc. Dự kiến tập nhỏ có thể broadcast; phụ thuộc cấu hình Spark, thống kê và độ rộng, không đảm bảo tự động broadcast. Không viết join.

## 04. Partitioning và parallelism

Bối cảnh: thay đổi số task trên laptop. Standard chia 24 file canonical, nhỏ chia 8. Có thể dùng rows_per_file thay file_count, cấu hình batch, row group và codec. File nhận liên tiếp transaction_id nhưng khóa nóng được trộn. Báo số dòng, byte và thống kê từng row group. Phù hợp so 1/4/8/16/200 shuffle partitions ở giai đoạn sau; file đầu vào không quyết định trực tiếp số shuffle partitions. Stress giữ số dòng standard, tăng description/merchant_name và dùng chuỗi có entropy theo khóa; chỉ chạy khi người dùng chủ động chọn stress. Không khẳng định mặc định gây spill hoặc scheduler overhead.

## 05. Scan Optimization

Bối cảnh: lọc một tháng, lọc status và chọn ít cột. Canonical không partition; bản Hive chia transaction_month; bản pushdown gom FAILED và SUCCESS thành các row group riêng bằng hai lượt quét theo cột. Giữ tất cả giá trị, ID, mô tả và codec; cột partition không nằm trong file vật lý, schema logic được khôi phục khi đọc Hive. Bản pushdown dùng cùng tổng số file (chia theo hai status), row group có min/max để quan sát bỏ nhóm. Đọc mỗi batch và tái tạo dòng chuẩn theo transaction_id để so chính xác mọi cột; kiểm tra tập ID xuất hiện đúng một lần; không so byte Parquet. Profiling xuất counts/bytes theo tháng, stats/status min-max, số null. Kích thước file partition khác canonical do chia tháng. Cả hai biến thể tùy chọn, không lẫn với baseline uniform. Hiệu quả thực tế phụ thuộc bộ đọc Spark, không đo benchmark ở đây.

## 06. Data Quality

Bối cảnh: CRM không chuẩn và nhận lại thông điệp. Chọn chính xác floor(profiles*0,05) thu nhập NULL và floor(profiles*0,10) phone không chuẩn. Dạng phone giả lập: local `0-SYN-...`, country `+84-SYN-...`, chèn dấu cách, dấu gạch; không phải số có thể gọi. Identity vẫn duy nhất. Raw batch đầu chứa toàn bộ canonical + đúng floor(transactions*0,01) sự kiện lặp, giữ mọi cột và ID. repeated_delivery_events thêm lượt lặp riêng, đếm rõ trong manifest; không sửa canonical. missing_profile_ratio bỏ đúng số hồ sơ và giảm số dòng CRM có chủ đích, công bố expected_counts sau tiêm; không lấp bằng hồ sơ mồ côi. Late arrival chỉ xuất hiện batch sau với event time cũ và updated_at mới. Đếm NULL, phone, raw ID/multiplicity và toàn bộ giá trị lặp; không tiêm lỗi khóa chuẩn.

## 07. Incremental

Bối cảnh: full load rồi nhận dòng thêm/sửa. Khóa thêm bắt đầu ngay sau miền ban đầu (CRM có offset riêng). File batch_02 chứa toàn bộ ảnh dòng nguồn; updated_at sau reference_time, created_at/loan_date/transaction_time không sau updated_at. Khách mới được tạo trước tài khoản, hồ sơ, vay và giao dịch mới. Bản sửa lấy nguyên dòng batch đầu rồi sửa đúng cột cần thiết; transaction status được đảo để đảm bảo thay đổi thật. Loại mọi tài khoản nóng, cohort và khách quá hạn đã dành khỏi cập nhật mặc định. Bật protect_reserved=false chỉ khi chủ động cần sửa chúng; expected cohort là snapshot batch đầu. counts sau áp dụng = counts đầu + inserts; updates không tăng tổng. Validate phân biệt insert/update theo miền khóa, so ảnh trước-sau, FK sau áp dụng, và updated_at. Duplicate batch sau nằm raw riêng; không thực hiện MERGE.

## Khả năng cấu hình và giới hạn

Tất cả tình huống có enabled riêng; `--scenario` tắt các tình huống khác và vẫn tạo đủ năm bảng nhất quán. Chấp nhận cả tên nghiệp vụ và scan/partitioning. Khóa dành được cấp trước, kiểm tra dung lượng và tập cập nhật trước khi ghi; lỗi cấu hình không để lại dataset dở. Không tự tăng counts. Trường hợp tắt cohort hoặc skew, các miền còn lại được cấp lại theo thứ tự trong manifest. Dataset lớn dùng mảng số gọn cho quan hệ và batch Arrow cho giá trị rộng, không giữ hàng triệu dictionary. Logical fingerprints SHA256 dùng IPC Arrow đã chuẩn hóa thành khối 10000 dòng liên tục theo PK, không phụ thuộc file hoặc row group. Các biến thể scan được so chính xác theo từng ID với bộ sinh đã so với canonical; không phụ thuộc fingerprint xác suất để kết luận tương đương. Tái sinh được kiểm thử bằng fingerprint với cùng seed, thay batch size và khác seed.
