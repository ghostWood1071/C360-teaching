-- Run with the authorized data_engineer or platform_admin identity.
SELECT 'customers' AS table_name, count(*) AS rows FROM lakehouse.bronze.customers
UNION ALL SELECT 'accounts', count(*) FROM lakehouse.bronze.accounts
UNION ALL SELECT 'transactions', count(*) FROM lakehouse.bronze.transactions
UNION ALL SELECT 'customer_profiles', count(*) FROM lakehouse.bronze.customer_profiles
UNION ALL SELECT 'loans', count(*) FROM lakehouse.bronze.loans;

SELECT date_format(transaction_time, '%Y-%m') AS transaction_month, count(*) AS rows
FROM lakehouse.bronze.transactions
GROUP BY 1 ORDER BY 1;

SELECT account_id, count(*) AS transaction_count
FROM lakehouse.bronze.transactions
GROUP BY account_id ORDER BY transaction_count DESC LIMIT 20;

