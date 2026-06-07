# Data And Safety

All demo content is synthetic or short public-source summary text. Data files use IDs such as `L-1001`, `EMP-001`, and `TEAM-SOC-A`. Lab artifacts use `example.com` accounts, documentation-reserved IP ranges, and synthetic vulnerability IDs such as `SYN-VULN-2026-014`.

Guardrails cover:

- Real-looking email or PII detection.
- Secret-like string detection.
- Exam dump request detection.
- Unsafe cyber intent detection.
- Citation presence checks.
- Citation grounding checks against retrieved evidence.
- Defensive-only lab framing.
- Lab-response validation for unsafe text, real-looking PII, fake secrets, and invalid option references.
- Local evaluation cases that exercise refusal behavior, citation coverage, grounding, fallback, manager privacy, and lab scoring.
- Sanitized Foundry evaluation export for optional cloud evaluation.
- Explicit fallback labeling when Foundry or Foundry IQ is unavailable.

Blocked requests should be redirected to defensive, synthetic cybersecurity learning.
