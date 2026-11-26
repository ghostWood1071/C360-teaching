SELECT customer_id, full_name, identity_number, phone, email, monthly_income
FROM lakehouse.silver.customer_master
ORDER BY customer_id LIMIT 20;

SELECT
  count(*) AS customers,
  count(phone) AS matched_phones,
  count_if(monthly_income IS NULL) AS missing_income,
  count(DISTINCT customer_id) AS unique_customers,
  count(DISTINCT identity_number) AS unique_identities
FROM lakehouse.silver.customer_master;

