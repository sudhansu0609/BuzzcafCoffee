---
title: SOP-10 Security and access
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: Where credentials live, who holds what, and how keys get rotated — written because a live Razorpay key was found in a plaintext CSV.
---

# SOP-10 Security and access

## 1. The rule

**No credential is ever stored in a file that is not a password manager or a gitignored `.env`.** Not in CSV, not in a text file "in the documents folder", not in chat, not in a screenshot.

Found on 2026-09-07 and to be fixed first: `Documents/rzp.csv` (Razorpay **live** key id + secret) and `buzzcaf woocommerce key.txt` (two copies). Action: rotate, delete, record in Ops → Tasks.

## 2. Password manager

One shared collection "Buzzcaf" in Bitwarden (free for two users) or 1Password. Every account below gets an entry with URL, login, 2FA recovery codes, and the *owner* noted in Ops → Contacts (`owner` field) — never the password itself.

| Account | Owner | 2FA |
|---|---|---|
| MCA V3 (company + both DINs / DSC tokens) | Sudhansu | DSC physical token — location noted |
| GST portal | Sudhansu | OTP to registered mobile — which number? record it |
| Income-tax portal (company PAN) | Sudhansu | |
| FoSCoS | Sudhansu | |
| Amazon Seller Central | Sudhansu; add Himansu as secondary user with limited permissions | Mandatory 2FA |
| Razorpay / Cashfree | Sudhansu | Enable 2FA; restrict API key to server IP where offered |
| Domain registrar + Cloudflare | Sudhansu | 2FA on both; registrar lock ON |
| Hosting (VPS / Vercel) + GitHub | Sudhansu | 2FA, SSH keys not passwords |
| Google Workspace / Zoho Mail (sudhansu@buzzcaf.com) | Sudhansu | |
| Instagram @buzzcaf, YouTube channels | Sudhansu | |
| Bank net-banking | Sudhansu | Hardware/OTP |
| Shiprocket, WhatsApp Business API | Sudhansu | |

Two people must be able to get in to every account if one is unavailable: recovery codes in the shared collection.

## 3. Runtime secrets

- Website: `.env` on the server only; `.env.example` in git with blank values. Gateway webhooks verified by signature; keys never shipped to the browser except the public key id.
- Ops: no secrets at all. It records IDs and owners, not passwords.
- BuzzcafAI: keeps its own `.env`; same rule.

## 4. Rotation

- Rotate any key that has ever been in a file, chat or screenshot — today.
- Rotate gateway and hosting keys every 12 months, and immediately when a laptop is lost, a contractor leaves, or a repo is made public.
- Log each rotation as a Task marked done with the date.

## 5. Devices and backups

- Laptop disk encryption on (BitLocker); screen lock 5 min.
- `ops/backups/latest.zip` contains the vault including KYC documents: store the cloud copy in an encrypted location (Drive with account 2FA at minimum; better, a zip with a password from the manager).
- The Ops app has **no login**. It binds to 127.0.0.1 only. Never expose it via a tunnel or a public port; if it must be reached remotely, put it behind Tailscale or Cloudflare Access.

## 6. Incident

Suspected compromise: rotate the affected key → check gateway/Amazon for unknown transactions or bank-account changes → change the account password and 2FA → log it in Decisions with what changed.
