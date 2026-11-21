# Release verification — 1.0.0

Date: 2026-11-21. Measured local environment: Windows, Python 3.11, openpyxl 3.1.5.

## Results

| Check | Observed result |
| --- | --- |
| Regression suite | 50 tests passed; no failures |
| Python source parse | 15 project Python files parsed successfully |
| Skill frontmatter | Bundled skill-creator validator passed |
| Real SCF import | All 1,534 control names/descriptions and 5,956 AO IDs/text compared with the fingerprinted prior JSONL; all matched |
| AO source associations | Eight ID-prefix differences recorded; source control-column ownership preserved |
| Approved terminology | All 620 records and 205 declared-alias lookups checked |
| Supplementary reference | All 759 usable records retained with original fields; all 43 held IDs excluded from runtime results |
| Authority overlaps | 24 shared headings/aliases checked; AFTA retained result authority |
| Independent forward review | Actual synthetic CLI workflow and adverse inputs exercised; reported conditional-formatting defect fixed and independently rechecked |
| Saved XLSX | One sheet, ten columns, exact values/IDs/scores, literal formula-like strings, no hidden output or conditional-formatting concealment |
| Python packaging | Wheel built and installed into an isolated local target; installed CLI exercised |

Detailed machine evidence is in [release-validation.json](../qa/release-validation.json), [local-reference-validation.json](../qa/local-reference-validation.json), [independent-review.json](../qa/independent-review.json) and [unit-tests.txt](../qa/unit-tests.txt).

## What the public tests cover

Canonical output must agree with approved relationship, rationale, score and original SCF fields. Invalid labels/IDs, missing/extra output columns, invented source fragments, wrong-owner or fabricated AO quotes, unresolved reviews, missing inherited context, contradictory no-match/coverage dispositions, duplicate pairs and source/version drift are rejected.

Threshold regressions reject 1–4 including 4, 4.0 and "4.0", and accept 5, 5.0, "5.0" and 10. Booleans, nonfinite values, out-of-range values and fractions are rejected. Multiple documents may reuse a clause number without collision; repeated child mappings do not duplicate the parent preamble.

Terminology tests exercise true-only inclusion, AFTA-primary/alias priority, ambiguity retention, original-file preservation, source fingerprint drift, complete-heading lookup and exclusion of held records from translation decisions. Translation heuristics test missing review, empty input, identifiers, numbers and negation. A supplementary book definition is never rewritten as an approved AFTA entry.

Excel tests reopen the actual file, detect changed cells, hidden rows/columns, unreadable base text colors, conditional-formatting concealment and hidden number formats. Export resets inherited template visibility, filters and conditional styles. All display cells are derived; no arbitrary output-row metadata bypass exists.

## Visual and platform limits

A synthetic workbook preview was generated and inspected with the bundled spreadsheet renderer, and its imported values were inspected. The renderer process exited abnormally after producing the preview. This was not the toolkit's export engine. Native Excel rendering, Persian bidirectional layout and print fidelity have not been manually certified. Source values, RTL settings and saved workbook structures were checked; long cells may need row expansion in Excel.

CI is configured for Windows/Ubuntu with Python 3.11/3.13. Those remote runs have not happened yet. Do not display a passing CI badge or claim cross-platform execution until the destination repository workflow actually succeeds.

No full source-PDF transcription review, independent real regulatory mapping certification or quantitative semantic-accuracy benchmark was performed. Approval fields are honest review attestations, not authenticated proof of a review. The code validates the supplied inventory/catalog and cannot prove that the inventory itself correctly transcribes the original legal document.

Full licensed/private reference files are deliberately excluded from the public payload. Their import and local verification are tested separately. Source books, SCF translations and regulatory documents require their own distribution rights.

## Reproduce

~~~bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/audit_release.py
python scripts/build_release.py --out local-data/scf-mapping-toolkit-1.0.0.zip
~~~

Optional private-data checks use scripts/verify_local_data.py with explicitly supplied catalog, fingerprinted prior JSONL/manifest and reference directory. Public CI never needs those files.
