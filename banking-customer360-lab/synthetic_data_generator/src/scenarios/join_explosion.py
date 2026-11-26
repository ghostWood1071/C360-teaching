import numpy as np
import pyarrow as pa
from ..common import money


def expected_metrics(ctx):
    j = ctx.cfg['simulation']['join_explosion']
    ids = ctx.cohort_customers
    n, a, t, l = len(ids), j['accounts_per_customer'], j['transactions_per_account'], j['loans_per_customer']
    cols = dict(customer_id=pa.array(ids), total_accounts=pa.array(np.full(n, a)),
                total_transactions_30d=pa.array(np.full(n, a*t)), total_loans=pa.array(np.full(n, l)),
                intermediate_detailed_join_rows=pa.array(np.full(n, a*t*l)))
    for key, value in dict(total_balance=a*100000000, total_credit_30d=a*t//2*1000000,
                           total_debit_30d=a*t//2*1000000, avg_transaction_amount_30d=1000000,
                           total_loan_amount=l*30000000, total_outstanding=l*20000000).items():
        cols[key] = money(np.full(n, value*100, dtype=np.int64))
    return pa.table(cols)
