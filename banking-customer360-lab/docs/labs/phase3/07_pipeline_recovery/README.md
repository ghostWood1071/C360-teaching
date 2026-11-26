# Lab 07 – Phục hồi và Idempotency

## 1. Bối cảnh nghiệp vụ
Task có thể fail sau commit; delivery có thể lặp; các bảng Delta không có transaction chung.

## 2. Mục tiêu học tập
Phục hồi có kiểm soát mà không xóa dữ liệu hợp lệ hoặc nhân đôi business data.

## 3. Dữ liệu đầu vào
Batch 01/02 và cờ failure injection mặc định tắt.

## 4. Kết quả mong đợi
Retry Bronze giữ count; replay incremental giữ current state; update cũ không ghi đè bản mới.

## 5. Logic xử lý
`replaceWhere` bảo vệ batch; MERGE bảo vệ timestamp; READY chỉ ghi sau toàn bộ dependency.

## 6. Code Spark liên quan
`ingest_bronze.py --inject-failure true`, `mark_batch_ready.py`, `writers.py`.

## 7. Chạy bằng Airflow
Chạy small Full Load với `inject_failure=true`; quan sát fail sau commit, đổi false rồi retry. Không dùng standard cho bài demo lỗi.

## 8. SQL kiểm tra
Kiểm tra count theo `_batch_id`, business-key uniqueness và `$history` bằng `06_delta_history.sql`.

## 9. Quan sát Spark UI
So hai application retry và Delta version; logical idempotency không có nghĩa số version giống nhau.

## 10. Câu hỏi thảo luận
Nếu Bronze thành công nhưng Silver fail thì dữ liệu nào còn dùng được? Khi nào batch được xem READY?

## 11. Lỗi thường gặp
Reset toàn stack khi chỉ một task fail, nhầm duplicate delivery với retry, hoặc cho Full Load ghi đè incremental.

## 12. Bài tập học viên
Replay Batch 02, so count/value trước-sau và giải thích thêm Delta commit hợp lệ.

