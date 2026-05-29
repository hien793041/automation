# Data Collection

## Human Recorder

Records:
- Touch events: x, y, pressure, action, timestamp
- Timing events: event_type, duration_ms, context
- Screenshots: timed captures

## Usage

```bash
python scripts/record_human.py --player-id player_001
```

## Distribution Fitting

After recording, fit distributions:

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
