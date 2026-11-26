import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.validation.validate import validate


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Validate generated source data')
    parser.add_argument('--data-path',required=True)
    args=parser.parse_args()
    report=validate(args.data_path)
    for check in report['checks']:
        if not check['passed']:
            print(f'FAILED: {check}',file=sys.stderr)
    sys.exit(0 if report['passed'] else 1)
