# Chính sách Ranger được quản lý bằng mã

`infra/ranger/bootstrap/bootstrap_ranger.py` chứa các payload policy có tên ổn định. Script đọc policy hiện tại qua Ranger REST API rồi tạo hoặc cập nhật theo ID, vì vậy có thể chạy lại an toàn. Các policy bao phủ quyền chạy query, tự impersonate, quyền đọc theo tầng, masking ba cột và row filter cho marketing.

Không đặt mật khẩu hoặc token trong thư mục này. Mật khẩu chỉ đến từ `.env` cục bộ đã bị Git bỏ qua.
