# Cấu hình Trino

Catalog `lakehouse` dùng Delta connector, HMS Thrift và native S3:

```properties
connector.name=delta_lake
hive.metastore.uri=thrift://hive-metastore:9083
fs.native-s3.enabled=true
s3.endpoint=http://minio:9000
s3.path-style-access=true
delta.register-table-procedure.enabled=false
```

Ở base, `delta.security=READ_ONLY`: phù hợp smoke query nhưng không có xác thực host. Chỉ bind vào `127.0.0.1`. Ở security, catalog chuyển sang `delta.security=SYSTEM` để Ranger quyết định quyền; server bật HTTPS, password file PBKDF2 và shared secret nội bộ. HTTP bị tắt.

Ví dụ:

```bash
docker compose --env-file .env -f infra/compose.yaml exec trino \
  trino --server http://localhost:8080 \
  --execute 'SELECT * FROM lakehouse.smoke_test.<ten_bang>'
```

Với security:

```bash
docker compose --env-file .env -f infra/compose.yaml \
  -f infra/compose.security.yaml exec trino \
  trino --server https://localhost:8443 --insecure \
  --user marketing_analyst --password
```

Trino không được dùng để ghi warehouse trong lab: connector read-only/system policy, register procedure tắt và MinIO identity không có `PutObject/DeleteObject`. Ba lớp này giảm lỗi cấu hình đơn lẻ.
