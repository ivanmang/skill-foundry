# Known failures (demo triage corpus)

Seed corpus *without* the vcvt pattern — used to show the "before" state of the
learning loop. The demo promotes a new entry into a copy of this file.

## Seed entries

### missing golden file
- Symptoms: `[ERROR] Failed to get file. Path = .../golden.bin`
- Fix: add the case name to gen_data.py.

### A6 camodel teardown crash
- Symptoms: segfault in `TmSim::reset()`
- Fix: run a kernel, then `aclrtResetDevice` + `aclFinalize`.