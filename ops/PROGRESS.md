# Buzzcaf Ops — Progress Log

Newest first. A row is **done** only with the evidence that proves it.

## 2026-09-10 — Ports: nothing hardcoded (GUARDIAN_PLAN.md section 11, P2)

- `ops/buzzcaf_ports.py` — byte-identical copy of
  `dexter/backend/buzzcaf_ports.py` (sha256 `51649b81…`, 18 243 bytes). Never
  edit it here.
- `ops/run.py` — `--port` is a preference, not an order: the port comes from
  `BUZZCAFCOFFEE_PORT` (else `app.main.PREFERRED_PORT`, the one place 8010 is
  written down), `pick_port` steps forward when something else holds it, the
  entry is published to `%LOCALAPPDATA%\Buzzcaf\ports.json` once `/health` answers as us, `READY port=N`
  goes to stdout and the entry is withdrawn on exit. `--reload` passes the
  chosen port to its child by environment so the child's health tells the truth.
- `ops/app/main.py` — `APP_ID`, `PREFERRED_PORT`, `set_bound_port()` and a new
  plain `/health` returning
  `{"app":"buzzcafcoffee","status":"ok","port":n,"pid":n,"version":…}`.
  `/api/health` keeps its `ok`/`db`/`vault` fields for existing callers and now
  carries the same identity.
- `ops/intake.py` printed `http://127.0.0.1:8010/documents/…`; it asks
  `discover()` where Ops actually is, and says nothing when Ops is not running.
- `ops/README.md` no longer advertises a fixed URL.

**Evidence.** `cd ops && python -m pytest tests -q` → **62 passed** (54 before,
+8 in `tests/test_ports.py`). Live against the real ledger (with
`BUZZCAF_OPS_DATA` pointed at a scratch directory, so `ops/data/ops.db` was
never touched):

```
preferred 8010 free      -> bound 8010
  ledger  {"port":8010,"pid":47196,"health":"http://127.0.0.1:8010/health","extra":{}}
  health  {"app":"buzzcafcoffee","status":"ok","port":8010,"pid":47196,"version":"1.1.0"}
preferred 8010 occupied  -> bound 8011   (the dummy listener kept 8010)
  health  {"app":"buzzcafcoffee","status":"ok","port":8011,"pid":20640,…}
after Ctrl-C             -> no "buzzcafcoffee" key in the ledger, both runs
```

**Not done:** `website/` (Next) has no launcher of its own — `npm run dev` is
started by hand — so there was nothing to wrap with `-p <pick_port(3000)>`. When
a launcher appears, it should pick 3000 through the same helper.
