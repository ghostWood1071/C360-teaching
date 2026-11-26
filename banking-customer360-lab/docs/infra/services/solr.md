# Solr audit

Solr là thành phần tùy chọn của profile `audit`, dùng collection `ranger_audits` để tìm kiếm audit event của Ranger. Base và security profile không cần Solr.

## Khởi động và kiểm tra

```bash
make up-audit
docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml -f infra/compose.audit.yaml ps solr
docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml -f infra/compose.audit.yaml logs --tail=200 solr
```

Giao diện mặc định ở `http://localhost:8983`. Healthcheck gọi ping của collection `ranger_audits`; Ranger và Trino chỉ khởi động sau khi Solr healthy trong audit profile.

Audit index nằm trong named volume `customer360-solr`. `make down` giữ volume; `make reset` xóa dữ liệu sau xác nhận. Nếu không thấy audit event, kiểm tra `RANGER_AUDIT_SOLR_ENABLED=true`, health collection và log Trino/Ranger trước khi kiểm tra truy vấn Solr.
