# Management Dashboard & CRM Control Center — Blueprint

A packaged, sellable blueprint for turning a single business's website + financial back-office into
a **white-label, multi-tenant management dashboard and CRM control center** that can be resold to
other companies and agencies.

It generalizes a real, revenue-generating stack:

- **LeadRadar** — the live agency command center & CRM (`app.leadradar.cc`): MRR, per-client health,
  contacts, tickets, deals, documents, prospecting pipeline.
- **Red Circle Tactical** — the first paying client site ($500 setup + $150/mo): online booking,
  capacities, scheduling, chat, email, calendar — and a collector that feeds its bookings/revenue
  into LeadRadar.

The core idea: **the command center is the product; each client site is a data source.**

## Contents

| File | What it is |
| --- | --- |
| [`BLUEPRINT.md`](./BLUEPRINT.md) | The full blueprint — architecture, data model, modules, security, billing, multi-tenancy, roadmap, GTM. |
| [`prototype/index.html`](./prototype/index.html) | A self-contained, clickable demo of the control-center UI (mock data, no backend). Open it in a browser or view it live on GitHub Pages. |

## The three things you can sell

1. **Agency Control Center** — the full command center for agencies to run their book of clients.
2. **Single-Business Ops Dashboard** — one SMB's site + a scoped dashboard (bookings, revenue, customers).
3. **White-Label Platform License** — a branded instance resellers sell downstream.

## Why it's low-risk to implement

The hard parts already exist and are proven in production:

- A **correct money engine** (MRR, overdue, auto-generated monthly invoices) in ~80 lines.
- A schema that is **multi-tenant by design** — every client row carries `company_id`, and users
  already split into `admin` / `client` roles, so a client portal is a permission change, not a rewrite.
- A **read-only collector pattern** so any client site (any stack) can feed the dashboard safely.
- A **real security posture**: hashed sessions, rate-limited login, CSRF, loopback-bind behind a
  Cloudflare tunnel, secrets off git.

The productization work is **hardening + white-labeling + billing + onboarding** — see the roadmap
in the blueprint.

## Quick start (viewing the prototype)

- **Locally:** open `prototype/index.html` in any browser — it's fully self-contained.
- **Live:** once this branch is on GitHub Pages, visit
  `https://ddylan24.github.io/dashboard-crm-blueprint/prototype/`.

## Prototype ≠ implementation

The prototype is a **UI demonstration with mock data** to make the blueprint tangible for a buyer
or investor. The real implementation lifts the `leadradar-platform` codebase (schema, money engine,
auth) as its skeleton — see **§14, "What to build first"** in the blueprint.
