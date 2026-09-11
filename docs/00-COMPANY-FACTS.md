# Buzzcaf — Company Facts (single source of truth)

Sourced from the company's own documents in `Buzzcaf/Buzzcaf/Buzzcaf/Documents/pdfs` (copied into `vault/`). Verified 7 Sep 2026 by reading the PDFs. Anything marked PLACEHOLDER must be filled by Sudhansu.

## Legal entity
| Field | Value |
|---|---|
| Legal name | BUZZCAF PRIVATE LIMITED |
| Brand | Buzzcaf |
| CIN | U15400PN2022PTC209619 |
| Incorporated | 23 March 2022 (Companies Act 2013, limited by shares) |
| Registered office (ROC) | S.No.25 Flat No 304, Laxmi Enclave, Lonkar Wasti, Keshavnagar, Mundhwa, Pune, Maharashtra 411036 |
| GSTIN | 27AAKCB6111C1Z3 (Regular; liable from 19 May 2022; amended certificate issued 6 Jul 2023) |
| GST principal place | Flat C1-1006, Wing C1, Saarthi Savvy Homes 2, Bhumkar Chowk, Hinjewadi, Pune 411057 |
| GST additional places | Amazon FBA warehouses (Bhiwandi x2, Chakan) per restart-plan |
| FSSAI licence | 11522079000056 — State licence, Maharashtra. Kind of business on record: "Repacker – General Manufacturing", category 14.1.5 coffee. Issued 24 Jun 2022. **EXPIRED** (last validity ended 23 Jun 2024 per restart plan). Licensed premises: Sr No 29/2, Shankar Nagar, Keshav Nagar, Mundhwa, Pune 411036 (modification receipt Oct 2022 shows Sr No 36, Flat 301, Matoshree Niwas, Manjri Road, Sonai Nagar, Keshavnagar) |
| Shop & Establishment (Maharashtra) | Reg no 2231000316356174 / 103571022203, issued 4 Apr 2022, Pune. Nature: dealing in coffee, coffee beans, dry fruits, spices and tea |
| Company PAN / TAN | On incorporation certificate (masked in PDF) — PLACEHOLDER: `AAKCB6111C` is the PAN embedded in the GSTIN |
| Company email (MCA) | sudhansu@buzzcaf.com |
| Domains | buzzcaf.com (was live with WooCommerce in 2022), buzzcaf.in (DNS not resolving) — status to verify at registrar |
| Trademark | Registered per restart-plan (class 30) — certificate NOT in vault. A TM-48 power of attorney (Mar 2022) names the filing agent as Noopur Jain, Katni — ask them for the application/registration number and certificate. PLACEHOLDER: TM number |
| Bank | HDFC current account 50200069779258 (Magarpatta branch, IFSC HDFC0000486). The May 2023 statement shows the account **BLOCKED** — reactivate (KYC) or open a new current account before any gateway payout |
| Udyam (MSME) | PLACEHOLDER — not found in documents; register (free) |

## People
| Name | Role | Notes |
|---|---|---|
| Sudhansu Kumar Singh | Director, DIN 09545568 | Resident Maharashtra. Runs Buzzcaf Media / YouTube channels. Email multisonu@gmail.com, sudhansu@buzzcaf.com |
| Himansu Kumar Singh | Director | Resident West Bengal |

## Products (existing brand, existing photography)
Flavoured instant coffee in 50 g glass jars with black labels. Four flavours:
1. Original (`original`)
2. Belgian Chocolate (`belgian-chocolate`) — label says "Belgium Chocolate"
3. Hazelnut (`hazelnut`) — earlier site called it "Irish Hazelnut"
4. Caramel (`caramel`)
Also a "Desire" page existed on the old site (unclear SKU; treat as retired).

Strategy chosen in restart-plan (Sept 2026): **private-label** (a licensed manufacturer blends, fills and labels; Buzzcaf becomes FSSAI "Relabeller" + "Retailer"), **Amazon FBA first**, own website as trust + D2C + subscription channel. Price band ₹300–1,000 (Amazon 0% referral window). Launch 2 flavours first, add others from revenue. GST on instant coffee: 5% (HSN 2101 11/12).

## Existing digital assets
- Amazon Seller Central account with Grocery & Gourmet approval and FBA history (2023)
- Instagram @buzzcaf (66 followers, dormant since 17 Jun 2023)
- Razorpay live account (key in `Documents/rzp.csv` — SECURITY: plaintext live secret; rotate it)
- Old WooCommerce store keys (`buzzcaf woocommerce key.txt`)
- Old Node/React store repo: github.com/sudhansu0609/Buzzcaf (2022, template-grade, not reused)
- YouTube channels under Buzzcaf Media: Beyond3Baje, Spilled Coffee After Dark, Life3Baje, Khayal3Baje, Spilled Coffee Studio (managed by BuzzcafAI Studio)

## Brand voice / visual
Black jar labels, cream + gold logo (two coffee beans in a circle, "BUZZCAF PVT. LTD."). Warm, honest, Indian-first ("how coffee is actually drunk here — with milk, cold, dalgona"). Registered company since 2022, FSSAI licensed. Fonts on site: display serif + clean sans.

## Placeholders to fill (Sudhansu)
- Consumer-care phone number (must be monitored) — PLACEHOLDER `+91-XXXXXXXXXX`
- Manufacturer name/address/FSSAI number (after supplier selection)
- Trademark number; Udyam number
- Bank account for payouts; Cashfree/Razorpay live keys (put in `.env`, never in repo)
- Nutritional panel per 100 g (lab report)
- Ingredients + flavouring type (natural / nature-identical / artificial) per flavour
- Shelf life, net quantity, MRP per SKU
