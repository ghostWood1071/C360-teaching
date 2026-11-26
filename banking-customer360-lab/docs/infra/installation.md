# Cài đặt và Quick Start Phase 2

## Yêu cầu

- Docker Desktop mới trên macOS/Windows, hoặc Docker Engine + Compose plugin trên Linux.
- `python3`, OpenSSL và `curl` trên macOS/Linux; Python và `curl.exe` trên Windows.
- Khuyến nghị 10–12 GiB RAM cấp cho Docker, 4 CPU và tối thiểu 20 GiB trống.
- Không đặt repository trong thư mục đồng bộ chậm khi build Ranger.

## Quick Start cho học viên

macOS/Linux:

```bash
make setup
make up
make health
make smoke-test
```

Không có Make:

```bash
./infra/scripts/setup.sh
./infra/scripts/up.sh base
./infra/scripts/healthcheck.sh base
./infra/scripts/smoke_test.sh
```

Windows PowerShell 7:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\infra\scripts\setup.ps1
.\infra\scripts\up.ps1 base
.\infra\scripts\healthcheck.ps1 base
.\infra\scripts\smoke_test.ps1
```

`setup` tạo `.env`, sinh secret ngẫu nhiên, tạo PBKDF2 password file và keystore TLS cục bộ, kiểm tra Compose, pull và build image. Không commit `.env`, `password.db` hoặc keystore.

## Các profile

```bash
make up-etl       # PostgreSQL, MinIO, HMS, Airflow, History Server
make up-query     # PostgreSQL, MinIO, HMS, Trino
make up-security  # base + Ranger + Trino TLS/password
make up-audit     # security + Solr
make security-test
make stats
make down         # giữ volume
```

PowerShell dùng `.\infra\scripts\up.ps1 security` và `python .\infra\scripts\verify_security.py`. Muốn xóa dữ liệu của đúng project này, chạy `make reset`; lệnh hỏi xác nhận. Không có lệnh `docker system prune`.

## URL mặc định

| Dịch vụ | URL |
|---|---|
| Airflow | http://localhost:8083 |
| MinIO Console | http://localhost:9001 |
| Trino base | http://localhost:8084 |
| Trino security | https://localhost:8443 |
| Ranger | http://localhost:6080 |
| Spark History | http://localhost:18080 |
| Solr audit | http://localhost:8983 |

Tài khoản và mật khẩu nằm trong `.env` chỉ dành cho lab cục bộ. Chứng thư Trino là self-signed nên client test dùng `verify=False`; không áp dụng cách này cho môi trường thật.

## Tài nguyên

| Hồ sơ | RAM Docker khuyến nghị | Ghi chú |
|---|---:|---|
| Base | 8–10 GiB | Spark job bị giới hạn tuần tự bằng Airflow pool |
| Security | 10–12 GiB | Thêm Ranger Admin |
| Audit | 12 GiB | Thêm Solr |
| Distributed | 12–16 GiB | Hai worker; không dùng cùng laptop yếu |

Giảm `SPARK_MASTER`, `SPARK_DRIVER_MEMORY`, `SPARK_CONTAINER_MEMORY` và `TRINO_HEAP_SIZE` đồng bộ; đừng đặt heap sát `mem_limit`. Profile thấp đã có `SPARK_LOW_*` cho data khởi tạo bảo mật. `make stats` ghi snapshot CSV thực tế.
