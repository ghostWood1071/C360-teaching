# Vận hành và xử lý sự cố

## Kiểm tra nhanh

```bash
make health
docker compose --env-file .env -f infra/compose.yaml ps
docker compose --env-file .env -f infra/compose.yaml logs --tail=200 <service>
make stats
```

`healthcheck` polling tối đa 5 phút, không dùng sleep cố định cho readiness.

## Lỗi thường gặp

| Hiện tượng | Kiểm tra và xử lý |
|---|---|
| Docker daemon không chạy | Mở Docker Desktop hoặc `systemctl start docker`; chạy `docker info` |
| Build Ranger thiếu RAM | Tăng RAM Docker; build riêng `ranger-admin`; ARM có thể dùng override amd64 |
| Spark OOM/exit 137 | Giảm `local[N]`, tăng `SPARK_CONTAINER_MEMORY`, giữ heap thấp hơn limit |
| Trino OOM | Giảm concurrency, kiểm tra `TRINO_HEAP_SIZE < TRINO_CONTAINER_MEMORY` |
| HMS không lên | Xem `hive-metastore-init` và PostgreSQL; schema init được phép chạy lại |
| MinIO AccessDenied | Kiểm tra đúng identity; chạy lại `minio-init`; không thay credential sau khi user đã tồn tại |
| Trino không thấy bảng mới | Chờ cache tối đa 1 phút ở base/30 giây ở security; xác nhận table đã đăng ký HMS |
| Ranger policy chưa áp dụng | Chờ `RANGER_POLICY_POLL_MS`; xem log Trino/Ranger và tên service |
| HTTPS certificate error | Lab dùng self-signed; dùng `--insecure` cho CLI test, không cho production |
| Port bận | Sửa port host trong `.env`; không sửa port nội bộ service |

## Bền vững và sao lưu

`make down` giữ named volume. Có thể xuất metadata bằng `pg_dump` trong container PostgreSQL và mirror bucket bằng `mc`; cần sao lưu cả hai tại cùng mốc logic. Event log/Airflow log không đủ để khôi phục lakehouse.

`make reset` xóa đúng volume được Compose quản lý cho project sau xác nhận. Thao tác không thể phục hồi nếu chưa backup. Không xóa volume hay container ngoài project và không chạy Docker system prune.

## Chỉ số tài nguyên

`make stats` ghi `infra/evidence/docker-stats-<UTC>.csv` gồm CPU, memory, network, block I/O và PIDs tại một thời điểm. Đây không phải benchmark. Khi báo cáo lab, ghi cả profile, cấu hình Docker và workload đang chạy.
