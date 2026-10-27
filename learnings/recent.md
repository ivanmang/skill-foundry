# Recent — pending learnings

Strict, machine-parseable format. One entry per `## LRN-…` block; fields in
this exact order. `scripts/log_correction.py` and `scripts/session_digest.py`
write entries; `scripts/promote_recent.py` parses and promotes them.

```markdown
## LRN-YYYYMMDD-NNN
- id: LRN-YYYYMMDD-NNN
- category: correction | error | knowledge_gap | feature
- context: <run-id or trigger, e.g. demo-live-20261027-110200>
- skill: <target skill name, or "harness">
- wrong: <what the flow previously did / symptom>
- correct: <what it should do instead>
- action: <precise edit or where to add>
- status: pending | promoted | rejected
```

Rules:

- Do not freeform-edit a `## LRN-…` block; use `log_correction.py`.
- Only `status: pending` entries are promoted by `promote_recent.py`.
- On promotion the entry moves to `promoted.md` and the change is logged in
  `corrections.md`.

(No entries yet.)