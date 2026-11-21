# Usage

Run commands from the repository root or use the installed scf-toolkit command with the same arguments.

## 1. Verify the included example

~~~bash
python skills/scf-mapping-translation/scripts/run.py validate --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json
python skills/scf-mapping-translation/scripts/run.py build-xlsx --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json --out local-data/demo.xlsx
python skills/scf-mapping-translation/scripts/run.py check-xlsx --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json --xlsx local-data/demo.xlsx
~~~

Expected structural statuses are READY_FOR_EXPORT and SAVED_XLSX_VERIFIED. They do not certify semantic correctness. The fixture intentionally has two independent obligations: one mapped, one no-match. Its reviews are explicitly synthetic.

## 2. Prepare real source inventory

Create documents and requirements as shown in examples/synthetic/inventory.json. Give each issuing document a source_id, version and original SHA-256. Preserve exact source wording, original parent numbers, physical PDF pages and any exact common preamble. Verify ambiguous extraction against source images before recording a source review.

Create atomic obligations using the independent-pass/fail test. Keep exact ordered fragments and inherited context; use a disclosed composite only when contiguous quotation is impossible. Distinguish absent qualifiers from invented ones. Store the inventory fingerprint and SCF catalog fingerprint in ledger metadata; update the metadata only after consciously reviewing changed inputs.

## 3. Discover and adjudicate candidates

~~~bash
python skills/scf-mapping-translation/scripts/run.py shortlist --catalog local-data/scf-2026.2.json --query "کنترل دسترسی فیزیکی" --k 15 --out local-data/candidates.json
~~~

BM25 includes AO text. The Persian bridge is a small retrieval aid, not a general translator or morphological analyzer. Empty/weak results require broader queries and manual domain/AO review. Never convert retrieval_score into relationship strength or accept only the top candidate without comparison.

For each obligation, record the actual search scope and candidate decisions. Retain exact selected AO/control quotations, alternatives, containment/difference evidence, strength reasoning and review attestations. Pinned profile vocabulary prevents silent Equal/Equal To or rationale conversion. Whole-number strengths 5–10 are preferred; genuine 1–4 fallback requires reviewed alternatives. No-match retains the obligation with blank SCF/score fields.

Each mapped obligation also needs combined coverage reasoning and an explicit residual-clause list, even if empty. These are recorded review results, not an automated set-union proof. Pending decisions block release. See [the complete data contract](../skills/scf-mapping-translation/references/data-contract.md).

## 4. Validate and export

~~~bash
python skills/scf-mapping-translation/scripts/run.py validate --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --report local-data/validation.json
python skills/scf-mapping-translation/scripts/run.py build-xlsx --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --out local-data/mapping.xlsx
python skills/scf-mapping-translation/scripts/run.py check-xlsx --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --xlsx local-data/mapping.xlsx
~~~

Validation stops on the first blocking data error and reports its cause; fix it and rerun. The output has exactly one visible STRM Mapping sheet with the canonical ten columns. Names/descriptions are copied from the frozen catalog. Source/child/page markers and residual explanations go in Notes. IDs are literal text and scores numeric. The exporter preserves a source preamble only on the first displayed parent row, with inherited context retained internally.

An optional --template must have the exact ten headers on row 1 and ten unmerged columns. It is read as input; the output must be a different file. Extra source-template sheets are not exported. The exporter resets hidden dimensions and canonical text styling; saved-file verification rejects hidden rows/columns, formulas, hyperlinks, changed values and unreadable text colors. Value reconciliation is not a full visual-layout or print-fidelity audit; long source text may require expanding row heights in Excel for comfortable reading.

Writes are staged to a temporary file, reconciled, then atomically moved to the output path. A failed export must not replace an existing final workbook. The default SCF Description remains original English; reviewed translations remain a separate bilingual dataset unless a distinct display workflow is explicitly implemented and verified.

## 5. Translate and review

Use the skill's translation instructions to produce faithful Persian units. The CLI supplies terminology and QA, not an LLM translator.

~~~bash
python skills/scf-mapping-translation/scripts/run.py lookup --references local-data/references --text "Access Control Policy and authentication are required."
python skills/scf-mapping-translation/scripts/run.py translation-qa examples/synthetic/translations.jsonl
python skills/scf-mapping-translation/scripts/run.py translation-qa local-data/translations.jsonl --references local-data/references --report local-data/translation-qa.json
~~~

Every translated unit needs an honestly recorded semantic review. Term decisions must point to eligible reference entries with matching source phrases, context rationale and verbatim Persian equivalents. A lower-tier supplementary choice behind an AFTA candidate requires a documented sense mismatch. Held records cannot support translation. Unknown/proposed terms should be documented separately as non-approved; do not fabricate an entry ID.

Identifier, number and negation checks are heuristic and may overflag legitimate forms or miss errors. A clean result still requires a complete semantic/terminology review. READY_FOR_SEMANTIC_REVIEW is a QA state, not permission to claim expert certification.

## Exit codes

0: the requested machine-checkable operation succeeded. 1: data validation, export or QA requires correction/review. 2: CLI usage error. Model review and human review must remain explicitly distinguished.
