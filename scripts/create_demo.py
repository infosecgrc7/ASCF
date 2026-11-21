"""Deterministic synthetic examples. These are not official SCF or regulatory records."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/scf-mapping-translation/scripts'))
from scf_toolkit.common import digest, write_json


def approved():
    return {'status': 'APPROVED', 'method': 'model', 'reviewer': 'synthetic-test-fixture',
            'reviewed_at': '2026-11-20T12:00:00Z', 'notes': 'Synthetic example only; not an actual semantic approval.'}


def generate(destination):
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    source = 'سازمان باید: رویدادهای امنیتی را ثبت کند؛ سوابق را برای ۹۰ روز نگهداری کند.'
    (dest / 'source.txt').write_text(source, encoding='utf-8')
    catalog = {'schema_version': '1.0', 'scf_version': '2026.2',
        'source': {'synthetic': True, 'filename': 'synthetic-fixture', 'sha256': hashlib.sha256(b'synthetic').hexdigest()},
        'controls': [
            {'id': 'TST-01', 'title': 'Synthetic Event Recording and Protection',
             'description': 'Record security events and protect their integrity.',
             'metadata': {'pptdf': 'Technology'}, 'assessment_objectives': [
                 {'id': 'TST-01_A01', 'text': 'security events are recorded.'},
                 {'id': 'TST-01_A02', 'text': 'event record integrity is protected.'}]},
            {'id': 'TST-02', 'title': 'Synthetic Monitoring', 'description': 'Analyze recorded security events.',
             'metadata': {'pptdf': 'Process'}, 'assessment_objectives': [
                 {'id': 'TST-02_A01', 'text': 'recorded events are analyzed.'}]},
            {'id': 'TST-03', 'title': 'Synthetic Physical Access', 'description': 'Restrict physical entry.',
             'metadata': {'pptdf': 'Facilities'}, 'assessment_objectives': [
                 {'id': 'TST-03_A01', 'text': 'physical entry is restricted.'}]}]}
    inventory = {'documents': [{'source_id': 'DEMO', 'title': 'آیین‌نامهٔ ساختگی برای آزمایش',
        'issuer': 'مرجع فرضی', 'version': '1.0', 'sha256': digest(dest / 'source.txt')}],
        'requirements': [{'source_id': 'DEMO', 'fde_id': '1', 'name': 'الزام نمونهٔ ساختگی',
            'text_exact': source, 'pages': [1], 'preamble_exact': 'سازمان باید:'}]}
    write_json(dest / 'catalog.json', catalog)
    write_json(dest / 'inventory.json', inventory)
    ids = ['DEMO::1::O01', 'DEMO::1::O02']
    texts = ['رویدادهای امنیتی را ثبت کند', 'سوابق را برای ۹۰ روز نگهداری کند.']
    obligations = []
    for oid, body in zip(ids, texts):
        obligations.append({'id': oid, 'source_id': 'DEMO', 'fde_id': '1', 'text_exact': body,
            'source_fragments': [body], 'description_mode': 'verbatim_excerpt', 'source_pages': [1],
            'testable_outcome': body, 'independent_pass_fail_test': 'One action can pass while the other fails.',
            'applicable_parent_context': 'سازمان باید:', 'five_tuple': {'actor': 'سازمان', 'action': body,
                'target_scope': 'رویدادهای امنیتی', 'frequency_trigger': '', 'jurisdiction_qualifier': ''},
            'source_review': approved()})
    mapping = {'obligation_id': ids[0], 'scf_id': 'TST-01', 'relationship': 'Subset Of', 'rationale': 'Functional',
        'score': 7, 'shared_mandatory_clause': 'Record security events', 'fde_only_clauses': '',
        'scf_only_clauses': 'Protect event record integrity', 'decision_reason': 'Synthetic containment example.',
        'falsification_check': {'counterexample_found': False, 'reason': 'Synthetic exercise compares recording outcomes.'},
        'semantic_review': approved(), 'score_review': approved(),
        'selection_review': {'scope': 'domain_specific', 'decision': 'Synthetic recording control is the direct match.',
            'selected_evidence': [{'ao_id': 'TST-01_A01', 'quote': 'security events are recorded.'}],
            'alternatives': [{'scf_id': 'TST-02', 'reason': 'Analysis of events differs from generating event records.'}]}}
    searches = []
    for oid in ids:
        searches.append({'obligation_id': oid, 'query': 'ثبت رویدادهای امنیتی' if oid == ids[0] else 'نگهداری ۹۰ روزهٔ سوابق',
            'search_scope': 'All three synthetic controls and all their AOs; not a real SCF search.',
            'candidates': [{'scf_id': c['id'], 'disposition': 'ACCEPTED' if oid == ids[0] and c['id'] == 'TST-01' else 'REJECTED',
                **({'score': 7} if oid == ids[0] and c['id'] == 'TST-01' else {}),
                'reason': 'Synthetic fixture decision; source concepts reviewed separately.'} for c in catalog['controls']],
            'review': approved()})
    ledger = {'schema_version': '1.0', 'metadata': {'scf_version': '2026.2',
        'catalog_sha256': digest(dest / 'catalog.json'), 'inventory_sha256': digest(dest / 'inventory.json'),
        'profile': {'equality_label': 'Equal', 'rationale': 'Functional',
            'methodology_url': 'https://securecontrolsframework.com/start-here/set-theory-relationship-mapping-strm',
            'note': 'Project spelling pinned explicitly; synthetic example only.'}},
        'obligations': obligations, 'mappings': [mapping], 'pending': [], 'search_reviews': searches,
        'no_matches': [{'obligation_id': ids[1], 'reason': 'No synthetic control imposes 90-day retention.', 'review': approved()}],
        'coverage_reviews': [{'obligation_id': ids[0], 'covered_by': ['TST-01'], 'residual_clauses': [],
            'reason': 'Recording outcome covered in this synthetic example.', 'review': approved()}]}
    write_json(dest / 'ledger.json', ledger)
    import json
    unit = {'id': 'DEMO-01', 'source_en': 'Record security events for 90 days. SCF DEMO-01.',
        'translation_fa': 'رویدادهای امنیتی را برای ۹۰ روز ثبت کنید. SCF DEMO-01.',
        'status': 'TRANSLATED', 'semantic_review': approved(), 'term_decisions': []}
    (dest / 'translations.jsonl').write_text(json.dumps(unit, ensure_ascii=False) + '\n', encoding='utf-8')
    return catalog, inventory, ledger


if __name__ == '__main__':
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'examples/synthetic')
