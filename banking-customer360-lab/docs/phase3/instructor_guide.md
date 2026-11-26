# Hướng dẫn giảng viên

Lịch gợi ý một ngày: 45 phút kiến trúc và khám phá nguồn; 75 phút Bronze; 90 phút Silver/identity; 60 phút incremental; 45 phút quality/recovery; 30 phút Spark UI và tổng kết.

Chuẩn bị trước lớp bằng `make up`, `make phase3-prepare-small`, mở Airflow/Trino/History Server và chạy test tĩnh. Chỉ dùng profile standard khi máy đã được xác minh đủ RAM/đĩa. Bộ small là chuẩn cho thực hành.

Chạy Full Load trước Incremental. Không đưa `batch_02` vào source staging trước khi học viên hoàn thành Full Load khi dạy mixed mode. Cho học viên quan sát Bronze duplicate rồi Silver uniqueness; nhấn mạnh data skew là dữ liệu nghiệp vụ hợp lệ.

Profile low được chọn qua `SPARK_RESOURCE_PROFILE=low` trong `.env` rồi restart Airflow. Tham số DAG phải khớp profile đang deploy để tránh học viên nghĩ đã đổi resource trong khi container vẫn dùng cấu hình cũ.
