"""Create a strict observed container inventory, not a complete platform SBOM."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def collect(pods,namespace):
    """Retain observed image identities and uses, never raw pod environment values."""
    components={}
    selected=[p for p in pods.get('items',[]) if p.get('metadata',{}).get('namespace')==namespace]
    if not selected:
        raise ValueError('No pods in requested namespace')
    for pod in selected:
        status=pod.get('status',{})
        statuses=[]
        for group in ('initContainerStatuses','containerStatuses','ephemeralContainerStatuses'):
            statuses.extend(status.get(group,[]))
        expected=sum(len(pod.get('spec',{}).get(k,[])) for k in ('initContainers','containers','ephemeralContainers'))
        if expected==0 or len(statuses)!=expected:
            raise ValueError('Incomplete runtime container inventory')
        for container in statuses:
            image_id=container.get('imageID','')
            match=re.search(r'(sha256:([0-9a-f]{64}))$',image_id)
            if not match:
                raise ValueError('Runtime image lacks immutable SHA-256 digest')
            digest=match.group(1)
            entry=components.setdefault(digest,{'digest':digest,'declared_images':set(),'uses':[]})
            entry['declared_images'].add(container.get('image',''))
            entry['uses'].append({'pod':pod['metadata']['name'],'container':container['name']})
    if not components:
        raise ValueError('No runtime image digests')
    for item in components.values():
        item['declared_images']=sorted(item['declared_images'])
        item['uses']=sorted(item['uses'],key=lambda u:(u['pod'],u['container']))
    return {'schema_version':1,'status':'observed-image-inventory-not-full-sbom','namespace':namespace,'images':[components[k] for k in sorted(components)]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pods-json',type=Path,required=True)
    parser.add_argument('--namespace',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        data=collect(json.loads(args.pods_json.read_text(encoding='utf-8-sig')),args.namespace)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
        print('Inventory saved; use approved SBOM tooling for packages, models, firmware and relationships')
    except (ValueError,KeyError,OSError) as error:
        parser.exit(1,f'Inventory failed: {error}\n')
