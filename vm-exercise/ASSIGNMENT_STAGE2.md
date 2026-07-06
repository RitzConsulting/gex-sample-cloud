# Stage 2 — Two VMs, private-only networking

## Why this exercise

If IBKR is kept in the cloud, the right design is: **IB Gateway on its own small
VM**, and the trading engine on a separate VM reaching it over a **private VPC
IP** — with that port **never exposed to the public internet**. This isolates the
flaky gateway from the engine and shrinks the attack surface.

This stage reuses the same two services from Stage 1, but splits them across
**two VMs**:

- **Gateway VM** — runs `service/gateway_stub.py` (the IB Gateway analog). Set
  `GATEWAY_HOST=0.0.0.0` so it listens on the VM's internal interface.
- **Engine VM** — runs `service/worker.py` with
  `GATEWAY_URL=http://<gateway-VM-private-ip>:8071`.

## Your goal

1. **Two VMs in the same VPC.** Gateway VM + Engine VM, each with a dedicated
   least-privilege service account.
2. **Private connectivity.** The engine reaches the gateway over the gateway VM's
   **internal IP** (`http://10.x.x.x:8071`), not localhost, not a public IP.
3. **Firewall to engine-only.** A VPC firewall rule allows **only the engine VM**
   (by network tag or service account) to reach the gateway on `:8071`. There is
   **no** rule allowing `0.0.0.0/0` to that port. Ideally the gateway VM has **no
   external IP** at all (egress via Cloud NAT if it needs the internet).
4. **Token still required.** `GATEWAY_TOKEN` from Secret Manager on both VMs
   (defense in depth on top of the firewall).
5. **Hardened.** SSH via IAP on both; no public app ports; internal only.

## Acceptance / how we re-test

- **Private path works** — on the **engine VM**:
  ```bash
  python tests/isolation_check.py engine     # worker is getting ticks via the private IP
  ```
- **Public is blocked** — from your laptop / Cloud Shell / any non-allowed host:
  ```bash
  GATEWAY_PUBLIC=http://<gateway-public-ip-or-name>:8071 python tests/isolation_check.py public
  ```
  This must **PASS by failing to connect** (the gateway is private-only). If the
  gateway VM has no external IP, confirm there's simply no public endpoint.
- **Non-allowed VM is blocked** (manual) — spin up a throwaway VM in the VPC that
  is **not** in the firewall allow rule and confirm it **cannot** reach
  `:8071`. Then delete it.
- **Review** — VPC + firewall IaC/commands, the private-IP wiring, no external IP
  / no public-allow rule, IAP, and Secret Manager.

## Deliverables

- Both VMs (or full IaC + teardown note).
- `SUBMISSION-STAGE2.md`: your VPC/subnet + firewall design (allow-by-tag or
  service account), the private-IP wiring, proof the port is unreachable publicly
  and from a non-allowed VM, and the isolation-probe output.
- Don't weaken the services to pass — this stage is purely about **network
  isolation**.

## Maps to the real migration

This is exactly how you'd place **IB Gateway + the futures bridge** on their own
VM in the cloud: private VPC IP to the engine, firewalled to engine-only, no
public exposure of the broker port.
