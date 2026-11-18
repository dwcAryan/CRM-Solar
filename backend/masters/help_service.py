"""
Solar CRM In-App Help & Knowledge Assistant Service.

Provides authoritative answers, categories, deep-link actions, and suggested
follow-ups for software-related queries regarding the Solar CRM system.
"""

from __future__ import annotations

import re
from typing import Any

# Master Help Knowledge Base
HELP_KNOWLEDGE_BASE: list[dict[str, Any]] = [
    {
        "id": "golden_rule",
        "category": "Core Rules",
        "title": "What is the Golden Rule of Solar CRM?",
        "keywords": [
            "golden rule", "rule", "followup rule", "mandatory followup", "next action",
            "status", "next followup", "core rule", "policy", "process"
        ],
        "answer": (
            "### The Golden Business Rule\n"
            "**Every call, visit, or interaction must end with an outcome.**\n\n"
            "Logging an outcome enforces three synchronized attributes on the lead:\n"
            "1. **Lead Status** (e.g., *Interested*, *Survey scheduled*, *Negotiation*)\n"
            "2. **Next Action** (e.g., *Book survey date*, *Share revised quote*)\n"
            "3. **Next Follow-up Date & Time** (mandatory for all non-terminal leads)\n\n"
            "A lead with no next follow-up date is **never allowed** (except terminal statuses: "
            "`Won`, `Lost`, `Do not contact`, `Merged`, or `Invalid contact`)."
        ),
        "action": {"label": "View Today's Queue", "path": "/today"},
        "related": ["retry_ladder", "who_can_mark_lost", "status_lifecycle"],
    },
    {
        "id": "retry_ladder",
        "category": "Call Outcomes",
        "title": "How does the 'No answer' retry ladder work?",
        "keywords": [
            "no answer", "retry", "attempt", "attempts", "unreachable", "max call attempts",
            "call retry", "attempt count", "retry rule", "ladder"
        ],
        "answer": (
            "### 'No Answer' Dynamic Retry Ladder\n"
            "When you log the **No answer** call outcome, the system automatically adjusts the follow-up:\n\n"
            "- **Attempt 1**: Follow-up scheduled for the **same day, 4 hours later**.\n"
            "- **Attempt 2**: Follow-up scheduled for the **next day (+1 day)**.\n"
            "- **Attempts 3 & 4**: Follow-up scheduled for **subsequent days (+1 to +2 days)**.\n"
            "- **Attempt 5 (Max Attempts)**: Automatically transitions lead to **Unreachable** with a follow-up in **14 days**.\n"
            "- **Another 'No answer' on Unreachable lead**: Automatically closed as **Lost** with reason *'no response'*.\n\n"
            "💡 *Any answered call or response from the customer resets the attempt counter to 0.*"
        ),
        "action": {"label": "Go to Today's Leads", "path": "/today"},
        "related": ["reengagement", "who_can_mark_lost", "golden_rule"],
    },
    {
        "id": "who_can_mark_lost",
        "category": "Permissions",
        "title": "Who can mark a lead as Lost?",
        "keywords": [
            "mark lost", "who can mark lost", "lost permission", "manager lost", "role lost",
            "close lead", "reject lead", "loss authority"
        ],
        "answer": (
            "### Loss Authority & Roles\n"
            "To protect the pipeline, the system enforces the `WHO_CAN_MARK_LOST` policy:\n\n"
            "- **Managers** and **Admins** have full authority to mark leads as **Lost**.\n"
            "- **Salespeople** cannot mark a lead as Lost directly unless approved or overridden by a manager.\n"
            "- Marking a lead as Lost always requires selecting a mandatory **Lost Reason** (e.g., *'price too high'*, *'chose a competitor'*, *'no suitable roof'*).\n"
            "- A confirmation dialog intercepts the action to prevent accidental closing."
        ),
        "action": {"label": "View All Leads", "path": "/leads"},
        "related": ["reengagement", "lost_reasons", "do_not_contact"],
    },
    {
        "id": "csv_import",
        "category": "Lead Import",
        "title": "How do I import leads from CSV or Excel?",
        "keywords": [
            "import", "csv", "excel", "xlsx", "upload leads", "bulk import", "duplicate import",
            "round robin", "undo import", "batch undo", "sample template"
        ],
        "answer": (
            "### CSV & Excel Lead Import Wizard\n"
            "Navigate to **Import Leads** (`/import-leads`) for the 4-step wizard:\n\n"
            "1. **Upload File**: Drag-and-drop `.csv` (with UTF-8 BOM support) or `.xlsx` up to **5 MB / 5,000 rows**. You can download the sample template here.\n"
            "2. **Column Mapping**: Headers auto-match case-insensitively (Name, Phone, Email, City, Address, Source, Monthly Bill, Roof Type). Inspect the 5-10 row preview.\n"
            "3. **Duplicate & Assignment Settings**:\n"
            "   - *Duplicates*: Choose **Skip**, **Update empty fields only**, or **Create anyway**.\n"
            "   - *Assignment*: Assign to a single salesperson, **Round-Robin** across sales team, or leave unassigned.\n"
            "   - *Golden Rule*: All imported leads automatically start as **New** with follow-up set to **Today**.\n"
            "4. **Results & 1-Click Undo**: Review import stats, download failed rows, or click **Undo Batch** in the history table to instantly delete all leads created by that batch."
        ),
        "action": {"label": "Open Import Leads", "path": "/import-leads"},
        "related": ["bulk_actions", "lead_dedup", "golden_rule"],
    },
    {
        "id": "site_surveys",
        "category": "Surveys",
        "title": "How do site surveys and roof suitability work?",
        "keywords": [
            "survey", "site survey", "book survey", "reschedule survey", "surveyor", "roof suitable",
            "design pending", "alternative", "survey missed", "site inspection"
        ],
        "answer": (
            "### Site Technical Surveys\n"
            "Technical inspections ensure roof viability before engineering:\n\n"
            "- **Booking**: Go to the lead page or Surveys tab and click **Book Survey**. Select the assigned surveyor, appointment date & time.\n"
            "- **Rescheduling**: If the customer or surveyor is delayed, click **Reschedule** (increments the reschedule counter).\n"
            "- **Survey Missed**: If the customer was unavailable on the day, mark **Missed** to trigger a 1-day follow-up.\n"
            "- **Mark Done (Verdict)**:\n"
            "  - **Suitable (Yes)**: Transitions lead to **Design pending** for CAD/electrical SLD generation.\n"
            "  - **Not Suitable (No)**: Prompts for unsuitability reason (shade, weak roof, insufficient area) and moves lead to **Alternative** or **Lost**."
        ),
        "action": {"label": "View Surveys Hub", "path": "/surveys"},
        "related": ["quotations", "golden_rule", "who_can_mark_lost"],
    },
    {
        "id": "quotations",
        "category": "Quotations",
        "title": "How do quotation versions and revisions work?",
        "keywords": [
            "quote", "quotation", "proposal", "revise quote", "quote version", "price", "subsidy",
            "net payable", "won", "accept quote", "reject quote", "kw"
        ],
        "answer": (
            "### Versioned Quotations & The 'Won' Milestone\n"
            "Solar proposals maintain an immutable historical audit trail:\n\n"
            "- **Creating Quotes**: Specify system capacity (kW), panel/inverter brand, gross price, and subsidy/discount (₹). The CRM dynamically calculates the **Customer Net Payable**.\n"
            "- **Mark Sent**: Moves lead status to **Quote sent**.\n"
            "- **Revising Quotes**: Quotes are **never overwritten**. Clicking **Revise** creates `v2`, `v3` while preserving earlier versions.\n"
            "- **Accepting Proposal (`Won`)**: Customer agreement marks the deal as **Won** and completes the CRM sales cycle.\n"
            "- **Rejecting Proposal (`Lost`)**: Prompts for mandatory lost reason (e.g., *'price too high'*, *'competitor'*) and marks the lead as Lost."
        ),
        "action": {"label": "View Quotations Hub", "path": "/quotes"},
        "related": ["who_can_mark_lost", "site_surveys", "status_lifecycle"],
    },
    {
        "id": "do_not_contact",
        "category": "Privacy & Safety",
        "title": "What happens when a lead is marked 'Do not contact'?",
        "keywords": [
            "do not contact", "dnc", "block calls", "stop calling", "block whatsapp", "privacy",
            "terminal status", "opt out"
        ],
        "answer": (
            "### 'Do Not Contact' Privacy Guardrail\n"
            "When a lead is marked **Do not contact** (terminal status):\n\n"
            "- The customer is immediately flagged with `do_not_contact = true`.\n"
            "- **Call** and **WhatsApp** buttons are strictly **disabled** in the UI with a prominent red badge.\n"
            "- Outbound automated WhatsApp messages and scheduler reminders are completely suppressed.\n"
            "- Any further activity logging on that lead is permanently blocked."
        ),
        "action": {"label": "Go to All Leads", "path": "/leads"},
        "related": ["reengagement", "status_lifecycle", "who_can_mark_lost"],
    },
    {
        "id": "lead_dedup",
        "category": "Lead Management",
        "title": "How do I merge duplicate leads?",
        "keywords": [
            "merge", "duplicate", "duplicate lead", "merge leads", "combine leads", "deduplication",
            "same phone", "duplicate enquiry"
        ],
        "answer": (
            "### Merging Duplicate Enquiries\n"
            "If a customer enquiries multiple times (e.g., via Meta ads and Website form):\n\n"
            "1. Open the duplicate lead detail page (`/leads/:id`).\n"
            "2. Click the **Merge Duplicate** button in the top action bar.\n"
            "3. Select the primary lead record you wish to retain.\n"
            "4. Provide an optional merge note and remark.\n"
            "5. Click **Confirm Merge**. The CRM transfers all activities, surveys, and quotations to the primary lead and marks the duplicate as **Merged** (terminal)."
        ),
        "action": {"label": "View All Leads", "path": "/leads"},
        "related": ["csv_import", "bulk_actions", "golden_rule"],
    },
    {
        "id": "bulk_actions",
        "category": "Lead Management",
        "title": "How do I perform bulk actions or export leads to CSV?",
        "keywords": [
            "bulk", "bulk action", "bulk assign", "change source", "export csv", "export leads",
            "select all", "download leads", "formula injection"
        ],
        "answer": (
            "### Bulk Operations & Filtered CSV Export\n"
            "On the **All Leads** page (`/leads`):\n\n"
            "- **Selecting Leads**: Use the checkboxes on table rows or the master header checkbox to select multiple leads.\n"
            "- **Floating Toolbar**: Appears at the bottom with options:\n"
            "  - **Bulk Assign**: Reassign selected leads to another salesperson.\n"
            "  - **Bulk Change Source**: Standardize origin source across leads.\n"
            "  - **Export Selected to CSV**: Download selected leads.\n"
            "- **Export Filtered View**: Click **Export CSV** at the top right to download all leads matching your current active filters.\n"
            "- **Formula Safety**: All CSV exports sanitize cells starting with `=`, `+`, `-`, or `@` to prevent spreadsheet formula injection attacks."
        ),
        "action": {"label": "Go to Leads List", "path": "/leads"},
        "related": ["csv_import", "lead_dedup", "keyboard_shortcuts"],
    },
    {
        "id": "reengagement",
        "category": "Workflow Rules",
        "title": "How are dormant (Lost, Nurture, Unreachable) leads re-engaged?",
        "keywords": [
            "reengage", "re-engagement", "nurture recall", "lost comeback", "dormant",
            "unreachable call back", "customer calls back"
        ],
        "answer": (
            "### Dormant Lead Re-engagement\n"
            "If a customer previously marked **Lost**, **Nurture**, or **Unreachable** contacts your company again:\n\n"
            "- Logging an incoming interaction immediately resets the lead status to **Follow-up**.\n"
            "- Sets the next follow-up date to **Today**.\n"
            "- Resets the call attempt count to 0.\n"
            "- Re-opens the sales cycle without needing to create a duplicate lead record."
        ),
        "action": {"label": "View Today's Leads", "path": "/today"},
        "related": ["retry_ladder", "who_can_mark_lost", "golden_rule"],
    },
    {
        "id": "keyboard_shortcuts",
        "category": "Ease-of-Use",
        "title": "What keyboard shortcuts and quick navigation features are available?",
        "keywords": [
            "keyboard", "shortcut", "search shortcut", "slash", "dark mode", "quick actions",
            "today queue", "navigation", "tips"
        ],
        "answer": (
            "### Keyboard Shortcuts & UI Pro-Tips\n"
            "- **Press `/`**: Instantly focuses the Global Search bar at the top of any page (safely ignores when you are typing inside an input/textarea).\n"
            "- **Dark Mode**: Click the Sun/Moon icon in the header to switch color schemes.\n"
            "- **Quick Outreach**: On `/today` or `/leads`, use the direct **Call** (`tel:`) and **WhatsApp** (`wa.me`) buttons.\n"
            "- **Add Remark**: Click **Remark** anywhere to add internal notes without altering the lead status or follow-up schedule.\n"
            "- **Missing Follow-up Warnings**: Watch for red `⚠️ NO FOLLOW-UP DATE` badges to catch neglected active leads."
        ),
        "action": {"label": "Open Leads", "path": "/leads"},
        "related": ["golden_rule", "bulk_actions", "today_queue"],
    },
    {
        "id": "status_lifecycle",
        "category": "Core Rules",
        "title": "What are all the lead statuses and stages?",
        "keywords": [
            "status", "statuses", "lifecycle", "stages", "pipeline", "interested", "won", "lost",
            "nurture", "design pending", "alternative", "callback scheduled"
        ],
        "answer": (
            "### All 21 Lead Lifecycle Statuses\n"
            "1. **Inbound / Outreach**: `New`, `Attempting contact`, `Callback scheduled`, `Follow-up`, `Interested`, `Unreachable`\n"
            "2. **Site Survey**: `Survey to schedule`, `Survey scheduled`, `Survey rescheduled`, `Survey missed`\n"
            "3. **Engineering & Quote**: `Design pending`, `Alternative`, `Quote sent`, `Revising quote`, `Negotiation`\n"
            "4. **Long-term**: `Nurture` (default 90 days)\n"
            "5. **Terminal Outcomes**: `Won` (🎉 Customer committed), `Lost` (❌ Closed), `Do not contact` (🚫 Opt-out), `Merged` (🔀 Duplicate), `Invalid contact` (⚠️ Bad phone)"
        ),
        "action": {"label": "View Leads Pipeline", "path": "/leads"},
        "related": ["golden_rule", "who_can_mark_lost", "quotations"],
    },
]


def query_help_assistant(query: str) -> dict[str, Any]:
    """
    Evaluates a user's natural language query against the knowledge base
    and returns the best matching topic or a courteous fallback.
    """
    clean_query = re.sub(r"[^\w\s]", " ", query.lower()).strip()
    words = [w for w in clean_query.split() if len(w) > 2]

    if not words:
        return {
            "matched": False,
            "title": "How can I help you with Solar CRM?",
            "answer": (
                "I am your Solar CRM assistant! You can ask me anything about software workflows, "
                "such as how to log call outcomes, retry ladders for 'No answer', CSV import rules, "
                "who can mark leads as Lost, or quotation versions."
            ),
            "category": "Assistant Help",
            "action": {"label": "Start Guided Tour", "path": "TOUR"},
            "related": ["golden_rule", "retry_ladder", "csv_import", "who_can_mark_lost"],
        }

    best_item: dict[str, Any] | None = None
    best_score = 0

    for item in HELP_KNOWLEDGE_BASE:
        score = 0

        # Exact title or keyword matches
        for kw in item["keywords"]:
            if kw in clean_query:
                score += 15
            else:
                kw_words = kw.split()
                if any(w in words for w in kw_words):
                    score += 5

        # Check title words
        title_lower = item["title"].lower()
        for w in words:
            if w in title_lower:
                score += 8
            if w in item["answer"].lower():
                score += 2

        if score > best_score:
            best_score = score
            best_item = item

    # If score meets threshold, return matched article
    if best_item and best_score >= 8:
        # Resolve related query titles
        related_titles = []
        for rel_id in best_item.get("related", []):
            rel_obj = next((k for k in HELP_KNOWLEDGE_BASE if k["id"] == rel_id), None)
            if rel_obj:
                related_titles.append(rel_obj["title"])

        return {
            "matched": True,
            "id": best_item["id"],
            "title": best_item["title"],
            "category": best_item["category"],
            "answer": best_item["answer"],
            "action": best_item.get("action"),
            "related": related_titles,
        }

    # Fallback response when no high-confidence match found
    suggested_faqs = [item["title"] for item in HELP_KNOWLEDGE_BASE[:4]]
    return {
        "matched": False,
        "title": "I couldn't find an exact match",
        "answer": (
            f"I didn't find an exact match for *\"{query}\"*. "
            "Here are some common software topics that might help, or you can take the interactive tour:"
        ),
        "category": "General Help",
        "action": {"label": "Take a Tour of the System", "path": "TOUR"},
        "related": suggested_faqs,
    }


def get_faq_list() -> list[dict[str, Any]]:
    """Returns the master list of FAQs for quick exploration."""
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "category": item["category"],
            "action": item.get("action"),
        }
        for item in HELP_KNOWLEDGE_BASE
    ]
