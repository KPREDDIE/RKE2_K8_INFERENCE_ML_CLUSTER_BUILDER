"""Check site inputs and optionally create a new review bundle. Never contacts a cluster.

Run --check first to list unresolved inputs. Then use --output with a new directory.
Both manifests must validate before any bundle is written; existing work is preserved.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import render

ROOT = Path(__file__).resolve().parents[1]


def load_inputs(config_dir):
    return {name: json.loads((config_dir / (name + '.json')).read_text(encoding='utf-8-sig'))
            for name in ('site', 'elemental', 'model-files')}


def check_inputs(data):
    """Report field names only; configuration may reference private infrastructure."""
    errors = []
    def inspect(value, path):
        if value is None or value == '' or value == {} or value == []:
            errors.append('Resolve ' + path)
        elif isinstance(value, dict):
            for key, child in value.items():inspect(child, path + '.' + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):inspect(child, path + '[' + str(index) + ']')
    for name, value in data.items():inspect(value, name)
    if errors:return errors
    try:
        minor = re.fullmatch(r'v(\d+\.\d+)\.\d+\+rke2r\d+', data['elemental']['rke2_version'])
        if not minor or data['site']['pod_security_version'] != 'v' + minor.group(1):
            errors.append('site.pod_security_version must match elemental.rke2_version minor')
        render.elemental(data['elemental'])
        render.workload(data['site'], data['model-files'])
    except (KeyError, ValueError, TypeError, OSError) as error:
        errors.append('Configuration invalid: ' + str(error))
    return errors


def prepare(config_dir, output=None):
    data = load_inputs(config_dir)
    errors = check_inputs(data)
    if errors:raise ValueError('\n'.join(errors))
    if output is None:return
    # Construct both before reserving a new output directory; never merge a bundle.
    manifests = {'elemental.json': render.elemental(data['elemental']),
                 'workload.json': render.workload(data['site'], data['model-files'])}
    output.mkdir(parents=True, exist_ok=False)
    hashes = []
    for name, items in manifests.items():
        content = (json.dumps({'apiVersion':'v1','kind':'List','items':items}, indent=2)+'\n').encode()
        (output/name).write_bytes(content)
        hashes.append(hashlib.sha256(content).hexdigest() + '  ' + name)
    (output/'CHECKSUMS.txt').write_text('\n'.join(hashes)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-dir', type=Path, default=ROOT/'config')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        prepare(args.config_dir, args.output)
        print('Inputs valid; no cluster contacted.' if args.check else 'Review bundle created; follow Day 0/1 before deployment.')
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, 'Preparation blocked:\n' + str(error) + '\n')
