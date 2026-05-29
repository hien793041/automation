# Humanization Engine

## Philosophy

> Humanization is NOT adding random noise.
> Humanization is SIMULATING the statistical distribution of real human behavior.

## Components

### Timing Engine
Samples delays from fitted distributions:
- Gaussian: reaction time, decision time
- Log-normal: click intervals
- Exponential: break durations
- Bimodal: session lengths

### Movement Engine
- Quadratic Bezier curves with perpendicular control offset
- Fitts's Law for movement duration
- Micro-jitter per point

### Decision Engine
- Fatigue: sigmoid curve after 2h
- Distraction probability increases with fatigue
- Misclick and change-mind rates

### Session Manager
- Schedule-aware activity probability
- Bimodal session lengths
- Poisson break intervals

## Validation

- Timing: KS-test p > 0.05 vs human
- Movement: DTW distance < threshold
- Session: Chi-square p > 0.05
