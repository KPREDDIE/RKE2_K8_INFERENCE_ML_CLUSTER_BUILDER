"""Install a complete skill into an explicitly chosen new destination directory."""
import argparse
import shutil
from pathlib import Path


def install(destination):
    source=Path(__file__).resolve().parents[1]
    target=Path(destination).resolve()
    if target.exists() or source==target or source in target.parents:
        raise ValueError('Destination must be new and outside this skill; existing installs are preserved')
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',required=True,type=Path)
    args=parser.parse_args()
    try:print(install(args.destination))
    except ValueError as error:parser.exit(2,str(error)+'\n')
