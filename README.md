# sewage_design

English | [한국어](README.ko.md)

**Every country's sewer design standards as open data, and one engine that designs the same network under any of them.**

![Same sewer network designed under five national standards](docs/SYN01_five_standards.png)

The same 27-pipe network, designed with each standard's own clauses: excavation varies by 66% and maximum burial depth by 2.3x. Engineers rarely see these differences, because each standard lives in its own long document, in its own language.

## What this is

- **Standards as data.** Sewer design values from five countries, with every value traced to its source clause, its binding force (mandatory / standard / guidance), and the flow condition it is defined under.
  | Country | Standard | Edition |
  |---|---|---|
  | Korea | KDS 61 40 00 · 61 10 00 · 61 45 00 | 2025-10-01 |
  | United States | Ten States Standards (Recommended Standards for Wastewater Facilities) | 2026 |
  | Japan | Yokohama City Sewer Design Guideline · Sewerage Act Enforcement Order | 2026 |
  | India | CPHEEO Manual on Sewerage and Sewage Treatment Systems, Part A | 2013 |
  | Colombia | RAS, Resolución 0330 de 2017 (compiled 2021) | 2021 |
- **A country-agnostic engine.** The core engine (`generic.py`, `design.py`) contains no country names, and a test fails if one appears. Each standard is described by a rules file (`criteria/rules/<standard_id>.json`, 13 rule types) plus its values. Swap the standard set and the same network is redesigned.
- **Literal, not "practical".** Values are encoded exactly as the source text says. Where a standard is silent, the gap is resolved only from other clauses of the same standard, or left as `unspecified`. Common practice is never filled in.
- **Comparable, not merged.** Each value carries a `basis` (which flow, which time horizon, full or partial pipe). Two numbers are compared only when their basis matches, so the comparison table never puts an apple next to an orange.
- **Design criteria report.** `engine.report` writes the full comparison as Markdown: adopted values per standard, side-by-side table, design results, and the clause that governed each pipe's slope and size ([example](docs/SYN01_design_criteria_report.md), in Korean).

## Where this is going

1. **More countries, added by the people who use them.** Adding a country means adding data files, not changing code. See [CONTRIBUTING.md](CONTRIBUTING.md). The goal is for engineers anywhere to design against, and compare, all of the world's standards at once.
2. **The rest of the design workflow.** Pump stations (data collected for all five countries), then the remaining design steps.
3. **Water supply, then related fields.** The same method applied to water supply networks and other water infrastructure.

## Status

Early (first public release October 2026). The gravity sewer engine, the five standards above, and the report generator work. Pump-station values are in the data but not yet in the engine.

## Quick start

Requires Python 3.12+ and PostgreSQL.

```bash
py -3 db/load_criteria.py <public DB DSN> [<private DB DSN>]
SEWAGE_DB_DSN=<public DB DSN> py -3 -m pytest tests
SEWAGE_DB_DSN=<public DB DSN> py -3 -m engine.design SYN01
SEWAGE_DB_DSN=<public DB DSN> py -3 -m engine.report SYN01 docs/SYN01_design_criteria_report.md
```

## Layout

| Path | Contents |
|---|---|
| `criteria/standards.json` | One entry per standard: issuer, edition, access, redistribution terms |
| `criteria/<country>_sewer.csv` | Design values with clause number and binding force |
| `criteria/normalized/*.jsonl` | Normalized conditions and `basis` tags ([vocabulary](db/vocabulary.md)) |
| `criteria/rules/<standard_id>.json` | How the engine applies each standard, with the clause behind each resolution |
| `criteria/pipe_catalog/*.csv` | Real pipe products per country (nominal vs. inner diameter) |
| `criteria/clauses/`, `criteria/assets/` | Full clause text and figures, only where redistribution is permitted |
| `criteria/projects/<id>.json` | Project-level choices where a standard gives a range or no number |
| `engine/` | Hydraulics, generic engine, network, metrics, report |
| `tests/` | Regression tests using the standards' own tables as the answer key |

## Copyright of source standards

Full text is published only where redistribution is permitted: Colombia RAS (official legal text), Japan's Sewerage Act Enforcement Order (statutes are not copyrighted), CPHEEO (free reproduction with attribution), and the KDS 61 series (identical to the annex of Ministry of Environment Notice No. 2025-165, a government notice excluded from copyright protection under Article 7(2) of the Korean Copyright Act). For Ten States and Yokohama, only values and clause numbers are published. Copyright in every standard remains with its issuer.

- CPHEEO, Manual on Sewerage and Sewage Treatment Systems, Part A: Engineering (2013), Ministry of Housing and Urban Affairs, Government of India.
- Great Lakes – Upper Mississippi River Board, Recommended Standards for Wastewater Facilities, 2026 Edition.
- Ministerio de Vivienda, Ciudad y Territorio (Colombia), Resolución 0330 de 2017 (RAS), texto compilado.

## License

AGPL-3.0-or-later ([LICENSE](LICENSE)).
