-- Trino Delta Lake system table syntax.
SELECT version, timestamp, operation, read_version, isolation_level, is_blind_append
FROM lakehouse.silver."transactions$history"
ORDER BY version DESC LIMIT 20;

-- Run separately in Spark SQL, not Trino:
-- DESCRIBE HISTORY silver.transactions;
-- SELECT * FROM delta.`s3a://warehouse/silver/transactions` VERSION AS OF 0 LIMIT 20;

