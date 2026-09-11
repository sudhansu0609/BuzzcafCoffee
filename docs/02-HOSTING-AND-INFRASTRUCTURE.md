# Hosting and Infrastructure Plan

## Decision
**Vercel (Hobby → Pro) + Neon PostgreSQL + Cloudflare DNS** for the storefront. Zero-ops, git-push deploys, free SSL, global CDN, and the site is Next.js which Vercel runs natively. Cost at launch: ₹0. Move to a VPS (plan B) only if Vercel Pro (~US$20/mo) becomes necessary and a ₹800/month Hetzner box is cheaper — the repo ships a Dockerfile + compose so that move is one afternoon.

Buzzcaf Ops (records system) stays **local** on your machine because it holds identity documents and licences. Backups via `ops/backup.py` to an encrypted cloud folder. It does not need to be on the internet.

## Components
| Layer | Service | Plan | Monthly cost | Why |
|---|---|---|---|---|
| Domain | buzzcaf.com + buzzcaf.in | Whichever registrar holds them (check GoDaddy / Namecheap / BigRock / Google→Squarespace) | ~₹1,500/yr combined | Recover first. `.in` is the Indian trust signal, `.com` is on the MCA record |
| DNS / CDN / WAF | Cloudflare | Free | ₹0 | DNS, caching, bot protection, cookie-less analytics |
| App hosting | Vercel | Hobby (free) → Pro when bandwidth > 100 GB or a second team member | ₹0 → ~₹1,700 | Native Next.js, preview deploys per branch |
| Database | Neon PostgreSQL | Free (0.5 GB) → Launch ($19) | ₹0 → ₹1,600 | Serverless Postgres, branches, point-in-time restore |
| Object storage (invoices, later images) | Cloudflare R2 | Free 10 GB | ₹0 | S3-compatible, no egress fees. Product images are in the repo for now |
| Domain mailboxes | Zoho Mail | Free (5 users) | ₹0 | sudhansu@, care@, orders@ buzzcaf.com |
| Transactional email | Resend | Free 3,000/mo | ₹0 | Order confirmations, password reset (adapter built) |
| WhatsApp | WhatsApp Business app now; Interakt/AiSensy API later | ₹0 → ₹999 | Order updates, reorder nudges |
| Payments | Cashfree (primary), Razorpay (fallback) | Pay-per-txn | UPI 0% on Cashfree; cards ~1.9% | Both integrated behind one interface |
| Shipping | Shiprocket | Free plan, ~₹45 per 500 g shipment | ₹0 | Adapter built; label + tracking |
| Monitoring | BetterStack (uptime) + Sentry (errors) | Free | ₹0 | Alerts to phone |
| Analytics | GA4 + Meta Pixel + Cloudflare Web Analytics | Free | ₹0 | Env IDs, no-op until set |
| Backups | Neon PITR + weekly `pg_dump` to R2 | Free | ₹0 | Restore-test once in October |
| Records system | Buzzcaf Ops, local SQLite | – | ₹0 | `ops/backup.py` → zip → encrypted cloud folder |

**Total at launch: ₹0–500/month. At 300 orders/month: about ₹4,000/month.**

## Environments
1. **Local** — `npm run dev` with SQLite (`file:./dev.db`), test payment keys, `cloudflared tunnel` (or ngrok) so payment webhooks reach localhost.
2. **Preview** — every git branch → Vercel preview URL, Neon branch database, test keys. Break checkout here, not in production.
3. **Production** — `main` branch → buzzcaf.com, Neon main, live keys, Cloudflare proxied.

## Go-live sequence (dated in `09-CALENDAR-SEP-NOV-2026.md`)
1. Recover domains → point nameservers to Cloudflare.
2. Create private GitHub repo `buzzcaf-web` → push `website/`.
3. Vercel: import repo, set env vars from `website/.env.example`, add domain.
4. Neon: create project `buzzcaf`, copy connection string to Vercel, run `prisma migrate deploy` + seed.
5. Zoho Mail: add MX/SPF/DKIM in Cloudflare; create the three mailboxes.
6. Policy pages live → submit Cashfree + Razorpay KYC (they check T&C, privacy, refund, shipping, contact, FSSAI).
7. Webhooks: Cashfree → `https://buzzcaf.com/api/payments/cashfree/webhook`; Razorpay → `https://buzzcaf.com/api/payments/razorpay/webhook`.
8. Shiprocket: create account, pickup address = Pune stock location, API user → env.
9. Place three real ₹1 test orders (UPI, card), refund them, check email + tracking page.
10. Switch keys to live, uptime monitor on, first order.

## Security baseline
- All secrets in Vercel env vars / local `.env` (git-ignored). Password manager (Bitwarden, free) for logins; 2FA on registrar, Vercel, GitHub, Seller Central, Cashfree, Razorpay, Zoho.
- Rotate the 2022 Razorpay live key today (Razorpay dashboard → Settings → API keys → regenerate). Delete `rzp.csv` after the new key is in the password manager.
- Admin panel: admin role only, strong password, and Cloudflare Access (free for up to 50 users) in front of `/admin` in production.
- Weekly dependency update; monthly restore test of the backup.

## Plan B — VPS
Hetzner CX22 (~₹800/mo) or DigitalOcean; Docker Compose (`website/docker-compose.yml`: app + postgres), Caddy for SSL, Coolify optional. Nightly `pg_dump` to R2. Same env vars. Steps are in `website/README.md`.
