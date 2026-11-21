"""Heuristic bilingual-unit QA and eligible terminology provenance checks."""
import json
import re
from .common import DataError, key, text
from .ledger import review

IDENTIFIERS = re.compile(r'(?<![\w])(?:[A-Z]{2,}(?:[-_/][A-Z0-9.]+)*|\d+(?:\.\d+)?%)(?![\w])')
NUMBERS = re.compile(r'\d+(?:[.,]\d+)*%?')
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def check_units(path, terminology=None):
    errors, warnings, identities = [], [], set()
    units = 0
    with open(path, encoding='utf-8-sig') as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            units += 1
            try:
                unit = json.loads(line)
                if not isinstance(unit, dict):
                    raise DataError('Translation unit must be an object')
                for field in ('id', 'source_en', 'translation_fa', 'status'):
                    if not text(unit.get(field)):
                        raise DataError('Missing string field ' + field)
                if unit['id'] in identities:
                    raise DataError('Duplicate translation unit ID')
                identities.add(unit['id'])
                if unit['status'] not in ('TRANSLATED', 'NEEDS_CONTEXT'):
                    raise DataError('Invalid translation status')
                if unit['status'] == 'NEEDS_CONTEXT':
                    errors.append({'line': line_no, 'type': 'NEEDS_CONTEXT'})
                if unit['status'] == 'TRANSLATED':
                    review(unit.get('semantic_review'), 'Translation semantic review')
                en, fa = unit['source_en'], unit['translation_fa']
                missing = set(IDENTIFIERS.findall(en)) - set(IDENTIFIERS.findall(fa))
                if missing:
                    warnings.append({'line': line_no, 'type': 'POSSIBLE_LOST_IDENTIFIER', 'tokens': sorted(missing)})
                if set(NUMBERS.findall(en.translate(DIGITS))) != set(NUMBERS.findall(fa.translate(DIGITS))):
                    warnings.append({'line': line_no, 'type': 'CHECK_NUMBERS'})
                if re.search(r'\b(must not|shall not|prohibited|never)\b', en, re.I) and not re.search(r'نباید|ممنوع|هرگز|مجاز نیست|نمی', fa):
                    warnings.append({'line': line_no, 'type': 'CHECK_NEGATION'})
                decisions = unit.get('term_decisions', [])
                if not isinstance(decisions, list):
                    raise DataError('term_decisions must be a list')
                for decision in decisions:
                    if terminology is None:
                        raise DataError('Terminology references required to verify term decisions')
                    entry = terminology.by_id.get(decision.get('entry_id'))
                    if entry is None:
                        raise DataError('Unknown or held terminology entry')
                    if entry['authority'] != decision.get('authority'):
                        raise DataError('Term authority label differs from source')
                    query = decision.get('source_en_phrase')
                    if not text(query) or not re.search(r'(?<!\w)' + re.escape(key(query)) + r'(?!\w)', key(en)):
                        raise DataError('Term decision phrase absent from source unit')
                    result = terminology.lookup(query)
                    eligible = {r['entry_id'] for r in result['matches']}
                    if entry['entry_id'] not in eligible:
                        if not text(decision.get('afta_sense_mismatch_reason')):
                            raise DataError('Lower tier bypasses an AFTA candidate without contextual rationale')
                        if entry['entry_id'] not in {r['entry_id'] for r in result['supplementary_context']}:
                            raise DataError('Selected term is not an exact source-heading candidate')
                    if not text(decision.get('context_rationale')):
                        raise DataError('Terminology context rationale required')
                    if entry['fa'] not in fa:
                        raise DataError('Source Persian equivalent absent or silently altered')
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                errors.append({'line': line_no, 'type': 'INVALID_UNIT', 'detail': str(error)})
    if not units:
        errors.append({'type': 'EMPTY_DATASET'})
    return {'status': 'READY_FOR_SEMANTIC_REVIEW' if not errors and not warnings else 'REVIEW_REQUIRED',
        'units': units, 'errors': errors, 'warnings': warnings, 'semantic_correctness_verified_by_code': False,
        'note': 'Heuristics may flag legitimate changes and miss semantic errors; review all units.'}
