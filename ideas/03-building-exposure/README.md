# 03 — Building exposure (OBAT and EMS grades)

**Owner / branch:** assign at kickoff.

**Question:** Which building points intersect the chosen event definition, and what can actual EMS grading say separately?

**Start with:** Annex 2; `data/reference/obat_*_database_profile.json`, `ems_damage_grades.csv`, `graded_asset_audit.csv`, and the country GeoPackages. Use `python scripts/query_obat.py --country be --limit 5` for a read-only database example.

**Output:** A table with unique point IDs, `use` class, geography, event definition and grade source where available. Produce `figures/generated/03_*.png`. Do not call an intersection a damaged home; flag the Belgian inventory limitation.
