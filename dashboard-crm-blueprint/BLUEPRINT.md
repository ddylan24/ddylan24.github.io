# Management Dashboard & CRM Control Center — Productization Blueprint

**The repeatable system behind a web/hosting agency: build the client's site, run their bookings,
customers and money, and hand them a dashboard — then do it again for the next company.**

Reference build: **LeadRadar** (live at `app.leadradar.cc`) + the **Red Circle Tactical** client site.
This blueprint turns that proven, revenue-generating stack into something you can deliver on repeat.

> **Who this is written for:** you are the agency. You host websites, CRM and financial services
> *for* client companies. The thing you sell is the **service package** — site, booking, customer
> list, invoicing, and an owner's dashboard. The platform in here is your internal control center
> and the source of every client's portal. You are not selling the software to other agencies.

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

The key structural insight: **each client site is a data source; the command center is where every
client converges.** Every client site drops metrics (bookings, revenue, pageviews, uptime) into the
command center through a thin read-only "collector." That gives you the whole book of business on
one screen — and gives each client a portal showing only their own numbers, which is what proves
the monthly fee is worth paying.

**What the client buys** (one package, one bill):

| Service line | What the client gets | Built from |
| --- | --- | --- |
| **Website + booking** | Their site, hosted and maintained: online booking with capacities, hours, blocked days, deposits | `redcircle-site` pattern |
| **CRM** | Customer list that builds itself, visitor chat, mass email, notes and history | `contacts` / `chat` / `email_log` |
| **Financial services** | Deposits at booking, invoices sent on time, revenue and overdue tracked | `payments` + money engine |
| **Owner's dashboard** | One login: what's booked, what it earned, who visited, what's owed | Client portal (P4) |

**What you keep for yourself:** the multi-client command center — every client's revenue, health,
tickets and pipeline in one place, so you can run twenty clients without twenty spreadsheets.

Everything below is grounded in the actual reference implementation, then generalized so the next
client is a repeat of the last one instead of a fresh build.

---

## 2. What the reference build proves (and why it generalizes)

The reference `leadradar-platform` schema was designed multi-tenant from day one. Every table that
holds client data carries a `company_id`, and the `users` table already has an `admin` / `client`
role split. That single decision is what makes the client portal a **permission change, not a
rewrite** — the same code serves you (all companies) and the client (only their own).

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

**Design rules that make the next client cheap**

1. `company_id` on every client-owned row → the client portal is a `WHERE company_id = ?` filter,
   never a separate app.
2. Money is stored in **whole units (integer)** to avoid float drift; format at the edge.
3. `outcomes` is a generic `(day, metric, value)` triple, so any trade's numbers fit without a
   schema change — a gym logs `checkins`, a shop logs `orders`, a clinic logs `appointments`.
   This is what lets you take on a salon next week without touching the platform.
4. `services_catalog` + `subscriptions` + `monthly_fee_override` lets you cut one client a deal
   without forking the plan. Your recurring revenue total stays correct automatically.

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

**What you charge a client** (the live Red Circle contract, generalized into a rate card):

| Line item | Price | Notes |
| --- | --- | --- |
| **Build** | $500 one-time | Site, booking, catalog, chat, email — deployed on their domain |
| **Hosting & service** | $150/month | Hosting, backups, uptime, CRM, invoicing, dashboard, support |
| Card payments (Stripe) | +$50/month | Optional — deposits are included in the base |
| Ad management | +$125/month | Optional |
| Priority support | +$40/month | Optional |
| Extra pages / custom features | Quoted | Bills as a one-time line on the ledger |

Every one of these is a row in `services_catalog`; per-client discounts go in
`monthly_fee_override` so recurring revenue stays correct without forking the plan.

**Unit economics that matter:** the build fee roughly covers the labour of onboarding, and the
monthly is near-pure margin because all clients share one box. That means **profit scales with
client count, not with hours worked** — which is exactly why the onboarding needs to be
mechanical (see §10) and why the collectors must be per-vertical adapters rather than bespoke code.

**Raising the monthly later** is a portal conversation, not a negotiation: when a client can see
the bookings and revenue their site produced, a $150→$200 move is measured against what they earned.

---

## 9. Scaling the client count (one platform, many companies)

You run **one** control center. Every client company is a `companies` row inside it, and their
portal login is a `users` row scoped to that company. There is no second instance to sell or
operate — so "multi-tenant" here means *many client companies on your one box*, not many buyers.

That model holds a long way. The realistic pressure points, in the order you'll hit them:

| Client count | What breaks first | The fix |
| --- | --- | --- |
| **1–25** | Nothing. SQLite + WAL on one small box is comfortable here. | Keep going. |
| **25–75** | Onboarding time per client; collector sprawl; backup blast radius. | Mechanical provisioning (§10), per-vertical collector kits (§6). |
| **75+** | Write contention on a single SQLite file; one box = one failure domain. | Move the platform DB to **Postgres**; keep each client *site* on its own SQLite. |

**Keep the client sites separate from the platform.** Each client's site owns its own database
(bookings, customers, chat) — the platform only ever *reads* from it. That's what keeps one
client's traffic spike or bad deploy from touching anyone else, and it means restoring a single
client is a single file copy.

**The isolation guarantee you're actually selling:** a `client`-role login can only ever read rows
carrying their own `company_id`. Enforce that in one query layer rather than per-route, and cover
it with tests — a client seeing another client's revenue is the one bug that ends the business.

Move the platform DB from SQLite to **Postgres** when writes start contending or you need a second
box for redundancy. The schema translates directly (types are already portable; drop the
SQLite-specific `PRAGMA`s).

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

## 11. Per-client branding checklist

Your control center keeps *your* brand. What varies per client is their **site** and the **portal
skin** they log into — so each client's experience feels like their business, not your software.

- [ ] **Client brand config** — name, logo, `--accent` color, support email, domain.
      (The reference CSS already centralizes theme in `:root` custom properties — swap tokens, done.)
- [ ] **Client domain** — their site on their own domain; the portal on a subdomain of yours
      (`clientname.leadradar.cc`) or theirs, whichever they prefer.
- [ ] **Email sender identity** per client — their domain and their app-password, so booking alerts
      and blasts come *from them*. (This is an open item on Red Circle today.)
- [ ] **Vertical presets** — ship each site kit's catalog, slot times and copy as a selectable
      template so a new salon isn't built from an empty page.
- [ ] **Portal module toggles** — show a client only what they bought (hide invoicing if you bill
      them off-platform, hide analytics on a base plan).
- [ ] **Your marks stay yours** — the client's site carries their brand; a discreet credit in the
      footer is a lead source worth keeping.

---

## 12. Implementation roadmap

Phased to mirror how the reference was actually built (P1–P3 shipped in a day, proving the pace),
then extended so client number five costs a fraction of client number one.

| Phase | Deliverable | Status in reference |
| --- | --- | --- |
| **P1** | Auth, companies, money engine (revenue/ledger) | ✅ built & live |
| **P2** | CRM (contacts/tickets/deals/docs), traffic pixel, password change | ✅ built & live |
| **P3** | Pipeline leads + convert-to-company | ✅ built & live |
| **P4** | **Client portal** (client-role logins, scoped views) — *what justifies the monthly* | ⬜ planned |
| **P5** | Vertical site kits (salon, gym, home-services) + a collector per kit | ⬜ new |
| **P6** | One-command client onboarding + Stripe for collecting your own fees | ⬜ new |
| **P7** | Per-client branding & sender identity; Postgres when client count demands it | ⬜ new |
| **P8** | Audit log, 2FA, backup drills, privacy terms — the trust layer | ⬜ new |

**Fast path to more revenue:** P4 (portal) is the single highest-leverage build — it's what turns
the $150/mo from a hosting bill into a service the client can see working, and it's mostly a
scoping change over code you already have. P5 is what makes the *next* client cheap to land.

---

## 13. Go-to-market (grounded in the reference playbook)

The reference already has a working motion worth repeating:

- **The build fee opens the door; the monthly is the business.** A $500 site is an easy yes for an
  owner who's been quoted $5k. The recurring $150 is what compounds — and it only survives if the
  client can see what it does, which is the portal.
- **Referrals from inside the vertical.** The reference `referral-ask.md` offers *one free month per
  signed referral*. A warm intro from a peer closes far better than a cold pitch, and the demo is
  their friend's own live site. Track it — `leads.source = "referral — <client>"` already exists.
- **Own one trade at a time.** Firearms/CPR/self-defense instructors know each other; so do barbers,
  so do landscapers. Each vertical kit you build makes the next business in that trade cheaper to
  win and faster to launch.
- **Sell the dashboard, not the website.** Anyone can point at a website. Almost no local web shop
  hands the owner a login showing bookings and revenue. That's the differentiator — lead with it.
- **Let the portal do the renewal.** When the client can see what their site earned last month,
  the monthly invoice stops being a cost and starts being a receipt.

---

## 14. What to build first

1. **Ship P4, the client portal.** Biggest revenue impact, smallest code — the schema already
   carries `company_id` everywhere and `users.role` already has `client`. This is a scoping and
   templating job, not a rewrite.
2. **Turn Red Circle into a repeatable kit.** Extract the site into a template with the catalog,
   slots and copy swappable, so the next training business is a configuration rather than a build.
3. **Write the second collector.** One more vertical (salon or home services) proves the adapter
   pattern generalizes and gives you a second market to sell into.
4. **Make onboarding one command.** New client = create company, seed services, provision subdomain,
   deploy site, wire pixel and collector. Every manual step here is margin you lose per client.
5. **Close the loop on billing.** Invoices already generate; add Stripe when chasing payments costs
   more than the integration.

The hard, risky work — a correct money engine, a schema that already scopes per client, a real
security posture, and a live paying customer — is **already done and proven**. What's left is
making the second, fifth and twentieth client cost a fraction of the first.

---

*See [`README.md`](./README.md) for a quick tour and [`prototype/index.html`](./prototype/index.html)
for a clickable, self-contained demo of the control center UI.*
