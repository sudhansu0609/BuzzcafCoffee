---
title: SOP-01 Supplier qualification and enquiry
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: How to approach, compare and qualify a private-label instant coffee manufacturer, and what must be in the agreement.
---

# SOP-01 Supplier qualification and enquiry

**Why this exists.** Supply failure ended Buzzcaf once (2023). Under private label the manufacturer's quality systems do the work we could not do ourselves — which only helps if we check they actually have them. As a *Relabeller*, FSSAI treats Buzzcaf as the manufacturer of a product we did not make: liability attaches to our brand, not to the factory gate.

## 1. Send the same enquiry to every candidate

Send to all six (Ops → Suppliers), the same day, the same text. A supplier who answers all of it clearly is already telling you how they operate.

> **Subject:** Private-label flavoured instant coffee — enquiry from Buzzcaf Private Limited (FSSAI 11522079000056)
>
> We are a Pune-registered company (CIN U15400PN2022PTC209619, GST 27AAKCB6111C1Z3) relaunching our flavoured instant coffee range (Original, Hazelnut, Belgian Chocolate, Caramel) in 50 g glass jars, sold on Amazon FBA and our own site. Please quote:
>
> 1. Price per kg **and** price per finished labelled unit (50 g jar), at 25 kg / 50 kg / 100 kg.
> 2. Also a bulk unbranded price per kg for comparison.
> 3. MOQ **per flavour**, and whether a combined minimum can be split across two flavours.
> 4. Lead time from order confirmation to dispatch.
> 5. Paid samples of each flavour — we will pay; please state the cost.
> 6. A copy of your FSSAI licence and confirmation it covers category 14.1.5 (coffee).
> 7. Spec sheet and a sample COA. Is the flavouring **natural, nature-identical, or artificial**?
> 8. Do you supply the jar/lid/induction seal, or do we? Do you apply our label?
> 9. Stated shelf life and the storage conditions it assumes.
> 10. Can you repeat the identical flavour profile at 3 and 6 months?
> 11. Do you provide a nutritional analysis per 100 g that we can legally print?
> 12. Batch coding format and how you support a recall/traceability request.
>
> Regards, Sudhansu Kumar Singh, Director · consumer care PLACEHOLDER phone · sudhansu@buzzcaf.com

Log the send date in Ops → Suppliers → status "enquiry sent". Chase after 5 working days.

## 2. The two-quote comparison

Build one table: finished-labelled ₹/unit vs bulk-unbranded ₹/kg for each supplier. One listing suggested a finished private-label jar can be *cheaper per kg* than other suppliers' raw bulk. Do not assume private label carries a premium — measure it.

## 3. Verify before you trust a PDF

| Check | How | Record in Ops |
|---|---|---|
| FSSAI licence valid, current, covers 14.1.5 | Search the number on foscos.fssai.gov.in yourself | Suppliers → `fssai_verified` + date + expiry |
| Corporate registration and trading history | MCA master data / GST search by GSTIN | notes |
| Third-party lab reports (last 12 months) | Ask; look for NABL lab name and dates | vault/08-suppliers |
| FSSAI inspections, notices, suspensions | Ask directly; listen for a practised answer | notes |
| How they handle a failed batch | Ask: replacement? credit? who pays freight? | notes |
| Visit the front-runner | Indore, Surat, Kushalnagar are a day from Pune. You are legally answerable for that facility (Schedule 4 hygiene) | `audit_visit_date` |

## 4. Samples → SOP-02

Paid samples from at least three. Run SOP-02 (blind tasting + 4-week shelf test) before committing the budget.

## 5. The agreement must contain

- Exclusive use of the Buzzcaf name, recipe and artwork — no reselling to others.
- Who supplies and pays for packaging; who owns unused packaging stock.
- **A COA with every batch**, not on request.
- Defective batch remedy: replacement, credit, return freight.
- Batch coding and traceability — trace any unit to a production lot.
- Delivery timelines with a stated remedy for lateness.
- Pre-production sample against final artwork before every full run.
- Confidentiality; termination notice period.
- Both parties' FSSAI numbers and the "Manufactured by / Marketed by" label wording (SOP-04).

Store the signed agreement in `vault/11-agreements/` and register it in Ops → Documents with the expiry/renewal date.

## 6. Decision gate

Approve a supplier only when: FSSAI verified on FoSCoS · samples pass blind tasting with milk and cold · 4-week shelf test passed · lab report or COA in hand · agreement signed. Set Suppliers → status "approved". Everyone else stays "rejected" with the reason in notes — you will want it next year.
