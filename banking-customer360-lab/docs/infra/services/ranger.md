# Ranger, MinIO IAM và kiểm thử bảo mật

Bootstrap idempotent tạo năm người dùng Ranger và service `customer360-trino`.

| Identity | Quyền mong đợi |
|---|---|
| `platform_admin` | Đọc Bronze/Silver/Gold |
| `data_engineer` | Đọc Bronze/Silver/Gold trong bài test hạ tầng |
| `risk_analyst` | Chỉ cột tài chính đã chọn ở Silver/Gold |
| `marketing_analyst` | Gold đã chọn; mask PII; chỉ khách `INDIVIDUAL` |
| `external_user` | Không đọc bảng bảo vệ |

Policy bắt buộc cho Trino gồm quyền `execute` query và tự impersonate `{USER}`. Policy table/column dùng `use`, `show`, `select`. Mask áp dụng `MASK_SHOW_LAST_4` cho `identity_number`, `phone`, `email`; row filter:

```sql
customer_type = 'INDIVIDUAL'
```

`infra/scripts/verify_security.py` xác nhận giá trị thực, denial rõ ràng, sai mật khẩu, policy polling, SQL write bị từ chối, MinIO credential read-only và credential giả bị từ chối. Nó còn tạo policy tạm cho `external_user`, chờ plugin poll rồi xóa trong `finally`.

```bash
make up-security
make security-test
```

Audit mặc định đi vào logger `ranger.audit` và Docker json log có rotation. `verify_security.py` yêu cầu thấy identity kiểm thử trong log. Profile `make up-audit` thêm Solr để tìm kiếm tập trung; đây là profile nặng hơn.

## MinIO IAM

- `spark_etl`: read/write/delete object trong ba bucket để Delta commit/vacuum hoạt động.
- `trino_reader`: list warehouse và chỉ `GetObject` trong các prefix lakehouse.
- `platform_admin`: toàn quyền ba bucket cho thao tác quản trị.
- Anonymous access bị tắt.

MinIO IAM bảo vệ object endpoint; Ranger bảo vệ truy vấn Trino. Spark ETL không đi qua Ranger. Người có quyền Docker host hoặc secret trong `.env` vẫn có thể vượt qua các lớp này.
