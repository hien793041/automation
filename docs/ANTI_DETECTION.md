# Anti-Detection Strategy

## Multi-Layer Defense

| Layer | Technique | Risk |
|-------|-----------|------|
| Process | No game modification | Undetectable |
| Memory | No injection/hook | Undetectable |
| Network | Normal request pattern | Low |
| Input | Windows PC input (`win32gui` + `pyautogui`) | Low |
| Timing | Distribution-based delays | Medium |
| Behavior | Fatigue, distraction, errors | Medium |
| Device | PC client, no emulator | Low |

## Biometric Profile

Each bot instance uses ONE consistent profile, loaded from `config/humanization.yaml` or an optional JSON timing profile:

- Timing distributions (`reaction_time`, `click_interval`, `decision_time`, ...)
- Movement profile (Fitts's-law Bezier paths, jitter)
- Fatigue / distraction / misclick rates

`DecisionEngine` is shared between `StateMachine`, `PCInput`, and every `BaseAction`, so fatigue and frustration accumulate consistently across the whole session instead of resetting per action.

## Recommendations

1. Run during realistic hours (evening heavy)
2. Take natural breaks
3. Vary session lengths realistically
4. Never play 24/7 without variation
