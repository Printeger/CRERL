# Demo 3 Utility Freeze Contract

- Utility metric id: `U_task_v1`
- Utility hash: `58752338d4a4966a2b86b4269148a9447d75361e26b9f2b48186b0010b7bc383`

```text
U_task_v1 =
  0.40 * success_flag
  -0.25 * collision_flag
  -0.15 * timeout_flag
  + 0.10 * clearance_score
  + 0.10 * time_efficiency_score
  + 0.10 * path_efficiency_score
```

The utility metric is frozen across clean, injected, and repaired.
