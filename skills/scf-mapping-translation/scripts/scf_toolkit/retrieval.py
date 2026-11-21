"""Unicode BM25 candidate discovery including AO text; never adjudicates relationships."""
from collections import Counter
import math
import re
import unicodedata
from .catalog import index_catalog
from .common import require

# Small retrieval bridge, not an approved Persian terminology dictionary.
BRIDGE = {'دسترسی': ['access'], 'احراز': ['authentication'], 'هویت': ['identity'],
    'رخداد': ['incident', 'event'], 'رویداد': ['event'], 'ثبت': ['logging', 'record'],
    'پایش': ['monitoring'], 'پشتیبان': ['backup'], 'بازیابی': ['recovery', 'restore'],
    'ریسک': ['risk'], 'خطر': ['risk'], 'دارایی': ['asset'], 'آموزش': ['training'],
    'رمزگذاری': ['encryption'], 'خط': ['policy'], 'مشی': ['policy'], 'تداوم': ['continuity'],
    'فیزیکی': ['physical'], 'آسیب': ['vulnerability'], 'پذیری': ['vulnerability'],
    'تامین': ['supply'], 'تأمین': ['supply'], 'ابری': ['cloud'], 'گواهی': ['certificate']}

def tokens(value, expand=False):
    normalized = unicodedata.normalize('NFKC', value).casefold().translate(str.maketrans({'ي':'ی','ك':'ک','\u200c':' '}))
    words = re.findall(r'[^\W_]+', normalized, flags=re.UNICODE)
    if expand:
        words += [word for token in list(words) for word in BRIDGE.get(token, [])]
    return words

class Search:
    def __init__(self, catalog):
        self.controls = list(index_catalog(catalog).values())
        self.docs, self.df = [], Counter()
        for control in self.controls:
            body = ' '.join([control['id'], control['title'], control['description'],
                str(control.get('metadata', {}).get('legacy_id', '')),
                *[ao['text'] for ao in control['assessment_objectives']]])
            counts = Counter(tokens(body))
            self.docs.append((counts, sum(counts.values())))
            self.df.update(counts.keys())
        self.average = sum(length for _, length in self.docs) / len(self.docs)

    def shortlist(self, query, k=15):
        require(isinstance(k, int) and not isinstance(k, bool) and k > 0, 'k must be a positive integer')
        terms = set(tokens(query, expand=True))
        results = []
        n = len(self.docs)
        for control, (counts, length) in zip(self.controls, self.docs):
            strength = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                idf = math.log(1 + (n - self.df[term] + .5) / (self.df[term] + .5))
                strength += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / self.average))
            if strength <= 0:
                continue
            evidence = [{'id': ao['id'], 'text': ao['text'], 'source': ao.get('source', {})}
                for ao in control['assessment_objectives'] if terms & set(tokens(ao['text']))]
            results.append({'scf_id': control['id'], 'title': control['title'], 'description': control['description'],
                'retrieval_score': round(strength, 6), 'ao_matches': evidence,
                'decision': 'CANDIDATE_ONLY', 'metadata': control.get('metadata', {})})
        return sorted(results, key=lambda row: (-row['retrieval_score'], row['scf_id']))[:k]
