import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_config, SCENARIOS
from src.pipeline import generate


def main():
    parser=argparse.ArgumentParser(description='Generate synthetic ABC Bank source data')
    parser.add_argument('--config',required=True)
    parser.add_argument('--scenario',choices=SCENARIOS)
    parser.add_argument('--output')
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    try:
        generate(load_config(args.config,args.scenario),args.output,args.overwrite)
    except (ValueError,KeyError) as error:
        parser.exit(2,f'Configuration/generation error: {error}\n')


if __name__=='__main__':
    main()
