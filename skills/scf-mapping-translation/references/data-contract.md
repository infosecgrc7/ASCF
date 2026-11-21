# Data contract (schema version 1.0)

Use examples/synthetic as an executable complete fixture. The JSON examples are intentionally fictional and do not quote a real SCF catalog or regulatory publication.

## Catalog

schema_version, scf_version, source (filename, SHA-256, sheets), counts and controls[]. A control has id, title, description, metadata, source coordinates and assessment_objectives[]. Each AO has id, text, source_control_id and source coordinates. Source text is preserved exactly. Duplicate control/AO IDs, orphan AO references, missing versioned sheets and missing AO coverage block workbook import.

## Source inventory

documents[] requires source_id, title, issuer, version and SHA-256 of the original source. requirements[] requires source_id, fde_id, name, text_exact and positive physical PDF pages[]. Optional preamble_exact must appear in the source text. The identity is (source_id, fde_id), not fde_id alone. Inventory fingerprint is stored separately in the ledger; verify the source-file fingerprint before recording source-review approval.

## Ledger

metadata contains scf_version, catalog_sha256, inventory_sha256 and profile: equality_label (Equal or Equal To), rationale (Functional or multi_basis), methodology_url. Arrays: obligations, search_reviews, mappings, no_matches, coverage_reviews and pending (must be explicitly empty for export).

An obligation requires id, source_id, fde_id, text_exact, source_fragments[], description_mode (verbatim_excerpt/composite), source_pages[], five_tuple, testable_outcome, independent_pass_fail_test and source_review. five_tuple has string actor, action, target_scope, frequency_trigger and jurisdiction_qualifier; absent qualifiers are empty strings. applicable_parent_context preserves any inherited preamble. Verbatim text equals one exact source fragment; composites preserve ordered exact fragments and require composite_rationale. Composite display is labelled in Notes.

A review requires status=APPROVED, method=human or model, reviewer, timezone-aware reviewed_at and notes. These fields record an attestation, not authenticated reviewer identity. Never fill them merely to pass a check.

Each search_review names an obligation, query, search_scope, candidates[] (scf_id, disposition ACCEPTED/REJECTED, reason and score for accepted candidates) and review. Every accepted candidate must have exactly one corresponding mapping. No-match obligations need all recorded candidates rejected. A shortlist is not an exhaustive search; document the actual scope and review domain alternatives.

Each mapping has obligation_id, scf_id, relationship, rationale, score, shared_mandatory_clause, fde_only_clauses, scf_only_clauses, decision_reason, semantic_review, score_review and selection_review. selection_review includes scope, decision, selected_evidence[] (exact quote with optional ao_id) and alternatives[] (scf_id, reason). Equality/subset also require falsification_check with counterexample_found=false and reason. Coverage_reviews name obligation_id, covered_by[], residual_clauses[], reason and review. no_matches contain obligation_id, reason and review. They never carry a fake control/score.

## Canonical output

Exactly ten keys in each optional output_rows record, in order:

1. FDE #
2. FDE Name
3. FDE Description
4. STRM Rationale
5. STRM Relationship
6. SCF Control
7. SCF #
8. SCF Description
9. Strength of Relationship
10. Notes

No internal child-ID column is exported. Source/child/page markers are in Notes. If output_rows is supplied, it must equal the derived sequence exactly. Export itself always derives the values from approved decisions and the frozen catalog. The Excel checker opens the actual saved file and verifies one visible sheet, ten exact headers, row counts, literal text/IDs, numeric scores and every value.

## Translation units (JSONL)

Each line: id, source_en, translation_fa, status (TRANSLATED/NEEDS_CONTEXT), semantic_review for translated units, and optional term_decisions[]. A term decision requires entry_id, authority, source_en_phrase and context_rationale; rejecting a matching AFTA candidate for a supplementary sense additionally requires afta_sense_mismatch_reason. Source Persian strings must remain present verbatim. Pass --references to verify decisions against eligible data. No source entries or terms are updated by QA.
