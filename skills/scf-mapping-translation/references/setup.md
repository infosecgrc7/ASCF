# Importing authorized references

The toolkit runs locally with Python 3.11+ and openpyxl 3.1.5+. No API key or automatic download is used. Install dependencies from the repository requirements.txt, or install the project package. When this skill folder is copied to an agent's skills directory, its scripts and references remain self-contained; run scripts/run.py by absolute path and choose your own private data directory.

## SCF workbook

Acquire the desired edition from the SCF publisher or your authorized project source. Preserve its original license and content. From this skill folder:

~~~bash
python scripts/run.py import-scf --xlsx /path/to/authorized-scf.xlsx --scf-version 2026.2 --out /path/to/private/scf-2026.2.json
~~~

The exact versioned SCF and Assessment Objectives sheets are required. The importer searches the first twenty rows for headers and preserves source text and row/column provenance. It blocks orphan/duplicate IDs and missing AO coverage. It records an AO-ID-prefix difference while preserving the source control-column association. Review source notes before using affected evidence. No version is upgraded automatically.

## Glossaries

Use the final supplied AFTA JSON and the two originally uploaded supplementary files. From this skill folder:

~~~bash
python scripts/run.py import-glossaries --afta /path/to/AFTA_Approved_Glossary_Final.json --supplementary /path/to/Cybersecurity_Glossary_FA.json --markdown /path/to/Cybersecurity_Glossary_FA.md --out /path/to/private/references
python scripts/run.py lookup --references /path/to/private/references "Access Control" "Cybersecurity Governance"
~~~

The supplementary importer pins the reviewed 802-record release: exactly 759 true-flagged records and 43 excluded records. It compares JSON and Markdown, archives original files byte-for-byte and writes a fingerprint manifest. A different source release needs an explicit importer/data review. Full archives stay private and audit-only; runtime references expose only eligible data and held metadata. Do not publish the book extraction without permission.

## Working inputs

Prepare a frozen source inventory and a separate reviewed ledger using the data-contract reference. Source documents and their private data should remain outside the public repository. The original document SHA-256 is supplied in the inventory; verify it against the actual source before recording source-review approval. The validator checks source fragments against the frozen inventory, not against PDF images.

Run shortlist for each obligation; review candidates and AO quotations. Run validate, then build-xlsx, then check-xlsx against the same frozen files. The repository's docs/SETUP.md and docs/USAGE.md provide the same commands from the repository root and a complete synthetic walkthrough. These root documents are optional when the skill is installed independently.
