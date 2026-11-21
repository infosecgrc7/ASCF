"""Source-grounded release checks and canonical ten-column rows.

A successful check confirms machine-checkable invariants and recorded reviews,
not the truth of a semantic or legal judgment.
"""
from collections import Counter, defaultdict
from datetime import datetime
import re
from .catalog import index_catalog
from .common import DataError, digest, require, score, text, unique

COLUMNS = ['FDE #', 'FDE Name', 'FDE Description', 'STRM Rationale', 'STRM Relationship',
           'SCF Control', 'SCF #', 'SCF Description', 'Strength of Relationship', 'Notes']


def review(value, label):
    require(isinstance(value, dict), label + ': review object required')
    require(value.get('status') == 'APPROVED', label + ': review not approved')
    require(value.get('method') in ('human', 'model'), label + ': reviewer method must be disclosed')
    require(all(text(value.get(k)) for k in ('reviewer', 'reviewed_at', 'notes')), label + ': review details missing')
    try:
        parsed = datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, label + ': timezone required')
    except (ValueError, TypeError):
        raise DataError(label + ': invalid review timestamp') from None


def inspect_inventory(inventory):
    require(isinstance(inventory, dict), 'Inventory must be an object')
    sources = inventory.get('documents')
    requirements = inventory.get('requirements')
    require(isinstance(sources, list) and sources and isinstance(requirements, list) and requirements,
            'Nonempty document and requirement inventories required')
    unique([s['source_id'] for s in sources], 'source IDs')
    source_map = {s['source_id']: s for s in sources}
    for source in sources:
        require(all(text(source.get(k)) for k in ('source_id', 'title', 'issuer', 'version')), 'Incomplete document metadata')
        require(bool(re.fullmatch('[a-f0-9]{64}', source.get('sha256', ''))), 'Document SHA-256 required')
    pairs = []
    for record in requirements:
        require(record.get('source_id') in source_map and text(record.get('fde_id')), 'Unknown source or blank FDE ID')
        require(isinstance(record.get('name'), str) and text(record.get('text_exact')), 'Exact requirement text/name required')
        pages = record.get('pages')
        require(isinstance(pages, list) and pages and all(type(p) is int and p > 0 for p in pages), 'Positive physical PDF pages required')
        preamble = record.get('preamble_exact', '')
        require(isinstance(preamble, str) and (not preamble or preamble in record['text_exact']), 'Preamble absent from source')
        pairs.append((record['source_id'], record['fde_id']))
    unique(pairs, '(source ID, FDE ID) source requirements')
    return {pair: record for pair, record in zip(pairs, requirements)}


def validate(doc, catalog, inventory, catalog_hash=None, inventory_hash=None):
    errors = []
    try:
        rows, summary = adjudicate(doc, catalog, inventory, catalog_hash, inventory_hash)
    except (DataError, KeyError, TypeError, AttributeError, ValueError, IndexError) as error:
        errors.append(str(error))
        rows, summary = [], {}
    return {'status': 'READY_FOR_EXPORT' if not errors else 'NOT_FINAL', 'errors': errors,
            'errors_count': len(errors), 'semantic_correctness_verified_by_code': False,
            'review_attestations_authenticated_by_code': False, **summary}, rows


def adjudicate(doc, catalog, inventory, catalog_hash=None, inventory_hash=None):
    require(isinstance(doc, dict), 'Ledger must be an object')
    controls = index_catalog(catalog)
    parents = inspect_inventory(inventory)
    meta = doc.get('metadata', {})
    require(meta.get('scf_version') == catalog.get('scf_version'), 'SCF version mismatch')
    for label, expected in [('catalog_sha256', catalog_hash), ('inventory_sha256', inventory_hash)]:
        require(bool(re.fullmatch('[a-f0-9]{64}', meta.get(label, ''))), label + ' required')
        if expected is not None:
            require(meta[label] == expected, label + ' mismatch')
    profile = meta.get('profile')
    require(isinstance(profile, dict), 'Explicit methodology profile required')
    equality = profile.get('equality_label')
    require(equality in ('Equal', 'Equal To'), 'Pin equality spelling to the selected methodology profile')
    rationale = profile.get('rationale')
    require(rationale in ('Functional', 'multi_basis'), 'Pin rationale profile')
    require(text(profile.get('methodology_url')), 'Methodology URL required')
    relations = {'Subset Of', 'Intersects With', equality, 'Superset Of'}
    require(doc.get('pending') == [], 'Explicit empty pending queue required for release')
    obligations = doc.get('obligations')
    mappings, gaps = doc.get('mappings'), doc.get('no_matches')
    coverage = doc.get('coverage_reviews')
    searches = doc.get('search_reviews')
    require(all(isinstance(v, list) for v in (obligations, mappings, gaps, coverage, searches)), 'Ledger arrays missing')
    require(bool(obligations), 'Empty atomic obligation inventory')
    unique([o['id'] for o in obligations], 'atomic obligation IDs')
    obs = {o['id']: o for o in obligations}
    children = defaultdict(list)
    for ob in obligations:
        require(text(ob.get('id')), 'Blank obligation ID')
        parent = parents.get((ob.get('source_id'), ob.get('fde_id')))
        require(parent is not None, 'Obligation references unknown source requirement')
        fragments = ob.get('source_fragments')
        require(isinstance(fragments, list) and fragments and all(text(f) for f in fragments), 'Exact source fragments required: ' + ob['id'])
        require(all(f in parent['text_exact'] for f in fragments), 'Source fragment absent from requirement: ' + ob['id'])
        # Enforce source order rather than accepting an arbitrary reordering of quoted fragments.
        cursor = 0
        for fragment in fragments:
            found = parent['text_exact'].find(fragment, cursor)
            require(found >= 0, 'Source fragments not in source order: ' + ob['id'])
            cursor = found + len(fragment)
        mode, body = ob.get('description_mode'), ob.get('text_exact')
        require(text(body) and mode in ('verbatim_excerpt', 'composite'), 'Obligation text/mode missing')
        if mode == 'verbatim_excerpt':
            require(len(fragments) == 1 and body == fragments[0], 'Verbatim obligation differs from its source fragment')
        else:
            require(text(ob.get('composite_rationale')), 'Composite rationale required')
        require(set(ob.get('source_pages', [])) and set(ob['source_pages']) <= set(parent['pages']), 'Obligation page not in source inventory')
        require(text(ob.get('testable_outcome')) and text(ob.get('independent_pass_fail_test')), 'Atomicity evidence required')
        five = ob.get('five_tuple')
        require(isinstance(five, dict) and all(isinstance(five.get(k), str) for k in
            ('actor', 'action', 'target_scope', 'frequency_trigger', 'jurisdiction_qualifier')), 'Five-tuple fields required; use empty strings for absent qualifiers')
        require(text(five['action']), 'Obligation action required')
        context = ob.get('applicable_parent_context', '')
        require(isinstance(context, str) and (not context or context in parent['text_exact']), 'Parent context must be an exact source passage')
        if parent.get('preamble_exact'):
            require(parent['preamble_exact'] in context, 'Inherited parent context must be retained in every child')
        review(ob.get('source_review'), 'Source/atomicity ' + ob['id'])
        children[(ob['source_id'], ob['fde_id'])].append(ob)
    require(set(children) == set(parents), 'Every source requirement must have atomic obligation disposition')
    for group in children.values():
        descriptions = [o['text_exact'] for o in group]
        require(len(set(descriptions)) == len(descriptions), 'Duplicate atomic descriptions need source/atomicity resolution')
        if len(group) > 1:
            parent = parents[(group[0]['source_id'], group[0]['fde_id'])]['text_exact']
            require(all(o['text_exact'] != parent for o in group), 'Full multi-obligation parent repeated in child')
    search_map = {}
    for item in searches:
        oid = item.get('obligation_id')
        require(oid in obs and oid not in search_map, 'Duplicate/unknown search review')
        require(text(item.get('query')) and text(item.get('search_scope')), 'Search query/scope required')
        candidates = item.get('candidates')
        require(isinstance(candidates, list) and candidates, 'Search candidate evidence required')
        unique([c['scf_id'] for c in candidates], 'search candidate IDs')
        for candidate in candidates:
            require(candidate.get('scf_id') in controls and text(candidate.get('reason')), 'Invalid search candidate')
            require(candidate.get('disposition') in ('ACCEPTED', 'REJECTED'), 'Unresolved candidate')
            if candidate['disposition'] == 'ACCEPTED':
                score(candidate.get('score'))
        review(item.get('review'), 'Search review ' + oid)
        search_map[oid] = item
    require(set(search_map) == set(obs), 'Every obligation needs a reviewed control/AO search')
    pairs, mapped, scores = [], defaultdict(list), defaultdict(list)
    for mapping in mappings:
        oid, sid = mapping.get('obligation_id'), mapping.get('scf_id')
        require(oid in obs and sid in controls, 'Unknown obligation/control mapping')
        pairs.append((oid, sid))
        require(mapping.get('relationship') in relations, 'Invalid relationship label')
        allowed_rationales = {'Functional'} if rationale == 'Functional' else {'Functional', 'Semantic', 'Syntactic'}
        require(mapping.get('rationale') in allowed_rationales, 'Rationale conflicts with pinned profile')
        strength = score(mapping.get('score'))
        require(float(strength).is_integer(), 'Project strength uses whole-number steps 1–10')
        require(text(mapping.get('shared_mandatory_clause')) and text(mapping.get('decision_reason')), 'Shared mandatory outcome and reason required')
        require(all(isinstance(mapping.get(k), str) for k in ('fde_only_clauses', 'scf_only_clauses')), 'Both set-difference fields must be explicit')
        rel = mapping['relationship']
        if rel == equality:
            require(not mapping['fde_only_clauses'].strip() and not mapping['scf_only_clauses'].strip(), 'Equality cannot have set differences')
        if rel == 'Subset Of':
            require(not mapping['fde_only_clauses'].strip() and text(mapping['scf_only_clauses']), 'Subset direction/differences inconsistent')
        if rel == 'Superset Of':
            require(text(mapping['fde_only_clauses']) and not mapping['scf_only_clauses'].strip(), 'Superset direction/differences inconsistent')
        if rel == 'Intersects With':
            require(text(mapping['fde_only_clauses']) and text(mapping['scf_only_clauses']), 'Intersection requires differences on both sides')
        if rel in (equality, 'Subset Of'):
            falsification = mapping.get('falsification_check', {})
            require(falsification.get('counterexample_found') is False and text(falsification.get('reason')), 'Containment requires a recorded counterexample review')
        review(mapping.get('semantic_review'), 'Semantic ' + oid + '/' + sid)
        review(mapping.get('score_review'), 'Score ' + oid + '/' + sid)
        selection = mapping.get('selection_review', {})
        require(selection.get('scope') in ('domain_specific', 'general_governance', 'generic_fallback') and text(selection.get('decision')), 'Selection scope/decision required')
        evidence = selection.get('selected_evidence')
        require(isinstance(evidence, list) and evidence, 'Exact control/AO evidence required')
        ao_map = {a['id']: a for a in controls[sid]['assessment_objectives']}
        for proof in evidence:
            require(isinstance(proof, dict) and text(proof.get('quote')), 'Evidence quote required')
            if proof.get('ao_id'):
                require(proof['ao_id'] in ao_map and proof['quote'] in ao_map[proof['ao_id']]['text'], 'AO evidence is not from selected control')
            else:
                require(proof['quote'] in controls[sid]['description'], 'Control evidence absent from original description')
        alternatives = selection.get('alternatives')
        require(isinstance(alternatives, list), 'Alternatives list required')
        broad = sid.startswith(('GOV-', 'HRS-')) or selection['scope'] in ('general_governance', 'generic_fallback')
        require(bool(alternatives) or not (broad or strength < 5), 'Broad/fallback mapping needs competing-control comparison')
        for alternate in alternatives:
            require(alternate.get('scf_id') in controls and alternate['scf_id'] != sid and text(alternate.get('reason')), 'Invalid competing control')
        require(not (selection['scope'] == 'generic_fallback' and strength >= 5), 'Generic fallback cannot receive a priority score')
        accepted = {c['scf_id']: c for c in search_map[oid]['candidates'] if c['disposition'] == 'ACCEPTED'}
        require(sid in accepted and score(accepted[sid].get('score')) == strength, 'Mapping differs from reviewed candidate decision')
        mapped[oid].append(mapping)
        scores[oid].append(strength)
    unique(pairs, '(obligation, control) mappings')
    for oid, strengths in scores.items():
        require(not (any(s < 5 for s in strengths) and any(s >= 5 for s in strengths)), 'Weak fallback coexists with priority mapping')
        accepted_ids = {c['scf_id'] for c in search_map[oid]['candidates'] if c['disposition'] == 'ACCEPTED'}
        require(accepted_ids == {m['scf_id'] for m in mapped[oid]}, 'Accepted candidates omitted from ledger')
    gap_map = {}
    for gap in gaps:
        oid = gap.get('obligation_id')
        require(oid in obs and oid not in mapped and oid not in gap_map, 'Duplicate/unknown/contradictory no-match disposition')
        require(text(gap.get('reason')), 'No-match explanation required')
        require(all(c['disposition'] == 'REJECTED' for c in search_map[oid]['candidates']), 'No-match has an accepted search candidate')
        review(gap.get('review'), 'No-match ' + oid)
        gap_map[oid] = gap
    require(set(mapped) | set(gap_map) == set(obs), 'Unaccounted atomic obligations')
    coverage_map = {}
    for item in coverage:
        oid = item.get('obligation_id')
        require(oid in mapped and oid not in coverage_map, 'Unknown/duplicate coverage review')
        require(set(item.get('covered_by', [])) == {m['scf_id'] for m in mapped[oid]}, 'Coverage union differs from selected controls')
        residual = item.get('residual_clauses')
        require(isinstance(residual, list) and all(text(v) for v in residual), 'Residual clauses must be explicit list')
        require(text(item.get('reason')), 'Combined coverage reasoning required')
        if residual:
            require(all(m['relationship'] not in (equality, 'Subset Of') for m in mapped[oid]), 'Residual gap contradicts full FDE containment')
        review(item.get('review'), 'Combined coverage ' + oid)
        coverage_map[oid] = item
    require(set(coverage_map) == set(mapped), 'Combined coverage/residual review required for every mapped obligation')
    expected = canonical_rows(doc, catalog, inventory)
    if 'output_rows' in doc:
        require(doc['output_rows'] == expected, 'Output rows differ from canonical approved ten-column values')
    return expected, {'source_documents': len(inventory['documents']), 'source_requirements': len(parents),
        'atomic_obligations': len(obs), 'mapping_rows': len(mappings), 'no_match_rows': len(gaps),
        'residual_gap_obligations': sum(bool(i['residual_clauses']) for i in coverage),
        'output_rows': len(expected), 'profile': profile}


def canonical_rows(doc, catalog, inventory):
    controls = {c['id']: c for c in catalog['controls']}
    parents = {(r['source_id'], r['fde_id']): r for r in inventory['requirements']}
    mappings = defaultdict(list)
    for item in doc['mappings']:
        mappings[item['obligation_id']].append(item)
    gaps = {g['obligation_id']: g for g in doc['no_matches']}
    coverage = {c['obligation_id']: c for c in doc['coverage_reviews']}
    rows = []
    for parent_key, parent in parents.items():
        first = True
        preamble = parent.get('preamble_exact', '')
        for ob in [o for o in doc['obligations'] if (o['source_id'], o['fde_id']) == parent_key]:
            body = ob['text_exact']
            # Remove only an exact source preamble at the beginning; retain full inherited context internally.
            child_body = body[len(preamble):].lstrip(' \r\n') if preamble and body.startswith(preamble) else body
            require(bool(child_body.strip()), 'Preamble cannot consume entire atomic obligation')
            decisions = mappings.get(ob['id']) or [None]
            for decision in decisions:
                display = (preamble + '\n' + child_body) if first and preamble and not body.startswith(preamble) else (
                          body if first else child_body)
                composite = ob['description_mode'] == 'composite' or bool(first and preamble and not body.startswith(preamble))
                notes = 'Source ' + ob['source_id'] + ' | Atomic obligation ' + ob['id'] + ' | PDF page ' + ', '.join(map(str, ob['source_pages']))
                if composite:
                    notes += ' | Contextual composite; not a verbatim quotation'
                if not first and preamble:
                    notes += ' | Inherits context from source clause ' + ob['fde_id']
                if decision:
                    control = controls[decision['scf_id']]
                    notes += ' | ' + decision['decision_reason']
                    residual = coverage[ob['id']]['residual_clauses']
                    if residual:
                        notes += ' | Residual: ' + '; '.join(residual)
                    values = [ob['fde_id'], parent['name'], display, decision['rationale'], decision['relationship'],
                              control['title'], control['id'], control['description'], score(decision['score']), notes]
                else:
                    notes += ' | ' + gaps[ob['id']]['reason']
                    values = [ob['fde_id'], parent['name'], display, '', 'No Relationship', '', '', '', '', notes]
                rows.append(dict(zip(COLUMNS, values)))
                first = False
    return rows
