# Step 81C Final Config Fix

The remaining three failures are caused by the experiment loader requiring
`home_field_advantage` and `probability_scale` in every experiment row.

Run:

```powershell
python .\scripts\apply_step81c_final_config_fix.py
python -m ruff check .
python -m pytest
```

Then verify:

```powershell
python -c "from pathlib import Path; from gridiron.experiments.config import load_experiments; x=load_experiments(Path('config/experiments.toml')); print('COUNT:',len(x)); [print(e.name,e.home_field_advantage,e.probability_scale,e.travel_miles_weight,e.travel_time_zone_weight) for e in x]"
```

Expected: `COUNT: 9`.

If green:

```powershell
python ship.py research --profile modern
```

Expected: 36 total research runs.
