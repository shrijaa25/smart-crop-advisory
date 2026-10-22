# Agricultural knowledge data

The engine will initially support **tomato** and **chilli** only.

Keep source documents unchanged under `data/raw/` if you choose to copy them here.
Normalized, machine-readable rules will be stored under `data/processed/`.

Planned datasets:
- `crop_stage_rules.csv` — crop stages, day ranges, stage names and source references.
- `fertilizer_schedule.csv` — crop, stage/day range, fertilizer, amount, unit, area basis,
  application method, frequency, source and verification status.
- `disease_treatment_rules.csv` — crop, disease/pest, treatment, label directions,
  restrictions, source and verification status.
- `irrigation_rules.csv` — crop/soil/stage water guidance and source.
- `task_templates.csv` — inspection, weeding, irrigation and other task templates.

Important:
- The supplied tomato/chilli documents have different schedule formats and may use
  different units, varieties, production systems or assumptions.
- Do not combine or convert these schedules silently.
- Do not issue automatic pesticide/fertilizer instructions until the source, units,
  crop applicability, product label and local agronomist review are checked.
- Store the exact source page/section for every normalized rule.
