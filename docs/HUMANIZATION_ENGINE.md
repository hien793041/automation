# Humanization Engine

## Philosophy

> Humanization is NOT adding random noise.
> Humanization is SIMULATING the statistical distribution of real human behavior.

## Components

### Timing Engine
Samples delays from fitted distributions:
- Gaussian: reaction time, decision time, transition/menu waits
- Log-normal: click intervals
- Exponential: break durations
- Bimodal: session lengths

Default distributions are defined in `src/rokbot/humanization/timing_engine.py` and can be overridden via `config/humanization.yaml` or a JSON profile.

### Movement Engine
- Quadratic Bezier curves with perpendicular control offset
- Fitts's Law for movement duration
- Micro-jitter per point

### Decision Engine
- Fatigue: sigmoid curve after 2h
- Distraction probability increases with fatigue
- Misclick and change-mind rates
- Shared across StateMachine, PCInput and all actions for consistent cognitive state

### Error Simulator
- Injects realistic misclicks near the intended target
- Occasional wrong-button selection when alternatives exist

### Session Manager
- Schedule-aware activity probability
- Bimodal session lengths
- Poisson break intervals

### BaseAction Integration
Every action inherits humanization helpers from `BaseAction`:

- `human_delay(distribution, fallback_seconds, min_seconds)` — sleep using the configured timing distribution.
- `pre_action_delay()` — short reaction delay before a step.
- `post_action_delay()` / `decision_delay()` — common pause types.
- `random_point_in_bbox(bbox, jitter_sigma, edge_margin)` — pick a click target with optional Gaussian jitter and edge margin.
- `humanized_tap(x, y, ...)` / `humanized_tap_match(match, ...)` — tap and then apply a humanized post-click delay.
- `record_success()` / `record_error()` — feed the shared DecisionEngine so fatigue/frustration evolve realistically.

### Action-Layer Coverage
All actions use the shared timing engine instead of hard-coded `time.sleep(random.uniform(...))`:
- `barbarian_attack`, `gather`, `gather_gem`
- `scout`, `train_troops`, `rally_fort`
- `scout_cave_high`, `scout_cave_low`
- `alliance_help`, `villager_help`, `reconnect`, `dynamic_combo`

Map navigation (`_ensure_in_city`, `_ensure_in_world`) also uses humanized transition waits and jittered click points.

## Configurable Timing Distributions

`config/humanization.yaml` exposes:
- `reaction_time` — quick pause before/after a tap
- `click_interval` — pause between consecutive clicks
- `decision_time` — longer "thinking" pause
- `menu_wait` — waiting for menus/popups to settle
- `transition_wait` — map transitions, screen loads
- `post_error_wait` — pause after ESC/error reset
- `break_duration` — session break length

## Validation

- Timing: KS-test p > 0.05 vs human
- Movement: DTW distance < threshold
- Session: Chi-square p > 0.05
