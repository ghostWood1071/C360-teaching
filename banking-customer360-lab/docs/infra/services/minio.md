# MinIO

MinIO cung cấp object storage tương thích S3 cho các bucket `raw`, `warehouse` và `spark-logs`. `minio-init` tạo bucket, user và policy: Spark có quyền ghi cần cho Delta, còn Trino mặc định chỉ đọc.

## Khởi động và kiểm tra

```bash
make up
docker compose --env-file .env -f infra/compose.yaml ps minio minio-init
docker compose --env-file .env -f infra/compose.yaml logs --tail=200 minio minio-init
```

Console mặc định ở `http://localhost:9001`, API ở `http://localhost:9000`; cả hai chỉ bind loopback theo `HOST_BIND`. Tài khoản lab nằm trong `.env`.

## Dữ liệu và xử lý lỗi

Object nằm trong named volume `customer360-minio`. `make down` giữ dữ liệu; `make reset` xóa volume sau xác nhận. Nếu gặp `AccessDenied`, kiểm tra đúng identity, log `minio-init` và policy trong `infra/minio/policies/`. Không đổi credential sau khi user đã được tạo mà không chủ động cập nhật lại user/policy.

Khi sao lưu lakehouse, cần sao lưu đồng bộ cả object MinIO và metadata Hive trong PostgreSQL tại cùng một mốc logic.
