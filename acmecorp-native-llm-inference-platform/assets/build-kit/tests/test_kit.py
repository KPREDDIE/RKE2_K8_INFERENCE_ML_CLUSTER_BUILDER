"""Offline regression checks. Synthetic fixtures are not deployment evidence."""
import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import render
import smoke
import verify_model
import runtime_inventory
import subprocess
from types import SimpleNamespace

HASH=hashlib.sha256(b'test fixture only').hexdigest()


def site_fixture():
    data=json.loads((ROOT/'config/site.json').read_text())
    data.update(runtime_image='example.invalid/sglang@sha256:'+HASH,gpu_node='test-gpu',compatibility_evidence='test fixture, not live evidence')
    return data


def inventory_fixture():
    data=json.loads((ROOT/'config/model-files.json').read_text())
    data['files']={'config.json':HASH,'tokenizer.json':HASH,'model.safetensors':HASH}
    return data


class RenderTests(unittest.TestCase):
    def test_unresolved_images_block_render(self):
        site=site_fixture();site['runtime_image']=None
        with self.assertRaises(ValueError):render.workload(site,inventory_fixture())

    def test_model_identity_and_paths_fail_closed(self):
        for change in ({'revision':'main'},{'files':{'../escape':HASH}}):
            data=inventory_fixture();data.update(change)
            with self.assertRaises(ValueError):render.workload(site_fixture(),data)

    def test_runtime_has_no_download_or_public_service(self):
        items=render.workload(site_fixture(),inventory_fixture())
        service=next(i for i in items if i['kind']=='Service')
        self.assertEqual(service['spec']['type'],'ClusterIP')
        deploy=next(i for i in items if i['kind']=='Deployment')
        pod=deploy['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['initContainers'][0]['name'],'verify-model')
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertEqual(pod['containers'][0]['resources']['limits']['nvidia.com/gpu'],'1')
        self.assertEqual(deploy['spec']['selector']['matchLabels'],service['spec']['selector'])
        self.assertEqual(deploy['spec']['strategy']['type'],'Recreate')
        deny=next(i for i in items if i['metadata']['name']=='default-deny')
        self.assertEqual(deny['spec']['policyTypes'],['Ingress','Egress'])
        self.assertNotIn('egress',deny['spec'])

    def test_elemental_no_unsafe_disk_default(self):
        config=json.loads((ROOT/'config/elemental.json').read_text())
        config.update(seed_image='example.invalid/seed@sha256:'+HASH,compatibility_evidence='fixture',ssh_public_key='ssh-ed25519 TEST_PUBLIC_KEY')
        with self.assertRaises(ValueError):render.elemental(config)
        for pool in config['pools']:pool['install_device']='/dev/disk/by-id/test-'+pool['name']
        items=render.elemental(config)
        selectors=[i['spec']['template']['spec']['selector']['matchLabels'] for i in items if i['kind']=='MachineInventorySelectorTemplate']
        self.assertEqual(len(selectors),2)
        self.assertNotEqual(selectors[0],selectors[1])
        cluster=next(i for i in items if i['kind']=='Cluster')
        roles=cluster['spec']['rkeConfig']['machinePools']
        self.assertFalse(roles[0]['workerRole'])
        self.assertTrue(roles[1]['workerRole'])
        self.assertFalse(roles[1]['etcdRole'])
        for resource in items:
            self.assertEqual(resource['metadata']['namespace'],'fleet-default')


class ModelTests(unittest.TestCase):
    def test_content_and_extra_file_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'weights').write_bytes(b'abc')
            inv={'files':{'weights':hashlib.sha256(b'abc').hexdigest()}}
            self.assertEqual(verify_model.verify(root,inv),1)
            (root/'weights').write_bytes(b'tampered')
            with self.assertRaises(ValueError):verify_model.verify(root,inv)
            (root/'weights').write_bytes(b'abc');(root/'extra').write_text('unexpected')
            with self.assertRaises(ValueError):verify_model.verify(root,inv)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):verify_model.verify(ROOT,{'files':{}})


class SmokeTests(unittest.TestCase):
    def test_empty_nodes_and_missing_readiness_do_not_pass(self):
        self.assertFalse(smoke.nodes_ok({'items':[]},2))
        self.assertFalse(smoke.nodes_ok({'items':[{'status':{}}]},1))
        self.assertFalse(smoke.pods_ok({'items':[]},'sha256:'+HASH))

    def test_endpoint_transport_boundary(self):
        for url in ('http://example.com','https://user:pass@example.com','https://example.com?token=x'):
            with self.assertRaises(ValueError):smoke.valid_endpoint(url)
        self.assertEqual(smoke.valid_endpoint('http://127.0.0.1:30000/'),'http://127.0.0.1:30000')
        with self.assertRaises(ValueError):smoke.NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_canary_requires_exact_finished_output(self):
        good={'model':'demo','choices':[{'message':{'content':'SMOKE_OK'},'finish_reason':'stop'}]}
        self.assertTrue(smoke.completion_ok(good,'demo'))
        for value in ('arbitrary',''):
            bad=copy.deepcopy(good);bad['choices'][0]['message']['content']=value
            self.assertFalse(smoke.completion_ok(bad,'demo'))
        good['choices'][0]['finish_reason']='length'
        self.assertFalse(smoke.completion_ok(good,'demo'))

    def test_all_unavailable_produces_nonzero_content_free_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);site=temp/'site.json';output=temp/'report.json'
            site.write_text(json.dumps(site_fixture()))
            (temp/'model-files.json').write_text(json.dumps(inventory_fixture()))
            argv=['smoke.py','--context','test-only','--site',str(site),'--endpoint','http://127.0.0.1:30000','--output',str(output)]
            with patch.object(sys,'argv',argv),patch('subprocess.run',side_effect=RuntimeError('SECRET_FAILURE_BODY')),patch.object(smoke,'fetch',side_effect=RuntimeError('SECRET_FAILURE_BODY')),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(),1)
            report=json.loads(output.read_text())
            self.assertEqual(report['failed_checks'],8)
            self.assertNotIn('SECRET_FAILURE_BODY',output.read_text())
            self.assertFalse(report['content_stored'])


    def test_success_path_with_fake_cluster_and_http(self):
        ready_node={'status':{'conditions':[{'type':'Ready','status':'True'}],'allocatable':{'nvidia.com/gpu':'1'}}}
        pod=copy.deepcopy(ready_node)
        pod['metadata']={'annotations':render.release_annotations(site_fixture(),inventory_fixture())}
        pod['spec']={'nodeName':site_fixture()['gpu_node'],'volumes':[{'name':'model','persistentVolumeClaim':{'claimName':site_fixture()['model_pvc']}}]}
        pod['status']['initContainerStatuses']=[{'name':'verify-model','imageID':'containerd://sha256:'+HASH,'state':{'terminated':{'exitCode':0}}}]
        pod['status']['containerStatuses']=[{'ready':True,'imageID':'containerd://sha256:'+HASH}]
        responses=[{'items':[ready_node,ready_node]},ready_node,{'items':[pod]},
            {'metadata':{'generation':2},'spec':{'replicas':1,'template':{'metadata':{'annotations':render.release_annotations(site_fixture(),inventory_fixture())}}},'status':{'observedGeneration':2,'updatedReplicas':1,'availableReplicas':1}}]
        alias=site_fixture()['model_alias']
        def http(url,headers,payload,deadline):
            if url.endswith('/models'):
                return json.dumps({'data':[{'id':alias}]}).encode()
            if url.endswith('/metrics'):
                return b'sglang:num_running_reqs 0\n'
            if payload.get('stream'):
                event={'model':alias,'choices':[{'delta':{'content':'SMOKE_OK'},'finish_reason':'stop'}]}
                return ('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode()
            return json.dumps({'model':alias,'choices':[{'message':{'content':'SMOKE_OK'},'finish_reason':'stop'}]}).encode()
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);site=temp/'site.json';output=temp/'report.json'
            site.write_text(json.dumps(site_fixture()))
            (temp/'model-files.json').write_text(json.dumps(inventory_fixture()))
            argv=['smoke.py','--context','test-only','--site',str(site),'--endpoint','http://127.0.0.1:30000','--output',str(output)]
            fake=[subprocess.CompletedProcess([],0,json.dumps(r),'') for r in responses]
            with patch.object(sys,'argv',argv),patch('subprocess.run',side_effect=fake) as commands,patch.object(smoke,'fetch',side_effect=http),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(),0)
                self.assertTrue(all('get' in call.args[0] and '--context' in call.args[0] for call in commands.call_args_list))
            report=json.loads(output.read_text())
            self.assertEqual(report['failed_checks'],0)
            self.assertNotIn('SMOKE_OK',output.read_text())
            # Same runtime and alias, but an undeployed model revision must fail.
            stale=site_fixture();stale['model_revision']='f'*40
            site.write_text(json.dumps(stale))
            inv=inventory_fixture();inv['revision']=stale['model_revision']
            (temp/'model-files.json').write_text(json.dumps(inv))
            argv[-1]=str(temp/'stale-report.json')
            fake=[subprocess.CompletedProcess([],0,json.dumps(r),'') for r in responses]
            with patch.object(sys,'argv',argv),patch('subprocess.run',side_effect=fake),patch.object(smoke,'fetch',side_effect=http),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(),1)
            stale_report=json.loads((temp/'stale-report.json').read_text())
            self.assertEqual(stale_report['failed_checks'],2)


class InventoryTests(unittest.TestCase):
    def fixture(self,image_id):
        return {'items':[{'metadata':{'namespace':'demo','name':'pod'},'spec':{'containers':[{'name':'app'}]},'status':{'containerStatuses':[{'name':'app','image':'example.invalid/model:v1','imageID':image_id}]}}]}

    def test_non_digest_and_incomplete_inventory_fail(self):
        for value in ('','containerd://mutable-tag'):
            with self.assertRaises(ValueError):runtime_inventory.collect(self.fixture(value),'demo')
        with self.assertRaises(ValueError):runtime_inventory.collect({'items':[]},'demo')
        data=self.fixture('containerd://sha256:'+HASH);data['items'][0]['status']['containerStatuses']=[]
        with self.assertRaises(ValueError):runtime_inventory.collect(data,'demo')

    def test_duplicate_digest_preserves_all_uses(self):
        data=self.fixture('containerd://sha256:'+HASH)
        other=copy.deepcopy(data['items'][0]);other['metadata']['name']='pod-two';data['items'].append(other)
        result=runtime_inventory.collect(data,'demo')
        self.assertEqual(len(result['images']),1)
        self.assertEqual(len(result['images'][0]['uses']),2)


if __name__=='__main__':unittest.main()
