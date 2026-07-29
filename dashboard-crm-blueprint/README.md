# Management Dashboard & CRM Control Center — Blueprint

The repeatable system behind the agency: **build a client's website, run their bookings, customers
and money, hand them an owner's dashboard — then do it again for the next company.**

You are the agency. You host websites, CRM and financial services *for* client companies. What you
sell is the **service package**; the platform in here is your control center and the source of every
client's portal.

It's built from a real, revenue-generating stack:

- **LeadRadar** — your command center (`app.leadradar.cc`): every client's revenue, site health,
  contacts, tickets, deals, documents and prospect pipeline in one place.
- **Red Circle Tactical** — client #1 ($500 build + $150/mo): online booking with class capacities,
  scheduling, chat, email and calendar — feeding its bookings and revenue back into the dashboard.

The structural idea: **each client site is a data source; the command center is where they all
converge.** You see the whole book of business; each client sees only their own numbers.

## Contents

| File | What it is |
| --- | --- |
| [`BLUEPRINT.md`](./BLUEPRINT.md) | The full blueprint — architecture, data model, the three service lines, security, rate card, scaling, roadmap and go-to-market. |
| [`landing/index.html`](./landing/index.html) | The **pitch-ready landing page** aimed at business owners — what they get, the owner's dashboard, how it works, the Red Circle case study, pricing and FAQ. |
| [`prototype/index.html`](./prototype/index.html) | A clickable demo of the **internal** control center (mock data, no backend) — the multi-client view you use, not what the client sees. |

## What the client buys

| Service line | What they get |
| --- | --- |
| **Website + booking** | Their site, hosted and maintained: booking with capacities, hours, blocked days, deposits |
| **CRM** | A customer list that builds itself, visitor chat, mass email, notes and history |
| **Financial services** | Deposits at booking, invoices sent on time, revenue and overdue tracked |
| **Owner's dashboard** | One login: what's booked, what it earned, who visited, what's owed |

Rate card: **$500 build + $150/month**, with optional add-ons (Stripe payments, ad management,
priority support). Full breakdown in §8 of the blueprint.

## Why it's low-risk to keep building

The hard parts already exist and run in production:

- A **correct money engine** — recurring revenue, overdue, auto-generated monthly invoices in ~80 lines.
- A schema that **already scopes per client** — every row carries `company_id` and `users.role`
  already has `client`, so the client portal is a permission change, not a rewrite.
- A **read-only collector pattern** so any client site, on any stack, can feed the dashboard safely.
- A **real security posture**: hashed sessions, rate-limited login, CSRF, loopback-bind behind a
  Cloudflare tunnel, secrets kept off git.

The remaining work is making client #5 cost a fraction of client #1 — see the roadmap in §12.

## Before you send the landing page to anyone

Three things in `landing/index.html` to confirm:

1. **Brand** — it's branded *LeadRadar* off your existing domain. Swap it if the client-facing
   business goes by another name.
2. **Contact** — the CTA points at `hello@leadradar.cc`. Make sure that inbox exists and you watch it.
3. **Case study + live link** — the page names Red Circle Tactical and links to their live site as
   proof. Worth a quick OK from Jimmi first; it pairs naturally with the referral ask you drafted.

## Viewing the pages

- **Locally:** open the `.html` files directly — both are fully self-contained.
- **Live:** once this branch is on GitHub Pages, `https://ddylan24.github.io/dashboard-crm-blueprint/landing/`.
