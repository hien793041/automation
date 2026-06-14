# Data Collection

> Note: The `scripts/record_human.py` recorder and `rokbot/telemetry/` package have been removed. Humanization parameters are now configured directly in `config/humanization.yaml` or loaded from an optional JSON timing profile.

## Distribution Fitting

If you have recorded timing data, fit distributions with:

```bash
python scripts/fit_distributions.py --input-dir data/human_recordings
```

## Storage

```
data/human_recordings/
  player_001/
    session_YYYY_MM_DD_HH_MM/
      screenshots/
      touch_events.jsonl
      timing_data.jsonl
      session_metadata.json
```

## Bot Telemetry

Runtime logs are written to `data/bot_telemetry/` via `loguru`. No separate telemetry collector is currently active.
