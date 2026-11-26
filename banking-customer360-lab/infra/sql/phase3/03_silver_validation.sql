SELECT count(*) AS rows, count(DISTINCT transaction_id) AS unique_keys
FROM lakehouse.silver.transactions;

SELECT count(*) AS orphan_transactions
FROM lakehouse.silver.transactions t
LEFT JOIN lakehouse.silver.accounts a ON t.account_id = a.account_id
WHERE a.account_id IS NULL;

SELECT
  sum(CASE WHEN status = 'SUCCESS' AND transaction_type = 'CREDIT' THEN amount ELSE DECIMAL '0.00' END) AS credit_total,
  sum(CASE WHEN status = 'SUCCESS' AND transaction_type = 'DEBIT' THEN amount ELSE DECIMAL '0.00' END) AS debit_total
FROM lakehouse.silver.transactions;

SELECT count(*) AS invalid_loans
FROM lakehouse.silver.loans
WHERE outstanding < 0 OR outstanding > loan_amount OR overdue_days < 0;

