# PostgreSQL

PostgreSQL lưu metadata của Airflow, Hive Metastore và Ranger. Khi bật source profile, nó còn tạo các database nguồn phục vụ bài lab. Service không publish cổng ra host; các container truy cập bằng hostname `postgres:5432` trên network Compose.

## Khởi động và kiểm tra

```bash
make up
docker compose --env-file .env -f infra/compose.yaml ps postgres
docker compose --env-file .env -f infra/compose.yaml logs --tail=200 postgres
```

Healthcheck dùng `pg_isready`. Script trong `infra/postgres/init/` tạo role/database theo biến trong `.env` và được thiết kế để khởi tạo volume mới.

## Dữ liệu và vận hành

Named volume mặc định là `customer360-postgres`. `make down` giữ volume; `make reset` xóa volume sau khi hỏi xác nhận. Muốn sao lưu, dùng `pg_dump` hoặc `pg_dumpall` bên trong container và lưu kết quả ngoài volume trước khi reset.

Nếu Hive, Airflow hoặc Ranger báo lỗi kết nối, kiểm tra lần lượt health của `postgres`, log init và các biến `*_DB_NAME`, `*_DB_USER`, `*_DB_PASSWORD` trong `.env`.
