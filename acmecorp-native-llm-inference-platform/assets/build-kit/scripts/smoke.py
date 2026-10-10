"""Read cluster state and execute bounded synthetic inference; save content-free evidence."""
import argparse
import hashlib
import json
import re
import subprocess
import time
import sys
from http_transport import fetch, NoRedirect
from render import inventory_check, release_annotations
from pathlib import Path
from urllib.parse import urlsplit


def ready(item):
    return any(c.get('type')=='Ready' and c.get('status')=='True' for c in item.get('status',{}).get('conditions',[]))


def nodes_ok(data,minimum):
    items=data.get('items',[])
    return len(items)>=minimum and all(ready(i) for i in items)


def pods_ok(data,digest):
    """Require ready non-terminating containers with the platform-specific digest."""
    items=data.get('items',[])
    return bool(items) and all(ready(p) and not p.get('metadata',{}).get('deletionTimestamp') and
        bool(p.get('status',{}).get('containerStatuses')) and
        all(c.get('ready') and c.get('imageID','').endswith(digest) for c in p['status']['containerStatuses']) for p in items)


def valid_endpoint(url):
    """Only the operator's localhost tunnel may use plain HTTP."""
    parsed=urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Endpoint must not contain credentials, query or fragment')
    if parsed.scheme!='https' and not(parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
        raise ValueError('TLS required except loopback port-forward')
    if not parsed.hostname:
        raise ValueError('Endpoint hostname missing')
    return url.rstrip('/')


def completion_ok(data,alias):
    choice=data.get('choices',[{}])[0] if data.get('choices') else {}
    content=choice.get('message',{}).get('content')
    return data.get('model')==alias and choice.get('finish_reason')=='stop' and isinstance(content,str) and content.strip()=='SMOKE_OK'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',required=True)
    parser.add_argument('--site',required=True,type=Path)
    parser.add_argument('--endpoint',required=True,help='Base URL without /v1; metrics must be on the same origin')
    parser.add_argument('--auth-file',type=Path)
    parser.add_argument('--inventory',type=Path,help='Defaults to model-files.json beside --site')
    parser.add_argument('--request-deadline',type=float,default=60,help='Total seconds per HTTP call (1-300)')
    parser.add_argument('--minimum-nodes',type=int,default=2)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:
        base=valid_endpoint(args.endpoint)
        site=json.loads(args.site.read_text(encoding='utf-8'))
        inventory=json.loads((args.inventory or args.site.parent/'model-files.json').read_text(encoding='utf-8-sig'))
        inventory_check(site,inventory)
        expected=release_annotations(site,inventory)
        if not 1 <= args.request_deadline <= 300:
            raise ValueError('Request deadline must be 1-300 seconds')
        image=site['runtime_image']
        if not isinstance(image,str) or not re.fullmatch(r'[^\s@]+@sha256:[0-9a-f]{64}',image):
            raise ValueError('Resolved runtime image required')
        if args.minimum_nodes<2:
            raise ValueError('Baseline expects separate server and GPU worker')
        headers={}
        if args.auth_file:
            token=args.auth_file.read_text(encoding='utf-8').strip()
            if not token or '\n' in token or '\r' in token:
                raise ValueError('Invalid token file')
            headers['Authorization']='Bearer '+token
        elif urlsplit(base).hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Remote endpoint requires an auth file')
        if args.output.exists():
            raise ValueError('Evidence file exists; choose a new output')
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(2,f'Invalid configuration: {error}\n')
    checks=[]
    def check(label,operation):
        started=time.monotonic()
        try:
            passed=bool(operation())
        except Exception:
            # No response/error body, token, model output or kubectl stderr is persisted.
            passed=False
        checks.append({'name':label,'status':'PASS' if passed else 'FAIL','elapsed_ms':round((time.monotonic()-started)*1000)})
    def kube(*parts):
        result=subprocess.run(['kubectl','--context',args.context,'--request-timeout=20s',*parts,'-o','json'],capture_output=True,text=True,timeout=25,check=True)
        return json.loads(result.stdout)
    def request(path,payload=None):
        # Isolate network I/O so even DNS or a trickling stream has a hard deadline.
        return fetch(base+path,headers,payload,args.request_deadline)
    ns=site['namespace']; alias=site['model_alias']
    check('nodes-ready',lambda:nodes_ok(kube('get','nodes'),args.minimum_nodes))
    def gpu_check():
        node=kube('get','node',site['gpu_node'])
        return ready(node) and int(node.get('status',{}).get('allocatable',{}).get('nvidia.com/gpu','0'))>=site['gpu_count']
    check('gpu-node-capacity',gpu_check)
    def serving():
        pods=kube('-n',ns,'get','pods','-l','app.kubernetes.io/name=sglang')
        if not pods_ok(pods,image.split('@')[1]):
            return False
        for pod in pods['items']:
            annotations=pod.get('metadata',{}).get('annotations',{})
            if any(annotations.get(key)!=value for key,value in expected.items()):
                return False
            spec=pod.get('spec',{})
            if spec.get('nodeName')!=site['gpu_node']:
                return False
            if not any(v.get('name')=='model' and v.get('persistentVolumeClaim',{}).get('claimName')==site['model_pvc'] for v in spec.get('volumes',[])):
                return False
            verified=pod.get('status',{}).get('initContainerStatuses',[])
            if not any(c.get('name')=='verify-model' and c.get('imageID','').endswith(image.split('@')[1]) and c.get('state',{}).get('terminated',{}).get('exitCode')==0 for c in verified):
                return False
        return True
    check('serving-pods-and-digest',serving)
    def rollout():
        d=kube('-n',ns,'get','deployment','sglang')
        s=d.get('status',{}); desired=d['spec'].get('replicas',1)
        observed=d['spec'].get('template',{}).get('metadata',{}).get('annotations',{})
        if any(observed.get(k)!=v for k,v in expected.items()):return False
        return desired>0 and s.get('observedGeneration',0)>=d['metadata']['generation'] and s.get('updatedReplicas',0)==desired and s.get('availableReplicas',0)==desired
    check('deployment-current',rollout)
    check('model-discovery',lambda:any(m.get('id')==alias for m in json.loads(request('/v1/models')).get('data',[])))
    payload={'model':alias,'messages':[{'role':'user','content':'Reply with exactly SMOKE_OK and nothing else.'}],'temperature':0,'max_tokens':32,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
    check('completion-canary',lambda:completion_ok(json.loads(request('/v1/chat/completions',payload)),alias))
    def stream_check():
        streaming=dict(payload,stream=True)
        raw=request('/v1/chat/completions',streaming).decode()
        chunks=[]; finished=False; done=False
        for line in raw.splitlines():
            if not line.startswith('data: '):
                continue
            data=line[6:]
            if data=='[DONE]':
                done=True
                continue
            event=json.loads(data)
            if event.get('model')!=alias or 'error' in event:
                return False
            for choice in event.get('choices',[]):
                chunks.append(choice.get('delta',{}).get('content') or '')
                finished=finished or choice.get('finish_reason')=='stop'
        return done and finished and ''.join(chunks).strip()=='SMOKE_OK'
    check('streaming-canary',stream_check)
    check('sglang-metrics',lambda:bool(re.search(rb'^sglang[:_][^\n]+',request('/metrics'),re.M)))
    failures=sum(c['status']=='FAIL' for c in checks)
    report={'schema_version':1,'release_id':site['release_id'],'expected_identity':expected,'context':args.context,'checks':checks,'failed_checks':failures,'content_stored':False,'scope':'cluster reads plus two synthetic GPU completions; not production acceptance'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(report,indent=2)+'\n')
    print(f'{len(checks)-failures}/{len(checks)} smoke checks passed; evidence: {args.output}')
    return 1 if failures else 0


if __name__=='__main__':
    raise SystemExit(main())
