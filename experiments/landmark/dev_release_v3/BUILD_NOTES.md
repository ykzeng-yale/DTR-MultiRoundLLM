# dev_release_v3 build notes

Built by `scripts/build_dev_release_v3.py` (source-only: ast parsing and literal_eval; no candidate, reference or control was executed; no model requests).

- Roster (fixed order): 918, 825, 842, 816, 895, 868, 288, 154, 863, 966, 652, 651, 499, 974.
- Retained: 14; held: 0 (see exclusions.json; no backfill).
- MBPP source sha256 `ccf64ceae9c5403bf50a044cb6d505bfd2a2963ee58338ba268fd65beab92a9f`; public example = test_list[0], private = test_list[1:] verbatim.
- Prompts copied verbatim from the public-specification table of `docs/e12_contract_review_20260922.md` (sha256 `eceae0c5e9d3c541ecc5ee20d2da1be790662b9880f78090d4d3c1281e6a5cbc`), including the 288 general-modulus amendment.
- public_context = interface line + the v2 format instruction + one rendered public example (diagnostic.render_public_examples).
- One source-designed wrong control per root; controls_rationale.json records a static hand trace showing each fails at least one private assertion. Controls compile and pass hack_gate.
- Deviation from the suggested control list: 825 uses 1-based indexing (the suggested sorted-index control passes both private cases, whose index lists are already sorted); 868 returns the word count (the suggested first-word control passes both private cases, 'PHP' and '').
- config.json and release_manifest.json are written by integration, not this builder.
