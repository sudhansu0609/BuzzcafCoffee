"""Idempotent seed: company documents (from vault/index.json), compliance
calendar, suppliers, contacts, week-one tasks and the decisions already made.

    python ops/seed.py            # seed / re-seed (never duplicates)
    python ops/seed.py --reset    # drop the database first
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import db, paths, services  # noqa: E402

TODAY = date.today().isoformat()


def upsert(con, key: str, match: dict, data: dict) -> int:
    where = " AND ".join(f"{k} = ?" for k in match)
    row = db.find_one(con, key, where, list(match.values()))
    if row:
        return int(row["id"])
    return db.insert(con, key, {**match, **data})


# ------------------------------------------------------------- documents ----
DOC_STATUS_OVERRIDES = {
    "fssai-state-licence-11522079000056.pdf": ("expired", "Expired 23 Jun 2024. Renewal + KOB change to Relabeller + add Retailer needed on FoSCoS before any sale. Late fee likely."),
    "hdfc-current-account-statement-2022-06-to-2023-05.pdf": ("expired", "Account shown as BLOCKED in May 2023 statement. Reactivate (KYC) or open a new current account before payouts."),
    "leave-and-licence-agreement-2022-02-02.pdf": ("expired", "11-month agreement from Feb 2022 — long lapsed. Registered office address proof will need a fresh agreement/NOC if ROC or bank asks."),
}


def seed_documents(con) -> int:
    idx = paths.VAULT_DIR / "index.json"
    if not idx.exists():
        return 0
    n = 0
    for r in json.loads(idx.read_text(encoding="utf-8")):
        if r["category"] in ("archive",):
            continue
        if r["category"] == "brand" and r["doc_type"] in ("photo", "logo") and "product-photos" in r["path"] or "stock-images" in r["path"]:
            continue  # bulk photos stay in the vault listing, not the registry
        if r["category"] == "brand" and "logos/" in r["path"] and not r["path"].endswith(".ai"):
            continue
        status, note = "valid", ""
        fname = r["path"].split("/")[-1]
        if fname in DOC_STATUS_OVERRIDES:
            status, note = DOC_STATUS_OVERRIDES[fname]
        elif r["category"] == "brand":
            status = "na"
        elif r["doc_type"] in ("challan", "photo", "address-proof", "inc-9", "inc-35", "spice-b", "moa", "aoa", "inc-20a", "fssai-receipt", "amazon-declaration"):
            status = "na"
        dt = {"kyc": "director-kyc", "aadhaar": "director-kyc", "pan": "pan"}.get(r["doc_type"], r["doc_type"])
        if r["category"] == "kyc":
            dt = "director-kyc"
        if dt not in [o for o in __import__("app.specs", fromlist=["DOC_TYPES"]).DOC_TYPES]:
            dt = "other"
        upsert(con, "documents", {"file_path": r["path"]}, {
            "title": r["title"], "doc_type": dt, "number": r.get("number") or "",
            "authority": r.get("authority") or "", "issue_date": r.get("issue_date") or "",
            "expiry_date": r.get("expiry_date") or "", "status": status,
            "restricted": 1 if r.get("restricted") else 0,
            "tags": r["category"], "notes": note, "renewal_lead_days": 90,
        })
        n += 1
    # Placeholders for documents the company should have but the vault lacks
    for title, dt, note in [
        ("Trademark registration certificate (Class 30, 'Buzzcaf')", "trademark", "PLACEHOLDER — restart-plan says the mark is registered; certificate/number not in vault. Needed for Amazon Brand Registry."),
        ("Udyam (MSME) registration", "udyam", "PLACEHOLDER — not found. Free, instant at udyamregistration.gov.in. Unlocks concessional TM fee and GS1 subsidy."),
        ("Company TAN", "tan", "PLACEHOLDER — allotted with incorporation (masked on certificate). Retrieve from MCA/Income-tax portal."),
        ("Current bank account (active)", "bank", "PLACEHOLDER — HDFC a/c 50200069779258 was blocked May 2023. Reactivate or open new; needed for Razorpay/Cashfree/Amazon payouts."),
        ("FSSAI annual return Form D1 — FY 2025-26", "fssai-annual-return", "PLACEHOLDER — due 31 May each year for the previous April–March. Confirm filing status on FoSCoS."),
        ("ROC annual filings AOC-4 / MGT-7A — FY 2024-25 & 2025-26", "roc-filing", "PLACEHOLDER — restart-plan says ROC filings current; obtain SRNs/receipts from the CA and file here."),
        ("Company ITR acknowledgements FY 2022-23 onwards", "itr", "PLACEHOLDER — obtain ITR-V acknowledgements from the CA."),
        ("Domain registration — buzzcaf.com", "domain", "PLACEHOLDER — verify registrar and expiry; restart-plan says buzzcaf.in does not resolve."),
        ("Domain registration — buzzcaf.in", "domain", "PLACEHOLDER — verify registrar and expiry; re-register if lapsed."),
        ("Amazon Seller Central — account details & category approval proof", "other", "PLACEHOLDER — screenshot/PDF of account health and Grocery & Gourmet approval."),
        ("Manufacturer FSSAI licence copy (chosen supplier)", "supplier-licence", "PLACEHOLDER — mandatory before contracting as Relabeller. Verify on FoSCoS."),
        ("Manufacturer agreement", "supplier-agreement", "PLACEHOLDER — clauses in SOP-01 / ground-work."),
        ("Nutrition lab report (per flavour)", "lab-report", "PLACEHOLDER — needed for the label. Ask whether the manufacturer's report covers Buzzcaf."),
        ("Label artwork — approved proofs (per flavour)", "label-artwork", "PLACEHOLDER — checked against SOP-04 before print."),
    ]:
        upsert(con, "documents", {"title": title}, {"doc_type": dt, "status": "pending", "notes": note, "tags": "placeholder"})
        n += 1
    return n


# ------------------------------------------------------------ compliance ----
COMPLIANCE = [
    ("GSTR-1 (outward supplies)", "GST portal", "monthly", {"type": "monthly", "day": 11}, 0, "Monthly if not on QRMP. Nil return still mandatory while registration is active."),
    ("GSTR-3B (summary + payment)", "GST portal", "monthly", {"type": "monthly", "day": 20}, 0, "Nil return mandatory even with zero sales. Late fee accrues per day."),
    ("GSTR-9 annual return", "GST portal", "annual", {"type": "annual", "dates": [[12, 31]]}, 0, "Optional below ₹2 Cr turnover but check current notification each year."),
    ("Annual General Meeting", "Board / CS", "annual", {"type": "annual", "dates": [[9, 30]]}, 0, "Within 6 months of FY end. Minutes to be kept."),
    ("AOC-4 (financial statements)", "MCA V3", "annual", {"type": "annual", "dates": [[10, 30]]}, 1500, "Within 30 days of AGM. Needs audited financials + CA/CS DSC."),
    ("MGT-7A (annual return, small company)", "MCA V3", "annual", {"type": "annual", "dates": [[11, 29]]}, 1500, "Within 60 days of AGM."),
    ("DIR-3 KYC (both directors)", "MCA V3", "annual", {"type": "annual", "dates": [[9, 30]]}, 0, "Free if on time; ₹5,000 per DIN if late and DIN gets deactivated."),
    ("ADT-1 (auditor appointment)", "MCA V3", "relative", {"type": "annual", "dates": [[10, 14]]}, 500, "Within 15 days of AGM whenever an auditor is appointed/re-appointed (5-year term)."),
    ("Company income-tax return", "Income-tax portal", "annual", {"type": "annual", "dates": [[10, 31]]}, 0, "Audit case deadline. Tax audit not applicable below thresholds but company ITR is always mandatory."),
    ("TDS returns (24Q/26Q) — if TDS deducted", "TRACES / IT portal", "quarterly", {"type": "quarterly", "dates": [[7, 31], [10, 31], [1, 31], [5, 31]]}, 0, "Only if any payment attracts TDS (rent > ₹2.4L/yr, contractor > ₹30k, professional fees > ₹30k)."),
    ("FSSAI annual return (Form D1)", "FoSCoS", "annual", {"type": "annual", "dates": [[5, 31]]}, 0, "For manufacturers/relabellers/importers. Penalty ₹100/day after 31 May."),
    ("FSSAI licence renewal — start", "FoSCoS", "once", {"type": "once", "date": TODAY}, 5000, "Licence 11522079000056 expired 23 Jun 2024. Renew/refile now: change KOB to Relabeller, add Retailer, correct premises address. Ask FoSCoS whether both KOBs fit one licence."),
    ("Shop & Establishment renewal check", "Maharashtra Labour (mahakamgar)", "annual", {"type": "annual", "dates": [[4, 4]]}, 0, "Intimation certificate 2231000316356174. Maharashtra intimation for <10 workers is generally valid without renewal — confirm annually and update address if changed."),
    ("Professional Tax (PTEC) annual payment", "Maharashtra mahagst", "annual", {"type": "annual", "dates": [[6, 30]]}, 2500, "Company PTEC ₹2,500/yr by 30 June. PTRC only if salaried staff."),
    ("Trademark renewal (10 years from filing)", "IP India", "ten-yearly", {"type": "yearly_from", "anchor": "2022-03-22", "years": 10}, 9000, "Anchor = approximate filing date (TM-48 dated 22 Mar 2022). Correct once certificate is found."),
    ("Amazon: refresh FSSAI documents on Seller Central", "Amazon Seller Central", "relative", {"type": "once", "date": TODAY}, 0, "Upload the renewed licence as soon as FoSCoS issues it; Grocery listings get suppressed on expired FSSAI."),
    ("Domain renewals (buzzcaf.com / buzzcaf.in)", "Registrar", "annual", {"type": "once", "date": TODAY}, 2000, "Set the real expiry once registrar login is recovered; change rule to annual."),
    ("Nightly backup restore test", "Ops", "quarterly", {"type": "quarterly", "dates": [[1, 15], [4, 15], [7, 15], [10, 15]]}, 0, "Restore ops/backups/latest into a temp dir and open the DB. An untested backup is not a backup."),
]


def seed_compliance(con) -> int:
    for name, auth, freq, rule, cost, notes in COMPLIANCE:
        upsert(con, "compliance", {"name": name}, {
            "authority": auth, "frequency": freq, "rule": json.dumps(rule), "cost_estimate": cost,
            "status": "active", "owner": "Sudhansu", "notes": notes,
        })
    services.refresh_compliance(con)
    return len(COMPLIANCE)


# ------------------------------------------------------------- suppliers ----
SUPPLIERS = [
    ("Dayum Food Products", "Indore, Madhya Pradesh", "Flavoured instant coffee: hazelnut, caramel, chocolate, vanilla", "10–25 kg per flavour (listing)", "~1–3 weeks (listing)", "Explicit private-labelling service; lowest MOQ found. Covers all four Buzzcaf flavours."),
    ("SLN Coffee Pvt Ltd", "Kushalnagar, Karnataka", "Instant coffee incl. hazelnut, vanilla, almond, cardamom, caramel", "Ask", "Ask", "Est. 1977, ~500 staff, ISO 22000 / FSSC 22000 / HALAL / KOSHER / FSSAI. Best quality signal."),
    ("Portim Consumer Product", "Surat, Gujarat", "30+ flavours; jars, pouches, sachets", "~209 jars (listing)", "1–20 days (listing)", "Explicit third-party labelling and customisation."),
    ("The Beanster Company", "Bhilai / Raipur, Chhattisgarh", "Sachets with custom branding", "2,000 pcs (listing)", "Ask", "Warm contact — they bought coffee from Buzzcaf in June 2023."),
    ("India Flavour", "New Delhi", "Wide flavour range, 50 g–500 g jars", "Ask", "Ask", ""),
    ("Indus Coffee Pvt Ltd", "Nellore, Andhra Pradesh", "Plain and flavoured, 100–250 g packs", "Ask", "Ask", ""),
]


def seed_suppliers(con) -> int:
    for name, city, products, moq, lead, notes in SUPPLIERS:
        upsert(con, "suppliers", {"name": name}, {
            "city": city, "products": products, "moq": moq, "lead_time": lead,
            "status": "enquiry to send", "notes": (notes + "\n\nMOQ/lead time are published listing figures (Sept 2026), not quotes. Send SOP-01 enquiry email.").strip(),
        })
    return len(SUPPLIERS)


# -------------------------------------------------------------- contacts ----
CONTACTS = [
    ("PLACEHOLDER — Chartered Accountant", "chartered accountant", "", "", "", "", "Who files GST/ITR/ROC today? Record name, phone, email, fee."),
    ("PLACEHOLDER — Company Secretary", "company secretary", "", "", "", "", "Needed for AOC-4/MGT-7A certification if not done by CA."),
    ("Govind Jethani (filed INC-20A, Oct 2022)", "company secretary", "Sai Datt Residency, Baner, Pune", "", "", "", "Name from the INC-20A challan. Possibly the practising professional used in 2022."),
    ("Noopur Jain — Trademark agent", "trademark agent", "1 Anand Vihar Colony, Bargawan, Katni 483501", "", "", "", "Authorised under TM-48 (Mar 2022). Ask her for the trademark number/certificate and renewal date."),
    ("HDFC Bank — Magarpatta branch", "bank", "HDFC Bank, The Destination Centre, Magarpatta City, Hadapsar, Pune", "18002026161", "", "Cust ID 200346433 · A/c 50200069779258 · IFSC HDFC0000486", "Account BLOCKED per May 2023 statement. Visit branch with KYC + board resolution."),
    ("FoSCoS helpdesk (FSSAI)", "FSSAI / FoSCoS", "Food Safety and Standards Authority of India", "1800112100", "helpdesk-foscos@fssai.gov.in", "Licence 11522079000056", "Ask: renewal of lapsed licence vs fresh application; can one licence hold Relabeller + Retailer KOBs."),
    ("FDA Maharashtra — Pune designated officer", "government", "Food & Drug Administration, Maharashtra", "", "", "", "State licensing authority for licence 11522079000056."),
    ("GST jurisdictional office", "government", "Bhosarigaon_705, Maharashtra State Tax", "", "", "GSTIN 27AAKCB6111C1Z3", "State Tax Officer on certificate: Jagtap Daulat Nagorao."),
    ("Amazon Seller Support", "Amazon", "Amazon Seller Services Pvt Ltd, Bangalore", "", "", "PLACEHOLDER merchant token", "Seller Central → Help. Grocery & Gourmet approval and FBA."),
    ("Razorpay", "payment gateway", "Razorpay Software Pvt Ltd", "", "", "PLACEHOLDER merchant ID", "Live key found in plaintext in old Documents/rzp.csv — ROTATE."),
    ("Cashfree Payments", "payment gateway", "Cashfree Payments India Pvt Ltd", "", "", "PLACEHOLDER", "Primary gateway per launch plan (0% UPI). Needs FSSAI + policy pages live to activate."),
    ("PLACEHOLDER — Domain registrar (buzzcaf.com / .in)", "domain / hosting", "", "", "", "", "Find via WHOIS; recover login."),
    ("PLACEHOLDER — Label printer", "printer / labels", "", "", "", "", "Ask manufacturer first; many bundle labelling."),
    ("Shiprocket", "courier / logistics", "Shiprocket", "", "", "PLACEHOLDER", "For own-site orders; API keys in .env only."),
    ("PLACEHOLDER — NABL lab (nutrition panel)", "lab", "", "", "", "", "Pune options: FARE Labs, Envirocare, TUV SUD. Get 3 quotes."),
    ("Ministry of Corporate Affairs helpdesk", "government", "MCA21 V3", "0120-4832500", "", "CIN U15400PN2022PTC209619", ""),
]


def seed_contacts(con) -> int:
    for name, role, org, phone, email, ref, notes in CONTACTS:
        upsert(con, "contacts", {"name": name}, {"role": role, "organisation": org, "phone": phone, "email": email, "account_ref": ref, "notes": notes})
    return len(CONTACTS)


# ----------------------------------------------------------------- tasks ----
TASKS = [
    ("Rotate the Razorpay live key found in plaintext (Documents/rzp.csv) and delete the CSV", "urgent", "security", 0, "Razorpay Dashboard → Settings → API Keys → Regenerate live key. Store new key only in the website .env and password manager. See vault/07-commerce/SECRETS-NOT-STORED-HERE.md."),
    ("Revoke old WooCommerce REST keys / confirm old WordPress is gone", "high", "security", 2, ""),
    ("Check both domain registrars — buzzcaf.com and buzzcaf.in; recover or re-register", "urgent", "website", 1, "WHOIS both. FSSAI licence lists sudhansu@buzzcaf.com so .com was held. Point DNS to Cloudflare."),
    ("Log into Amazon Seller Central: account health, Grocery & Gourmet approval, surviving listings, FBA registrations", "urgent", "amazon", 1, "Screenshot everything into vault/07-commerce."),
    ("Log into FoSCoS: renew licence 11522079000056, change KOB to Relabeller, add Retailer, correct premises address", "urgent", "compliance", 3, "Ask explicitly whether both KOBs can sit on one licence and whether a lapsed licence renews or needs a fresh application. Budget ₹4–8k + late fee."),
    ("Email all six suppliers the SOP-01 enquiry (price/kg, price/finished unit, MOQ per flavour, split MOQ, lead time, paid samples, FSSAI copy, spec sheet natural/artificial)", "high", "supply", 3, "Dayum, SLN, Portim, Beanster (warm), India Flavour, Indus."),
    ("Decide the two launch flavours; park the other two until batch one sells through", "high", "supply", 7, "Suggested: Hazelnut + Belgian Chocolate (most searched flavoured-instant terms); Original as flavour three."),
    ("Set up Google Business Profile for Buzzcaf Private Limited", "normal", "marketing", 7, "20 minutes, free."),
    ("Collect every CA report and filing (FY2022-23 to FY2025-26) into vault/13-accounts-and-audit and register each in Ops", "high", "compliance", 7, "Ask the CA for the full per-year set listed in vault/13-accounts-and-audit/README.md, starting with the one-page compliance status report. File each with: python ops/intake.py <file> --kind <kind> --fy <yyyy-yy> --date <date>. Then mark the matching obligations done in Ops → Compliance with the SRN/ARN."),
    ("Draft the seven Amazon listing images as a shot list", "normal", "amazon", 10, "Hero on white; flavour infographic; prepared cup (cold coffee/latte); jar in hand; 3-step how-to; full label readable; brand & trust."),
    ("Reactivate HDFC current account (blocked) or open a new current account", "urgent", "finance", 5, "Needed for gateway payouts and Amazon disbursements."),
    ("Register Udyam (MSME) — free", "normal", "compliance", 7, "udyamregistration.gov.in with company PAN AAKCB6111C."),
    ("Obtain trademark certificate/number from Noopur Jain; record renewal date", "high", "compliance", 7, "Needed for Amazon Brand Registry."),
    ("Confirm GST return filing status for every month since last sale (nil returns)", "urgent", "compliance", 3, "Unfiled nil returns accrue late fees; check GST portal → Returns dashboard."),
    ("Confirm ROC filings (AOC-4, MGT-7A) and DIR-3 KYC are current for FY 2024-25", "high", "compliance", 7, ""),
    ("Fill consumer-care phone number and support email everywhere (label, website, Amazon)", "high", "admin", 7, "Number must be monitored."),
    ("Add real product data: ingredients, flavouring type, nutrition per 100 g, shelf life, net qty, MRP per SKU", "high", "website", 14, "Blocks label print and Legal Metrology fields on the website."),
    ("Run the 4-week shelf test on front-runner supplier samples (SOP-02)", "high", "supply", 35, ""),
    ("Set up Cashfree merchant account (primary) and keep Razorpay as fallback", "normal", "website", 14, "Both need FSSAI + policy pages live on the domain."),
    ("Revive Instagram @buzzcaf — first batch shoot (3 posts/week)", "normal", "marketing", 21, "Do not create a new handle."),
    ("Set a recurring calendar reminder for FSSAI annual return (31 May) and AGM/ROC season (Sep–Nov)", "normal", "compliance", 7, "Or just open Buzzcaf Ops dashboard weekly."),
]


def seed_tasks(con) -> int:
    from datetime import timedelta
    for title, prio, area, due_days, details in TASKS:
        upsert(con, "tasks", {"title": title}, {
            "priority": prio, "area": area, "status": "todo", "owner": "Sudhansu",
            "due_date": (date.today() + timedelta(days=due_days)).isoformat(), "details": details,
        })
    return len(TASKS)


DECISIONS = [
    ("2026-09-06", "Outsource production: private-label with an FSSAI-licensed manufacturer; Buzzcaf becomes Relabeller (deemed manufacturer).", "supply", "Supply failure and self-repacking quality issues ended the business in 2023. Manufacturer quality systems replace ours. restart-plan §Model."),
    ("2026-09-06", "Outsource fulfilment: Amazon FBA first; own website is trust + D2C + subscriptions, not the launch sales engine.", "strategy", "Self-shipping cost ₹84 per ₹213 order in 2023 (39%). FBA warehouses already on GST. Amazon 0% referral in ₹300–1,000 Grocery band (Mar 2026 policy). restart-plan §Model."),
    ("2026-09-06", "Launch two flavours, not four; add the others from revenue.", "supply", "MOQ is per flavour. Two funded SKUs always in stock beat four half-funded ones; stock-outs cost Amazon ranking."),
    ("2026-09-06", "Keep every listing priced ₹300–1,000.", "amazon", "0% referral window; below ₹300 closing fee dominates, above ₹1,000 10% referral. Sanity-check the model at 7%."),
    ("2026-09-06", "No paid ads until 15+ genuine reviews at 4.3+.", "marketing", "Below that base traffic does not convert. Never incentivise reviews — account health is the most valuable asset."),
    ("2026-09-06", "Skip quick commerce (Blinkit/Zepto/Instamart) at launch.", "strategy", "Inventory-led, NDA margins, ₹25k/SKU/state entry; needs 70%+ gross margin. Revisit month six with sell-through data. launch-plan call #4."),
    ("2026-09-07", "Company records live in Buzzcaf Ops (this system) + vault/; secrets live only in a password manager and .env files.", "security", "Live Razorpay key was found in a plaintext CSV from 2022."),
    ("2026-09-07", "Diwali 2026: only a small market-test quantity if a supplier can turn a small run fast; the real launch targets January 2027 after proper sampling and the 4-week shelf test.", "strategy", "Rushing production is exactly what broke the business in 2023. restart-plan §Timing."),
]


def seed_decisions(con) -> int:
    for d, decision, area, rationale in DECISIONS:
        upsert(con, "decisions", {"decision": decision}, {"date": d, "area": area, "rationale": rationale, "decided_by": "Sudhansu (via agency plan)", "source": "docs/ + restart-plan.html"})
    return len(DECISIONS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete the database first")
    a = ap.parse_args()
    paths.ensure_dirs()
    p = paths.db_path()
    if a.reset and p.exists():
        p.unlink()
        for ext in ("-wal", "-shm"):
            q = Path(str(p) + ext)
            if q.exists():
                q.unlink()
    con = db.connect(p)
    db.init_schema(con)
    counts = {
        "documents": seed_documents(con),
        "compliance": seed_compliance(con),
        "suppliers": seed_suppliers(con),
        "contacts": seed_contacts(con),
        "tasks": seed_tasks(con),
        "decisions": seed_decisions(con),
    }
    services.auto_expire_documents(con)
    db.meta_set(con, "seeded_at", db.now())
    con.close()
    print("seeded:", json.dumps(counts))
    print("db:", p)


if __name__ == "__main__":
    main()
