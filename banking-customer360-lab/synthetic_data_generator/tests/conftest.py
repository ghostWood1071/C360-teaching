from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_config


@pytest.fixture
def tiny_config():
    cfg=load_config(Path(__file__).resolve().parents[1]/'configs/small.yaml')
    cfg['volume']=dict(customers=200,accounts=400,transactions=1000,customer_profiles=200,loans=200)
    cfg['generation'].update(batch_size=71,row_group_size=23)
    cfg['output'].update(transaction_file_count=4)
    cfg['simulation']['skew']['hot_accounts']=[dict(account_id=1,transaction_count=300),dict(account_id=2,transaction_count=100),dict(account_id=3,transaction_count=50)]
    cfg['simulation']['join_explosion'].update(customer_count=2,transactions_per_account=10)
    cfg['simulation']['incremental'].update(new_customers=4,new_customer_profiles=4,new_accounts=8,
        updated_accounts=10,new_transactions=20,updated_transactions=5,updated_customer_profiles=8,
        new_loans=4,updated_loans=10)
    return cfg
