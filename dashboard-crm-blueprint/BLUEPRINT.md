# Management Dashboard & CRM Control Center — Productization Blueprint

**A white-label, multi-tenant command center you can implement once and resell to any small business or agency.**

Reference build: **LeadRadar** (live at `app.leadradar.cc`) + the **Red Circle Tactical** client site.
This blueprint generalizes that proven, revenue-generating stack into a repeatable product.

---

## 1. Executive summary

The reference system already works and already earns money. It is two halves:

1. **The client-facing site** — a bookings/e-commerce/lead-capture website for one business
   (reference: Red Circle Tactical, a firearms-training academy: online booking with class
   capacities, no-overlap scheduling, adjustable hours, visitor↔owner chat, mass email,
   calendar feed).
2. **The command center** — a single back-office app that tracks *every* client, service, and
   dollar: MRR, per-client health/traffic/outcomes, contacts, tickets, deals, documents, and a
   prospecting pipeline (reference: LeadRadar, GoHighLevel-style).

The insight worth selling: **the command center is the product; each client site is a data
source that feeds it.** Every client site drops metrics (bookings, revenue, pageviews, uptime)
into the command center through a thin read-only "collector," so the operator sees the whole book
of business on one screen and can prove ROI to each client from their own portal.

This blueprint packages that into a **white-label SaaS** with three sellable shapes:

| Shape | Who buys it | What they get |
| --- | --- | --- |
| **A. Agency Control Center** | Web/marketing agencies, freelancers | The full LeadRadar command center to run *their* book of clients — MRR, CRM, pipeline, health. |
| **B. Single-Business Ops Dashboard** | One SMB (gym, range, salon, clinic) | Their own site + a scoped dashboard: bookings, revenue, customers, uptime — no multi-client layer. |
| **C. White-Label Platform License** | Larger agencies / resellers | Their own branded instance they resell downstream. Per-seat or per-tenant licensing. |

Everything below is grounded in the actual reference implementation, then generalized so it can
be rebuilt cleanly for resale.

---

## 2. What the reference build proves (and why it generalizes)

The reference `leadradar-platform` schema was designed multi-tenant from day one. Every table that
holds client data carries a `company_id`, and the `users` table already has an `admin` / `client`
role split. That single decision is what makes reselling a **permission change, not a rewrite** —
the same code serves the agency operator (sees all companies) and the client (sees only their own).

Proven building blocks, ready to lift:

- **Money engine** (`money.py`): `MRR` = sum of live subscription fees for active companies;
  `overdue()` = unpaid payments past due; `ensure_monthly_payments()` = idempotently generates one
  monthly invoice row per active company per month from their earliest subscription. This is the
  entire financial backend in ~80 lines and it already reconciles correctly.
- **Collector pattern** (`collectors/rc_adapter.py`): reads a client site's database **strictly
  read-only** (`mode=ro`) and upserts daily metrics (bookings, chats, revenue booked) into the
  command center's `outcomes` table. New client verticals = new adapters, no core changes.
- **First-party traffic pixel** (`/pixel` → `pageviews`): each client site embeds a 1-line beacon;
  the command center owns the analytics, so there's no Google-Analytics dependency and no cookie
  banner problem.
- **Health checks**: uptime/latency per client site every few minutes → a green/amber/red status
  the operator (and client) can see.
- **Security posture that already ships**: hashed session tokens, rate-limited login, CSRF header,
  loopback-only bind behind a Cloudflare tunnel, secrets kept out of git.

If it earns $150/mo today from one client with this architecture, the productization task is
**hardening + white-labeling + billing + onboarding**, not invention.

---

## 3. Product architecture

```
                          ┌─────────────────────────────────────────────┐
                          │            CONTROL CENTER (SaaS)             │
                          │  multi-tenant · white-label · role-scoped    │
                          │                                              │
   Client Site A ──pixel──▶  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
   (bookings)   ──collector─▶│ Overview │  │   CRM    │  │  Finance   │  │
                          │  │  (MRR,   │  │ contacts │  │ subs,      │  │
   Client Site B ──pixel──▶  │  health) │  │ tickets  │  │ invoices,  │  │
   (store)      ──collector─▶│          │  │ deals    │  │ overdue    │  │
                          │  └──────────┘  └──────────┘  └────────────┘  │
   Client Site C ──pixel──▶  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
   (leads)      ──collector─▶│ Pipeline │  │  Client  │  │   Team     │  │
                          │  │  leads   │  │  Portal  │  │  activity  │  │
                          │  │ scoring  │  │ (scoped) │  │  board     │  │
                          │  └──────────┘  └──────────┘  └────────────┘  │
                          └───────────────────┬──────────────────────────┘
                                               │
                        Host: single box (Raspberry Pi / VPS / container)
                        Edge: Cloudflare tunnel · app bound to loopback
                        Jobs: cron collectors (health 5m, outcomes hourly)
```

**Tier boundaries**

- **Edge / ingress** — Cloudflare tunnel (or Caddy/Traefik). App never binds to a public
  interface; only the tunnel reaches it. Free TLS, DDoS shielding, no open ports.
- **App** — one process (Flask/FastAPI reference; portable to Node/Rails). Serves the SPA-ish
  dashboard, the JSON API, the ingest endpoints (`/pixel`, collector writes), and auth.
- **Data** — SQLite with WAL for the reference/single-box deployment; **swap to Postgres** for
  the multi-tenant SaaS (see §9). Schema is identical in shape.
- **Jobs** — cron/systemd timers run collectors and `ensure_monthly_payments`. Stateless; safe to
  re-run (idempotent).
- **Client sites** — independent apps (any stack). They only owe the platform two things: embed
  the pixel, and expose a read-only metrics surface (their DB, or a signed JSON endpoint).

---

## 4. Data model (the sellable core)

Lifted and generalized from the live schema. Rename `companies`→`accounts`/`clients` per brand.

| Entity | Purpose | Key fields |
| --- | --- | --- |
| **companies** | The tenant/client record | `name, slug, status(lead\|active\|churned), url, notes, started_at` |
| **users** | Operators & client logins | `email, pw_hash, role(admin\|client), company_id` |
| **sessions** | Hashed session tokens | `token_hash, user_id, expires_at` |
| **services_catalog** | Sellable products/plans | `name, setup_fee, monthly_fee` |
| **subscriptions** | What a client is on | `company_id, service_id, monthly_fee_override, started, ended` |
| **payments** | The ledger | `company_id, amount, kind(setup\|monthly\|other), due, paid_at, note` |
| **health_checks** | Uptime/latency samples | `company_id, url, status_code, latency_ms, ts` |
| **outcomes** | Daily per-client KPIs (from collectors) | `company_id, day, metric, value` (unique per company/day/metric) |
| **contacts** | CRM people | `company_id, name, role, email, phone, is_primary` |
| **tickets** | Support/work items | `company_id, title, body, status(open\|in_progress\|done)` |
| **deals** | Sales pipeline | `company_id, title, value, stage(prospect\|proposed\|won\|lost), close_est` |
| **documents** | Files per client | `company_id, filename, path, size, uploaded` |
| **leads** | Prospecting funnel | `company_name, industry, score, score_rationale, status, source, converted_company_id` |
| **team_posts** | Internal collaboration feed | `author_id, company_id?, body, pinned` |
| **pageviews** | First-party analytics | `site_slug, path, referrer, ua_class, ts` |

**Design rules that make it resellable**

1. `company_id` on every client-owned row → the client portal is a `WHERE company_id = ?` filter,
   never a separate app.
2. Money is stored in **whole units (integer)** to avoid float drift; format at the edge.
3. `outcomes` is a generic `(day, metric, value)` triple, so any vertical's KPIs fit without schema
   changes — a gym logs `checkins`, a store logs `orders`, a clinic logs `appointments`.
4. `services_catalog` + `subscriptions` + `monthly_fee_override` lets you price per client without
   forking the plan. MRR stays correct automatically.

---

## 5. Modules (the screens you ship)

Each maps to real, built API routes in the reference (`app.py`).

1. **Overview / Financial cockpit** — MRR, active/lead/churned counts, overdue total, per-client
   health lights, revenue trend. *The screen the buyer falls in love with.*
2. **Companies / Clients** — list + detail; status lifecycle lead→active→churned; the hub every
   other module hangs off.
3. **Finance** — services catalog, subscriptions (with per-client fee overrides), the payments
   ledger, auto-generated monthly invoices, one-click "mark paid," overdue queue.
4. **CRM** — contacts (primary flag), tickets (open/in-progress/done), deals (prospect→won/lost
   with value + close estimate). This is the GoHighLevel-style core.
5. **Pipeline / Leads** — imported/scored prospects with rationale and source; "convert to company"
   turns a won lead into an active client in one action.
6. **Analytics** — first-party pageviews per client site (path, referrer, device class); health &
   latency history.
7. **Documents** — per-client file vault (contracts, invoices, assets) with safe filenames and
   scoped download.
8. **Team** — internal activity board: author-attributed posts, pin-to-top, optional client link,
   moderation. Multi-operator from the start.
9. **Client Portal** *(the flagship sellable upgrade)* — same app, `role=client`, scoped to one
   `company_id`: the client logs in and sees their own uptime, traffic, outcomes, tickets, invoices.
   This is what turns "my dashboard" into "a product I sell."

---

## 6. The client-site side (data sources)

The command center is only as good as what feeds it. The reference client site (`redcircle-site`)
is the template for a **productized site kit**: a small, self-hostable business site that captures
the money-making event and exposes it to the platform.

Reference feature set (generalize per vertical):

- **Booking/scheduling** with per-offering capacity and no-overlap slots; adjustable business
  hours and blocked days; deposit handling; booking-alert emails; ICS calendar feed.
- **Catalog** of offerings (courses/services/products) with price, duration, description.
- **Visitor↔owner chat** with unread tracking.
- **Mass client email** with unsubscribe + send log.
- **Staff portal** gated by a rotating passcode (secrets kept off git, on the host).

**Vertical kits to package** (same engine, different catalog + copy):

| Kit | Money event | Extra collector metric |
| --- | --- | --- |
| Training / classes (reference) | Booking a class seat | `bookings`, `revenue_booked` |
| Salon / barber / spa | Appointment | `appointments`, `no_shows` |
| Gym / studio | Membership + drop-in | `checkins`, `signups` |
| Home services (landscaping, HVAC) | Quote request | `leads`, `quotes_sent` |
| Local retail / e-commerce | Order | `orders`, `revenue` |
| Clinic / practice | Appointment | `appointments`, `cancellations` |

**Contract between a site and the platform** (keep it this thin):

1. Embed the pixel: `<script src="https://YOUR-PLATFORM/pixel.js" data-site="client-slug"></script>`.
2. Expose metrics read-only — either the platform's collector reads the site DB in `mode=ro`, or
   the site pushes a signed daily JSON of `{day, metric, value}` rows.

That's it. Any stack that can do those two things is a valid data source.

---

## 7. Security & compliance (must-haves for selling)

The reference already does the hard parts; productizing adds the paperwork.

**Already implemented — keep:**
- Session tokens **hashed** at rest; never store raw tokens.
- **Rate-limited login** with attempt logging (`login_attempts`).
- **CSRF header** requirement on mutating requests.
- **Loopback-only bind** behind the tunnel — the app is unreachable except through the edge.
- Secrets (passcodes, keys) kept **out of git**, written to host files, rotatable.
- Collectors are **read-only** against client data (`mode=ro`) — a compromised collector can't write.

**Add for resale:**
- **Password reset** + email verification flow (reference has change-password; add self-serve reset).
- **Per-tenant data isolation guarantees** — enforce `company_id` scoping in a single query layer,
  not per-route, and add tests that a `client` role can never read another company's rows (the
  reference `test_security.py` / `test_p2_auth.py` pattern extends here).
- **Audit log** — who changed what, when (append-only table).
- **Backups** — the reference already has `pi-backup-pull.sh`; formalize to nightly off-box +
  restore drills.
- **Data Processing Agreement + privacy policy** — you're now a processor for clients' customers.
- **PCI scope avoidance** — never touch card data; hand off to Stripe (see §8), keep only the
  Stripe IDs.
- **2FA (TOTP)** for operator/admin accounts.

---

## 8. Billing & monetization

**How you charge (matches the reference contract): setup fee + monthly.** Reference deal:
`$500 setup + $150/mo`. The `services_catalog`/`subscriptions`/`payments` tables already model this;
`ensure_monthly_payments()` already generates the recurring invoices.

**Two billing modes:**

- **Manual/ledger mode (ships today)** — invoices auto-generate, operator marks paid. Zero payment
  integration, zero PCI scope. Good for high-touch agencies. This is literally already built.
- **Stripe mode (the upgrade)** — add `stripe_customer_id`/`stripe_sub_id` to `subscriptions`,
  create a Stripe subscription on activation, and reconcile `payments.paid_at` from Stripe webhooks.
  The ledger stays the source of truth for *display*; Stripe is the source of truth for *collection*.

**Pricing the product itself (what you sell it for):**

| Plan | Target | Price (illustrative) | Includes |
| --- | --- | --- | --- |
| **Starter** | Solo operator, ≤5 clients | $49/mo | Command center, CRM, ledger billing, 1 site kit |
| **Agency** | ≤50 clients, team seats | $199/mo | + client portal, analytics, collectors, team board |
| **White-label** | Resellers | $499/mo + $X/tenant | + your brand/domain, remove platform marks, API |
| **Setup / site kit** | Per client site | $300–$1,000 one-time | Built + deployed vertical site (your services revenue) |

The dual revenue model (SaaS subscription **and** per-site setup services) is exactly what the
reference agency runs — it's proven, not theoretical.

---

## 9. Multi-tenant hardening (SQLite → SaaS)

The reference runs SQLite on one box and serves one agency's book. To sell to *many* independent
buyers, pick an isolation model:

| Model | How | Best for |
| --- | --- | --- |
| **Row-level (shared DB)** | Add `tenant_id` above `company_id`; every query scoped by both | Many small buyers, lowest ops cost. Requires Postgres + RLS. |
| **Schema/DB-per-tenant** | One SQLite file (or PG schema) per buyer | Medium buyer count, strong isolation, easy per-tenant backup/restore. Maps cleanly onto today's file-per-instance model. |
| **Instance-per-tenant** | A container per buyer (today's box, replicated) | White-label / high-touch / regulated buyers. |

**Recommended path:** start **DB-per-tenant** (it's the smallest leap from the current
`LR_DATA`-per-process design — each tenant just gets its own data dir), then graduate heavy buyers
to their own instance and offer row-level shared-DB only if you chase high-volume self-serve.

Move from SQLite to **Postgres** when you cross ~a few hundred writes/sec or need concurrent
multi-region — the schema translates directly (types are already portable; drop the SQLite-specific
`PRAGMA`s).

---

## 10. Deployment & operations

Reference ops (keep the shape, scale the box):

- **Host:** single Raspberry Pi today → a $5–$20/mo VPS or a container platform for SaaS.
- **Process:** `systemd` service (`platform.service`) bound to loopback; auto-restart.
- **Edge:** Cloudflare tunnel → free TLS, hidden origin, no inbound ports.
- **Jobs:** cron/systemd timers — health check every 5 min, outcome collectors hourly,
  `ensure_monthly_payments` daily.
- **Deploy:** a `setup-platform.sh`-style idempotent installer; per-client a `/deploy-<client>`
  routine. Productize this into a **one-command tenant provisioner**.
- **Backups:** nightly off-box pull (reference has `pi-backup-pull.sh`), plus a monthly restore drill.
- **Observability:** the app's own `/healthz`, plus health_checks history; add error alerting
  (email/Slack) for collector failures and overdue spikes.

**Provisioning a new buyer (the repeatable motion):**
1. Run the tenant provisioner → new data dir/DB + seed admin + subdomain via the tunnel.
2. Set brand (name, logo, accent color, domain) from the white-label config.
3. Build/deploy their first client site kit; wire the pixel + collector.
4. Enter services & subscription → invoices start generating; MRR reflects it.

---

## 11. White-labeling checklist

To make one codebase sell under many brands:

- [ ] **Brand config per tenant** — name, logo, `--accent` color, support email, custom domain.
      (The reference CSS already centralizes theme in `:root` custom properties — swap tokens, done.)
- [ ] **Remove hard-coded product names** from templates → pull from tenant config.
- [ ] **Custom domain per tenant** via the tunnel/edge (`app.buyersbrand.com`).
- [ ] **Configurable module set** — toggle Pipeline/Team/Analytics per plan.
- [ ] **Email sender identity** per tenant (their domain, their SMTP/app-password).
- [ ] **"Powered by" toggle** — on for Starter/Agency, removable on White-label.
- [ ] **Seed data & vertical presets** — ship each site kit's catalog as a selectable template.

---

## 12. Implementation roadmap

Phased to mirror how the reference was actually built (P1–P3 shipped in a day, proving the pace),
then extended for resale.

| Phase | Deliverable | Status in reference |
| --- | --- | --- |
| **P1** | Auth, companies, money engine (MRR/ledger) | ✅ built & live |
| **P2** | CRM (contacts/tickets/deals/docs), traffic pixel, password change | ✅ built & live |
| **P3** | Pipeline leads + convert-to-company | ✅ built & live |
| **P4** | **Client portal** (client-role logins, scoped views) — *the sellable feature* | ⬜ planned |
| **P5** | Collector SDK + 3 vertical site kits (salon, gym, home-services) | ⬜ new |
| **P6** | Stripe billing + self-serve signup + tenant provisioner | ⬜ new |
| **P7** | White-label config (brand/domain/modules) + Postgres option | ⬜ new |
| **P8** | Audit log, 2FA, DPA/privacy, backup drills — "enterprise-ready" | ⬜ new |

**Fast path to first external sale:** P4 (portal) + minimal P7 (brand/domain) is enough to sell
Shape A (Agency Control Center) to a second agency. Everything else is expansion revenue.

---

## 13. Go-to-market (grounded in the reference playbook)

The reference already has a working motion worth generalizing:

- **Land with services, expand with SaaS.** Sell a client a site ($300–$1k setup), then the
  dashboard subscription rides along. The site is the demo.
- **Referral engine.** The reference `referral-ask.md` offers *one free month per signed referral*.
  Productize this into an in-app referral tracker (a `leads.source = "referral"` path already exists).
- **Vertical beachheads.** Own one niche at a time (the reference targets firearms/CPR/self-defense
  instructors — adjacent, warm-intro-friendly). Each vertical kit unlocks a network.
- **Prove ROI from their own portal.** The client logs in and sees bookings/revenue you generated.
  That screen is the renewal.

---

## 14. What to build first (if you implement this)

1. **Lift the reference `leadradar-platform`** as the skeleton (schema, money engine, auth are done).
2. **Ship P4 client portal** — biggest value unlock, smallest code (it's a scoping change).
3. **Extract the collector into an SDK** + document the two-line site contract (§6).
4. **Add a brand/tenant config layer** (§11) so a second buyer is a config row, not a fork.
5. **Wrap billing** — keep ledger mode default, add Stripe as the upgrade.
6. **Provisioner script** — make onboarding a new buyer a single command.

The hard, risky work (a correct money engine, a multi-tenant-shaped schema, a real security posture,
a live paying client) is **already done and proven**. This blueprint is the map from "one agency's
tool" to "a product other companies buy."

---

*See [`README.md`](./README.md) for a quick tour and [`prototype/index.html`](./prototype/index.html)
for a clickable, self-contained demo of the control center UI.*
