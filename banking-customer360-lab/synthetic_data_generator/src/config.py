from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import math
import yaml
import pyarrow as pa

SCENARIOS = ('data_skew', 'join_explosion', 'broadcast_join', 'partitioning',
             'scan_optimization', 'data_quality', 'incremental')


def load_config(path, scenario=None):
    with open(path, encoding='utf-8') as stream:
        cfg = yaml.safe_load(stream)
    cfg = deepcopy(cfg)
    cfg.setdefault('seed', 42)
    gen = cfg.setdefault('generation', {})
    for key, value in dict(batch_size=50000, compression='snappy', row_group_size=10000).items():
        gen.setdefault(key, value)
    dist = cfg.setdefault('distribution', {})
    for key, value in dict(corporate_customer_ratio=.05, inactive_customer_ratio=.15,
                           never_transacted_customer_ratio=.10).items():
        dist.setdefault(key, value)
    sim = cfg.setdefault('simulation', {})
    defaults = {
        'skew': dict(enabled=True, hot_accounts=[dict(account_id=1, ratio=.30),
                      dict(account_id=2, ratio=.10), dict(account_id=3, ratio=.05)]),
        'join_explosion': dict(enabled=True, customer_count=100, accounts_per_customer=5,
                              transactions_per_account=100, loans_per_customer=10),
        'broadcast_join': dict(enabled=True, overdue_loan_ratio=.01),
        'data_quality': dict(enabled=True, duplicate_transaction_ratio=.01,
                             missing_income_ratio=.05, inconsistent_phone_ratio=.10,
                             missing_profile_ratio=0., repeated_delivery_events=0),
        'transaction_history': dict(months=12),
        'incremental': dict(enabled=True, new_customers=1000, new_customer_profiles=1000,
                            new_accounts=2000, updated_accounts=10000, new_transactions=50000,
                            updated_transactions=1000, updated_customer_profiles=5000,
                            new_loans=1000, updated_loans=5000, late_arriving_transactions=0,
                            protect_reserved=True),
    }
    for name, vals in defaults.items():
        current = sim.setdefault(name, {})
        for key, value in vals.items():
            current.setdefault(key, deepcopy(value))
    out = cfg.setdefault('output', {})
    for key, value in dict(base_path='./data', format='parquet', transaction_file_count=24,
                           rows_per_file=None, generate_month_partitioned_variant=True,
                           generate_pushdown_variant=True, generate_uniform_baseline=False).items():
        out.setdefault(key, value)
    widths = cfg.setdefault('descriptive_columns', {})
    for key, value in dict(description=192, merchant_name=64).items():
        widths.setdefault(key, value)
    if scenario:
        if scenario not in SCENARIOS:
            raise ValueError(f'Unknown scenario: {scenario}')
        mapping = dict(data_skew='skew', join_explosion='join_explosion',
                       broadcast_join='broadcast_join', data_quality='data_quality', incremental='incremental')
        for key in mapping.values():
            sim[key]['enabled'] = mapping.get(scenario) == key
        out['generate_month_partitioned_variant'] = scenario == 'scan_optimization'
        out['generate_pushdown_variant'] = scenario == 'scan_optimization'
        out['generate_uniform_baseline'] = scenario == 'data_skew'
    cfg['selected_scenario'] = scenario
    validate_config(cfg)
    return cfg


def reference(cfg):
    return datetime.fromisoformat(cfg['reference_time'].replace('Z', '+00:00')).astimezone(timezone.utc)


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')


def validate_config(cfg):
    integer(cfg['seed'], 'seed')
    raw_time = datetime.fromisoformat(cfg['reference_time'].replace('Z', '+00:00'))
    if raw_time.tzinfo is None:
        raise ValueError('reference_time must include a timezone')
    for name in ('customers', 'accounts', 'transactions', 'customer_profiles', 'loans'):
        integer(cfg['volume'][name], f'volume.{name}', 1)
    if cfg['volume']['customer_profiles'] > cfg['volume']['customers']:
        raise ValueError('Profiles cannot exceed customers while identity_number is unique')
    for key in ('batch_size', 'row_group_size'):
        integer(cfg['generation'][key], key, 1)
    if not pa.Codec.is_available(cfg['generation']['compression']):
        raise ValueError('Compression codec unavailable')
    integer(cfg['output']['transaction_file_count'], 'transaction_file_count', 1)
    if cfg['output']['rows_per_file'] is not None:
        integer(cfg['output']['rows_per_file'], 'rows_per_file', 1)
    if cfg['output']['format'] != 'parquet':
        raise ValueError('Only parquet output is supported')
    for key, value in cfg['distribution'].items():
        if not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value < 1:
            raise ValueError(f'Invalid ratio distribution.{key}')
    if sum(cfg['distribution'][x] for x in ('inactive_customer_ratio', 'never_transacted_customer_ratio')) >= 1:
        raise ValueError('Inactive and never-transacted ratios must sum to < 1')
    for section in ('data_quality', 'broadcast_join'):
        for key, value in cfg['simulation'][section].items():
            if key.endswith('_ratio') and (not math.isfinite(value) or not 0 <= value <= 1):
                raise ValueError(f'Invalid ratio {section}.{key}')
    for section in ('skew','join_explosion','broadcast_join','data_quality','incremental'):
        if not isinstance(cfg['simulation'][section]['enabled'],bool):
            raise ValueError(f'{section}.enabled must be a boolean')
    if 'overdue_loan_count' in cfg['simulation']['broadcast_join']:
        integer(cfg['simulation']['broadcast_join']['overdue_loan_count'],'overdue_loan_count')
    for flag in ('generate_month_partitioned_variant','generate_pushdown_variant','generate_uniform_baseline'):
        if not isinstance(cfg['output'][flag],bool):
            raise ValueError(f'{flag} must be a boolean')
    integer(cfg['simulation']['data_quality']['repeated_delivery_events'], 'repeated_delivery_events')
    integer(cfg['simulation']['transaction_history']['months'], 'months', 1)
    for name, length in cfg['descriptive_columns'].items():
        integer(length, name, 16)
    for key, value in cfg['simulation']['incremental'].items():
        if key not in ('enabled', 'protect_reserved'):
            integer(value, key)
    if cfg['simulation']['incremental']['late_arriving_transactions'] > cfg['simulation']['incremental']['new_transactions']:
        raise ValueError('Late arrivals are part of new_transactions, not additional rows')
    j = cfg['simulation']['join_explosion']
    for key in ('customer_count', 'accounts_per_customer', 'transactions_per_account', 'loans_per_customer'):
        integer(j[key], key, 1)
    if j['transactions_per_account'] % 2:
        raise ValueError('Cohort transactions_per_account must be even for equal CREDIT/DEBIT')
    if cfg['simulation']['skew']['enabled']:
        effective_files = (math.ceil(cfg['volume']['transactions']/cfg['output']['rows_per_file'])
                           if cfg['output']['rows_per_file'] else cfg['output']['transaction_file_count'])
        if effective_files < 2:
            raise ValueError('Skew requires multiple transaction files to spread hot records')
        ids = []
        for hot in cfg['simulation']['skew']['hot_accounts']:
            integer(hot['account_id'], 'hot account_id', 1)
            ids.append(hot['account_id'])
            if 'transaction_count' in hot:
                integer(hot['transaction_count'], 'hot transaction_count', 1)
            elif 'ratio' not in hot or not 0 < hot['ratio'] < 1:
                raise ValueError('Hot accounts need positive transaction_count or ratio')
        if len(set(ids)) != len(ids) or len(ids) < 1:
            raise ValueError('Hot account IDs must be unique and nonempty')
        if max(ids) > cfg['volume']['accounts']:
            raise ValueError('Hot account ID exceeds account volume')
