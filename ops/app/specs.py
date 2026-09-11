"""Declarative resource specifications.

Every module (documents, suppliers, batches, ...) is a Resource: a table name,
an ordered list of Fields, which columns the list page shows, and which field
is the human title. The generic router in routes.py turns each Resource into
list / detail / new / edit HTML pages and a JSON API. Module-specific logic
(next-due dates, complaint patterns, retention samples) lives in services.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- field kinds --------------------------------------------------------------
# text, textarea, date, int, real, bool, select, file, ref, json, readonly


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"
    options: list[str] | None = None   # for select
    ref: str | None = None             # for ref: target resource key
    required: bool = False
    help: str = ""
    default: Any = None

    @property
    def sql_type(self) -> str:
        return {"int": "INTEGER", "real": "REAL", "bool": "INTEGER"}.get(self.kind, "TEXT")


@dataclass
class Resource:
    key: str                 # url segment + table name
    singular: str
    plural: str
    fields: list[Field]
    list_columns: list[str]
    title_field: str
    icon: str = "•"
    order_by: str = "id DESC"
    search_fields: list[str] = field(default_factory=list)
    description: str = ""

    def field(self, name: str) -> Field:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)


DOC_TYPES = [
    "incorporation", "moa", "aoa", "inc-9", "inc-20a", "inc-35", "spice-b", "challan",
    "pan", "tan", "gst", "fssai-licence", "fssai-receipt", "fssai-annual-return",
    "amazon-declaration", "shop-act", "rent-agreement", "address-proof",
    "trademark", "udyam", "bank", "board-resolution", "roc-filing", "itr",
    "financial-statements", "audit-report", "board-minutes", "form-26as", "gst-return",
    "tds-return", "ledger", "bank-statement", "ca-report",
    "supplier-agreement", "supplier-licence", "coa", "lab-report", "label-artwork",
    "insurance", "director-kyc", "domain", "invoice", "photo", "logo", "other",
]

RESOURCES: dict[str, Resource] = {}


def register(r: Resource) -> Resource:
    RESOURCES[r.key] = r
    return r


register(Resource(
    key="documents", singular="Document", plural="Documents", icon="📄",
    description="Every company paper, with number, dates and where the file lives in the vault.",
    title_field="title",
    list_columns=["title", "doc_type", "number", "issue_date", "expiry_date", "status"],
    search_fields=["title", "number", "tags", "notes"],
    order_by="CASE status WHEN 'expired' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, expiry_date, id",
    fields=[
        Field("title", "Title", required=True),
        Field("doc_type", "Type", "select", options=DOC_TYPES, required=True),
        Field("number", "Document number"),
        Field("authority", "Issuing authority"),
        Field("issue_date", "Issue date", "date"),
        Field("expiry_date", "Expiry date", "date", help="Leave blank if it never expires."),
        Field("renewal_lead_days", "Renewal lead (days)", "int", default=90,
              help="How many days before expiry the renewal should start."),
        Field("status", "Status", "select", options=["valid", "expired", "pending", "na"], default="valid"),
        Field("file_path", "Vault file", "file", help="Path relative to vault/, or upload a new file."),
        Field("restricted", "Restricted (personal ID)", "bool", default=0),
        Field("tags", "Tags", help="comma separated"),
        Field("notes", "Notes", "textarea"),
        Field("sha256", "SHA-256", "readonly"),
        Field("source", "Source", help="how it arrived: manual, intake, inbox-auto, mail:<message id>"),
    ],
))

register(Resource(
    key="compliance", singular="Obligation", plural="Compliance calendar", icon="📅",
    description="Recurring statutory obligations with computed next-due dates.",
    title_field="name",
    list_columns=["name", "authority", "frequency", "next_due", "owner", "status", "cost_estimate"],
    search_fields=["name", "authority", "notes"],
    order_by="CASE status WHEN 'active' THEN 0 ELSE 1 END, next_due",
    fields=[
        Field("name", "Obligation", required=True),
        Field("authority", "Authority / portal"),
        Field("frequency", "Frequency", "select", options=["monthly", "quarterly", "annual", "once", "relative", "ten-yearly"], default="annual"),
        Field("rule", "Rule (JSON)", "json",
              help='e.g. {"type":"monthly","day":11} · {"type":"annual","dates":[[12,31]]} · {"type":"once","date":"2026-09-30"} · {"type":"relative","anchor":"2026-09-30","days":30}'),
        Field("next_due", "Next due", "readonly"),
        Field("last_done", "Last done", "date"),
        Field("owner", "Owner", default="Sudhansu"),
        Field("cost_estimate", "Cost estimate (₹)", "int", default=0),
        Field("status", "Status", "select", options=["active", "not-applicable", "suspended"], default="active"),
        Field("applies_if", "Applies if", help="condition, e.g. 'turnover > 2 Cr' or 'TDS deducted'"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="suppliers", singular="Supplier", plural="Suppliers", icon="🏭",
    description="Manufacturers and vendors, their licences, quotes and qualification status.",
    title_field="name",
    list_columns=["name", "city", "products", "moq", "lead_time", "status", "fssai_verified"],
    search_fields=["name", "city", "products", "notes"],
    order_by="CASE status WHEN 'approved' THEN 0 WHEN 'sampling' THEN 1 WHEN 'quoted' THEN 2 ELSE 3 END, name",
    fields=[
        Field("name", "Name", required=True),
        Field("city", "City / state"),
        Field("contact_name", "Contact person"),
        Field("phone", "Phone"),
        Field("email", "Email"),
        Field("website", "Website / listing URL"),
        Field("fssai_number", "FSSAI licence no"),
        Field("fssai_verified", "FSSAI verified on FoSCoS", "bool", default=0),
        Field("fssai_verified_on", "Verified on", "date"),
        Field("fssai_expiry", "Their licence expiry", "date"),
        Field("products", "Products / flavours"),
        Field("moq", "MOQ (per flavour)"),
        Field("lead_time", "Lead time"),
        Field("quote_per_kg", "Quote ₹/kg bulk unbranded", "real"),
        Field("quote_per_unit", "Quote ₹/finished labelled unit", "real"),
        Field("quote_date", "Quote date", "date"),
        Field("samples_received", "Samples received", "bool", default=0),
        Field("samples_received_on", "Samples received on", "date"),
        Field("sample_result", "Sample test result", "select", options=["", "pending", "pass", "fail"], default=""),
        Field("shelf_test_result", "4-week shelf test", "select", options=["", "pending", "pass", "fail"], default=""),
        Field("agreement_status", "Agreement", "select", options=["none", "drafting", "signed"], default="none"),
        Field("audit_visit_date", "Audit / visit date", "date"),
        Field("status", "Status", "select",
              options=["enquiry to send", "enquiry sent", "quoted", "sampling", "approved", "rejected"], default="enquiry to send"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="batches", singular="Batch", plural="Batches & QC", icon="📦",
    description="Every production lot received, its COA, the six receiving checks, and where the stock went.",
    title_field="batch_no",
    list_columns=["batch_no", "product", "supplier_id", "manufacture_date", "best_before", "qty_received", "qty_remaining", "qc_result"],
    search_fields=["batch_no", "product", "coa_reference", "notes"],
    fields=[
        Field("batch_no", "Batch number", required=True),
        Field("product", "Product / flavour", "select",
              options=["Original", "Belgian Chocolate", "Hazelnut", "Caramel", "Duo pack", "Other"], required=True),
        Field("supplier_id", "Supplier", "ref", ref="suppliers"),
        Field("manufacture_date", "Manufacture date", "date"),
        Field("best_before", "Best before", "date"),
        Field("received_date", "Received on", "date"),
        Field("qty_received", "Qty received (units)", "int", default=0),
        Field("qty_remaining", "Qty remaining (units)", "int", default=0),
        Field("coa_reference", "COA reference"),
        Field("coa_file", "COA file", "file"),
        Field("chk_paperwork", "1 · Paperwork: COA present, batch legible, dates consistent", "bool", default=0),
        Field("chk_sensory", "2 · Opened one unit: aroma, colour, free-flowing, brewed hot & cold", "bool", default=0),
        Field("chk_label", "3 · Label vs artwork: both FSSAI nos, net qty, MRP, batch, dates", "bool", default=0),
        Field("chk_fill_seal", "4 · Fill weight & induction seal checked", "bool", default=0),
        Field("chk_retention", "5 · Two retention samples stored", "bool", default=0),
        Field("chk_logged", "6 · Logged (this record complete)", "bool", default=0),
        Field("qc_result", "QC result", "select", options=["pending", "pass", "fail", "quarantine"], default="pending"),
        Field("destination", "Stock went to", "select", options=["own stock", "FBA", "split", "returned to supplier", "destroyed"], default="own stock"),
        Field("fba_shipment_id", "FBA shipment ID"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="retention_samples", singular="Retention sample", plural="Retention samples", icon="🧪",
    description="Sealed samples kept per batch, stored past best-before, to settle complaints.",
    title_field="label",
    list_columns=["label", "batch_id", "storage_location", "stored_on", "discard_after", "status"],
    fields=[
        Field("label", "Label", required=True),
        Field("batch_id", "Batch", "ref", ref="batches", required=True),
        Field("storage_location", "Storage location"),
        Field("stored_on", "Stored on", "date"),
        Field("discard_after", "Discard after", "date", help="Best-before + 6 months"),
        Field("status", "Status", "select", options=["stored", "opened for investigation", "discarded"], default="stored"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="complaints", singular="Complaint / review", plural="Complaints & reviews", icon="💬",
    description="Every complaint and notable review, logged against a batch number.",
    title_field="summary",
    list_columns=["date", "channel", "product", "batch_no", "issue", "severity", "resolved"],
    search_fields=["summary", "batch_no", "customer", "action"],
    order_by="resolved, date DESC",
    fields=[
        Field("date", "Date", "date", required=True),
        Field("channel", "Channel", "select", options=["Amazon", "website", "Instagram", "phone", "WhatsApp", "email", "Flipkart", "other"], default="Amazon"),
        Field("customer", "Customer (name / order id)"),
        Field("product", "Product", "select", options=["Original", "Belgian Chocolate", "Hazelnut", "Caramel", "Duo pack", "Unknown"], default="Unknown"),
        Field("batch_no", "Batch number", help="From the jar. 'unknown' if the customer cannot read it."),
        Field("issue", "Issue category", "select",
              options=["clumping", "stale", "taste", "damaged", "packaging", "delivery", "wrong item", "praise", "other"], default="other"),
        Field("severity", "Severity", "select", options=["low", "medium", "high", "safety"], default="medium"),
        Field("summary", "Summary", required=True),
        Field("rating", "Star rating (if review)", "int"),
        Field("action", "Action taken", "textarea"),
        Field("resolved", "Resolved", "bool", default=0),
        Field("resolved_on", "Resolved on", "date"),
    ],
))

register(Resource(
    key="lab_tests", singular="Lab test", plural="Tests & lab reports", icon="🔬",
    description="Nutrition, microbial, moisture and contaminant tests with their validity.",
    title_field="test_type",
    list_columns=["test_type", "lab", "sample", "batch_id", "date", "result", "valid_until"],
    fields=[
        Field("test_type", "Test type", "select",
              options=["nutrition panel", "microbial", "moisture", "contaminants / heavy metals", "caffeine", "shelf-life", "other"], required=True),
        Field("lab", "Laboratory (NABL)"),
        Field("sample", "Sample description"),
        Field("batch_id", "Batch", "ref", ref="batches"),
        Field("supplier_id", "Supplier", "ref", ref="suppliers"),
        Field("date", "Report date", "date"),
        Field("result", "Result", "select", options=["pending", "pass", "fail"], default="pending"),
        Field("valid_until", "Valid until", "date", help="Nutrition panels: retest on recipe change or every 12 months."),
        Field("report_file", "Report file", "file"),
        Field("cost", "Cost (₹)", "int"),
        Field("notes", "Notes / values", "textarea"),
    ],
))

register(Resource(
    key="contacts", singular="Contact", plural="Contacts", icon="☎️",
    description="Who to call: CA, CS, bank, FoSCoS, Amazon, gateways, registrar, printers, couriers.",
    title_field="name",
    list_columns=["name", "role", "organisation", "phone", "email", "account_ref"],
    search_fields=["name", "role", "organisation", "notes"],
    order_by="role, name",
    fields=[
        Field("name", "Name", required=True),
        Field("role", "Role", "select",
              options=["chartered accountant", "company secretary", "bank", "FSSAI / FoSCoS", "Amazon", "Flipkart", "payment gateway",
                       "domain / hosting", "printer / labels", "courier / logistics", "lab", "supplier", "trademark agent", "government", "other"],
              default="other"),
        Field("organisation", "Organisation"),
        Field("phone", "Phone"),
        Field("email", "Email"),
        Field("url", "Portal URL"),
        Field("account_ref", "Account / customer ID", help="IDs only. Never passwords - those live in the password manager."),
        Field("owner", "Who holds the login", default="Sudhansu"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="tasks", singular="Task", plural="Tasks", icon="✅",
    description="What needs doing, by when, and what it is linked to.",
    title_field="title",
    list_columns=["title", "status", "priority", "due_date", "area", "owner"],
    search_fields=["title", "details"],
    order_by="CASE status WHEN 'doing' THEN 0 WHEN 'todo' THEN 1 ELSE 2 END, CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, due_date",
    fields=[
        Field("title", "Task", required=True),
        Field("status", "Status", "select", options=["todo", "doing", "done", "dropped"], default="todo"),
        Field("priority", "Priority", "select", options=["urgent", "high", "normal", "low"], default="normal"),
        Field("due_date", "Due", "date"),
        Field("area", "Area", "select",
              options=["compliance", "supply", "amazon", "website", "marketing", "finance", "security", "admin", "content", "other"], default="other"),
        Field("owner", "Owner", default="Sudhansu"),
        Field("link", "Linked record", help="e.g. documents/3 or suppliers/1 or a URL"),
        Field("details", "Details", "textarea"),
        Field("done_on", "Done on", "date"),
    ],
))

register(Resource(
    key="decisions", singular="Decision", plural="Decisions log", icon="🧭",
    description="Decisions made, when, and why - so they are not re-litigated.",
    title_field="decision",
    list_columns=["date", "decision", "area", "decided_by"],
    search_fields=["decision", "rationale"],
    order_by="date DESC",
    fields=[
        Field("date", "Date", "date", required=True),
        Field("decision", "Decision", required=True),
        Field("area", "Area", "select",
              options=["strategy", "supply", "compliance", "amazon", "website", "marketing", "finance", "security", "other"], default="strategy"),
        Field("decided_by", "Decided by", default="Sudhansu"),
        Field("rationale", "Rationale", "textarea"),
        Field("revisit_on", "Revisit on", "date"),
        Field("source", "Source", help="e.g. restart-plan.html §Model"),
    ],
))

register(Resource(
    key="facts", singular="Fact", plural="Finance data", icon="📈",
    description="Numbers pulled out of filed documents (financial statements, GST returns, ITR, bank statements). Each row is one metric for one period, traceable to its source file. Edit anything the extractor got wrong.",
    title_field="metric",
    list_columns=["fy", "period", "metric", "value", "unit", "confidence", "method", "source_id"],
    search_fields=["metric", "fy", "period", "notes"],
    order_by="fy DESC, period DESC, metric",
    fields=[
        Field("fy", "Financial year", required=True, help="e.g. 2024-25"),
        Field("period", "Period", help="'FY' for the whole year, or 2026-09 for a month, or Q2"),
        Field("metric", "Metric", required=True,
              help="revenue, total_income, total_expenses, pbt, pat, total_assets, total_liabilities, equity, cash, gst_taxable_value, gst_tax_payable, gst_itc, gst_tax_paid_cash, itr_total_income, itr_tax_payable, bank_opening, bank_closing, bank_credits, bank_debits, amazon_sales, amazon_orders"),
        Field("value", "Value", "real", required=True),
        Field("unit", "Unit", default="INR"),
        Field("source_id", "Source document", "ref", ref="documents"),
        Field("confidence", "Confidence (0-1)", "real", default=1.0),
        Field("method", "Method", "select", options=["auto", "llm", "manual"], default="manual"),
        Field("notes", "Notes", "textarea"),
    ],
))

register(Resource(
    key="mail", singular="Mail", plural="Mail", icon="✉️",
    description="Emails the assistant has read from the company mailbox: who, what, what it means for Buzzcaf, and what was done about it.",
    title_field="subject",
    list_columns=["received", "sender", "subject", "category", "importance", "status"],
    search_fields=["subject", "sender", "summary", "body_excerpt"],
    order_by="received DESC",
    fields=[
        Field("message_id", "Message-ID", help="RFC 822 Message-ID; used to avoid re-reading"),
        Field("uid", "IMAP UID"),
        Field("received", "Received", "date"),
        Field("sender", "From"),
        Field("subject", "Subject", required=True),
        Field("category", "Category", "select",
              options=["ca-accounts", "gst", "mca-roc", "income-tax", "fssai", "bank", "amazon", "supplier", "customer",
                       "payment-gateway", "domain-hosting", "legal-notice", "government", "marketing", "newsletter", "other"],
              default="other"),
        Field("importance", "Importance", "select", options=["urgent", "high", "normal", "low", "ignore"], default="normal"),
        Field("summary", "What it says", "textarea"),
        Field("action_needed", "Action needed", "textarea"),
        Field("due_date", "Deadline mentioned", "date"),
        Field("amount", "Amount mentioned (₹)", "real"),
        Field("attachments", "Attachments", help="filenames saved to inbox/"),
        Field("documents", "Filed as documents", help="documents/<id> list after auto-sorting"),
        Field("task_id", "Task created", "ref", ref="tasks"),
        Field("status", "Status", "select", options=["new", "read", "actioned", "ignored"], default="new"),
        Field("method", "Understood by", "select", options=["rules", "llm"], default="rules"),
        Field("body_excerpt", "Body (first 4000 chars)", "textarea"),
    ],
))

NAV_ORDER = ["documents", "facts", "mail", "compliance", "suppliers", "batches", "retention_samples", "complaints",
             "lab_tests", "contacts", "tasks", "decisions"]
