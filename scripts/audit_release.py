#!/usr/bin/env python3
"""Check public payload boundaries, local documentation links and optional hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'README.md', 'README.fa.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'CHANGELOG.md', 'AGENTS.md', 'pyproject.toml', 'requirements.txt', '.gitignore',
    '.gitattributes', '.editorconfig'}
PUBLIC_DIRS = {'skills', 'docs', 'tests', 'scripts', 'examples', '.github', 'qa'}
IGNORED_TOP = {'local-data', 'private', 'build', 'dist', '.git', '.venv', 'venv', '.pytest_cache'}
ALLOWED_SUFFIXES = {'.py', '.md', '.txt', '.json', '.jsonl', '.toml', '.yml', '.yaml'}


def public_files(root=ROOT):
    result = []
    for entry in root.iterdir():
        if entry.name == 'RELEASE_MANIFEST.json' or entry.name in IGNORED_TOP or entry.name.endswith('.egg-info'):
            continue
        if entry.is_symlink():
            raise ValueError('Symlink not allowed in release payload: ' + entry.name)
        if entry.is_file():
            if entry.name not in TOP_FILES:
                raise ValueError('Unclassified top-level payload file: ' + entry.name)
            result.append(entry)
        elif entry.name in PUBLIC_DIRS:
            for file in entry.rglob('*'):
                if '__pycache__' in file.parts or any(part.endswith('.egg-info') for part in file.parts) or file.suffix in ('.pyc', '.pyo'):
                    continue
                if file.is_symlink():
                    raise ValueError('Symlink in public tree')
                if not file.is_file():
                    continue
                if 'source_archive' in file.parts or 'local-data' in file.parts:
                    raise ValueError('Private reference directory inside public tree')
                if file.suffix not in ALLOWED_SUFFIXES:
                    raise ValueError('Unclassified public file: ' + file.relative_to(root).as_posix())
                result.append(file)
        else:
            raise ValueError('Unclassified top-level directory: ' + entry.name)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())


def audit(root=ROOT, verify_manifest=True):
    files = public_files(root)
    names = {p.relative_to(root).as_posix() for p in files}
    required = TOP_FILES | {'skills/scf-mapping-translation/SKILL.md',
                           'skills/scf-mapping-translation/scripts/run.py', '.github/workflows/ci.yml',
                           'qa/release-validation.json', 'docs/QA.md'}
    missing = sorted(required - names)
    if missing:
        raise ValueError('Missing release files: ' + ', '.join(missing))
    prohibited = [re.compile(r'(?i)\b[A-Z]:[\\/]Users[\\/]'),
                  re.compile(r'account_id' + r'=personal'), re.compile(r'file_id' + r'=libfile_'),
                  re.compile(r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}'),
                  re.compile(r'\bsk-[A-Za-z0-9_-]{25,}')]
    links_checked = 0
    for file in files:
        body = file.read_text(encoding='utf-8')
        for pattern in prohibited:
            if pattern.search(body):
                raise ValueError('Personal path/account/secret-like content: ' + file.relative_to(root).as_posix())
        if file.suffix == '.md':
            prose = re.sub(r'(?ms)^(\x60{3,}|~{3,}).*?^\1\s*$', '', body)
            for destination in re.findall(r'\[[^\]]*\]\(([^)\n]+)\)', prose):
                target = destination.strip().strip('<>')
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                linked = (file.parent / unquote(parsed.path)).resolve()
                if not linked.is_relative_to(root.resolve()) or not linked.exists():
                    raise ValueError('Broken/escaping documentation link: ' + file.name + ' -> ' + target)
                links_checked += 1
    license_text = (root / 'LICENSE').read_text(encoding='utf-8').lower()
    if 'all rights reserved' not in license_text or 'no open-source license' not in license_text:
        raise ValueError('Rights-reserved license decision missing')
    skill = (root / 'skills/scf-mapping-translation/SKILL.md').read_text(encoding='utf-8')
    if not skill.startswith('---\n') or not re.search(r'^name: scf-mapping-translation$', skill, re.M) or not re.search(r'^description: .+', skill, re.M):
        raise ValueError('Skill frontmatter missing')
    fixture = json.loads((root / 'examples/synthetic/catalog.json').read_text(encoding='utf-8'))
    if fixture.get('source', {}).get('synthetic') is not True or not all(c['id'].startswith('TST-') for c in fixture['controls']):
        raise ValueError('Public catalog is not explicitly synthetic')
    verified_hashes = 0
    manifest_path = root / 'RELEASE_MANIFEST.json'
    if verify_manifest and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if set(manifest['files']) != names:
            raise ValueError('Manifest payload file set differs')
        for rel, expected in manifest['files'].items():
            raw = (root / rel).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected['sha256'] or len(raw) != expected['bytes']:
                raise ValueError('Manifest hash mismatch: ' + rel)
            verified_hashes += 1
    return {'status': 'PUBLIC_PAYLOAD_CHECKED', 'payload_files': len(files), 'local_document_links_checked': links_checked,
            'verified_manifest_hashes': verified_hashes, 'full_reference_data_included': False,
            'code_license': 'All rights reserved', 'scope': 'Focused publication checks; not a comprehensive secret/security audit'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-manifest', action='store_true')
    args = parser.parse_args()
    try:
        result = audit(verify_manifest=not args.no_manifest)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'RELEASE_BLOCKED', 'error': str(error)}, ensure_ascii=False))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
