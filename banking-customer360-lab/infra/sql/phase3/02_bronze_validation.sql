SELECT _batch_id, count(*) AS rows
FROM lakehouse.bronze.transactions GROUP BY _batch_id ORDER BY _batch_id;

SELECT transaction_id, count(*) AS delivery_events
FROM lakehouse.bronze.transactions
WHERE _batch_id = 'batch_01'
GROUP BY transaction_id HAVING count(*) > 1
ORDER BY delivery_events DESC, transaction_id LIMIT 20;

SELECT
  count_if(_source_system IS NULL) AS missing_source,
  count_if(_batch_id IS NULL) AS missing_batch,
  count_if(_ingested_at IS NULL) AS missing_ingestion_time
FROM lakehouse.bronze.transactions;

