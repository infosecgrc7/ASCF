# Security and data handling

The toolkit runs locally and makes no network calls. Imported source text is treated as data; the CLI does not execute it. Excel output strings remain literal text, including formula-like values, and saved output is reconciled after writing.

Keep private documents, reference books, translation datasets and mappings in an ignored directory outside the public payload. Checksums detect accidental drift; they are not signatures and do not authenticate a reviewer. Untrusted workbooks should be handled in a suitable isolated environment with current dependencies.

If you find a defect, provide a synthetic reproducer without credentials or private source data. Once a repository exists, use its owner's private reporting channel for sensitive details. No support email or private reporting address is invented by this release.
