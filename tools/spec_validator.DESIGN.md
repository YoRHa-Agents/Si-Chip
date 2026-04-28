# tools/spec_validator.py — Interface Design (DESIGN-only)

> Stage S1 (design only). Implementation is owned by S2 wave W2.C; this document only freezes the
> CLI contract, exit semantics, and the eight machine-checkable assertions the validator must emit.
> Authoritative spec: `.local/research/spec_v0.1.0.md` §13.4 ("Machine-checkable items").

---

## 1. Purpose

`tools/spec_validator.py` is the static checker that turns spec §13.4's "machine-checkable items"
into a CI-callable script. It loads `.local/research/spec_v0.1.0.md` (or a `--spec` override) and
asserts that the frozen Normative content (§3, §4, §5.3, §6.1, §7.2, §8.1, §8.2, §11.1) still
matches the structural invariants below. It does NOT execute the dogfood loop, the router test,
or any metric collection; it only verifies that the spec text itself remains structurally sound.

---

## 2. CLI Contract

```
python tools/spec_validator.py [--spec PATH] [--strict] [--json]
```

| Flag | Default | Behavior |
|---|---|---|
| `--spec PATH` | `.local/research/spec_v0.1.0.md` | Path to the spec markdown to check |
| `--strict` | off | Treat any warning (e.g. duplicate trailing whitespace, table column drift below the assertion threshold) as a failure; without `--strict` only the eight invariants below trigger non-zero exit |
| `--json` | off | Write a machine-readable JSON report to stdout (schema in §4); when set, no human-readable text is written to stdout (warnings still go to stderr) |

---

## 3. Assertions (one per spec §13.4 item, eight total — VERBATIM)

The validator MUST emit exactly the following eight assertions; each maps 1:1 to a spec §13.4
machine-checkable item. Wording is fixed so CI grep checks remain stable.

1. `BasicAbilityProfile` schema field set matches spec §2.1 (count + names)
2. R6 metric key set has exactly 28 entries across 7 dimensions per spec §3.1
3. Threshold table (§4.1) has exactly 21 numeric cells across 7 metrics × 3 profiles, each row strict-monotone
4. Router-test matrix has exactly 8 cells (MVP) and the Full has 96 (`6×4×4`) per spec §5.3
5. Value vector has exactly 7 axes per spec §6.1
6. Platform priority is exactly Cursor → Claude Code → Codex per spec §7.2
7. Self-Dogfood protocol §8.1 has exactly 8 ordered steps and §8.2 lists exactly 6 evidence files
8. §11.1 forever-out list contains exactly: marketplace, router-training, IDE-compat, MD-to-CLI converter

> Note on count rationale for assertion 3: spec §4.1 lists 10 metric rows × 3 profile columns = 30
> numeric cells in total, but only 7 of those rows are referenced in §13.4 as the "threshold
> table" (the four task / trigger / footprint / latency rows plus three routing rows). The
> validator MUST read the §13.4 wording verbatim ("21 numeric cells across 7 metrics × 3 profiles");
> if a future spec bump revises §4.1 row selection, the assertion text in this document must be
> updated together with the spec-version bump per spec §12.2.

---

## 4. Return Contract

- **Exit code 0**: all eight assertions pass.
- **Exit code > 0**: at least one assertion failed; specifically:
  - `1`: one or more of assertions 1-8 failed.
  - `2`: spec file not found, unreadable, or front-matter malformed.
  - `3`: `--strict` was set and a non-fatal warning fired.
- **stderr (always)**: a structured one-line-per-failure summary in the form
  `FAIL [N] <assertion text> :: <observed> != <expected>` so it stays grep-friendly.
- **stdout**:
  - default mode: a short human-readable PASS/FAIL banner plus, on failure, a copy of the stderr
    summary; on success a single `OK spec_v0.1.0 8/8 invariants` line.
  - `--json` mode: a JSON object written to stdout with the following schema:
    ```json
    {
      "spec_path": "<resolved path>",
      "spec_version": "<from frontmatter>",
      "exit_code": <int>,
      "results": [
        {"id": 1, "name": "<assertion text>", "passed": true|false,
         "observed": <any>, "expected": <any>, "detail": "<optional string>"},
        ...
      ]
    }
    ```
    Length of `results` MUST equal 8.

---

## 5. Implementation Note

The implementation lands in S2 wave W2.C. This DESIGN doc only locks the interface so any
parallel work in S2 (Skill body, scripts, CI wiring) can wire to a stable command without waiting
for the validator code. The implementation MUST NOT add additional invariants without first
bumping spec §13.4 and refreshing this document together with `.rules/si-chip-spec.mdc`.
