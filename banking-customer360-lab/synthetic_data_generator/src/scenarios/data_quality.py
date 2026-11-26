import math
from .data_skew import permutation_parameters


def injection_counts(cfg, profiles):
    s = cfg['simulation']['data_quality']
    enabled = s['enabled']
    return dict(missing_income=math.floor(profiles*s['missing_income_ratio']) if enabled else 0,
                inconsistent_phone=math.floor(profiles*s['inconsistent_phone_ratio']) if enabled else 0,
                missing_profiles=math.floor(cfg['volume']['customer_profiles']*s['missing_profile_ratio']) if enabled else 0,
                duplicate_transactions=math.floor(cfg['volume']['transactions']*s['duplicate_transaction_ratio']) if enabled else 0,
                repeated_delivery_events=s['repeated_delivery_events'] if enabled else 0)


def ranks(ids, count, seed):
    a, b = permutation_parameters(max(count, 1), seed)
    return ((ids-1)*a+b) % max(count, 1)
