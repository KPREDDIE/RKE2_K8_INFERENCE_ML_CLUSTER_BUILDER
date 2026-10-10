"""Offline artifact checks; optional --schemas uses jsonschema and PyYAML for vendor schemas."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'acmecorp-native-llm-inference-platform'
KIT=SKILL/'assets/build-kit'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schemas',type=Path)
    args=parser.parse_args()
    failures=[];count=0
    # Candidate pins must agree with the shipped defaults; site-specific supported
    # deviations belong in a generated kit and require their own evidence.
    baseline=json.loads((KIT/'versions/candidates.json').read_text(encoding='utf-8'))
    site=json.loads((KIT/'config/site.json').read_text(encoding='utf-8'))
    elemental=json.loads((KIT/'config/elemental.json').read_text(encoding='utf-8'))
    model=json.loads((KIT/'config/model-files.json').read_text(encoding='utf-8'))
    if elemental['rke2_version']!=baseline['rke2'] or site['sglang_version']!=baseline['sglang']:
        failures.append('Candidate/default version drift')
    if site['model_id']!=baseline['model']['id'] or site['model_revision']!=baseline['model']['revision'] or model['revision']!=site['model_revision'] or model['model_id']!=site['model_id']:
        failures.append('Candidate/default model identity drift')
    if site['pod_security_version']!='.'.join(baseline['rke2'].split('.')[:2]):
        failures.append('Pod Security minor differs from RKE2 candidate')
    for file in [ROOT/'buildspec.json', * (ROOT/'tools').glob('*.py')]:
        if file.suffix=='.json':json.loads(file.read_text(encoding='utf-8'))
        else:compile(file.read_text(encoding='utf-8'),str(file),'exec')
        count+=1
    for file in SKILL.rglob('*'):
        if not file.is_file() or '__pycache__' in file.parts:continue
        if file.suffix=='.json':
            json.loads(file.read_text(encoding='utf-8'));count+=1
        if file.suffix=='.py':
            compile(file.read_text(encoding='utf-8'),str(file),'exec');count+=1
        if file.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):continue
                target=file.parent/link.split('#')[0]
                if not target.exists():failures.append(f'Broken link: {file.relative_to(ROOT)} -> {link}')
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(KIT/'tests'),'-v'],capture_output=True,text=True)
    print(proc.stdout+proc.stderr)
    if proc.returncode:failures.append('Offline test suite failed')
    for mode in ('elemental','workload'):
        # Unresolved supplied configuration must fail before creating any output.
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'must-not-exist.json'
            result=subprocess.run([sys.executable,str(KIT/'scripts/render.py'),mode,'--output',str(out)],capture_output=True,text=True)
            if result.returncode!=2 or out.exists():failures.append('Unresolved config did not fail closed: '+mode)
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        temporary=Path(temporary)
        for script,flag,target in [('scaffold.py','--output',temporary/'kit'),('install.py','--destination',temporary/'skill')]:
            command=[sys.executable,str(SKILL/'scripts'/script),flag,str(target)]
            first=subprocess.run(command,capture_output=True,text=True)
            marker=target/'preserve.txt'
            if first.returncode==0:marker.write_text('preserve existing work',encoding='utf-8')
            second=subprocess.run(command,capture_output=True,text=True)
            if first.returncode!=0 or second.returncode!=2 or not marker.exists() or marker.read_text()!='preserve existing work':
                failures.append('Copy/refusal validation failed: '+script)
        copied=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(temporary/'kit/tests')],capture_output=True,text=True)
        if copied.returncode:failures.append('Generated standalone kit tests failed')
    print('Scaffold/install and overwrite-protection checks completed')
    if args.schemas:
        import yaml
        from jsonschema import Draft4Validator,RefResolver
        sys.path.insert(0,str(KIT/'tests'))
        from test_kit import site_fixture,inventory_fixture,HASH
        import render
        swagger=json.loads((args.schemas/'kubernetes-v1.37.1.json').read_text(encoding='utf-8'))
        # OpenAPI v2 encodes Kubernetes union scalars as string formats.
        def normalize(value):
            if isinstance(value,dict):
                if value.get('format') in ('int-or-string','quantity'):
                    value['type']=['integer','string']
                for child in value.values():normalize(child)
            elif isinstance(value,list):
                for child in value:normalize(child)
        normalize(swagger)
        validated=[]
        for item in render.workload(site_fixture(),inventory_fixture()):
            version=item['apiVersion'].split('/')[-1]
            group=item['apiVersion'].split('/')[0] if '/' in item['apiVersion'] else ''
            key=next(k for k,v in swagger['definitions'].items() if any(x['kind']==item['kind'] and x['version']==version and x.get('group','')==group for x in v.get('x-kubernetes-group-version-kind',[])))
            Draft4Validator(swagger['definitions'][key],resolver=RefResolver.from_schema(swagger)).validate(item)
            validated.append(item['kind'])
        config=json.loads((KIT/'config/elemental.json').read_text(encoding='utf-8'))
        config.update(seed_image='example.invalid/seed@sha256:'+HASH,compatibility_evidence='test fixture only',ssh_public_key='ssh-ed25519 TEST_PUBLIC_KEY')
        for pool in config['pools']:pool['install_device']='/dev/disk/by-id/test-'+pool['name']
        schemas={}
        for file in args.schemas.glob('*.yaml'):
            crd=yaml.safe_load(file.read_text(encoding='utf-8'))
            schemas[crd['spec']['names']['kind']]=next(v['schema']['openAPIV3Schema'] for v in crd['spec']['versions'] if v['name']=='v1beta1')
        for item in render.elemental(config):
            if item['kind'] in schemas:
                Draft4Validator(schemas[item['kind']]).validate(item)
                validated.append(item['kind'])
        print(f'Vendor-schema validation PASS: {len(validated)} objects; Rancher Cluster server validation still required')
    print(f'Parsed/compiled {count} JSON/Python files; checked local Markdown links')
    if failures:
        print('\n'.join(failures));return 1
    print('Offline artifact validation PASS; no live cluster contacted')
    return 0


if __name__=='__main__':raise SystemExit(main())
