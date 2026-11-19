# Translation & Localization Guide (Phase 14L)

This guide documents the localization architecture for Solar CRM, instructions for translators and administrators, the shared glossary, non-translatable tokens, and the 5-step data-only process for adding new languages without touching application code.

---

## 1. Localization Principles

1. **Two Independent Language Settings**:
   - **Staff Interface Language** (`User.preferred_language`): The UI language seen by internal team members in the dashboard, navigation, forms, and tables.
   - **Customer Communication Language** (`Lead.preferred_language`): The language used for outbound customer messages (WhatsApp, SMS, and email notifications/quotes).
2. **Stable Codes for Business Logic**:
   - Business logic, workflow rules, lead statuses, outcome evaluation, and RBAC permissions strictly rely on invariant system codes (e.g. `STATUS_WON`, `CALL_CONNECTED`), NEVER translated strings.
3. **Dynamic Read-Time Rendering of History**:
   - System audit logs, activity timeline entries, and notifications are stored with a `message_code` and structured JSON `params`. The human-readable text is localized dynamically at render/read time based on the active user's locale.
4. **Machine Translation as Draft**:
   - Any machine-translated string is flagged `needs_review` (`status='needs_review'`). Only strings reviewed and approved by native speakers are flagged `approved`.
   - Customer-facing templates in regulated regions (e.g., DLT in India) cannot be dispatched if unapproved.
5. **Data Privacy**:
   - Translation endpoints and machine translation jobs only process UI keys, static templates, and glossary terms. No customer PII (names, phone numbers, addresses, loan figures) is ever transmitted to translation services.

---

## 2. Adding a New Language (5-Step Pure Data Workflow)

Adding support for any new language (e.g. Gujarati, Marathi, Tamil, Punjabi, Bengali, Arabic, etc.) is **100% data-driven** and requires **zero code deployment or server restart**.

### Step 1: Register the Language in Masters
- In the Admin Panel -> **Languages & Translations** tab -> Click **"Add Language"** (or via Django admin / API `POST /api/masters/languages/`).
- Fields:
  - `Code`: BCP-47 language tag (e.g., `gu`, `mr`, `ta`, `pa`, `bn`, `ar`).
  - `Name`: English name (e.g., "Gujarati").
  - `Native Name`: Endonym (e.g., "ગુજરાતી").
  - `Direction`: `ltr` (or `rtl` for Arabic/Urdu/Hebrew).
  - `Is Active`: Leave unticked initially until initial strings are translated and verified.

### Step 2: Export Translation Templates
- In Admin Panel -> **Export Translations**:
  - Select source language: **English (`en`)**.
  - Choose format: **CSV** or **JSON**.
  - Download the catalog bundle covering all core namespaces: `common`, `auth`, `leads`, `surveys`, `quotes`, `activities`, `tour`, `helpbot`, `admin`, `errors`.

### Step 3: Populate Translations (or Auto-Draft)
- **Option A (Professional Translators)**: Translators edit the CSV/JSON file. Ensure all ICU placeholders (e.g. `{count}`, `{name}`, `{{rate}}`) are preserved exactly as written.
- **Option B (Auto-Draft via CLI / Admin)**:
  Run the automated drafting command:
  ```bash
  python backend/manage.py translate_missing --lang <lang_code>
  ```
  This creates initial draft entries flagged with `status='needs_review'`.

### Step 4: Import and Validate Bundle
- In Admin Panel -> Click **"Import Translations"** and upload the translated file.
- The system automatically validates:
  - File size ($\le 5\text{MB}$) and row limits ($\le 5,000$ entries).
  - HTML escaping and strict whitelisted tag sanitization (no script tags or attribute event handlers).
  - Exact ICU placeholder parity with the English source string.
  - Absence of unescaped format tokens.

### Step 5: Review, Approve, and Activate
- Use the side-by-side **Translation Editor** to review strings.
- Native speaker approves strings by changing status from `needs_review` to `approved`.
- Toggle **"Active"** on the Language Master entry.
- The new language is immediately available in the UI Language Selector and Customer Language dropdowns.

---

## 3. Shared Glossary & Non-Translatable Tokens

### Do Not Translate:
- **Brand Names & Product Identifiers**: `Solar CRM`, `WhatsApp`, `SMS`, `Twilio`, `Brevo`, `Razorpay`, `Stripe`.
- **System Codes & Tokens**: Invariant codes such as `lead_id`, `quote_number`, `user_id`, `status_code`.
- **ICU Formatting Placeholders**: `{count}`, `{name}`, `{date}`, `{amount}`, `{status}`, `{due_date}`.
- **Mathematical / Engineering Units**: `kW`, `kWh`, `V`, `A`, `Wp`, `deg`, `°`.

### Standardized Solar CRM Glossary:

| English Term | Hindi (`hi`) | Notes / Usage Context |
| :--- | :--- | :--- |
| Lead | लीड | Potential customer in the CRM pipeline |
| Opportunity | अवसर / डील | Qualified solar prospect |
| Site Survey | साइट सर्वेक्षण | On-site technical assessment of roof and electrical setup |
| Quotation | कोटेशन / मूल्य प्रस्ताव | Financial pricing estimate sent to prospect |
| Follow-up | फ़ॉलो-अप | Scheduled customer contact activity |
| Inverter | इन्वर्टर | Solar power converter hardware |
| Solar Panel / Module | सोलर पैनल | Photovoltaic solar module |
| Grid-tied | ग्रिड-टाइड | System connected to the utility electricity grid |
| Net Metering | नेट मीटरिंग | Bi-directional grid electricity billing |
| Subsidy | सब्सिडी / सरकारी अनुदान | Government financial support / MNRE subsidy |

---

## 4. SMS Character Counting & Multi-Language Rules

When drafting outbound SMS templates:
- **GSM-7 Standard (Latin/English)**:
  - Single SMS: Up to 160 characters.
  - Multi-part concatenated SMS: 153 characters per segment.
- **UCS-2 Standard (Hindi, Devanagari, Emoji, Accented characters)**:
  - Single SMS: Up to 70 characters.
  - Multi-part concatenated SMS: 67 characters per segment.
- **Important**: The messaging engine automatically detects character encoding and calculates segment counts in real-time. Translators and marketers should be mindful of character limits when composing SMS in non-Latin scripts to optimize telecom costs.
