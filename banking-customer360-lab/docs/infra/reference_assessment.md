# Đánh giá repository tham chiếu

Repository được khảo sát: `ghostWood1071/data-platform-lab`, commit `0156444b4f18051bc0da5829e9ef727ff26f21bd` (2025-11-11).

## Ý tưởng được tái sử dụng

- Topology MinIO + PostgreSQL + Hive Metastore trong một network Compose.
- Entry point setup đa nền tảng.
- Tách cấu hình service khỏi dữ liệu bền vững.

Không sao chép nguyên file cấu hình; các thành phần được dựng lại theo yêu cầu Phase 2 và phiên bản đã chọn.

## Thành phần loại bỏ/thay thế

- Credential hard-coded được thay bằng `.env` sinh cục bộ.
- Iceberg catalog bị loại bỏ; lab dùng Delta Lake.
- Trino 441 coordinator/worker được thay bằng Trino 484 single-node tiết kiệm RAM.
- HiveServer2 bị loại bỏ; chỉ cần Metastore.
- Spark Master/Worker thường trực bị loại khỏi base; chuyển thành DockerOperator container tạm thời.
- Redis/Celery và Airflow 2.7.3 bị thay bằng LocalExecutor/Airflow 2.10.5.
- JAR trùng/xung đột được thay bằng runtime JAR ghim bản và Hive client classpath riêng.
- Bind `0.0.0.0` được thay bằng `127.0.0.1` mặc định.

Ranger 2.6.0 được đối chiếu thêm với source chính thức Apache tại commit tag `a1786ac2fe02196af9cda2ed25716310cac44d43`, đặc biệt service definition Trino và Docker development assets.
