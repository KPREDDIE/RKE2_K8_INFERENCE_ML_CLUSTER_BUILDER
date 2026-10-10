"""Verify every model file against a reviewed SHA-256 inventory; never download code."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(root, inventory):
    """Reject missing, extra, linked or changed files before loading model weights.

    The operator must obtain the inventory independently; hashing an unknown local
    snapshot and approving its own hashes would not establish provenance.
    """
    root=Path(root).resolve()
    files=inventory.get('files',{})
    if not files:
        raise ValueError('Empty model inventory')
    observed={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if observed != set(files):
        raise ValueError('Model file set differs from approved inventory')
    for relative, expected in files.items():
        path=PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative:
            raise ValueError('Unsafe inventory path')
        target=root.joinpath(*path.parts)
        if target.is_symlink() or root not in target.resolve().parents:
            raise ValueError('Model symlinks or path escape refused')
        digest=hashlib.sha256()
        with target.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024*1024),b''):
                digest.update(block)
        if digest.hexdigest()!=expected:
            raise ValueError('Model checksum mismatch')
    return len(files)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--inventory',required=True,type=Path)
    args=parser.parse_args()
    try:
        count=verify(args.root,json.loads(args.inventory.read_text(encoding='utf-8')))
        print(f'Verified {count} files')
    except (ValueError,OSError) as error:
        parser.exit(1,f'Verification failed: {error}\n')
