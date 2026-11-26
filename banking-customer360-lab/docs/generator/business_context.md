# ABC Bank: bối cảnh và quy tắc nghiệp vụ

Đây là dữ liệu hoàn toàn giả lập phục vụ một ngày thực hành Customer 360. Không dùng dữ liệu cá nhân thật. Tên Việt Nam được ghép từ từ điển nhỏ; doanh nghiệp, địa chỉ, số giấy tờ và số điện thoại đều mang dấu hiệu giả lập. Email dùng `example.com`. Đơn vị tiền duy nhất là VND; lưu DECIMAL(18,2), tính bằng số nguyên đơn vị 0,01 VND.

Core Banking quản lý khách hàng, tài khoản và giao dịch. CRM dùng khóa riêng `profile_id`, liên kết bằng `identity_number`. Loan System liên kết logic qua `customer_id`. Không coi tài khoản đang mở đồng nghĩa với khách hàng đang hoạt động. Tài khoản đóng vẫn có thể có lịch sử giao dịch; số dư hiện tại bằng 0.

Thời gian chuẩn là UTC, khoảng báo cáo dùng `[reference_time - 30 ngày, reference_time)`. Hoạt động chỉ tính giao dịch SUCCESS, kể cả khi tài khoản hiện tại đã đóng. Inactive nghĩa là không có SUCCESS trong 90 ngày trước mốc tham chiếu, bao gồm khách chưa giao dịch. Giao dịch FAILED không tính vào chỉ tiêu hành vi. Dư nợ và quá hạn chỉ xét khoản vay ACTIVE; tổng số khoản vay và tổng gốc gồm cả khoản đã đóng. Số tài khoản gồm cả tài khoản đã đóng; tổng số dư chỉ xét ACTIVE.

VIP: tổng số dư ACTIVE >= 1 tỷ. PRIORITY: từ 200 triệu đến dưới 1 tỷ. MASS: dưới 200 triệu. Overdue: tồn tại khoản ACTIVE có overdue_days > 0. Ứng viên thẻ: INDIVIDUAL, thu nhập >= 20 triệu và không quá hạn; thu nhập thiếu không đủ điều kiện. Các quy tắc này là giả định đơn giản cho đào tạo, không phải chính sách tín dụng.

Khách không có tài khoản/vay/giao dịch vẫn phải xuất hiện đúng một lần trong Gold. Tổng và đếm thiếu được điền 0. Trung bình giao dịch, ngày giao dịch cuối và số ngày từ giao dịch cuối là NULL nếu chưa có SUCCESS; tuổi NULL với pháp nhân. Không suy diễn số dư hiện tại từ lịch sử giao dịch: lịch sử chỉ bao phủ 12 tháng, không phải sổ cái đầy đủ.

Giai đoạn này chỉ chuẩn bị dữ liệu, mô hình, kiểm định và hồ sơ dữ liệu. Không có Spark, DAG, Docker, notebook, MERGE, dashboard hoặc API.
