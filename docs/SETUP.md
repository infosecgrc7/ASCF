# Setup

## Requirements

- Python 3.11 or newer.
- openpyxl 3.1.5; a reproducible requirements file is provided.
- No model API, credentials or automatic network download.

~~~bash
python -m venv .venv
~~~

Activate the environment using the command appropriate to your shell, then:

~~~bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -q
~~~

The CLI also works directly without installing the project. Installing it with python -m pip install . adds the scf-toolkit command. The wheel contains only the Python package; agent instructions remain in the repository's skills folder.

## Install the agent skill

Copy the complete skills/scf-mapping-translation folder to your agent's supported skill directory. Preserve scripts/scf_toolkit and references. Use an absolute path to scripts/run.py when calling it from another working directory. The skill can operate independently with user-selected input paths; synthetic examples live in this repository and are optional.

## Import SCF and AO data

Obtain an authorized original workbook and pin the edition explicitly. Replace the source path below with your local input; keep outputs in ignored local-data.

~~~bash
python skills/scf-mapping-translation/scripts/run.py import-scf --xlsx /path/to/authorized-scf.xlsx --scf-version 2026.2 --out local-data/scf-2026.2.json
~~~

The importer requires matching SCF and Assessment Objectives versioned sheets. It discovers headers in the first twenty rows. Duplicate IDs, orphan objectives, missing source text or missing AO coverage stop import. Source text is unchanged; normalized strings are used only for header discovery and search.

Source-association notes preserve cases where an AO ID prefix differs from the source control-column value. Review these notes before relying on affected evidence. The importer follows the explicit source column and does not silently repair IDs.

## Import terminology

Use the supplied final AFTA JSON and the original 802-entry supplementary JSON/Markdown pair:

~~~bash
python skills/scf-mapping-translation/scripts/run.py import-glossaries --afta /path/to/AFTA_Approved_Glossary_Final.json --supplementary /path/to/Cybersecurity_Glossary_FA.json --markdown /path/to/Cybersecurity_Glossary_FA.md --out local-data/references
python skills/scf-mapping-translation/scripts/run.py lookup --references local-data/references "Access Control" "Cybersecurity Governance"
~~~

The operational reference contains 759 original boolean-true records; 43 held records stay excluded. The importer checks JSON/Markdown consistency, count/allowlist agreement and provenance fields. It preserves original inputs byte-for-byte and pins all derived reference files by SHA-256. Reimporting a different frozen input over an existing directory is refused; use a new directory and review the change.

## Data boundaries

local-data, private source documents, full glossary books, workbooks, translation memories and real mappings are not packaged in the public release. Do not move them into tracked directories. The public example uses fictional control IDs and source text. Third-party terms, including restrictions on adapted SCF content, apply separately from this project's rights-reserved notice.
