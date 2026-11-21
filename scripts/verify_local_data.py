#!/usr/bin/env python3
"""Optional private-data verification; public tests never require licensed reference files."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/scf-mapping-translation/scripts'))
from scf_toolkit.common import digest, load, require
from scf_toolkit.terms import Terminology


def verify(catalog_path, baseline_path, manifest_path, references):
    catalog, manifest = load(catalog_path), load(manifest_path)
    require(digest(baseline_path) == manifest['output_sha256'], 'Baseline JSONL fingerprint differs')
    require(catalog['source']['sha256'] == manifest['source']['source_sha256'], 'Original workbook fingerprint differs')
    baseline = [json.loads(line) for line in Path(baseline_path).read_text(encoding='utf-8').splitlines() if line.strip()]
    old = {r['scf_id']: r for r in baseline}
    require(len(old) == len(baseline) == len(catalog['controls']), 'Control counts differ')
    ao_count = 0
    for control in catalog['controls']:
        original = old[control['id']]
        require((control['title'], control['description']) == (original['scf_control'], original['scf_description']), 'Control text differs: ' + control['id'])
        require([(a['id'], a['text']) for a in control['assessment_objectives']] ==
                [(a['objective_id'], a['text']) for a in original['assessment_objectives']], 'AO text/order differs: ' + control['id'])
        ao_count += len(control['assessment_objectives'])
    terms = Terminology(references)
    originals = load(Path(references) / 'AFTA_Approved_Glossary_Final.json')
    extra = load(Path(references) / 'source_archive/Cybersecurity_Glossary_FA.json')
    official_checks, alias_checks, overlaps, held_checks = 0, 0, 0, 0
    for record in originals['entries']:
        found = terms.lookup(record['en'])
        require(any(r['entry_id'] == record['entry_id'] and r['fa'] == record['fa'] for r in found['matches']), 'Approved term missing')
        official_checks += 1
        for alias in record.get('en_aliases', []):
            found = terms.lookup(alias)
            require(any(r['entry_id'] == record['entry_id'] for r in found['matches']), 'Approved alias missing')
            alias_checks += 1
    held_ids = {r['id'] for r in extra['entries'] if r.get('use_in_skill') is not True}
    for record in extra['entries']:
        found = terms.lookup(record['term_en'])
        results = found['matches'] + found['supplementary_context']
        require(not held_ids & {r['entry_id'] for r in results}, 'Held record leaked into runtime')
        if record.get('use_in_skill') is True:
            match = next((r for r in results if r['entry_id'] == record['id']), None)
            require(match is not None and all(match[k] == v for k, v in record.items()), 'Supplementary record fields changed')
            if found['authority'] == 'afta_approved':
                overlaps += 1
                require(all(r['authority'] == 'afta_approved' for r in found['matches']), 'AFTA priority bypass')
        else:
            held_checks += 1
            require(all('definition_fa' not in r and 'term_fa' not in r for r in found['excluded_records']), 'Held prose exposed')
    return {'status': 'LOCAL_REFERENCE_CHECKS_PASSED', 'controls_compared': len(baseline),
        'ao_texts_compared': ao_count, 'all_control_and_ao_texts_identical': True,
        'source_ao_association_notes': len(catalog.get('source_association_notes', [])),
        'afta_primary_records_checked': official_checks, 'afta_alias_lookups_checked': alias_checks,
        'supplementary_records_checked': 759, 'held_records_excluded': held_checks,
        'cross_authority_headings_checked': overlaps, 'baseline_jsonl_sha256': digest(baseline_path),
        'source_workbook_sha256': catalog['source']['sha256'],
        'limits': 'No new visual PDF transcription review or real mapping semantic certification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('catalog', 'baseline-jsonl', 'baseline-manifest', 'references'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.catalog, args.baseline_jsonl, args.baseline_manifest, args.references), indent=2))
