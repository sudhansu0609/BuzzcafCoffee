# Buzzcaf — Morning Review (built overnight, 7 Sep 2026)

You asked for an agency. This folder is the agency's output: the website, the records system, the plans, and the YouTube kit. Read this page, then the "Your list for today" section. Everything else is reference.

## What exists now
| Folder | What it is | Open it with |
|---|---|---|
| `docs/` | The plans. Start with `00-COMPANY-FACTS.md`, then `01-BUSINESS-PLAN-SEP-NOV-2026.md` and `09-CALENDAR-SEP-NOV-2026.md` | Any markdown viewer |
| `website/` | New storefront built from scratch: Next.js + Prisma, accounts, cart, checkout with Razorpay and Cashfree (test mode), coupons, order tracking, admin panel, policy pages, YouTube landing page `/yt` | `website/README.md` → `npm install && npm run dev` |
| `ops/` | **Buzzcaf Ops** — company records system: documents with expiry, compliance calendar, suppliers, batches & QC, complaints, lab tests, contacts, tasks/decisions, 12 SOPs | `ops/README.md` → `python ops/run.py` → http://127.0.0.1:8010 |
| `inbox/` | **The drop zone.** Put any file here (CA reports, returns, bank statements, Amazon reports, quotes, lab reports). The assistant reads it, files it in the vault, registers it in Ops, extracts the numbers and ticks the filing off the compliance calendar | `python ops/assistant.py sort` or Ops → Inbox |
| `vault/` | Every company document, sorted and indexed (`vault/INDEX.md`). CA output lands in `vault/13-accounts-and-audit/FY<yyyy-yy>/`; unsure files in `vault/12-uploads/needs-review/` | File explorer |
| `youtube/` | Copy-paste kit: description blocks, pinned comments, end-screen script, community posts, video briefs, Amazon listing copy, links + coupon codes | `youtube/README.md` |
| `assets/` | Web-optimised product photos and logos | – |
| `ground-work.html`, `restart-plan.html`, `launch-plan.html` | Your earlier plans (unchanged). The new docs follow `restart-plan` (private label + FBA) | Browser |

## The assistant (added 9 Sep 2026)
Ops now has a virtual employee: **Inbox** (drop zone → auto-filed), **Finance dashboard** (filing matrix per FY, KPIs, GST by month, bank — built from the filed documents), **Mail** (reads your mailbox over IMAP, summarises, creates tasks, pulls attachments into the inbox) and a **Morning brief** (on screen, JSON, and e-mailed daily). Run `python ops/run.py --assistant`. To connect the mailbox copy `ops/.env.example` to `ops/.env` (Gmail app password). Scanned PDFs and photos are read with OCR (RapidOCR, offline). With an `ANTHROPIC_API_KEY` in that file, Claude reads the mail and the unclear documents; without it everything runs on rules. Full description: `docs/11-ASSISTANT.md`.

## The strategy in five lines
1. Private-label instant coffee (a licensed manufacturer makes and labels it; Buzzcaf is the FSSAI Relabeller). Two flavours first.
2. Amazon FBA for strangers; buzzcaf.com for people who came from your videos, for subscriptions, and for Diwali gifting.
3. The five YouTube channels are the ad budget: a coupon code and link per channel on every upload, jar on the desk in every shot, one dedicated coffee video a fortnight from 20 Oct.
4. Diwali (≈ 8 Nov) is a small test run, not the bet. January is the real order, placed only after a 4-week shelf test passes.
5. Everything the company owns or owes is tracked in Buzzcaf Ops, so nothing expires unnoticed again.

## Three things I found in the papers that you need to know
1. **The HDFC current account (50200069779258) shows BLOCKED on the May 2023 statement.** No gateway can pay out to it. Reactivate with KYC or open a new current account this week.
2. **The FSSAI licence expired on 23 June 2024** and its Kind of Business (Repacker) is wrong for private label. A two-year lapse likely means a fresh application, not a renewal.
3. **ROC and GST filing status is unknown.** The Ops dashboard lists AGM, DIR-3 KYC, AOC-4, MGT-7A, ITR and GSTR returns as overdue on the assumption nothing was filed; if your CA did file them, mark them done in Ops → Compliance and the dashboard clears.

## Your list for today (only you can do these)
1. **Rotate the Razorpay live key.** It sits in plaintext in the old `Documents/rzp.csv`. Details: `docs/10-SECURITY-NOTES.md`.
2. **Bank.** Call HDFC about the blocked current account, or open a new one (needed for Cashfree/Razorpay payouts and Amazon).
3. **Domains.** Check the registrar for buzzcaf.com and buzzcaf.in. Recover or re-register.
4. **FoSCoS.** Start the FSSAI application: Kind of Business → Relabeller + Retailer, correct address. Call 1800112100 and ask whether both KOBs sit on one licence.
5. **Amazon Seller Central.** Log in; screenshot account health, category approval, surviving listings into `vault/07-commerce/`.
6. **Appoint a CA** and ask for the GST filing status and MCA (ROC) compliance status. This is the one unknown that could carry real penalties.
7. **Send the supplier enquiry** (template: Ops → Protocols → SOP-01) to all six suppliers (Ops → Suppliers has their details).
8. **Decide** provisional launch flavours (my recommendation: Hazelnut + Original) and confirm MRP ₹349 / ₹649 / ₹999 or change it in the website Admin.
9. **Fill the placeholders**: consumer-care phone number; trademark certificate (the TM-48 in the vault names the filing agent, Noopur Jain, Katni; ask them for the number and certificate); Udyam registration (free, 15 min).
10. Run the site locally and click through: home → Hazelnut → add to cart → checkout (test mode). Then read `docs/02-HOSTING-AND-INFRASTRUCTURE.md` for the deploy steps (about two hours, Vercel + Neon, ₹0).

## Placeholders I could not fill
Consumer-care phone; manufacturer name/address/FSSAI number; trademark and Udyam numbers; bank details; live gateway keys; per-flavour ingredients, flavouring type, nutrition panel, shelf life; final MRP; Amazon ASINs. All are marked `PLACEHOLDER` in the code and docs and listed in `docs/00-COMPANY-FACTS.md`.

## Build status (verified 7 Sep 2026, ~03:40)
| Piece | State | Proof |
|---|---|---|
| Website | Builds (`npm run build` clean, 40 routes), type-check clean, every public route returns 200, admin login works, cart → checkout works in test mode. One commit in `website/.git`. No secrets or database committed | `docs/screenshots/` (home, product page, mobile, cart, checkout, admin products, coupons, product edit) |
| Payments | Razorpay + Cashfree adapters written and wired; **not yet run against real test keys** (none available). Follow `website/TESTING.md` sections A/B once you add `rzp_test_*` or Cashfree sandbox keys | `website/DECISIONS.md` |
| Buzzcaf Ops | Runs at http://127.0.0.1:8010; seeded with 55 documents, 18 obligations, 6 suppliers, 16 contacts, 20 tasks, 8 decisions; 12 SOPs; 20 tests pass; backup verified | `ops/README.md` |
| Vault | 116 MB, 11 folders, indexed. Identity documents flagged restricted. Secrets deliberately excluded | `vault/INDEX.md` |
| Docs | 11 documents in `docs/` (facts, business plan, hosting, payments/users, promotion, sales channels, compliance, SOP index, budget, calendar, security) | – |
| YouTube kit | 9 files, codes and links already live in the site's coupon table | `youtube/README.md` |

## What was not done
- No external accounts were created or touched (registrar, Vercel, Neon, Cashfree, Shiprocket, Google, YouTube). They need your logins and are the deploy steps in `docs/02`.
- Subscription recurring billing, phone-OTP login and WhatsApp API are stubbed (`website/DECISIONS.md`).
- BuzzcafAI itself was not modified; the brand-guide text to add is in `youtube/buzzcafai-brand-guide-snippet.md` and the Ops mount instructions are in `ops/README.md`.
- The background builds hit an API session limit part-way; the gaps (admin panel, deploy files, tests, docs, a Tailwind bug and a threading bug in Ops) were finished directly afterwards.
