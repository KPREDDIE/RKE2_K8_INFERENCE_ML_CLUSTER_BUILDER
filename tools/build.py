"""One offline build command: validate first, then package into a new directory.

Uses buildspec.json relative to this script, so the caller can run from any folder.
Never installs dependencies, resolves mutable tags, or connects to a cluster.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate without making archives')
    parser.add_argument('--output', type=Path, help='New release directory (required unless --check)')
    args = parser.parse_args()
    if not args.check and args.output is None:parser.error('Choose --check or --output NEW_DIRECTORY')
    try:
        spec = json.loads((ROOT/'buildspec.json').read_text(encoding='utf-8'))
        if spec['schema_version'] != 1 or spec['stages'] != ['validate','package']:
            raise ValueError('Unsupported buildspec; validation must precede packaging')
        minimum = tuple(int(n) for n in spec['python_minimum'].split('.'))
        if sys.version_info[:2] < minimum:raise ValueError('Python '+spec['python_minimum']+' or newer required')
        baseline = json.loads((ROOT/spec['baseline']).read_text(encoding='utf-8'))
        print('Baseline checked '+baseline['checked_on']+'; '+baseline['status'], flush=True)
        if args.output and args.output.exists():raise ValueError('Output exists; choose a new release directory')
        subprocess.run([sys.executable,str(ROOT/'tools/validate.py')],check=True)
        if not args.check:
            subprocess.run([sys.executable,str(ROOT/'tools/package.py'),'--output',str(args.output.resolve())],check=True)
        return 0
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as error:
        print('Build stopped: '+str(error),file=sys.stderr)
        return 1


if __name__ == '__main__':raise SystemExit(main())
