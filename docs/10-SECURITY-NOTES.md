# Security Notes — read first

## Findings from the old folder (7 Sep 2026)
1. **Live Razorpay API key + secret in plaintext** at `Buzzcaf/Buzzcaf/Buzzcaf/Documents/rzp.csv` (key id prefix `rzp_live_`). Anyone with that file can create orders/refunds on your account. **Action**: Razorpay dashboard → Account & Settings → API Keys → Regenerate live key. Store the new pair in Bitwarden. Delete `rzp.csv`. The agency did not copy this file anywhere; `vault/07-commerce/` only has a note.
2. **WooCommerce REST key/secret** in `Documents/buzzcaf woocommerce key.txt` (and a duplicate in `pdfs/`). The old WooCommerce site is presumably gone; delete the files anyway.
3. **AWS key pair** `buzzcaf_keypair.pem` and `.ppk` in the old repo folder. If the EC2 instance is gone, delete these; if not, terminate the instance (it may be billing you).
4. **Director identity documents** (Aadhaar, PAN, rent agreements) sit unencrypted in the old folder and now also in `vault/05-directors-kyc/`. Keep the whole `BuzzcafCoffee/` folder on an encrypted drive (BitLocker on B:) and out of any cloud sync that is not end-to-end encrypted.
5. **Old repo** on GitHub (`sudhansu0609/Buzzcaf`) had a "removing pem" commit — the key was committed once. Assume it is compromised; see point 3. Consider making that repo private or deleting it.

## Rules going forward (SOP-10 in Ops)
- Secrets only in `.env` (git-ignored) locally and in Vercel env vars in production. Never in docs, CSVs, screenshots, or chat.
- Password manager + 2FA everywhere (registrar, GitHub, Vercel, Neon, Cloudflare, Zoho, Seller Central, Cashfree, Razorpay, FoSCoS, GST portal, MCA, bank).
- Admin URL behind Cloudflare Access in production.
- Ops system stays local; backups encrypted (7-Zip AES or Cryptomator) before going to cloud storage.
- Quarterly: review who has access to what (Ops → Contacts has an "access" column).
