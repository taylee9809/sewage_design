# Contributing a country's standard

The goal of this project is for every country's sewer design standard to sit side by side, so engineers anywhere can design against and compare all of them at once. You don't need to touch the engine to add yours. A standard is data plus a rules file.

If you know your country's standard, you are the right person to add it. Open an issue first, naming the standard and edition, so others don't duplicate the work.

## Ground rules

1. **Encode the text literally.** Write each value exactly as the standard states it, with its clause number. Don't fill a gap with common practice. If the standard is silent, resolve it only from other clauses of the same standard, or mark it `unspecified`.
2. **Respect copyright.** Check whether the standard's text may be redistributed:
   - `full_text`: statutes, regulations, or documents whose terms permit reproduction. You may add clause text and short quotes.
   - `values_only`: everything else. Add values and clause numbers only, and leave `quote_short` empty.
   - If you aren't sure, use `values_only`.
3. **One source per value.** Every row needs `source_url` and `retrieved_at`.

## Steps

Use an existing country as a template. Colombia (`CO_RAS_0330_2017_COMP2021`) is the most complete example.

### 1. Register the standard: `criteria/standards.json`

Add one entry keyed by a `standard_id` of the form `<CC>_<SHORT_NAME>_<EDITION>`:

```json
"XX_EXAMPLE_2025": {
  "country": "XX", "issuer": "...", "title": "...", "edition": "2025",
  "effective_date": "2025-01-01", "is_latest": true, "access": "free",
  "source_url": "https://...", "redistributable": "values_only",
  "license_note": "where the redistribution terms come from"
}
```

### 2. Add the values: `criteria/<country>_sewer.csv`

Columns:

```
standard_id,param_key,condition,value_min,value_max,value_text,unit_orig,value_si,unit_si,clause_no,clause_title,binding,binding_raw,quote_short,source_url,retrieved_at,note
```

- `param_key`: use an existing key where one fits (`min_velocity`, `min_slope`, `max_depth_ratio`, `min_pipe_diameter`, `min_cover`, `manhole_max_spacing`, `peak_factor_hourly` ...). Run `cut -d, -f2 criteria/*_sewer.csv | sort -u` to see them all.
- `condition`: when the value applies, as the standard words it (pipe size, material, system type ...).
- `binding`: `mandatory`, `standard`, or `guide`. Keep the original wording ("shall", "should") in `binding_raw`.
- Pump-station values go in `criteria/<country>_pump_sewer.csv` with the same columns.

### 3. Tag conditions and basis: `criteria/normalized/<country>.jsonl`

Run the loader once. It writes `criteria/normalized/_rows_for_tagging.jsonl` with a stable `row_key` for each row. For each of your rows, add one line:

```json
{"row_key": "...", "condition": {"system": "separate", "dia_mm": {"ge": 200}}, "basis": {"flow": "design_peak_hourly", "horizon": "ultimate", "hydraulic_state": "partial"}, "tag_note": "why"}
```

The `basis` says which flow and pipe state the value is defined under. It is what keeps comparisons honest: a minimum velocity at full flow is not the same rule as one at design depth. The vocabulary is in [db/vocabulary.md](db/vocabulary.md). If you need a new key or value, propose it in your pull request.

### 4. Describe how to apply it: `criteria/rules/<standard_id>.json`

The rules file tells the engine how your standard is applied: velocity limits, slope tables, capacity, minimum diameter, cover, junctions, manhole spacing, and how design flow is built up. There are 13 rule types; copy them from the existing files. Every interpretation goes in a `resolution` field together with the clause it comes from.

If your standard needs a rule the engine doesn't have, open an issue. New rule types are added in a country-neutral way. The test `test_no_country_branches_in_generic_engine` fails if a country name appears in the core engine.

### 5. Add real pipe products: `criteria/pipe_catalog/<cc>_pipes.csv`

List the nominal and inner diameters of pipes actually sold in your country, from a manufacturer catalog or a product standard. The engine sizes pipes by inner diameter.

### 6. Run the comparison

Add your standard to `criteria/projects/SYN01.json`, including any project-level choices where your standard gives a range or no number, each with a `rationale`. Then:

```bash
py -3 db/load_criteria.py <DSN>
SEWAGE_DB_DSN=<DSN> py -3 -m pytest tests
SEWAGE_DB_DSN=<DSN> py -3 -m engine.report SYN01 docs/SYN01_design_criteria_report.md
```

Check that your column in the report makes sense to an engineer from your country.

### 7. Optional: clause text

If your standard is `full_text`, add `criteria/clauses/<name>.jsonl` (one clause per line, with `standard_id`, `clause_no`, `clause_title`, `body_text`, `page`, `source_url`). Figures and equations go in `criteria/assets/`.

## Pull request checklist

- [ ] `standards.json` entry with `redistributable` set and its source explained
- [ ] Every value row has a clause number, `source_url`, and `retrieved_at`
- [ ] No quotes or clause text from `values_only` standards
- [ ] Every row is tagged in `criteria/normalized/`
- [ ] Every interpretation in the rules file has a `resolution` with its clause
- [ ] Tests pass

## Other contributions

Corrections to existing values (with the clause), translations of the docs, and new rule types are all welcome. By contributing, you agree that your contribution is licensed under AGPL-3.0-or-later.
