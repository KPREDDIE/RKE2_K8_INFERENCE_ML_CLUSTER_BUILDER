"""Render reviewable Kubernetes JSON (valid YAML) without contacting a cluster."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DIGEST = re.compile(r'^[^\s@]+@sha256:[0-9a-f]{64}$')
DNS = re.compile(r'^[a-z0-9](?:[-a-z0-9]*[a-z0-9])?$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def name(value):
    require(isinstance(value, str) and len(value) <= 63 and DNS.fullmatch(value), 'Invalid Kubernetes name')
    return value


def immutable(value):
    require(isinstance(value, str) and DIGEST.fullmatch(value), 'Immutable image repo@sha256 digest required')
    require(len(set(value.rsplit(':', 1)[1])) > 1, 'Obvious placeholder digest refused')
    return value


def inventory_check(site, inventory):
    require(inventory['revision'] == site['model_revision'] and inventory['model_id'] == site['model_id'], 'Model identity mismatch')
    require(re.fullmatch(r'[0-9a-f]{40}', inventory['revision']), 'Exact model commit required')
    files = inventory['files']
    require(isinstance(files, dict) and files, 'Model file checksum inventory is unresolved')
    require('config.json' in files and any(p.endswith('.safetensors') for p in files), 'Config and safetensors weights required')
    require(any('tokenizer' in p for p in files), 'Tokenizer inventory required')
    for path, checksum in files.items():
        p = PurePosixPath(path)
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in path and ':' not in path, 'Unsafe model inventory path')
        require(re.fullmatch(r'[0-9a-f]{64}', checksum) and len(set(checksum)) > 1, 'Invalid or placeholder model hash')


def obj(kind, object_name, namespace=None, spec=None, api='v1', **extra):
    item = {'apiVersion': api, 'kind': kind, 'metadata': {'name': object_name}}
    if namespace:
        item['metadata']['namespace'] = namespace
    if spec is not None:
        item['spec'] = spec
    item.update(extra)
    return item


def release_annotations(site, inventory):
    """Bind a rollout to its reviewed release, model identity and file inventory."""
    return {'acmecorp.release': site['release_id'],
            'acmecorp.model-id': site['model_id'],
            'acmecorp.model-revision': site['model_revision'],
            'acmecorp.inventory-sha256': hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()}


def workload(site, inventory):
    """Render the private workload. Null site values intentionally block output."""
    ns = name(site['namespace'])
    image = immutable(site['runtime_image'])
    name(site['model_pvc'])
    name(site['model_alias'])
    require(site.get('gpu_node') and isinstance(site['gpu_node'], str), 'Verified GPU node hostname required')
    require(site.get('compatibility_evidence'), 'Compatibility evidence reference required')
    require(site['gpu_count'] == 1, 'Baseline is one whole GPU; use an ADR and extended profile for tensor parallelism')
    require(128 <= site['context_length'] <= 4096 and 1 <= site['max_running_requests'] <= 2, 'Demo capacity limits exceeded')
    require(re.fullmatch(r'v1\.\d+', site['pod_security_version']), 'Pod Security version must match target Kubernetes minor')
    inventory_check(site, inventory)
    labels = {'app.kubernetes.io/name': 'sglang', 'app.kubernetes.io/part-of': 'acmecorp-demo'}
    inventory_text = json.dumps(inventory, sort_keys=True)
    require(len(inventory_text.encode()) < 700000, 'Inventory too large for ConfigMap; use a reviewed artifact-volume extension')
    verify = (ROOT / 'scripts' / 'verify_model.py').read_text(encoding='utf-8')
    proxy = (ROOT / 'scripts' / 'metrics_proxy.py').read_text(encoding='utf-8')
    security = {'allowPrivilegeEscalation': False, 'readOnlyRootFilesystem': True, 'capabilities': {'drop': ['ALL']}}
    mounts = [{'name': 'model', 'mountPath': '/model', 'readOnly': True}, {'name': 'tmp', 'mountPath': '/tmp'}, {'name': 'shm', 'mountPath': '/dev/shm'}]
    container = {
        'name': 'sglang', 'image': image,
        'command': ['python3', '-m', 'sglang.launch_server'],
        'args': ['--model-path', '/model', '--served-model-name', site['model_alias'], '--host', '0.0.0.0', '--port', '30000', '--dtype', 'bfloat16', '--tp-size', '1', '--context-length', str(site['context_length']), '--max-running-requests', str(site['max_running_requests']), '--mem-fraction-static', '0.8', '--enable-metrics', '--reasoning-parser', 'qwen3', '--log-level', 'warning'],
        'ports': [{'name': 'http', 'containerPort': 30000}],
        'env': [{'name': k, 'value': v} for k, v in {'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1', 'HF_HOME':'/tmp/hf', 'HOME':'/tmp', 'TRITON_CACHE_DIR':'/tmp/triton'}.items()],
        'resources': {'requests': {'cpu': site['cpu'], 'memory': site['memory'], 'nvidia.com/gpu': '1'}, 'limits': {'cpu': site['cpu'], 'memory': site['memory'], 'nvidia.com/gpu': '1'}},
        'securityContext': security, 'volumeMounts': mounts,
        'startupProbe': {'httpGet': {'path': '/health', 'port': 'http'}, 'periodSeconds': 10, 'failureThreshold': 180, 'timeoutSeconds': 5},
        'readinessProbe': {'httpGet': {'path': '/health', 'port': 'http'}, 'periodSeconds': 10, 'timeoutSeconds': 5},
        'livenessProbe': {'httpGet': {'path': '/health', 'port': 'http'}, 'periodSeconds': 30, 'failureThreshold': 5, 'timeoutSeconds': 10}
    }
    pod = {'automountServiceAccountToken': False, 'nodeSelector': {'kubernetes.io/hostname': site['gpu_node']},
           'securityContext': {'runAsNonRoot': True, 'runAsUser': 10001, 'runAsGroup': 10001, 'fsGroup': 10001, 'seccompProfile': {'type': 'RuntimeDefault'}},
           'terminationGracePeriodSeconds': 120, 'containers': [container],
           'initContainers': [{'name': 'verify-model', 'image': image, 'command': ['python3', '/verify/verify_model.py', '--root', '/model', '--inventory', '/verify/model-files.json'], 'securityContext': security, 'resources': {'requests': {'cpu':'1','memory':'256Mi'}, 'limits': {'cpu':'2','memory':'1Gi'}}, 'volumeMounts': [{'name':'model','mountPath':'/model','readOnly':True},{'name':'verify','mountPath':'/verify','readOnly':True}]}],
           'volumes': [{'name':'model','persistentVolumeClaim':{'claimName':site['model_pvc'],'readOnly':True}}, {'name':'tmp','emptyDir':{'sizeLimit':'16Gi'}}, {'name':'shm','emptyDir':{'medium':'Memory','sizeLimit':'8Gi'}}, {'name':'verify','configMap':{'name':'model-verification'}}]}
    # Monitoring gets its own HTTP path allowlist; never open inference to scrapers.
    pod['containers'].append({
        'name': 'metrics-proxy', 'image': image,
        'command': ['python3', '/verify/metrics_proxy.py'],
        'ports': [{'name': 'metrics', 'containerPort': 30001}],
        'securityContext': security,
        'resources': {'requests': {'cpu': '50m', 'memory': '32Mi'},
                      'limits': {'cpu': '200m', 'memory': '128Mi'}},
        'volumeMounts': [{'name': 'verify', 'mountPath': '/verify', 'readOnly': True}],
        'readinessProbe': {'tcpSocket': {'port': 'metrics'}, 'periodSeconds': 10},
    })
    namespace = obj('Namespace', ns)
    namespace['metadata']['labels'] = {'pod-security.kubernetes.io/enforce':'restricted', 'pod-security.kubernetes.io/enforce-version':site['pod_security_version']}
    deployment = obj('Deployment','sglang',ns,{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':labels},'template':{'metadata':{'labels':labels,'annotations':release_annotations(site, inventory)},'spec':pod}},api='apps/v1')
    service = obj('Service','sglang',ns,{'type':'ClusterIP','selector':labels,'ports':[{'name':'http','port':30000,'targetPort':'http'}, {'name':'metrics','port':30001,'targetPort':'metrics'}]})
    deny = obj('NetworkPolicy','default-deny',ns,{'podSelector':{},'policyTypes':['Ingress','Egress']},api='networking.k8s.io/v1')
    allow = obj('NetworkPolicy','sglang-clients',ns,{'podSelector':{'matchLabels':labels},'policyTypes':['Ingress'],'ingress':[{'from':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'observability'}},'podSelector':{'matchLabels':{'acmecorp.metrics-client':'true'}}}],'ports':[{'protocol':'TCP','port':30001}]}]},api='networking.k8s.io/v1')
    # No pod egress: model is pre-staged. Kubelet probes/port-forward do not rely on ordinary client pod ingress.
    return [namespace, obj('ConfigMap','model-verification',ns,data={'model-files.json':inventory_text,'verify_model.py':verify,'metrics_proxy.py':proxy}), deny, allow, service, deployment]


def elemental(config):
    """Generate management resources; applying then booting media can erase disks."""
    cluster = name(config['cluster_name'])
    ns = name(config['management_namespace'])
    image = immutable(config['seed_image'])
    require(config.get('compatibility_evidence'), 'Rancher/Elemental/RKE2/OS support evidence required')
    require(re.fullmatch(r'v\d+\.\d+\.\d+\+rke2r\d+', config['rke2_version']), 'Stable RKE2 version required')
    key = config.get('ssh_public_key')
    require(isinstance(key,str) and key.startswith(('ssh-ed25519 ', 'ssh-rsa ', 'ecdsa-sha2-')), 'Operator SSH public key required; never provide a private key')
    pools = config['pools']
    require({p['name'] for p in pools} == {'server','gpu'} and len(pools)==2, 'Exactly server and gpu pools required')
    resources, machine_pools = [], []
    for pool in pools:
        role = pool['name']
        device = pool.get('install_device')
        require(isinstance(device,str) and device.startswith('/dev/disk/by-id/') and '..' not in device, 'Verified persistent install disk by-id is required per pool')
        require(pool['quantity'] == 1, 'Baseline requires one host per registration; extend per-host disk mapping for HA')
        if role == 'server':
            require(pool['quantity'] in (1,3,5), 'Use one demo server or an odd HA server count')
        registration = f'{cluster}-{role}'
        selectors = {'acmecorp-cluster':cluster,'acmecorp-role':role}
        resources.append(obj('MachineRegistration',registration,ns,{'config':{'cloud-config':{'users':[{'name':'root','ssh_authorized_keys':[key]}]},'elemental':{'install':{'device':device,'reboot':True,'debug':False}}},'machineInventoryLabels':selectors},api='elemental.cattle.io/v1beta1'))
        resources.append(obj('SeedImage',registration,ns,{'baseImage':image,'type':'iso','targetPlatform':'linux/x86_64','cleanupAfterMinutes':60,'registrationRef':{'apiVersion':'elemental.cattle.io/v1beta1','kind':'MachineRegistration','name':registration,'namespace':ns}},api='elemental.cattle.io/v1beta1'))
        resources.append(obj('MachineInventorySelectorTemplate',registration,ns,{'template':{'spec':{'selector':{'matchLabels':selectors}}}},api='elemental.cattle.io/v1beta1'))
        machine_pools.append({'name':role,'quantity':pool['quantity'],'controlPlaneRole':role=='server','etcdRole':role=='server','workerRole':role=='gpu','machineConfigRef':{'apiVersion':'elemental.cattle.io/v1beta1','kind':'MachineInventorySelectorTemplate','name':registration},'unhealthyNodeTimeout':'0s'})
    resources.append(obj('Cluster',cluster,ns,{'kubernetesVersion':config['rke2_version'],'rkeConfig':{'machinePools':machine_pools,'machineGlobalConfig':{'cni':'canal','disable':['rke2-ingress-nginx','rke2-traefik'],'write-kubeconfig-mode':'0600','etcd-snapshot-schedule-cron':'0 */6 * * *','etcd-snapshot-retention':5}}},api='provisioning.cattle.io/v1'))
    return resources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['workload','elemental'])
    parser.add_argument('--config',type=Path)
    parser.add_argument('--inventory',type=Path,default=ROOT/'config/model-files.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    config=args.config or ROOT/'config'/('site.json' if args.mode=='workload' else 'elemental.json')
    try:
        data=json.loads(config.read_text(encoding='utf-8'))
        items=workload(data,json.loads(args.inventory.read_text(encoding='utf-8'))) if args.mode=='workload' else elemental(data)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump({'apiVersion':'v1','kind':'List','items':items},stream,indent=2)
        print(f'Rendered {len(items)} objects; no cluster contacted')
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(2,f'Render blocked: {error}\n')


if __name__=='__main__':
    main()
