from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest
import yaml
from src.allocation import Allocation
from src.config import load_config, validate_config, SCENARIOS
from src.pipeline import generate
from src.validation.validate import validate
from src.profiling.profile import profile
from src.common import cents, seconds
from src.writers.parquet_writer import read_batches


def assert_valid(path):
    report=validate(path)
    assert report['passed'],[x for x in report['checks'] if not x['passed']]
    return report


def test_end_to_end_determinism_and_profiling(tiny_config,tmp_path):
    first=generate(tiny_config,tmp_path/'first')
    one=assert_valid(first)
    stats=profile(first)
    assert stats['hot_accounts']['1']['count']==300
    assert stats['hot_accounts']['1']['files']==4
    assert stats['overdue']['rows']==2
    assert stats['overdue']['distinct_customers']==2
    assert stats['uniform_baseline']['max_background_count']-stats['uniform_baseline']['min_background_count']<=1
    second_cfg=deepcopy(tiny_config)
    second_cfg['generation']['batch_size']=37
    second=generate(second_cfg,tmp_path/'second')
    two=assert_valid(second)
    assert one['logical_fingerprints']==two['logical_fingerprints']
    different=deepcopy(tiny_config)
    different['seed']+=1
    third=generate(different,tmp_path/'third')
    three=assert_valid(third)
    assert one['logical_fingerprints']['transactions']!=three['logical_fingerprints']['transactions']


@pytest.mark.parametrize('scenario',SCENARIOS)
def test_each_scenario_complete_dataset(tiny_config,tmp_path,scenario):
    config=tmp_path/'test.yaml'
    config.write_text(yaml.safe_dump(tiny_config))
    cfg=load_config(config,scenario)
    path=generate(cfg,tmp_path/scenario)
    result=assert_valid(path)
    assert len(result['actual_counts'])==5


def test_optional_missing_profiles_late_repeated_and_rows_per_file(tiny_config,tmp_path):
    tiny_config['simulation']['data_quality'].update(missing_profile_ratio=.1,repeated_delivery_events=3)
    tiny_config['simulation']['incremental']['late_arriving_transactions']=7
    tiny_config['output']['rows_per_file']=125
    path=generate(tiny_config,tmp_path/'optional')
    report=assert_valid(path)
    assert report['actual_counts']['customer_profiles']==180
    assert report['raw_delivery']['batch_01']['rows']==1013
    assert len(list((path/'batch_01/core_banking/transactions').glob('*.parquet')))==8
    changes=pa.concat_tables(list(read_batches(path/'batch_02/core_banking/transactions')))
    new=changes.filter(pc.greater(changes['transaction_id'],1000))
    ctx=Allocation(tiny_config)
    late=seconds(new['transaction_time'])<ctx.ref
    assert int(late.sum())==7
    assert np.all(new['account_id'].to_numpy()[late]<=400)


def test_variant_corruption_is_detected(tiny_config,tmp_path):
    path=generate(tiny_config,tmp_path/'corrupt')
    file=next((path/'variants/transactions_pushdown_friendly').glob('*.parquet'))
    data=pq.ParquetFile(file).read()
    changed=data.set_column(data.schema.get_field_index('description'),data.schema.field('description'),
                            pa.array(['CORRUPTED']*len(data)))
    pq.write_table(changed,file)
    result=validate(path)
    assert not result['passed']
    assert not next(x for x in result['checks'] if x['name']=='transactions_pushdown_friendly.logical_values')['passed']


def test_bad_config_rejected_without_output(tiny_config,tmp_path):
    tiny_config['simulation']['skew']['hot_accounts'][0]['transaction_count']=1001
    with pytest.raises(ValueError,match='exceed'):
        generate(tiny_config,tmp_path/'invalid')
    assert not (tmp_path/'invalid').exists()


def test_update_capacity_rejected(tiny_config):
    tiny_config['simulation']['incremental']['updated_accounts']=400
    with pytest.raises(ValueError,match='unprotected'):
        Allocation(tiny_config)


def test_custom_hot_ids_and_ratios(tiny_config,tmp_path):
    tiny_config['simulation']['skew']['hot_accounts']=[dict(account_id=k,ratio=r) for k,r in [(17,.3),(29,.1),(33,.05)]]
    ctx=Allocation(tiny_config)
    assert ctx.hot_counts==[300,100,50]
    assert np.array_equal(ctx.account_owner[[17,29,33]],[1,2,3])
    assert not set(ctx.hot_accounts)&set(ctx.cohort_accounts)
    assert_valid(generate(tiny_config,tmp_path/'ratios'))


def test_empty_incremental_cannot_repeat_deliveries(tiny_config,tmp_path):
    tiny_config['simulation']['data_quality']['repeated_delivery_events']=1
    tiny_config['simulation']['incremental'].update(new_transactions=0,updated_transactions=0)
    with pytest.raises(ValueError,match='empty incremental'):
        generate(tiny_config,tmp_path/'empty')
    assert not (tmp_path/'empty').exists()


def test_config_and_output_guards(tiny_config,tmp_path):
    wrong=deepcopy(tiny_config)
    wrong['reference_time']='2027-01-01'
    with pytest.raises(ValueError,match='timezone'):
        validate_config(wrong)
    wrong=deepcopy(tiny_config)
    wrong['simulation']['join_explosion']['transactions_per_account']=11
    with pytest.raises(ValueError,match='even'):
        validate_config(wrong)
    wrong=deepcopy(tiny_config)
    wrong['simulation']['skew']['hot_accounts'][1]['account_id']=1
    with pytest.raises(ValueError,match='unique'):
        validate_config(wrong)
    path=generate(tiny_config,tmp_path/'guard')
    with pytest.raises(ValueError,match='not empty'):
        generate(tiny_config,path)


def test_standard_exact_allocations():
    cfg=load_config(Path(__file__).resolve().parents[1]/'configs/standard.yaml')
    ctx=Allocation(cfg)
    assert ctx.hot_counts==[600000,200000,100000]
    assert ctx.overdue_count==5000
    assert len(ctx.cohort_customers)==100
    assert ctx.cohort_tx_count==50000
    assert ctx.manifest()['join_explosion']['expected_intermediate_rows']==500000
    assert len(set(ctx.hot_customers)&set(ctx.cohort_customers))==0
    assert ctx.counts==cfg['volume']
