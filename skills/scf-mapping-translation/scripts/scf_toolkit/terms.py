"""AFTA-first terminology; supplementary inclusion is strict boolean True."""
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
from .common import DataError, digest, key, load, require, unique, write_json


def blocks(markdown):
    result = {}
    for part in re.split(r'(?=<a id="csg-\d+-\d+"></a>)', markdown):
        match = re.match(r'<a id="(csg-\d+-\d+)"></a>', part)
        if match:
            identity = match[1].upper()
            require(identity not in result, 'Duplicate Markdown anchor')
            result[identity] = part
    return result


def import_glossaries(afta_path, supplementary_path, markdown_path, destination):
    afta, source = load(afta_path), load(supplementary_path)
    require(isinstance(afta.get('entries'), list) and afta['entries'], 'AFTA entries missing')
    unique([r['entry_id'] for r in afta['entries']], 'AFTA IDs')
    unique([r['id'] for r in source['entries']], 'supplementary IDs')
    allowed = [r for r in source['entries'] if r.get('use_in_skill') is True]
    held = [r for r in source['entries'] if r.get('use_in_skill') is not True]
    require([r['id'] for r in allowed] == source.get('operational_entry_ids'), 'Boolean filter differs from operational allowlist/order')
    counts = source.get('counts', {})
    require(counts.get('entries_total') == len(source['entries']) and counts.get('entries_usable') == len(allowed)
            and counts.get('entries_held') == len(held), 'Source count inconsistency')
    require(len(source['entries']) == 802 and len(allowed) == 759 and len(held) == 43,
            'This importer pins the supplied 802/759/43 supplementary release; review other releases explicitly')
    require(all(r.get('status') == 'usable' and r.get('term_fa') and r.get('definition_fa') and r.get('source_location')
                and r.get('term_fa_evidence') and 1 <= r['page'] <= r['page_end'] <= source['source']['page_count']
                for r in allowed), 'Usable record lacks definition/equivalent/provenance')
    raw_md = Path(markdown_path).read_text(encoding='utf-8-sig')
    sections = blocks(raw_md)
    require(set(sections) == {r['id'] for r in source['entries']}, 'Markdown/JSON entry IDs differ')
    for record in source['entries']:
        block = sections[record['id']]
        heading = re.search(r'^### (.+)$', block, re.M)
        paragraphs = [html.unescape(re.sub(r'<[^>]+>', '', p)) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', block, re.S)]
        require(heading and html.unescape(heading[1]) == record['term_en'] and record['definition_fa'] in paragraphs,
                'Markdown definition/heading mismatch: ' + record['id'])
        equivalents = [record['term_fa']] + record.get('alternates_fa', []) if record.get('term_fa') else []
        require(not equivalents or any(p.endswith(' — ' + ' / '.join(equivalents)) for p in paragraphs),
                'Markdown equivalent mismatch: ' + record['id'])
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / 'source_archive'
    archive.mkdir(exist_ok=True)
    frozen = {'AFTA_Approved_Glossary_Final.json': afta_path,
              'source_archive/Cybersecurity_Glossary_FA.json': supplementary_path,
              'source_archive/Cybersecurity_Glossary_FA.md': markdown_path}
    for rel, original in frozen.items():
        target = dest / rel
        if target.exists():
            require(digest(target) == digest(original), 'Refusing to overwrite a different frozen reference: ' + rel)
        else:
            shutil.copyfile(original, target)
    active = {'source': source['source'], 'resource_role': 'supplementary',
              'operational_entry_ids': source['operational_entry_ids'], 'entries': allowed}
    write_json(dest / 'supplementary_operational.json', active)
    operational_md = '# Supplementary operational reference — 759 eligible records only\n\nAFTA retains authority for matching term and sense.\n\n'
    (dest / 'supplementary_operational.md').write_text(operational_md + ''.join(sections[r['id']] for r in allowed), encoding='utf-8')
    exclusions = [{k: r[k] for k in ('id', 'term_en', 'page', 'page_end', 'status')} for r in held]
    write_json(dest / 'excluded.json', {'entries': exclusions, 'role': 'exclusion_metadata_only'})
    paths = list(frozen) + ['supplementary_operational.json', 'supplementary_operational.md', 'excluded.json']
    manifest = {'schema_version': '1.0', 'counts': {'afta': len(afta['entries']), 'supplementary': len(allowed), 'held': len(held)},
        'files': {rel: {'sha256': digest(dest / rel), 'bytes': (dest / rel).stat().st_size} for rel in paths},
        'note': 'Full uploaded sources are audit-only and are not a fallback for held records.'}
    write_json(dest / 'manifest.json', manifest)
    return manifest


class Terminology:
    def __init__(self, directory):
        directory = Path(directory)
        manifest = load(directory / 'manifest.json')
        required = {'AFTA_Approved_Glossary_Final.json', 'supplementary_operational.json', 'excluded.json',
                    'source_archive/Cybersecurity_Glossary_FA.json', 'source_archive/Cybersecurity_Glossary_FA.md',
                    'supplementary_operational.md'}
        require(set(manifest.get('files', {})) == required, 'Reference manifest file set differs from schema')
        for rel, proof in manifest['files'].items():
            file = directory / rel
            require(digest(file) == proof['sha256'] and file.stat().st_size == proof['bytes'], 'Reference checksum mismatch: ' + rel)
        afta, active, excluded = (load(directory / p) for p in
            ('AFTA_Approved_Glossary_Final.json', 'supplementary_operational.json', 'excluded.json'))
        source = load(directory / 'source_archive/Cybersecurity_Glossary_FA.json')
        allowed = [r for r in source['entries'] if r.get('use_in_skill') is True]
        require(active['entries'] == allowed and active['operational_entry_ids'] == [r['id'] for r in allowed]
                and len(allowed) == 759 and len(excluded['entries']) == 43, 'Active/held filter invariant failed')
        held_ids = {r['id'] for r in excluded['entries']}
        require(not held_ids & {r['id'] for r in allowed}, 'Held ID found in operational data')
        require(active['source'] == source['source'], 'Supplementary source metadata changed')
        self.official, self.extra, self.excluded = defaultdict(list), defaultdict(list), defaultdict(list)
        self.by_id = {}
        for r in afta['entries']:
            for rank, term in [(0, r['en'])] + [(1, alias) for alias in r.get('en_aliases', [])]:
                result = dict(r, authority='afta_approved', match_type='primary' if rank == 0 else 'alias',
                              source_file='AFTA_Approved_Glossary_Final.json', source=afta['source'])
                if not any(m['entry_id'] == r['entry_id'] for m in self.official[key(term)]):
                    self.official[key(term)].append(result)
                self.by_id[r['entry_id']] = result
        for r in allowed:
            result = dict(r, entry_id=r['id'], en=r['term_en'], fa=r['term_fa'], source_page=r['page'],
                authority='supplementary', match_type='primary', source_file='supplementary_operational.json', source=active['source'])
            self.extra[key(r['term_en'])].append(result)
            self.by_id[r['id']] = result
        for r in excluded['entries']:
            self.excluded[key(r['term_en'])].append(r)
        self.counts = manifest['counts']

    def lookup(self, term):
        normalized = key(term)
        official = sorted(self.official.get(normalized, []), key=lambda r: (r['match_type'] != 'primary', r['source_page'], r['entry_id']))
        extra = self.extra.get(normalized, [])
        held = self.excluded.get(normalized, [])
        matches = official or extra
        return {'query': term, 'status': 'FOUND' if matches else ('EXCLUDED_REFERENCE' if held else 'NOT_FOUND'),
            'authority': matches[0]['authority'] if matches else None, 'matches': matches,
            'supplementary_context': extra if official else [], 'excluded_records': held,
            'decision': 'NEEDS_CONTEXT' if len({r['fa'] for r in matches}) > 1 else ('CANDIDATE_REQUIRES_CONTEXT' if matches else 'NO_ELIGIBLE_MATCH'),
            'context_review_required': bool(matches), 'auto_translation': False}

    def scan(self, value):
        normalized = key(value)
        spans = []
        for phrase in set(self.official) | set(self.extra) | set(self.excluded):
            spans += [(m.start(), m.end(), phrase) for m in re.finditer(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', normalized)]
        selected = []
        for start, end, phrase in sorted(spans, key=lambda x: (-(x[1]-x[0]), x[0], x[2])):
            if not any(start < e and end > s for s, e, _ in selected):
                selected.append((start, end, phrase))
        return {'mode': 'phrase_candidates_only', 'auto_translation': False,
                'candidates': [self.lookup(phrase) for _, _, phrase in sorted(selected)]}
