---
title: SOP-06 FBA inbound shipment
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: Getting a checked batch into Amazon's warehouse without a rejection, and never running out of stock.
---

# SOP-06 FBA inbound shipment

## Before the first shipment (once)

- **Retailer KOB on the FSSAI licence.** Amazon requires it for FBA food eligibility. Confirm on FoSCoS before creating any shipment — discovering this at the warehouse door costs weeks.
- Licence valid with **2+ months** remaining, uploaded in Seller Central → Account Info → Grocery documents.
- Grocery & Gourmet approval active; GTIN exemption in place (or GS1 barcodes if you bought them).
- Listing complete with Legal Metrology fields (SOP-04 B) and the shelf-life declaration.
- FBA warehouses (Bhiwandi, Chakan) are already additional places of business on GST 27AAKCB6111C1Z3 — check they still appear on the GST certificate; add any new FC Amazon assigns.

## Per shipment

1. Batch has **QC pass** in Ops (SOP-03). No exceptions.
2. Check Amazon's **remaining-shelf-life rule** for Grocery in Seller Central *today* (it changes). Stock arriving too close to best-before is rejected and returned at your cost.
3. Create the shipment in Seller Central → Send to Amazon. Prefer **ship direct from the manufacturer to the FC** — saves a freight leg and a handling step. If so, the SOP-03 checks happen at the manufacturer with photos, or on a sample courier'd to you first.
4. Labels: FNSKU on each unit (or manufacturer-applied), box labels, expiry date on the outer carton as Amazon specifies for expiring goods.
5. Record in Ops → Batches: `destination` = FBA, `fba_shipment_id`, units sent. Reduce `qty_remaining` for own stock accordingly.
6. Send a **first tranche**, not everything. Storage fees on slow stock are real; you can always send more.

## After

- Allow **real time for receipting** — it is slower than you expect and outside your control. Do not plan a seasonal window around it.
- Watch **Inventory → Restock** weekly. Set a reorder threshold (e.g. 4 weeks of cover). Going out of stock costs search ranking that takes weeks to rebuild; reorder at the threshold, not when the shelf is empty.
- Reconcile FBA inventory with Ops batches weekly (SOP-12).
- Use **Request a Review** on every order (Orders → Request a review). It is built in, compliant, and almost nobody does it consistently.
