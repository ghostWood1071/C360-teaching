import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.profiling.profile import profile


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Profile generated Parquet data')
    parser.add_argument('--data-path',required=True)
    profile(parser.parse_args().data_path)
