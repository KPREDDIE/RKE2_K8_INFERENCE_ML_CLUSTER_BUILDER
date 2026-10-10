"""Copy the self-contained demo kit without overwriting user work."""
import argparse
import shutil
from pathlib import Path


def scaffold(output):
    source = Path(__file__).resolve().parents[1] / 'assets' / 'build-kit'
    target = Path(output).resolve()
    if target.exists() or source == target or source in target.parents:
        raise ValueError('Choose a new directory outside the template; overwrites are refused')
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(scaffold(args.output))
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
