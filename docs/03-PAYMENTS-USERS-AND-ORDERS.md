# Payments, User Management and Order Flow

Implementation lives in `website/` (see its README for env vars and exact endpoints). This document is the business-level design and the operating rules.

## Payment gateways
| | Cashfree (primary) | Razorpay (fallback) |
|---|---|---|
| Why | 0% on UPI as standing pricing; 0% platform fee offer for new sign-ups after 21 Jul 2026 up to ₹20 L GMV/month until 31 Mar 2027 | Existing account since 2022 (used for FSSAI fee); widest method support |
| Fees (typical) | UPI 0%, cards/netbanking ~1.9% + GST | 2% + GST on most methods |
| KYC needs | Company PAN, CIN, GST, bank proof, director KYC, **FSSAI licence**, live website with policies + contact | Same |
| Settlement | T+1 standard | T+2 standard, T+0 on request |
| Switch | `PAYMENT_PROVIDER=cashfree` | `PAYMENT_PROVIDER=razorpay` |

Rules: never store card data (both gateways are hosted checkout). Every webhook is HMAC-verified before an order is marked paid. Test mode until the go-live checklist is complete. Refunds are issued from the gateway dashboard and mirrored in Admin → Orders.

**Immediate action**: the Razorpay live key/secret sits in plaintext in `Documents/rzp.csv` from 2022. Regenerate it in the Razorpay dashboard, store the new pair in a password manager, put it only in `.env`/Vercel.

## COD
Off at launch (`ENABLE_COD=false`). Food/FMCG prepaid RTO is 4–12%, COD 25–40%. Turn on in month two only with a partial-prepay or OTP-verified address, and only after the actual RTO rate is known.

## User management
- **Guest checkout** is default: phone + email + address. Accounts are optional and created after the first order ("save your details").
- **Accounts**: email + password now; phone OTP login stubbed behind an interface (add MSG91 / Twilio Verify when volume justifies ₹0.20 per OTP).
- **Roles**: `customer`, `admin`. Admin seeded from env. Add `staff` role when someone else handles orders.
- **Data**: name, email, phone, addresses, orders, subscriptions, newsletter consent, attribution (which YouTube channel / UTM brought them). Privacy policy covers this. DPDP Act 2023 principles: collect only what is needed, delete on request (admin can delete a user), no selling data.
- **Subscriptions**: 2/4/6-week interval, pause/skip/cancel, stored in DB. Recurring charge is Phase 2: Razorpay Subscriptions or Cashfree Subscriptions (UPI AutoPay mandate); until then the cron route sends a WhatsApp/email reorder link at the interval, which is honestly what most small D2C brands do first.

## Order lifecycle
```
cart → checkout (address, coupon, attribution cookie) → gateway order created
  → customer pays on hosted checkout → webhook verified → Order.status = paid
  → email + WhatsApp confirmation → Admin packs (SOP-07) → Shiprocket AWB → status shipped
  → tracking page /order/[number] → delivered → "Request a review" nudge day +5
```
Order numbers: `BZC-2026-000001`. GST invoice PDF generated per paid order (Admin → Orders → Invoice) with GSTIN 27AAKCB6111C1Z3, HSN 2101 12 00, 5% GST split CGST/SGST for Maharashtra, IGST otherwise.

## Coupons and attribution
- One coupon per YouTube channel (`BEYOND10`, `AFTERDARK10`, `LIFE10`, `KHAYAL10`, `STUDIO10`) plus `WELCOME10`.
- `/yt?c=<channel>` landing page auto-applies the coupon and sets the attribution cookie; UTM parameters are stored on the order. Admin dashboard shows orders and revenue per channel — this is how we know which channel sells coffee.

## Inventory across channels
Same physical stock is on Amazon (FBA) and the site (own stock). Below 30 orders/day: a daily manual reconciliation (SOP-12) — Admin → Products → stock is the site's source of truth; FBA is Amazon's. Above that: move to Unicommerce/Easyecom.

## Reconciliation and accounting
- Monthly: Cashfree/Razorpay settlement report + Amazon Payments report + Shiprocket invoice → CA. Ops → Compliance has the GSTR-1/3B dates.
- GST on gateway and Amazon fees (18%) is input credit; instant coffee output GST is 5%.
