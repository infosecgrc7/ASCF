"""Import a deliberately selected local SCF workbook; no silent version upgrades."""
import re
from pathlib import Path
from .common import DataError, digest, require, unique, write_json

def heading(value):
    return ' '.join(str(value or '').casefold().split())

def find_header(sheet, kind):
    for rowno, row in enumerate(sheet.iter_rows(max_row=20, values_only=True), 1):
        names = [heading(v) for v in row]
        if 'scf #' not in names:
            continue
        if kind == 'control':
            desc = [i for i, n in enumerate(names) if 'control description' in n]
            titles = [i for i, n in enumerate(names) if n == 'scf control']
            if not desc or not titles:
                continue
            return rowno, names, {'id': names.index('scf #'), 'title': titles[0], 'description': desc[0]}
        aoid = [i for i, n in enumerate(names) if n in ('scf ao #', 'ao #', 'objective #', 'assessment objective #')]
        aotext = [i for i, n in enumerate(names) if ('assessment objective' in n and '#' not in n
                  and not any(token in n for token in ('origin', 'basis', 'source')))]
        if aoid and aotext:
            return rowno, names, {'control_id': names.index('scf #'), 'id': aoid[0], 'text': aotext[0]}
    raise DataError('Required ' + kind + ' header not found in ' + sheet.title)

def extract(workbook, version, destination):
    import openpyxl
    require(bool(re.fullmatch(r'20\d{2}\.\d+(?:\.\d+)*', version)), 'Explicit SCF version required')
    before = digest(workbook)
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=False)
    try:
        control_sheets = [s for s in wb if s.title.strip().casefold() == ('scf ' + version).casefold()]
        ao_sheets = [s for s in wb if s.title.strip().casefold() == ('assessment objectives ' + version).casefold()]
        require(len(control_sheets) == 1 and len(ao_sheets) == 1,
                'Exactly one SCF and AO sheet must match the requested version')
        sheet, aosheet = control_sheets[0], ao_sheets[0]
        header_row, heads, fields = find_header(sheet, 'control')
        controls = []
        id_pattern = re.compile(r'^[A-Z]{2,8}-\d+(?:\.\d+)*$')
        def value(row, index):
            return row[index] if index is not None and index < len(row) else None
        for rowno, row in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), header_row + 1):
            raw_id = value(row, fields['id'])
            if raw_id is None or str(raw_id).strip() == '':
                continue
            identity = str(raw_id).strip()
            require(bool(id_pattern.fullmatch(identity)), 'Invalid control ID at row ' + str(rowno))
            title, desc = value(row, fields['title']), value(row, fields['description'])
            require(isinstance(title, str) and title.strip() and isinstance(desc, str) and desc.strip(),
                    'Missing control title/description: ' + identity)
            metadata = {}
            for name, patterns in {'domain': ['scf domain'], 'question': ['scf control question'],
                    'weight': ['relative control weighting'], 'pptdf': ['pptdf applicability'],
                    'legacy_id': ['legacy scf #', 'legacy #'], 'evidence_request_ids': ['evidence request list (erl) #']}.items():
                index = next((i for i, h in enumerate(heads) if h in patterns), None)
                v = value(row, index)
                if v is not None:
                    metadata[name] = v
            controls.append({'id': identity, 'title': title, 'description': desc, 'metadata': metadata,
                'source': {'sheet': sheet.title, 'row': rowno, 'id_column': fields['id'] + 1,
                           'description_column': fields['description'] + 1}, 'assessment_objectives': []})
        require(bool(controls), 'Empty SCF catalog')
        unique([c['id'] for c in controls], 'control IDs')
        by_id = {c['id']: c for c in controls}
        ah, anames, afields = find_header(aosheet, 'ao')
        all_aos, blank, association_notes = [], 0, []
        for rowno, row in enumerate(aosheet.iter_rows(min_row=ah + 1, values_only=True), ah + 1):
            sid, oid, body = (value(row, afields[n]) for n in ('control_id', 'id', 'text'))
            if all(v is None or str(v).strip() == '' for v in (sid, oid, body)):
                blank += 1
                continue
            require(all(isinstance(v, str) and v.strip() for v in (sid, oid, body)), 'Incomplete AO at row ' + str(rowno))
            sid, oid = sid.strip(), oid.strip()
            require(sid in by_id, 'Orphan AO: ' + oid)
            if not oid.startswith(sid + '_'):
                association_notes.append({'code': 'AO_ID_PREFIX_DIFFERS_FROM_SOURCE_CONTROL',
                    'control_id': sid, 'ao_id': oid, 'source_row': rowno,
                    'resolution': 'Preserved exact source control-column association; no prefix inference.'})
            objective = {'id': oid, 'text': body, 'source_control_id': sid, 'source': {'sheet': aosheet.title, 'row': rowno,
                          'text_column': afields['text'] + 1}}
            # Original source values remain unmodified; normalization is used for discovery only.
            extras = {anames[i]: v for i, v in enumerate(row) if i < len(anames) and anames[i]
                      and i not in afields.values() and v is not None}
            if extras:
                objective['metadata'] = extras
            by_id[sid]['assessment_objectives'].append(objective)
            all_aos.append(oid)
        unique(all_aos, 'assessment objective IDs')
        require(all_aos and all(c['assessment_objectives'] for c in controls), 'Missing AO coverage; review source layout/version')
        require(digest(workbook) == before, 'Source workbook changed during import')
        catalog = {'schema_version': '1.0', 'scf_version': version, 'source': {
            'filename': Path(workbook).name, 'sha256': before, 'control_sheet': sheet.title,
            'ao_sheet': aosheet.title, 'content_owner': 'Secure Controls Framework Council, LLC',
            'license_url': 'https://creativecommons.org/licenses/by-nd/4.0/'},
            'source_association_notes': association_notes,
            'counts': {'controls': len(controls), 'assessment_objectives': len(all_aos), 'ignored_blank_ao_rows': blank},
            'controls': controls}
        write_json(destination, catalog)
        return catalog
    finally:
        wb.close()

def index_catalog(catalog):
    require(isinstance(catalog, dict) and isinstance(catalog.get('controls'), list), 'Catalog must contain controls[]')
    controls = catalog['controls']
    unique([c['id'] for c in controls], 'control IDs')
    aos = []
    for c in controls:
        require(all(isinstance(c.get(k), str) and c[k].strip() for k in ('id', 'title', 'description')), 'Incomplete control')
        require(isinstance(c.get('assessment_objectives'), list), 'AO list missing: ' + c['id'])
        for ao in c['assessment_objectives']:
            require(isinstance(ao.get('id'), str) and isinstance(ao.get('text'), str) and ao['text'].strip(), 'Incomplete AO')
            require(ao.get('source_control_id', c['id']) == c['id'], 'AO source ownership mismatch')
            aos.append(ao['id'])
    unique(aos, 'AO IDs')
    require(bool(controls) and bool(aos), 'Empty control/AO catalog')
    return {c['id']: c for c in controls}
