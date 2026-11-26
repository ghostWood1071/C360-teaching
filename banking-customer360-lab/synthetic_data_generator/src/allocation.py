import numpy as np
from .common import hashed, history_start
from .config import reference
from .scenarios.data_skew import hot_allocations, permutation_parameters
from .scenarios.broadcast_join import overdue_count
from .scenarios.data_quality import injection_counts


class Allocation:
    def __init__(self, cfg):
        self.cfg, self.seed = cfg, cfg['seed']
        self.ref = int(reference(cfg).timestamp())
        self.start = history_start(reference(cfg), cfg['simulation']['transaction_history']['months'])
        self.counts = dict(cfg['volume'])
        self.hot_accounts, self.hot_counts = hot_allocations(cfg)
        h = len(self.hot_accounts)
        self.hot_customers = np.arange(1, h+1, dtype=np.int64)
        j = cfg['simulation']['join_explosion']
        k = j['customer_count'] if j['enabled'] else 0
        self.cohort_customers = np.arange(h+1, h+k+1, dtype=np.int64)
        self.reserved_customers = h+k
        n, a, t, l = [self.counts[x] for x in ('customers','accounts','transactions','loans')]
        ca, cl = k*j['accounts_per_customer'], k*j['loans_per_customer']
        self.cohort_tx_count = ca*j['transactions_per_account']
        self.overdue_count = overdue_count(cfg)
        if (h+k >= n or ca+h >= a or cl+self.overdue_count > l or
                sum(self.hot_counts)+self.cohort_tx_count > t or self.overdue_count > n-h-k):
            raise ValueError('Reserved scenario allocations exceed configured volume')
        if any(c < 2 for c in self.hot_counts):
            raise ValueError('Hot transaction allocations must be >= 2 to span multiple files')
        self.customer_ids = np.arange(1, n+1, dtype=np.int64)
        self.customer_hash = hashed(self.customer_ids, self.seed, 1)
        self.corporate = self.customer_hash % 10000 < int(cfg['distribution']['corporate_customer_ratio']*10000)
        self.corporate[:h] = True
        state = hashed(self.customer_ids, self.seed, 2) % 10000
        never_cut = int(cfg['distribution']['never_transacted_customer_ratio']*10000)
        inactive_cut = never_cut + int(cfg['distribution']['inactive_customer_ratio']*10000)
        self.never = state < never_cut
        self.inactive = (state >= never_cut) & (state < inactive_cut)
        self.never[:h+k] = False
        self.inactive[:h+k] = False
        background_customers = self.customer_ids[h+k:]
        account_ids = np.arange(1, a+1, dtype=np.int64)
        free = account_ids[~np.isin(account_ids, self.hot_accounts)]
        self.cohort_accounts = free[:ca]
        self.account_owner = np.zeros(a+1, dtype=np.int64)
        self.account_owner[account_ids] = background_customers[hashed(account_ids, self.seed, 3) % len(background_customers)]
        self.account_owner[self.hot_accounts] = self.hot_customers
        if ca:
            self.account_owner[self.cohort_accounts] = np.repeat(self.cohort_customers, j['accounts_per_customer'])
        self.cohort_account_index = np.full(a+1, -1, dtype=np.int64)
        self.cohort_account_index[self.cohort_accounts] = np.arange(ca)
        eligible = ~self.never[self.account_owner[1:]-1]
        eligible &= ~np.isin(account_ids, self.cohort_accounts)
        self.uniform_accounts = account_ids[eligible]
        self.background_accounts = account_ids[eligible & ~np.isin(account_ids, self.hot_accounts)]
        if not len(self.background_accounts) or not len(self.uniform_accounts):
            raise ValueError('No eligible background transaction accounts')
        if (self.start >= self.ref - 91*86400) and np.any(self.inactive[self.account_owner[self.background_accounts]-1]):
            raise ValueError('History must exceed 91 days when inactive customers are enabled')
        self.loan_owner = np.zeros(l+1, dtype=np.int64)
        loan_ids = np.arange(1, l+1, dtype=np.int64)
        loan_customers = background_customers[hashed(background_customers, self.seed, 4) % 100 < 60]
        if not len(loan_customers):
            raise ValueError('No background loan customers')
        self.loan_owner[1:] = loan_customers[hashed(loan_ids, self.seed, 5) % len(loan_customers)]
        if cl:
            self.loan_owner[1:cl+1] = np.repeat(self.cohort_customers, j['loans_per_customer'])
        self.cohort_loan_count = cl
        self.overdue_customers = background_customers[:self.overdue_count]
        self.loan_owner[cl+1:cl+self.overdue_count+1] = self.overdue_customers
        dq = injection_counts(cfg, self.counts['customer_profiles'])
        self.counts['customer_profiles'] -= dq['missing_profiles']
        self.dq = injection_counts(cfg, self.counts['customer_profiles'])
        self.dq['missing_profiles'] = dq['missing_profiles']
        self.profile_customer_ids = self.customer_ids[:self.counts['customer_profiles']]
        self.multiplier, self.offset = permutation_parameters(t, self.seed)
        self.validate_incremental()

    def tx_ranks(self, ids):
        return ((ids-1)*self.multiplier+self.offset) % self.counts['transactions']

    def protected_customers(self):
        return np.concatenate((self.customer_ids[:self.reserved_customers], self.overdue_customers))

    def validate_incremental(self):
        s = self.cfg['simulation']['incremental']
        if not s['enabled']:
            return
        protect = s['protect_reserved']
        reserved = self.protected_customers() if protect else np.array([], dtype=np.int64)
        self.update_account_pool = np.flatnonzero(~np.isin(self.account_owner[1:], reserved))+1
        self.update_loan_pool = np.flatnonzero(~np.isin(self.loan_owner[1:], reserved))+1
        self.update_profile_pool = np.flatnonzero(~np.isin(self.profile_customer_ids, reserved))+1
        # Transaction eligibility is checked without allocating wide source rows.
        from .generators.transactions import relationship
        transaction_ids = np.arange(1, self.counts['transactions']+1, dtype=np.int64)
        owners = self.account_owner[relationship(self, transaction_ids)[0]]
        self.update_tx_pool = transaction_ids[~np.isin(owners, reserved)]
        for key, pool in [('updated_accounts', self.update_account_pool), ('updated_loans', self.update_loan_pool),
                          ('updated_customer_profiles', self.update_profile_pool), ('updated_transactions', self.update_tx_pool)]:
            if s[key] > len(pool):
                raise ValueError(f'{key} exceeds available unprotected records')
        if s['new_customer_profiles'] > s['new_customers']:
            raise ValueError('New CRM profiles cannot exceed new customers')
        dq = self.cfg['simulation']['data_quality']
        if dq['enabled'] and dq['repeated_delivery_events'] and s['new_transactions']+s['updated_transactions']==0:
            raise ValueError('Cannot repeat delivery events from an empty incremental transaction batch')

    def manifest(self):
        j = self.cfg['simulation']['join_explosion']
        return dict(hot_accounts=[dict(account_id=a, customer_id=int(c), transaction_count=n)
                     for a,c,n in zip(self.hot_accounts,self.hot_customers,self.hot_counts)],
                    join_explosion=dict(customer_ids=self.cohort_customers.tolist(),
                        account_ids=self.cohort_accounts.tolist(), **j,
                        loan_id_start=1, loan_count=self.cohort_loan_count,
                        expected_intermediate_rows=len(self.cohort_customers)*j['accounts_per_customer']*
                            j['transactions_per_account']*j['loans_per_customer']),
                    broadcast_join=dict(overdue_loan_count=self.overdue_count,
                        overdue_customer_ids=self.overdue_customers.tolist(),
                        first_loan_id=self.cohort_loan_count+1),
                    never_transacted_customer_ids=self.customer_ids[self.never].tolist())
