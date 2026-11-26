# Chiến lược incremental và phục hồi

Full Load nhận `batch_01`; Incremental Load nhận `batch_02`. Bronze thay thế đúng partition batch. Silver customer_master được rebuild đầy đủ từ mọi batch đã giao; ba bảng facts dùng Delta MERGE với điều kiện `source.updated_at > target.updated_at`.

Do đó:

- chạy lại batch không tạo thêm business key;
- update cũ đến sau không ghi đè giá trị mới;
- transaction mới nhưng transaction_time cũ vẫn được insert;
- CLOSED account/loan vẫn tồn tại;
- event delivery lặp vẫn ở Bronze nhưng chỉ có một current record ở Silver.

`inject_failure=true` làm ingestion thất bại sau khi commit Bronze để minh họa retry. Tắt cờ rồi chạy lại: `replaceWhere` giữ count ổn định. Một batch chỉ được đánh dấu READY sau validation và reconciliation. Các Delta table độc lập không tạo một transaction nguyên tử xuyên nhiều bảng; Airflow dependency thể hiện trạng thái hoàn tất logic.

Full Load bị từ chối nếu Bronze đã có batch khác, tránh vô tình xóa current state sau incremental. Muốn học lại từ đầu phải dùng reset có xác nhận và chuẩn bị nguồn lại.
