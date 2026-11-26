# Spark History Server

Mọi Spark job bật event logging tới named volume `spark-events`. History Server mount volume ở chế độ read-only và phục vụ giao diện tại http://localhost:18080.

Sau smoke test:

```bash
curl -fsS http://localhost:18080/api/v1/applications
```

Ít nhất bốn application theo các bước create/append/merge/validate sẽ xuất hiện sau khi event log được đóng. Retention mặc định là 7 ngày qua `SPARK_EVENT_LOG_MAX_AGE`; cleaner chỉ xóa event log cũ, không xóa Delta table hoặc metadata.

Nếu không thấy ứng dụng:

1. kiểm tra task Spark đã kết thúc thành công;
2. kiểm tra volume `customer360-spark-events` được mount read-write vào job;
3. xem `docker compose ... logs spark-history`;
4. chạy `make smoke-test` thay vì gọi Spark image không gắn volume.
