"""
System history dynamic renderer.
Renders status history, activities, notifications, and audit entries from
stable message_code and parameters into the viewer's current language at read time.
"""
from typing import Any, Dict, Optional

HISTORY_TEMPLATES: Dict[str, Dict[str, str]] = {
    'STATUS_INITIAL': {
        'en': 'Initial transition to {status}',
        'hi': 'प्रारंभिक स्थिति: {status}',
        'en-AU': 'Initial transition to {status}',
        'en-IN': 'Initial transition to {status}',
    },
    'STATUS_CHANGED': {
        'en': 'Status updated from {old_status} to {new_status}',
        'hi': 'स्थिति {old_status} से बदलकर {new_status} की गई',
        'en-AU': 'Status updated from {old_status} to {new_status}',
        'en-IN': 'Status updated from {old_status} to {new_status}',
    },
    'CALL_LOGGED': {
        'en': 'Call logged: {outcome}',
        'hi': 'कॉल विवरण दर्ज: {outcome}',
        'en-AU': 'Call logged: {outcome}',
        'en-IN': 'Call logged: {outcome}',
    },
    'VISIT_LOGGED': {
        'en': 'Site visit recorded: {outcome}',
        'hi': 'साइट विजिट दर्ज: {outcome}',
        'en-AU': 'Site inspection recorded: {outcome}',
        'en-IN': 'Site visit recorded: {outcome}',
    },
    'WHATSAPP_LOGGED': {
        'en': 'WhatsApp message logged: {outcome}',
        'hi': 'व्हाट्सएप संदेश दर्ज: {outcome}',
        'en-AU': 'WhatsApp message logged: {outcome}',
        'en-IN': 'WhatsApp message logged: {outcome}',
    },
    'NOTE_ADDED': {
        'en': 'Note added: {text}',
        'hi': 'टिप्पणी जोड़ी गई: {text}',
        'en-AU': 'Note added: {text}',
        'en-IN': 'Note added: {text}',
    },
    'SURVEY_SCHEDULED': {
        'en': 'Site survey booked for {time}',
        'hi': 'साइट सर्वे {time} के लिए निर्धारित किया गया',
        'en-AU': 'Site survey booked for {time}',
        'en-IN': 'Site survey booked for {time}',
    },
    'SURVEY_COMPLETED': {
        'en': 'Site survey completed successfully',
        'hi': 'साइट सर्वे सफलतापूर्वक पूरा हुआ',
        'en-AU': 'Site survey completed successfully',
        'en-IN': 'Site survey completed successfully',
    },
    'SURVEY_RESCHEDULED': {
        'en': 'Site survey rescheduled to {time}',
        'hi': 'साइट सर्वे का समय बदलकर {time} किया गया',
        'en-AU': 'Site survey rescheduled to {time}',
        'en-IN': 'Site survey rescheduled to {time}',
    },
    'QUOTE_CREATED': {
        'en': 'Quote v{version} created for {kw} kW system',
        'hi': '{kw} किलोवाट प्रणाली के लिए कोटेशन v{version} तैयार किया गया',
        'en-AU': 'Proposal v{version} created for {kw} kW system',
        'en-IN': 'Quote v{version} created for {kw} kW system',
    },
    'QUOTE_SENT': {
        'en': 'Quote v{version} dispatched to customer',
        'hi': 'कोटेशन v{version} ग्राहक को भेजा गया',
        'en-AU': 'Proposal v{version} sent to customer',
        'en-IN': 'Quote v{version} dispatched to customer',
    },
    'QUOTE_WON': {
        'en': 'Customer accepted proposal. Deal marked as Won!',
        'hi': 'ग्राहक ने प्रस्ताव स्वीकार किया। सौदा सफल (जीता) चिह्नित किया गया!',
        'en-AU': 'Customer accepted proposal. Deal Won!',
        'en-IN': 'Customer accepted proposal. Deal Won!',
    },
    'LEAD_ASSIGNED': {
        'en': 'Lead assigned to {user}',
        'hi': 'लीड {user} को सौंपी गई',
        'en-AU': 'Lead assigned to {user}',
        'en-IN': 'Lead assigned to {user}',
    },
    'LEAD_REASSIGNED': {
        'en': 'Lead reassigned from {old_user} to {new_user}',
        'hi': 'लीड {old_user} से हटाकर {new_user} को पुनः सौंपी गई',
        'en-AU': 'Lead reassigned from {old_user} to {new_user}',
        'en-IN': 'Lead reassigned from {old_user} to {new_user}',
    },
    'LEAD_CREATED': {
        'en': 'Lead created via {source}',
        'hi': 'लीड {source} के माध्यम से बनाई गई',
        'en-AU': 'Lead created via {source}',
        'en-IN': 'Lead created via {source}',
    },
    'DNC_MARKED': {
        'en': 'Lead marked as Do Not Contact',
        'hi': 'लीड को संपर्क न करने योग्य (DNC) चिह्नित किया गया',
        'en-AU': 'Lead added to Do Not Call register',
        'en-IN': 'Lead marked as Do Not Contact',
    },
}


def render_history_text(
    message_code: Optional[str],
    params: Optional[Dict[str, Any]],
    language: str = 'en',
    fallback_text: str = '',
) -> str:
    """
    Renders a localized message from code and params.
    If message_code is absent or unmapped, returns fallback_text (legacy compatibility).
    """
    if not message_code or message_code not in HISTORY_TEMPLATES:
        return fallback_text or ''

    templates_by_lang = HISTORY_TEMPLATES[message_code]
    target_lang = language or 'en'
    template_str = (
        templates_by_lang.get(target_lang)
        or templates_by_lang.get('en')
        or fallback_text
    )

    clean_params = params or {}
    try:
        return template_str.format(**clean_params)
    except Exception:
        # Fallback gracefully if parameter keys are mismatched
        return template_str
