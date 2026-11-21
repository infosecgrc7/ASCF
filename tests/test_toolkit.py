"""Observable regression tests. All public fixtures are synthetic."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/scf-mapping-translation/scripts'))
from scf_toolkit.catalog import extract, index_catalog
from scf_toolkit.common import DataError, digest, load, write_json
from scf_toolkit.ledger import COLUMNS, canonical_rows, validate
from scf_toolkit.retrieval import Search, tokens
from scf_toolkit.terms import Terminology, import_glossaries
from scf_toolkit.translation import check_units
from scf_toolkit.workbook import build_workbook, verify_workbook
spec = importlib.util.spec_from_file_location('demo_builder', ROOT / 'scripts/create_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.catalog, self.inventory, self.doc = demo.generate(self.directory)
    def tearDown(self):
        self.temp.cleanup()
    def check(self, doc=None, catalog=None, inventory=None):
        return validate(doc or self.doc, catalog or self.catalog, inventory or self.inventory)
    def assertBlocked(self, doc=None, catalog=None, inventory=None):
        self.assertEqual(self.check(doc, catalog, inventory)[0]['status'], 'NOT_FINAL')
    def save(self):
        for name, value in [('catalog', self.catalog), ('inventory', self.inventory)]:
            write_json(self.directory / (name + '.json'), value)
        self.doc['metadata']['catalog_sha256'] = digest(self.directory / 'catalog.json')
        self.doc['metadata']['inventory_sha256'] = digest(self.directory / 'inventory.json')
        write_json(self.directory / 'ledger.json', self.doc)
    def test_complete_atomic_disposition(self):
        result, rows = self.check()
        self.assertEqual(result['status'], 'READY_FOR_EXPORT', result)
        self.assertEqual((result['atomic_obligations'], result['mapping_rows'], result['no_match_rows']), (2, 1, 1))
        self.assertEqual(list(rows[0]), COLUMNS)
        self.assertEqual(rows[1]['STRM Relationship'], 'No Relationship')
        for field in ('SCF #', 'SCF Control', 'SCF Description', 'STRM Rationale', 'Strength of Relationship'):
            self.assertEqual(rows[1][field], '')
    def test_output_mutations_cannot_bypass_approval(self):
        rows = self.check()[1]
        mutations = [('STRM Relationship', 'Supports'), ('Strength of Relationship', 999),
            ('STRM Rationale', 'Unrecognized'), ('SCF Control', 'Fabricated title'),
            ('SCF Description', 'Fabricated description')]
        for field, value in mutations:
            with self.subTest(field=field):
                doc = copy.deepcopy(self.doc)
                doc['output_rows'] = copy.deepcopy(rows)
                doc['output_rows'][0][field] = value
                self.assertBlocked(doc)
    def test_missing_extra_output_columns_blocked(self):
        for mutation in ('missing', 'extra'):
            doc = copy.deepcopy(self.doc)
            doc['output_rows'] = self.check()[1]
            if mutation == 'missing':
                del doc['output_rows'][0]['SCF Description']
            else:
                doc['output_rows'][0]['Eleventh column'] = 'X'
            self.assertBlocked(doc)
    def test_id_and_relation_errors(self):
        for field, value in [('scf_id', 'UNKNOWN-99'), ('relationship', 'Supports'), ('rationale', 'Semantic')]:
            doc = copy.deepcopy(self.doc)
            doc['mappings'][0][field] = value
            self.assertBlocked(doc)
    def test_duplicate_mapping(self):
        self.doc['mappings'].append(copy.deepcopy(self.doc['mappings'][0]))
        self.assertBlocked()
    def test_unresolved_review(self):
        self.doc['pending'].append('unresolved')
        self.assertBlocked()
    def test_fake_source_quote(self):
        self.doc['obligations'][0]['text_exact'] = 'Invented obligation absent from source'
        self.assertBlocked()
    def test_fragments_must_be_exact(self):
        self.doc['obligations'][0]['source_fragments'] = ['Invented source quotation']
        self.assertBlocked()
    def test_missing_parent_context(self):
        del self.doc['obligations'][1]['applicable_parent_context']
        self.assertBlocked()
    def test_foreign_ao_evidence(self):
        proof = self.doc['mappings'][0]['selection_review']['selected_evidence'][0]
        proof['ao_id'] = 'TST-02_A01'
        proof['quote'] = 'recorded events are analyzed.'
        self.assertBlocked()
    def test_nonexistent_ao_quote(self):
        self.doc['mappings'][0]['selection_review']['selected_evidence'][0]['quote'] = 'invented'
        self.assertBlocked()
    def test_review_attestation_required(self):
        self.doc['mappings'][0]['semantic_review']['status'] = 'PENDING'
        self.assertBlocked()
    def test_numeric_fallback_representations(self):
        for value in (4, 4.0, '4.0'):
            doc = copy.deepcopy(self.doc)
            doc['mappings'][0]['score'] = value
            doc['mappings'][0]['selection_review']['scope'] = 'generic_fallback'
            doc['search_reviews'][0]['candidates'][0]['score'] = value
            self.assertEqual(self.check(doc)[0]['status'], 'READY_FOR_EXPORT')
    def test_invalid_strengths(self):
        for value in (True, False, None, 0, 11, float('nan'), float('inf'), 'NaN', 4.5):
            with self.subTest(value=value):
                doc = copy.deepcopy(self.doc)
                doc['mappings'][0]['score'] = value
                self.assertBlocked(doc)
    def test_unaccounted_and_conflicting_obligations(self):
        doc = copy.deepcopy(self.doc)
        doc['no_matches'] = []
        self.assertBlocked(doc)
        self.doc['no_matches'].append(dict(self.doc['no_matches'][0], obligation_id='DEMO::1::O01'))
        self.assertBlocked()
    def test_residual_cannot_coexist_with_subset(self):
        self.doc['coverage_reviews'][0]['residual_clauses'] = ['A source duty remains uncovered']
        self.assertBlocked()
    def test_missing_union_review(self):
        self.doc['coverage_reviews'] = []
        self.assertBlocked()
    def test_source_and_catalog_hashes(self):
        result, _ = validate(self.doc, self.catalog, self.inventory, '0' * 64, digest(self.directory / 'inventory.json'))
        self.assertEqual(result['status'], 'NOT_FINAL')
    def test_version_drift(self):
        self.doc['metadata']['scf_version'] = '2099.1'
        self.assertBlocked()
    def test_preamble_once_for_repeated_mapping_of_same_child(self):
        control = copy.deepcopy(self.catalog['controls'][0])
        control['id'] = 'TST-04'
        for ao in control['assessment_objectives']:
            ao['id'] = ao['id'].replace('TST-01', 'TST-04')
        self.catalog['controls'].append(control)
        ob = self.doc['obligations'][0]
        ob['text_exact'] = 'سازمان باید: ' + ob['text_exact']
        ob['source_fragments'] = [ob['text_exact']]
        extra = copy.deepcopy(self.doc['mappings'][0])
        extra['scf_id'] = 'TST-04'
        extra['selection_review']['selected_evidence'][0]['ao_id'] = 'TST-04_A01'
        self.doc['mappings'].append(extra)
        self.doc['search_reviews'][0]['candidates'].append({'scf_id': 'TST-04', 'disposition': 'ACCEPTED', 'score': 7, 'reason': 'Synthetic test'})
        self.doc['coverage_reviews'][0]['covered_by'].append('TST-04')
        result, rows = self.check()
        self.assertEqual(result['status'], 'READY_FOR_EXPORT', result)
        self.assertTrue(rows[0]['FDE Description'].startswith('سازمان باید:'))
        self.assertNotIn('سازمان باید:', rows[1]['FDE Description'])
    def test_multi_source_repeated_parent_id(self):
        self.inventory['documents'].append(dict(self.inventory['documents'][0], source_id='SECOND'))
        parent = dict(self.inventory['requirements'][0], source_id='SECOND')
        self.inventory['requirements'].append(parent)
        for ob in copy.deepcopy(self.doc['obligations']):
            ob['id'] = ob['id'].replace('DEMO::', 'SECOND::')
            ob['source_id'] = 'SECOND'
            self.doc['obligations'].append(ob)
        for item in copy.deepcopy(self.doc['search_reviews']):
            item['obligation_id'] = item['obligation_id'].replace('DEMO::', 'SECOND::')
            for candidate in item['candidates']:
                candidate['disposition'] = 'REJECTED'
                candidate.pop('score', None)
            self.doc['search_reviews'].append(item)
            self.doc['no_matches'].append({'obligation_id': item['obligation_id'], 'reason': 'Synthetic alternative outcome', 'review': demo.approved()})
        result, rows = self.check()
        self.assertEqual(result['status'], 'READY_FOR_EXPORT', result)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['FDE #'] == '1' for r in rows))
        self.assertTrue(any('Source SECOND' in r['Notes'] for r in rows))
    def test_build_and_independently_check_saved_xlsx(self):
        target = self.directory / 'mapping.xlsx'
        result = build_workbook(self.doc, self.catalog, self.inventory, target,
            digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'))
        self.assertEqual(result['status'], 'SAVED_XLSX_VERIFIED')
        import openpyxl
        wb = openpyxl.load_workbook(target)
        ws = wb.active
        self.assertTrue(ws.sheet_view.rightToLeft)
        self.assertEqual(ws.freeze_panes, 'A2')
        ws['I2'] = 999
        wb.save(target)
        wb.close()
        with self.assertRaises(DataError):
            verify_workbook(target, self.check()[1])
    def test_hidden_rows_columns_and_unreadable_text_rejected(self):
        import openpyxl
        for change in ('row', 'column', 'font'):
            target = self.directory / (change + '.xlsx')
            build_workbook(self.doc, self.catalog, self.inventory, target,
                digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'))
            wb = openpyxl.load_workbook(target)
            if change == 'row':
                wb.active.row_dimensions[2].hidden = True
            elif change == 'column':
                wb.active.column_dimensions['C'].hidden = True
            else:
                from openpyxl.styles import Font
                wb.active['C2'].font = Font(color='FFFFFF')
            wb.save(target)
            wb.close()
            with self.assertRaises(DataError):
                verify_workbook(target, self.check()[1])
    def test_template_hidden_dimensions_are_reset(self):
        import openpyxl
        template = self.directory / 'template.xlsx'
        build_workbook(self.doc, self.catalog, self.inventory, template,
            digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'))
        wb = openpyxl.load_workbook(template)
        wb.active.row_dimensions[2].hidden = True
        wb.active.column_dimensions['C'].hidden = True
        wb.save(template)
        wb.close()
        result = build_workbook(self.doc, self.catalog, self.inventory, self.directory / 'from-template.xlsx',
            digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'), template)
        self.assertEqual(result['status'], 'SAVED_XLSX_VERIFIED')

    def test_conditional_formatting_and_hidden_number_formats_rejected(self):
        import openpyxl
        from openpyxl.formatting.rule import FormulaRule
        from openpyxl.styles import Font
        for change in ('conditional', 'format'):
            target = self.directory / (change + '.xlsx')
            build_workbook(self.doc, self.catalog, self.inventory, target,
                digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'))
            wb = openpyxl.load_workbook(target)
            if change == 'conditional':
                wb.active.conditional_formatting.add('A2:J3', FormulaRule(formula=['TRUE'], font=Font(color='FFFFFF')))
            else:
                wb.active['C2'].number_format = ';;;'
            wb.save(target)
            wb.close()
            with self.assertRaises(DataError):
                verify_workbook(target, self.check()[1])

    def test_literal_formula_like_data(self):
        # A source ID/name beginning '=' must remain literal without changing its value.
        self.inventory['requirements'][0]['name'] = '=1+1'
        self.save()
        target = self.directory / 'literal.xlsx'
        build_workbook(self.doc, self.catalog, self.inventory, target,
            digest(self.directory / 'catalog.json'), digest(self.directory / 'inventory.json'))
        import openpyxl
        wb = openpyxl.load_workbook(target, data_only=False)
        self.assertEqual(wb.active['B2'].value, '=1+1')
        self.assertEqual(wb.active['B2'].data_type, 's')
        wb.close()
    def test_cli_from_unrelated_directory(self):
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
            str(ROOT / 'skills/scf-mapping-translation/scripts/run.py'), 'validate',
            '--catalog', str(self.directory / 'catalog.json'), '--inventory', str(self.directory / 'inventory.json'),
            '--ledger', str(self.directory / 'ledger.json')], cwd=self.directory, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'READY_FOR_EXPORT')


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load(ROOT / 'examples/synthetic/catalog.json')
    def test_persian_query_retrieves_control_and_ao(self):
        result = Search(self.catalog).shortlist('ثبت رویدادهای امنیتی')
        self.assertEqual(result[0]['scf_id'], 'TST-01')
        self.assertTrue(result[0]['ao_matches'])
        self.assertEqual(result[0]['decision'], 'CANDIDATE_ONLY')
    def test_ao_only_phrase_is_searchable(self):
        self.catalog['controls'][2]['assessment_objectives'][0]['text'] = 'Uniquequartz mechanism is tested.'
        self.assertEqual(Search(self.catalog).shortlist('Uniquequartz')[0]['scf_id'], 'TST-03')
    def test_unicode_persian_forms(self):
        self.assertEqual(tokens('ي ك'), tokens('ی ک'))
        self.assertTrue(any(t == 'ثبت' for t in tokens('ثبت رویداد')))
    def test_no_zero_score_padding(self):
        self.assertEqual(Search(self.catalog).shortlist('nonexistentquux'), [])
    def test_invalid_k(self):
        with self.assertRaises(DataError):
            Search(self.catalog).shortlist('events', 0)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def workbook(self, orphan=False, duplicate=False, prefix_mismatch=False, banner=False):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'SCF 2026.2'
        if banner:
            ws.append(['Source banner'])
        ws.append(['SCF Domain', 'SCF Control', 'SCF #', 'Secure Controls Framework (SCF)\nControl Description'])
        ws.append(['Test', 'Original title', 'TST-01', 'Original description'])
        if duplicate:
            ws.append(['Test', 'Duplicate', 'TST-01', 'Description'])
        ao = wb.create_sheet('Assessment Objectives 2026.2')
        if banner:
            ao.append(['Source banner'])
        ao.append(['SCF #', 'SCF AO #', 'SCF Assessment Objective (AO)\nThe assessor shall examine evidence', 'SCF Assessment Objective (AO) Origin(s)'])
        ao.append(['UNKNOWN-01' if orphan else 'TST-01', 'LEGACY-99_A01' if prefix_mismatch else 'TST-01_A01', 'Original AO text', 'Origin'])
        p = self.directory / 'source.xlsx'
        wb.save(p)
        wb.close()
        return p
    def test_import_headers_and_provenance(self):
        p = self.workbook(banner=True)
        before = digest(p)
        result = extract(p, '2026.2', self.directory / 'catalog.json')
        self.assertEqual(result['controls'][0]['title'], 'Original title')
        self.assertEqual(result['controls'][0]['assessment_objectives'][0]['text'], 'Original AO text')
        self.assertEqual(result['controls'][0]['source']['row'], 3)
        self.assertEqual(digest(p), before)
    def test_source_association_not_inferred_from_id_prefix(self):
        result = extract(self.workbook(prefix_mismatch=True), '2026.2', self.directory / 'catalog.json')
        self.assertEqual(result['controls'][0]['assessment_objectives'][0]['id'], 'LEGACY-99_A01')
        self.assertEqual(result['source_association_notes'][0]['control_id'], 'TST-01')
        self.assertEqual(len(index_catalog(result)), 1)
    def test_orphan_ao_rejected(self):
        with self.assertRaises(DataError):
            extract(self.workbook(orphan=True), '2026.2', self.directory / 'out.json')
    def test_duplicate_control_rejected(self):
        with self.assertRaises(DataError):
            extract(self.workbook(duplicate=True), '2026.2', self.directory / 'out.json')
    def test_corrupt_workbook_cli_returns_json_failure(self):
        source = self.directory / 'corrupt.xlsx'
        source.write_bytes(b'not an Excel archive')
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
            str(ROOT / 'skills/scf-mapping-translation/scripts/run.py'), 'import-scf',
            '--xlsx', str(source), '--scf-version', '2026.2', '--out', str(self.directory / 'out.json')],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['status'], 'NOT_FINAL')
        self.assertFalse((self.directory / 'out.json').exists())

    def test_wrong_version_rejected(self):
        with self.assertRaises(DataError):
            extract(self.workbook(), '2099.1', self.directory / 'out.json')


def synthetic_glossaries(directory):
    afta = {'source': {'title': 'SYNTHETIC approved authority fixture'}, 'entries': [
        {'entry_id': 'SYN-A1', 'en': 'Access Control', 'fa': 'مصوب آزمایشی', 'source_page': 4, 'en_aliases': ['Access Regulation']},
        {'entry_id': 'SYN-A2', 'en': 'Cipher', 'fa': 'گزینهٔ اول', 'source_page': 5, 'en_aliases': []},
        {'entry_id': 'SYN-A3', 'en': 'Algorithm', 'fa': 'گزینهٔ دوم', 'source_page': 6, 'en_aliases': ['Cipher']}]}
    entries, markdown = [], []
    for i in range(802):
        page = i // 3 + 1
        identity = 'CSG-%03d-%02d' % (page, i % 3 + 1)
        allowed = i < 759
        record = {'id': identity, 'term_en': 'Synthetic Term ' + str(i), 'term_fa': 'معادل آزمایشی ' + str(i),
            'definition_fa': 'تعریف ساختگی ' + str(i), 'page': page, 'page_end': page, 'status': 'usable' if allowed else 'source_conflict',
            'use_in_skill': allowed, 'source_location': {'printed_page': page, 'bbox': [0,0,10,10]},
            'term_fa_evidence': [{'page': page, 'quote': 'معادل آزمایشی ' + str(i)}]}
        if i == 0:
            record['term_en'] = 'Access Control'
        if i == 1:
            record['term_en'] = 'Access Regulation'
        if i == 759:
            record['term_en'] = 'Held Only'
        entries.append(record)
        markdown.append('<a id="' + identity.lower() + '"></a>\n\n### ' + record['term_en'] + '\n\n<p>' + record['definition_fa'] + '</p>\n\n<p>معادل — ' + record['term_fa'] + '</p>\n\n')
    source = {'source': {'title_fa': 'Synthetic fixture, not a book', 'page_count': 291}, 'entries': entries,
        'operational_entry_ids': [r['id'] for r in entries if r['use_in_skill'] is True],
        'counts': {'entries_total': 802, 'entries_usable': 759, 'entries_held': 43}}
    write_json(directory / 'afta.json', afta)
    write_json(directory / 'supp.json', source)
    (directory / 'supp.md').write_text(''.join(markdown), encoding='utf-8')
    return afta, source


class TerminologyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.afta, self.source = synthetic_glossaries(self.directory)
        self.dest = self.directory / 'references'
        import_glossaries(self.directory / 'afta.json', self.directory / 'supp.json', self.directory / 'supp.md', self.dest)
        self.terms = Terminology(self.dest)
    def tearDown(self):
        self.temp.cleanup()
    def test_afta_primary_and_alias_outrank_supplementary(self):
        for term in ('Access Control', 'Access Regulation'):
            result = self.terms.lookup(term)
            self.assertEqual(result['authority'], 'afta_approved')
            self.assertEqual(result['matches'][0]['fa'], 'مصوب آزمایشی')
            self.assertTrue(result['supplementary_context'])
    def test_759_included_43_excluded(self):
        for record in self.source['entries']:
            result = self.terms.lookup(record['term_en'])
            eligible = result['matches'] + result['supplementary_context']
            ids = {m['entry_id'] for m in eligible}
            self.assertEqual(record['id'] in ids, record['use_in_skill'] is True)
        held = self.terms.lookup('Held Only')
        self.assertEqual(held['status'], 'EXCLUDED_REFERENCE')
        self.assertNotIn('definition_fa', held['excluded_records'][0])
        active_md = (self.dest / 'supplementary_operational.md').read_text(encoding='utf-8')
        self.assertNotIn('Held Only', active_md)
    def test_ambiguity_retained(self):
        result = self.terms.lookup('Cipher')
        self.assertEqual(result['decision'], 'NEEDS_CONTEXT')
        self.assertEqual(len(result['matches']), 2)
    def test_no_substring_replacement(self):
        self.assertEqual(self.terms.lookup('Access Controller')['status'], 'NOT_FOUND')
        self.assertEqual(len(self.terms.scan('preAccess Controller')['candidates']), 0)
    def test_boolean_true_required(self):
        self.source['entries'][0]['use_in_skill'] = 'true'
        write_json(self.directory / 'supp.json', self.source)
        with self.assertRaises(DataError):
            import_glossaries(self.directory / 'afta.json', self.directory / 'supp.json', self.directory / 'supp.md', self.directory / 'other')
    def test_drift_detected(self):
        p = self.dest / 'supplementary_operational.json'
        p.write_bytes(p.read_bytes() + b' ')
        with self.assertRaises(DataError):
            Terminology(self.dest)
    def test_term_decision_must_match_a_whole_source_phrase(self):
        unit = {'id':'U2','source_en':'preAccess Control','translation_fa':'مصوب آزمایشی','status':'TRANSLATED',
            'semantic_review':demo.approved(),'term_decisions':[{'entry_id':'SYN-A1','authority':'afta_approved',
                'source_en_phrase':'Access Control','context_rationale':'Synthetic test'}]}
        p = self.directory / 'unit.jsonl'
        p.write_text(json.dumps(unit,ensure_ascii=False)+'\n',encoding='utf-8')
        self.assertTrue(check_units(p,self.terms)['errors'])

    def test_full_originals_preserved(self):
        self.assertEqual((self.dest / 'AFTA_Approved_Glossary_Final.json').read_bytes(), (self.directory / 'afta.json').read_bytes())
        self.assertEqual((self.dest / 'source_archive/Cybersecurity_Glossary_FA.md').read_bytes(), (self.directory / 'supp.md').read_bytes())
    def test_held_term_cannot_support_translation(self):
        unit = {'id':'U1', 'source_en':'Held Only', 'translation_fa':'معادل آزمایشی', 'status':'TRANSLATED',
            'semantic_review':demo.approved(), 'term_decisions':[{'entry_id': self.source['entries'][759]['id'],
                'authority':'supplementary','source_en_phrase':'Held Only','context_rationale':'test'}]}
        p = self.directory / 'unit.jsonl'
        p.write_text(json.dumps(unit,ensure_ascii=False)+'\n',encoding='utf-8')
        self.assertTrue(check_units(p,self.terms)['errors'])


class TranslationTests(unittest.TestCase):
    def test_complete_fixture(self):
        result = check_units(ROOT / 'examples/synthetic/translations.jsonl')
        self.assertFalse(result['errors'])
        self.assertFalse(result['warnings'])
    def test_negative_identifier_and_number_risks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'units.jsonl'
            p.write_text(json.dumps({'id':'1','source_en':'SCF must not retain records for 90 days.',
                'translation_fa':'سوابق نگهداری شود.', 'status':'TRANSLATED','semantic_review':demo.approved()},ensure_ascii=False)+'\n',encoding='utf-8')
            result = check_units(p)
            self.assertEqual({i['type'] for i in result['warnings']}, {'POSSIBLE_LOST_IDENTIFIER','CHECK_NUMBERS','CHECK_NEGATION'})
    def test_empty_and_missing_review(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'units.jsonl'
            p.write_text('',encoding='utf-8')
            self.assertTrue(check_units(p)['errors'])
            p.write_text(json.dumps({'id':'1','source_en':'text','translation_fa':'متن','status':'TRANSLATED'})+'\n',encoding='utf-8')
            self.assertTrue(check_units(p)['errors'])


if __name__ == '__main__':
    unittest.main()
