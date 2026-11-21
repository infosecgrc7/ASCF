#!/usr/bin/env python3
"""Build a deterministic source ZIP from the audited public payload only."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from audit_release import ROOT, audit, public_files


def build(destination):
    destination = Path(destination).resolve()
    if destination.suffix.lower() != '.zip':
        raise ValueError('Release destination must be a .zip file')
    if destination.is_relative_to(ROOT) and destination.relative_to(ROOT).parts[0] not in ('local-data', 'dist'):
        raise ValueError('Place generated archives outside the public source tree or in local-data/dist')
    audit(ROOT, verify_manifest=False)
    files = public_files(ROOT)
    manifest = {'version': '1.0.0', 'release_date': '2026-11-21', 'hash_algorithm': 'SHA-256',
        'note': 'Hashes cover every public payload file except this manifest itself.', 'files': {}}
    for file in files:
        raw = file.read_bytes()
        manifest['files'][file.relative_to(ROOT).as_posix()] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    manifest_path = ROOT / 'RELEASE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    audit(ROOT, verify_manifest=True)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in files + [manifest_path]:
            rel = 'scf-mapping-toolkit/' + file.relative_to(ROOT).as_posix()
            entry = zipfile.ZipInfo(rel, (2026, 11, 21, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, file.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or len(set(archive.namelist())) != len(archive.namelist()):
            raise ValueError('ZIP integrity failed')
        for name in archive.namelist():
            p = Path(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('Unsafe ZIP member')
    return {'status': 'RELEASE_ZIP_VERIFIED', 'filename': destination.name, 'bytes': destination.stat().st_size,
            'files': len(files) + 1, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.out), indent=2))
