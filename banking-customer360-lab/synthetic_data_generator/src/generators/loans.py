import numpy as np
from ..common import hashed, money, timestamps, dates, choose
from ..schema import table


def generate(ctx, ids, owners=None):
    new = owners is not None
    owners = ctx.loan_owner[ids] if owners is None else owners
    h = hashed(ids, ctx.seed, 40)
    amount = (10000000+h%2990000001)*100
    closed = h%100 < 20
    outstanding = amount * (20+h%71)//100
    overdue = np.zeros(len(ids),dtype=np.int32)
    if not new:
        cohort = ids <= ctx.cohort_loan_count
        due = (ids>ctx.cohort_loan_count) & (ids<=ctx.cohort_loan_count+ctx.overdue_count)
        amount[cohort], outstanding[cohort], closed[cohort] = 3000000000, 2000000000, False
        overdue[due], closed[due] = 1+h[due]%180, False
    outstanding[closed] = 0
    loan_day = np.full(len(ids),(ctx.ref+10800)//86400) if new else (ctx.start//86400-365+h%365)
    return table('loans', dict(loan_id=ids, customer_id=owners, loan_type=choose(['HOME','CAR','PERSONAL','BUSINESS'],h),
        loan_amount=money(amount), outstanding=money(outstanding), overdue_days=overdue,
        loan_date=dates(loan_day), status=np.where(closed,'CLOSED','ACTIVE'),
        updated_at=timestamps(np.full(len(ids),ctx.ref+86400 if new else ctx.ref-1))))
