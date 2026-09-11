# Secrets are not stored in the vault

Two credential files exist in the OLD documents folder
(`Buzzcaf/Buzzcaf/Buzzcaf/Documents/`) and were deliberately NOT copied here:

| File | What it is | Action |
|---|---|---|
| `rzp.csv` | Razorpay **live** key id + key secret, plaintext (2022) | **Rotate now** in Razorpay Dashboard -> Settings -> API Keys -> Regenerate. Then delete the CSV. |
| `buzzcaf woocommerce key.txt` (also in `pdfs/`) | WooCommerce REST consumer key/secret for the old buzzcaf.com store | Old store is gone; revoke if the WordPress install still exists, then delete both copies. |

Rules (see SOP-10 Security & access):
- Credentials live in a password manager (Bitwarden / 1Password) in a shared "Buzzcaf" collection, never in git, CSV, chat, or this folder.
- Runtime secrets go in `.env` files that are gitignored.
- The Ops "Contacts" module records *where* an account lives and who owns it, never the password.
