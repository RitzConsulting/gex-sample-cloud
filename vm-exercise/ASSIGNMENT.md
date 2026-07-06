# Assignment — VM Lift-and-Shift Readiness (Path A rehearsal)

## Why this exercise

The real migration's **Path A** moves the trading backend from a local PC to a
**single hardened GCE VM** — because the broker gateway (IB Gateway) is a
long-lived, GUI-based process that **cannot run serverless**. This exercise
rehearses exactly those skills with dummy services:

- `service/worker.py` — a **stateful worker** (the trading-engine analog): polls
  the gateway, persists every tick to SQLite, keeps a heartbeat, exposes
  `/health` + `/status`. It already handles outages with retry/backoff.
- `service/gateway_stub.py` — a **flaky gateway** (the **IB Gateway analog**):
  requires a token and returns `reauth_required` (503) for ~10s of every minute,
  like IB's real session drops.

Your job is the **VM operations** that make this reliable, secure, and
observable — the same work Path A needs.

## Your goal

Deploy both services to **your own** hardened GCE VM such that:

1. **Both run under `systemd`** with `Restart=always`; the gateway is supervised
   so a crash auto-restarts it.
2. **Data persists across a VM reboot** — the SQLite DB lives on a **persistent
   disk**; after `sudo reboot`, `tick_count` keeps climbing (does **not** reset).
3. **The worker rides gateway outages** — during the 503 windows it backs off and
   **reconnects** (its `reconnects` counter increases), never crashing.
4. **Secrets from Secret Manager** — `GATEWAY_TOKEN` is injected from Secret
   Manager, not written as a literal in the unit files or repo.
5. **Hardened + fronted** — OS firewall allows only what's needed; **SSH via IAP**
   (no public port 22 to the world); internal service ports stay on `127.0.0.1`;
   expose only `/health` through **nginx + TLS** (or keep everything private and
   reach it via an SSH tunnel).
6. **Observability** — a **Cloud Monitoring uptime check** on `/health`, and an
   **alert** that fires when the worker stays **degraded** for more than a few
   minutes (i.e. the gateway has been down too long — the IB-disconnect alarm).

## How we'll re-test

- **Automated:** `tests/readiness_probe.py` against your worker URL (through your
  TLS front or an SSH tunnel) — confirms it's alive and persisting through an
  outage window.
- **Resilience demo (you record):**
  - `sudo systemctl stop gex-gateway` → worker goes degraded → gateway
    auto-restarts (or you start it) → worker `reconnects` increments.
  - `sudo reboot` → both services come back on their own → `tick_count` continued
    from before (data survived).
- **Review:** systemd units, persistent-disk mount, firewall/IAP, Secret Manager
  wiring, nginx/TLS, and the alert policy + uptime check (screenshots or IaC).

## Deliverables

- The running VM (or full IaC + a teardown note to avoid spend).
- `SUBMISSION-VM.md`: your VM setup, how the gateway is supervised, the persistent
  disk + reboot proof, secret handling, firewall/IAP, TLS, and monitoring
  evidence (screenshots). Include the readiness-probe output.
- Don't weaken the worker's resilience logic to pass — strengthen only, and
  document it.

## Time

Aim for **4–8 hours**. The point isn't the dummy app — it's proving you can run
and **supervise a flaky long-lived dependency on a hardened VM with persistence
and alerting**, which is the crux of Path A.
