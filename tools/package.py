"""Build deterministic skill and source ZIPs from this distribution; excludes local evidence/secrets."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAME='acmecorp-native-llm-inference-platform'
EXCLUDED={'__pycache__','.git','generated','evidence','release','.env','.env.local'}


def selected(directory):
    result=[]
    for path in sorted(directory.rglob('*')):
        relative=path.relative_to(directory)
        if any(part in EXCLUDED for part in relative.parts):continue
        if path.is_symlink():raise ValueError('Symlink refused in release source')
        if path.is_file() and path.suffix not in ('.pyc','.token','.kubeconfig','.iso','.raw'):
            result.append(path)
    return result


def archive(path,members,prefix):
    checksums=''.join(f'{hashlib.sha256(content).hexdigest()}  {name}\n' for name,content in sorted(members.items()))
    members=dict(members)
    members[prefix+'/CHECKSUMS.txt']=checksums.encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for name,content in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,5,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            output.writestr(info,content,compresslevel=9)
    with zipfile.ZipFile(path) as check:
        if check.testzip() is not None:raise ValueError('Archive CRC failure')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'release')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    skill={NAME+'/'+p.relative_to(ROOT/NAME).as_posix():p.read_bytes() for p in selected(ROOT/NAME)}
    skill_file=args.output/(NAME+'.skill')
    archive(skill_file,skill,NAME)
    prefix='acmecorp-llm-demonstrator'
    members={prefix+'/'+name:data for name,data in skill.items()}
    for file in ('README.md','VALIDATION.md','INPUTS.json','buildspec.json','.gitignore'):
        members[prefix+'/'+file]=(ROOT/file).read_bytes()
    for file in selected(ROOT/'tools'):
        members[prefix+'/tools/'+file.relative_to(ROOT/'tools').as_posix()]=file.read_bytes()
    bundle=args.output/'acmecorp-llm-demonstrator.zip'
    archive(bundle,members,prefix)
    checksum=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in (skill_file,bundle))
    (args.output/'CHECKSUMS.txt').write_text(checksum,encoding='utf-8',newline='\n')
    print(checksum,end='')


if __name__=='__main__':main()
