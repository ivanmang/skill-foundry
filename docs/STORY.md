# The Story — a pi agent, a developer, and the harness

A short story about how a **developer** and a **pi agent** actually use the
regression harness. Everything below is how it really works — the commands are
real, the roles are real, only the names are made up.

---

## Characters

- **Maya** — a developer who owns a pto-isa change she's nervous about.
- **Pi** — the coding agent. It has no memory of its own; it reads the Skills
  and drives the harness.
- **The harness** — `./harness` + `.claude/skills/` + `config/` + `learnings/` +
  `reports/baseline/`. The durable memory and machinery.

---

## Act I — "Is my machine even ready?"

Morning. Maya opens the terminal and types the first thing she always types.

```bash
./harness status
```

```text
 environment
  ✓ python3    ✓ git
  ✓ ASCEND_HOME_PATH  9.1.0-beta.1
  ✓ pto-isa  /home/ivanmang/pto-isa

 target: pto-isa (CPU-ST + NPU-sim)  (pto-isa)
  ✓ repo … · ✓ baseline (baseline-seed, 1d ago)
    [✓] npu-sim-a5   [✓] npu-sim-a3   [!] npu-sim-a6 (no A6 headers)
    [!] cpu-st       (no clang++>=15 here)
```

The harness didn't ask a single question. It **detected** everything itself —
which CANN is installed, which sims exist, what's missing. That's the harness
doing its job automatically. Maya just reads it.

She wants to run the A5 simulator suite, so she tells Pi.

> **Maya:** "Run the pto-isa A5 sim regression for the tadd testcase."

Pi doesn't guess. It reads `.claude/skills/pto-isa/SKILL.md`, which tells it the
exact invocation and the gotchas. Then it previews before committing:

```bash
./harness run --suite npu-sim-a5 --testcase tadd --dry-run
```

```text
dry-run: would run 1 suite(s) for 'pto-isa':
  - npu-sim-a5  mode=npu-sim  (up to 120m)
no run.json written (dry-run).
```

Maya glances at it — "fine, go."

```bash
./harness run --suite npu-sim-a5 --testcase tadd --quiet
```

Three minutes of compile and simulate later:

```text
+------------+--------+------+------+------+-------+----------+
| suite      | status | pass | fail | skip | total | duration |
+------------+--------+------+------+------+-------+----------+
| npu-sim-a5 | PASS   | 1    | 0    | 0    | 1     | 261.88s  |
+------------+--------+------+------+------+-------+----------+

  ✓ all passed.
  next: ./harness report --open   or   ./harness review
```

The harness even **suggests the next step**. That's the whole point — it doesn't
just run, it leads.

---

## Act II — "Did anything regress?"

Maya wants the signal, not the raw output.

```bash
./harness review
```

```text
regressions: 0  fixes: 0  new: 201  removed: 0  perf_flags: 0
```

"Zero regressions, p99 stable," Pi summarizes. "The baseline says all 201 cases
that were PASS are still PASS."

Relief. Maya commits her change and moves on. **The USE loop is done** —
run → report → review — and neither Maya nor Pi had to remember any of the
mechanics. The harness ran it, and the agent read the result.

---

## Act III — Something actually breaks

A week passes. Maya pushes a refactor of the vector-convert path. This time:

```bash
./harness run --suite npu-sim-a5 --quiet
```

```text
| npu-sim-a5 | FAIL   | 200 | 1 | 0 | 201 | 7m 12s |
  ⚠  npu-sim-a5: first error — VecOpTest.case_vcvt_bf16fp16_128x128
```

Pi reads the log, follows the skill's triage recipe — first error line, then
classify, then check `known-failures.md`.

> **Pi:** "The failing case is `VecOpTest.case_vcvt_bf16fp16_128x128`. It's not
> in the known-failures corpus. It looks like a new regression in your change."

> **Maya:** "No, that's the known vcvt round-field silicon behavior — it was
> already there before my change."

That sentence is all it takes. Pi doesn't wait to be told the command — **it
auto-captures**, because the skill says to on "no / actually / remember…":

```bash
./harness teach "device vcvt round-field mismatch -> known vcvt pattern, annotate -> promote to known-failures"
```

```text
✓ logged LRN-20261030-001 (correction) → learnings/recent.md
```

Pi: "Captured as `LRN-20261030-001`."

Notice what just happened: the **content** of that correction — the *"known
vcvt pattern"* part — is Maya's judgment. The **logging** is automatic. The
machine runs and remembers; only the human decides what's true.

---

## Act IV — From memory to skill

Now the lesson sits in `learnings/recent.md` with `status: pending`. To turn it
into something every future run benefits from, Pi proposes the exact edit:

```bash
./harness promote --propose
```

```diff
--- a/.claude/skills/pto-isa/references/known-failures.md
+++ b/.claude/skills/pto-isa/references/known-failures.md
+### known vcvt pattern, annotate
+- Symptoms: device vcvt round-field mismatch
+- Correct: known vcvt pattern, annotate
+- Action: promote to known-failures
+- Seen in: 20261030-091200-pto-isa
```

Maya reads it. It's exactly what she meant. "Ship it."

```bash
./harness promote --pr
```

The harness applies the edit, flips the entry to `promoted`, appends a summary
to `promoted.md` + an audit block to `corrections.md`, commits on
`feat/learnings-20261030`, pushes, and prints a merge-request URL.

Maya opens the MR and clicks **Merge**. That's the human gate — the harness
never self-merges.

---

## Act V — The payoff

The next morning, any teammate (or any agent) who re-runs gets a smarter report:

```markdown
- `npu-sim-a5/VecOpTest.case_vcvt_bf16fp16_128x128` — **known**: vcvt round-field swap
```

The failure that cost Maya ten minutes yesterday is now annotated in one line.
**The agent didn't get smarter — the harness did.** And everyone gets it via git.

---

## Who did what

| Step | Who |
|---|---|
| Detect env, run, dry-run, normalize logs, report, review | 🟢 harness (automatic) |
| Read the skills, run `teach` when Maya says "no/actually" | 🤖 Pi (automatic on trigger) |
| Decide the triage was *known*, approve the diff, merge the MR | 🟡 Maya (human) |
| Remove or weaken an existing check | 🔴 nobody, ever |

That's the whole relationship, in story form: **you steer, the agent conducts,
the harness runs and remembers.**