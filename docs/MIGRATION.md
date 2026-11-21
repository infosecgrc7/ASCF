# Migration from earlier materials

This is a new integrated 1.0.0 package, not a renaming of every earlier skill version. Keep old inputs and outputs immutable for traceability.

| Earlier material | Retained or improved | Deliberately changed |
| --- | --- | --- |
| Mapping v7 | Independent obligations, source/child identities, 5–10 preference, 1–4 fallback, no-match accounting and one ten-column sheet | Canonical rows replace partially checked output_rows; source text and selected AO evidence are checked; the saved Excel is reopened and reconciled |
| Gold v3 local design | Local workbook extraction, AO-aware Unicode search, explicit qualifiers, counterexample review and residual-gap reasoning | No automatic latest-version switching; no silent rationale rewriting; no multi-sheet final output; no claim that recorded union reviews automatically prove coverage |
| Translation v2 | AFTA-first authority, strict 759/43 supplementary filter, source/page/evidence provenance and heuristic QA | Private reference import replaces bundling full books into the public ZIP; runtime schema and CLI are unified |

## Review old ledgers before migration

Do not copy approval flags as proof of fresh review. Create the new inventory and obligations, preserve original legal IDs and assign distinct source IDs for different documents. Transfer decisions only after verifying source wording, SCF version/IDs, selected AO associations, all qualifiers, actual alternative comparisons and strength rationale.

Mapping-v7 output_rows are not directly schema-compatible. The new representation derives all ten columns from mappings and the catalog. Its optional output_rows must exactly equal that canonical sequence. Arbitrary title, description, relationship, rationale or score edits are blocked.

Gold's 5–10-only filter and multi-sheet output are not the current project rules. New output uses the v7 fallback/no-match protocol and single-sheet layout. Equality spelling and rationale are explicit profile values: they are not silently converted during export.

The real SCF 2026.2 source used during local preparation contained eight AO-ID-prefix differences. Associations were preserved from the source control column, documented and not guessed from ID spelling. A future edition must be imported and reviewed on its own evidence.

## Deferred capabilities

Transitive mapping, inverse mapping, automatic legacy-ID migration, multi-sheet Annex exports, OCR and model-provider integrations are not implemented by this release. A prior document describing them does not mean they are tested runtime features. Add them only with an explicit data contract and observable end-to-end tests.
