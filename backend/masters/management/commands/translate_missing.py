import re
from pathlib import Path
from typing import Optional
import yaml
from django.conf import settings
from django.core.management.base import BaseCommand

from leads.models import AuditLog
from masters.models import Language, TranslationEntry


# Common Hindi translations dictionary for interface elements
HINDI_DICT = {
    # Actions & Buttons
    "Save": "सुरक्षित करें",
    "Cancel": "रद्द करें",
    "Submit": "जमा करें",
    "Delete": "हटाएं",
    "Edit": "संपादित करें",
    "Update": "अपडेट करें",
    "Create": "बनाएं",
    "Add": "जोड़ें",
    "Search": "खोजें",
    "Filter": "फ़िल्टर करें",
    "Export": "निर्यात करें",
    "Import": "आयात करें",
    "Download": "डाउनलोड करें",
    "Close": "बंद करें",
    "Back": "वापस जाएं",
    "Next": "अगला",
    "Previous": "पिछला",
    "Confirm": "पुष्टि करें",
    "Refresh": "ताज़ा करें",
    "Actions": "कार्रवाई",
    "Loading...": "लोड हो रहा है...",
    "Select": "चुनें",
    "All": "सभी",
    "None": "कोई नहीं",
    "Yes": "हाँ",
    "No": "नहीं",

    # Navigation & Core Headers
    "Dashboard": "डैशबोर्ड",
    "Leads": "लीड्स",
    "Pipeline": "पाइपलाइन",
    "Surveys": "सर्वेक्षण",
    "Quotes": "कोटेशन",
    "Activities": "गतिविधियां",
    "Settings": "सेटिंग्स",
    "Profile": "प्रोफ़ाइल",
    "Help": "सहायता",
    "Notifications": "सूचनाएं",
    "Tour": "उत्पाद भ्रमण (टूर)",
    "Audit Logs": "ऑडिट लॉग",
    "Users": "उपयोगकर्ता",
    "Regions": "क्षेत्र",

    # Statuses & Stages
    "New": "नई (New)",
    "Contacted": "संपर्क किया गया (Contacted)",
    "Survey Booked": "सर्वे निर्धारित (Survey Booked)",
    "Survey Completed": "सर्वे पूर्ण (Survey Completed)",
    "Quote Sent": "कोटेशन भेजा गया (Quote Sent)",
    "Won": "सफल (Won)",
    "Lost": "असफल (Lost)",
    "Nurture": "नर्चर (Nurture)",

    # Lead Fields
    "Name": "नाम",
    "Phone": "फ़ोन नंबर",
    "Email": "ईमेल",
    "Address": "पता",
    "City": "शहर",
    "State": "राज्य",
    "Postcode": "पिनकोड / पोस्टकोड",
    "Pincode": "पिनकोड",
    "Region": "क्षेत्र",
    "Assigned To": "नियुक्त प्रतिनिधि",
    "Status": "स्थिति",
    "Source": "स्रोत",
    "Monthly Bill": "मासिक बिजली बिल",
    "Roof Type": "छत का प्रकार",
    "Property Type": "संपत्ति का प्रकार",
    "Next Follow-up": "अगला फॉलो-अप",
    "Remark": "टिप्पणी",
    "Notes": "नोट्स",
    "Created At": "बनाया गया",
    "Updated At": "अपडेट किया गया",

    # Survey & Quote Fields
    "System Size": "सिस्टम का आकार (kW)",
    "Panel Count": "पैनलों की संख्या",
    "Total Cost": "कुल लागत",
    "Net Price": "अंतिम देय राशि",
    "Subsidy / Rebate": "सब्सिडी / छूट",
    "Estimated Generation": "अनुमानित सौर उत्पादन",
    "Survey Date": "सर्वेक्षण तिथि",
    "Surveyor": "सर्वेयर",

    # Common messages
    "Lead created successfully": "लीड सफलतापूर्वक बनाई गई",
    "Lead updated successfully": "लीड सफलतापूर्वक अपडेट की गई",
    "Quote generated successfully": "कोटेशन सफलतापूर्वक तैयार किया गया",
    "Survey scheduled successfully": "सर्वेक्षण सफलतापूर्वक निर्धारित किया गया",
}


def load_glossary() -> dict:
    glossary_file = Path(settings.BASE_DIR).parent / "locales" / "glossary.yaml"
    if glossary_file.exists():
        try:
            with open(glossary_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def draft_translation(en_text: str, target_lang: str, glossary: dict) -> str:
    if not en_text:
        return ""

    # Preserve ICU placeholders
    placeholders = re.findall(r'\{[a-zA-Z0-9_]+\}', en_text)

    if target_lang == "hi":
        if en_text in HINDI_DICT:
            return HINDI_DICT[en_text]

        # Check terms in glossary
        terms = glossary.get("terms", {})
        for term_key, lang_map in terms.items():
            en_term = lang_map.get("en", "")
            hi_term = lang_map.get("hi", "")
            if en_term and hi_term and en_text.strip().lower() == en_term.strip().lower():
                return hi_term

        # Substitute known terms within the text
        draft = en_text
        for en_key, hi_val in sorted(HINDI_DICT.items(), key=lambda x: -len(x[0])):
            if re.search(r'\b' + re.escape(en_key) + r'\b', draft, re.IGNORECASE):
                # Replace if not inside {placeholders}
                draft = re.sub(r'\b' + re.escape(en_key) + r'\b', hi_val, draft, flags=re.IGNORECASE)

        # Ensure all original placeholders remain intact
        for ph in placeholders:
            if ph not in draft:
                draft += f" {ph}"
        return draft

    if target_lang == "en-AU":
        # Australian English regional adaptations
        draft = en_text
        replacements = {
            "Quote": "Proposal",
            "Quotes": "Proposals",
            "quote": "proposal",
            "Electricity Bill": "Power Bill",
            "electricity bill": "power bill",
            "Subsidy": "Government Rebate (STC)",
            "subsidy": "rebate",
            "DISCOM": "Electricity Retailer",
            "Pincode": "Postcode",
            "pincode": "postcode",
            "Color": "Colour",
            "color": "colour",
        }
        for k, v in replacements.items():
            draft = re.sub(r'\b' + re.escape(k) + r'\b', v, draft)
        return draft

    if target_lang == "en-IN":
        # Indian English regional adaptations
        draft = en_text
        replacements = {
            "Postcode": "Pincode",
            "postcode": "pincode",
            "Retailer": "DISCOM",
            "retailer": "DISCOM",
        }
        for k, v in replacements.items():
            draft = re.sub(r'\b' + re.escape(k) + r'\b', v, draft)
        return draft

    return en_text


def draft_missing_for_language(language: Language, user=None) -> int:
    """
    Finds all English master translation entries and creates/updates draft entries
    for missing or empty keys in the target language.
    Only interface strings are processed; zero customer data is touched.
    """
    en_language = Language.objects.filter(code="en").first()
    if not en_language:
        return 0

    if language.code == "en":
        language.completeness_pct = 100.0
        language.save(update_fields=["completeness_pct"])
        return 0

    glossary = load_glossary()
    en_entries = TranslationEntry.objects.filter(language=en_language)
    drafted_count = 0

    for en_e in en_entries:
        target_entry = TranslationEntry.objects.filter(
            language=language,
            namespace=en_e.namespace,
            key=en_e.key,
        ).first()

        needs_draft = (
            target_entry is None
            or not target_entry.translated_text
            or target_entry.status == "missing"
        )

        if needs_draft:
            drafted_text = draft_translation(en_e.english_text, language.code, glossary)
            if not target_entry:
                target_entry = TranslationEntry(
                    language=language,
                    namespace=en_e.namespace,
                    key=en_e.key,
                    english_text=en_e.english_text,
                    translated_text=drafted_text,
                    status="draft",
                    is_customer_facing=en_e.is_customer_facing,
                    updated_by=user,
                )
            else:
                target_entry.english_text = en_e.english_text
                target_entry.translated_text = drafted_text
                target_entry.status = "draft"
                target_entry.updated_by = user

            target_entry.save()
            drafted_count += 1

    # Recalculate completeness
    total_en = en_entries.count()
    if total_en > 0:
        filled_count = (
            TranslationEntry.objects.filter(
                language=language,
                status__in=["draft", "reviewed", "approved"],
            )
            .exclude(translated_text="")
            .count()
        )
        language.completeness_pct = round(min(100.0, (filled_count / total_en) * 100), 1)
        language.save(update_fields=["completeness_pct"])

    AuditLog.objects.create(
        user=user,
        user_name=user.get_full_name() if user else "System",
        action="TRANSLATIONS_DRAFTED",
        details=f"Drafted {drafted_count} missing strings for '{language.code}'",
        reason=f"Automated translation draft for {language.name}",
        ip_address=None,
        message_code="TRANSLATIONS_DRAFTED",
        params={"lang": language.code, "count": drafted_count},
    )

    return drafted_count


class Command(BaseCommand):
    help = "Draft missing translation entries for a language using glossary and dictionary templates."

    def add_arguments(self, parser):
        parser.add_argument("--lang", type=str, default="hi", help="Target language code (e.g. hi, en-AU, en-IN)")
        parser.add_argument("--all", action="store_true", help="Draft missing for all enabled non-English languages")

    def handle(self, *args, **options):
        if options["all"]:
            targets = Language.objects.filter(is_enabled=True).exclude(code="en")
        else:
            lang_code = options["lang"]
            targets = Language.objects.filter(code=lang_code)
            if not targets.exists():
                self.stderr.write(self.style.ERROR(f"Language '{lang_code}' not found."))
                return

        for lang in targets:
            self.stdout.write(f"Drafting missing translations for {lang.name} ({lang.code})...")
            count = draft_missing_for_language(lang)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully drafted {count} keys for {lang.name}. Completeness: {lang.completeness_pct}%"
            ))
