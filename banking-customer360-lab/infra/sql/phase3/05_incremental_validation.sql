SELECT _batch_id, count(*) AS rows
FROM lakehouse.bronze.accounts GROUP BY _batch_id ORDER BY _batch_id;

SELECT
  (SELECT count(*) FROM lakehouse.silver.customer_master) AS customers,
  (SELECT count(*) FROM lakehouse.silver.accounts) AS accounts,
  (SELECT count(*) FROM lakehouse.silver.transactions) AS transactions,
  (SELECT count(*) FROM lakehouse.silver.loans) AS loans;

SELECT batch_id, load_type, status, dag_run_id, ready_at
FROM lakehouse.quality.pipeline_batches ORDER BY ready_at DESC;

