"""Natural Language Processing, retrieval, classification, and answer generation for Helpbot."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import yaml
from django.conf import settings
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .prompts import (
    DEFAULT_STARTER_QUESTIONS,
    REFUSAL_MESSAGE,
    REFUSAL_MESSAGES,
    STARTER_QUESTIONS_BY_LANG,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

HELPBOT_DIR = Path(__file__).resolve().parent
DATA_DIR = HELPBOT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
TRAINING_FILE = HELPBOT_DIR / 'training' / 'intents.yaml'
KNOWLEDGE_DIR = HELPBOT_DIR / 'knowledge'
MODEL_FILE = DATA_DIR / 'intent_classifier.joblib'
VECTORIZER_FILE = DATA_DIR / 'vectorizer.joblib'
INDEX_FILE = DATA_DIR / 'knowledge_index.json'
DYNAMIC_FACTS_FILE = DATA_DIR / 'dynamic_facts.json'

import unicodedata

NUKTA_MAP = {
    'क़': 'क', 'ख़': 'ख', 'ग़': 'ग', 'ज़': 'ज',
    'ड़': 'ड', 'ढ़': 'ढ', 'फ़': 'फ', 'य़': 'य',
}
DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')


def is_devanagari(text: str) -> bool:
    return bool(re.search(r'[\u0900-\u097F]', text or ''))

HINGLISH_MAP = {
    'kya': 'what',
    'kaise': 'how',
    'karein': 'do',
    'karna': 'do',
    'kare': 'do',
    'karo': 'do',
    'kyu': 'why',
    'kyun': 'why',
    'kahan': 'where',
    'kidhar': 'where',
    'kab': 'when',
    'kis': 'which',
    'kisko': 'whom',
    'zaroori': 'required',
    'zaroorat': 'needed',
    'shuru': 'start',
    'wapas': 'replay',
    'chahiye': 'needed',
    'bhejo': 'send',
    'bhejein': 'send',
    'bhejna': 'send',
    'milega': 'find',
    'dikhega': 'view',
    'nahi': 'not',
    'ha': 'yes',
    'hota': 'happens',
    'arvo': 'afternoon',
    'brekkie': 'breakfast',
    'rego': 'registration',
    'sparkie': 'electrician',
    'tradie': 'tradesperson',
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt",
    r"jailbreak",
    r"you are now",
    r"dan mode",
    r"act as an unfiltered",
    r"override rules",
    r"forget your instructions",
]

PII_PATTERNS = [
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"(?i)\bpassword\s*[:=]\s*\S+", "password: [REDACTED]"),
    (r"(?i)\bapi[_-]?key\s*[:=]\s*\S+", "api_key: [REDACTED]"),
]

TOUR_MAP = {
    'golden_rule': {'id': 'leads', 'title': 'Leads & Interaction Tour'},
    'call_outcomes': {'id': 'leads', 'title': 'Leads & Interaction Tour'},
    'retry_rules': {'id': 'leads', 'title': 'Retry Ladder Tour'},
    'lost_rules': {'id': 'leads', 'title': 'Leads & Interaction Tour'},
    'site_surveys': {'id': 'surveys', 'title': 'Site Surveys Tour'},
    'quotes_proposals': {'id': 'quotes', 'title': 'Quotes & Proposals Tour'},
    'import_csv': {'id': 'import', 'title': 'CSV Lead Import Tour'},
    'roles_permissions': {'id': 'getting-started', 'title': 'Role & Getting Started Tour'},
    'regions_compliance': {'id': 'regions', 'title': 'Multi-Country Settings Tour'},
    'notifications_app': {'id': 'notifications', 'title': 'Notifications Tour'},
    'email_smtp': {'id': 'admin', 'title': 'Email & Admin Settings Tour'},
    'ai_suggestions': {'id': 'ai-suggestions', 'title': 'AI Suggestions Tour'},
    'tour_shortcuts': {'id': 'getting-started', 'title': 'Getting Started Tour'},
    'security_privacy': {'id': 'admin', 'title': 'Security & Admin Tour'},
}


class Normalizer:
    @staticmethod
    def sanitize_input(text: str) -> Tuple[str, bool]:
        """Returns cleaned text and a flag indicating if prompt injection was detected."""
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return text, True
        return text, False

    @staticmethod
    def scrub_pii(text: str) -> str:
        """Removes phone numbers, emails, passwords from text."""
        result = text
        for pattern, replacement in PII_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    @classmethod
    def normalize(cls, text: str) -> str:
        """Lowercases, normalizes Devanagari (NFC, nukta, digits), handles Hinglish slang/synonyms, cleans punctuation."""
        if not text:
            return ""
        text = unicodedata.normalize('NFC', text)
        text = text.translate(DEVANAGARI_DIGITS)
        for nukta_char, plain_char in NUKTA_MAP.items():
            text = text.replace(nukta_char, plain_char)
        text = text.lower().strip()
        words = re.findall(r"\b[\w'-]+\b", text)
        translated = [HINGLISH_MAP.get(w, w) for w in words]
        return " ".join(translated)


class IntentEngine:
    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[LogisticRegression] = None
        self.load_or_train()

    def load_or_train(self, force_retrain: bool = False):
        if not force_retrain and MODEL_FILE.exists() and VECTORIZER_FILE.exists():
            try:
                self.vectorizer = joblib.load(VECTORIZER_FILE)
                self.classifier = joblib.load(MODEL_FILE)
                return
            except Exception as e:
                logger.warning("Failed to load cached intent model: %s. Retraining...", e)

        self.train()

    def train(self):
        if not TRAINING_FILE.exists():
            raise FileNotFoundError(f"Training data missing at {TRAINING_FILE}")

        with open(TRAINING_FILE, 'r', encoding='utf-8') as f:
            intents = yaml.safe_load(f)

        texts = []
        labels = []
        for topic, examples in intents.items():
            for ex in examples:
                norm_ex = Normalizer.normalize(ex)
                texts.append(norm_ex)
                labels.append(topic)

        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
        )
        X = self.vectorizer.fit_transform(texts)
        self.classifier = LogisticRegression(max_iter=500, C=3.0)
        self.classifier.fit(X, labels)

        joblib.dump(self.vectorizer, VECTORIZER_FILE)
        joblib.dump(self.classifier, MODEL_FILE)
        logger.info("Intent classifier trained with %d examples across %d topics.", len(texts), len(intents))

    def predict(self, text: str) -> Tuple[str, float]:
        norm = Normalizer.normalize(text)
        if not self.vectorizer or not self.classifier:
            self.load_or_train()

        X = self.vectorizer.transform([norm])
        probs = self.classifier.predict_proba(X)[0]
        max_idx = probs.argmax()
        topic = self.classifier.classes_[max_idx]
        confidence = float(probs[max_idx])

        # If predicted class is out_of_scope or probability is below threshold, treat as out_of_scope
        if topic == 'out_of_scope' or confidence < 0.10:
            return 'out_of_scope', confidence
        return topic, confidence


class KnowledgeRetriever:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.load_or_build()

    def load_or_build(self, force_rebuild: bool = False):
        if not force_rebuild and INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                corpus = [doc['tokens'] for doc in self.documents]
                if corpus:
                    self.bm25 = BM25Okapi(corpus)
                    return
            except Exception as e:
                logger.warning("Failed to load knowledge index: %s. Rebuilding...", e)

        self.build_index()

    def build_index(self):
        docs = []

        # 1. Parse markdown knowledge files
        if KNOWLEDGE_DIR.exists():
            for md_path in KNOWLEDGE_DIR.glob('*.md'):
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                meta = {}
                body = content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        try:
                            meta = yaml.safe_load(parts[1]) or {}
                            body = parts[2]
                        except Exception:
                            pass

                # Chunk markdown by headings
                sections = re.split(r'\n(?=#{1,3}\s)', body)
                topic = meta.get('topic', md_path.stem.replace('_hi', ''))
                title = meta.get('title', md_path.stem.replace('_', ' ').title())
                is_hi = meta.get('language') == 'hi' or md_path.stem.endswith('_hi')
                doc_lang = 'hi' if is_hi else 'en'

                for idx, sec in enumerate(sections):
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue
                    tokens = Normalizer.normalize(sec_clean).split()
                    docs.append({
                        'id': f"{topic}_{doc_lang}_{idx}",
                        'topic': topic,
                        'title': title,
                        'content': sec_clean,
                        'tokens': tokens,
                        'language': doc_lang,
                        'roles': meta.get('roles', []),
                        'regions': meta.get('regions', []),
                    })

        # 2. Add Dynamic Facts if available
        if DYNAMIC_FACTS_FILE.exists():
            try:
                with open(DYNAMIC_FACTS_FILE, 'r', encoding='utf-8') as f:
                    facts = json.load(f)
                for f_item in facts:
                    text = f"{f_item.get('title', '')}: {f_item.get('content', '')}"
                    tokens = Normalizer.normalize(text).split()
                    docs.append({
                        'id': f_item.get('id', 'dynamic_fact'),
                        'topic': f_item.get('topic', 'dynamic'),
                        'title': f_item.get('title', 'Live System Setting'),
                        'content': f_item.get('content', ''),
                        'tokens': tokens,
                        'language': 'en',
                        'roles': f_item.get('roles', []),
                        'regions': f_item.get('regions', []),
                    })
            except Exception as e:
                logger.warning("Could not read dynamic facts: %s", e)

        self.documents = docs
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2)

        corpus = [doc['tokens'] for doc in docs]
        if corpus:
            self.bm25 = BM25Okapi(corpus)
        logger.info("Knowledge index built with %d passages.", len(docs))

    def retrieve(self, query: str, top_k: int = 3, topic: Optional[str] = None, language: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.documents:
            self.load_or_build()
        if not self.bm25:
            return []

        if language is None:
            language = 'hi' if is_devanagari(query) else 'en'

        tokens = Normalizer.normalize(query).split()
        scores = self.bm25.get_scores(tokens)

        scored_docs = list(zip(scores, self.documents))
        boosted = []
        for score, doc in scored_docs:
            b_score = score
            if topic and topic != 'out_of_scope' and doc.get('topic') == topic:
                b_score *= 1.8
            if doc.get('language') == language:
                b_score *= 1.5
            boosted.append((b_score, doc))

        boosted.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in boosted[:top_k] if score > 0.05]


class HelpbotEngine:
    def __init__(self):
        self.intents = IntentEngine()
        self.retriever = KnowledgeRetriever()

    def process_query(self, query: str, user_role: str = 'salesperson', user_region: str = 'IN') -> Dict[str, Any]:
        """Main entry point for Helpbot query processing."""
        user_lang = 'hi' if is_devanagari(query) else 'en'
        refusal_msg = REFUSAL_MESSAGES.get(user_lang, REFUSAL_MESSAGE)
        starter_qs = STARTER_QUESTIONS_BY_LANG.get(user_lang, DEFAULT_STARTER_QUESTIONS)

        # 1. Prompt injection check
        clean_query, is_injection = Normalizer.sanitize_input(query)
        if is_injection:
            return {
                'answer': refusal_msg + ("\n\nकृपया सोलर सीआरएम सॉफ़्टवेयर के उपयोग से संबंधित प्रश्न पूछें।" if user_lang == 'hi' else "\n\nPlease ask questions related to operating the Solar CRM software."),
                'topic': 'out_of_scope',
                'confidence': 1.0,
                'is_refusal': True,
                'suggested_questions': starter_qs,
                'tour': None,
            }

        # 2. PII Scrubbing
        safe_query = Normalizer.scrub_pii(clean_query)

        # 3. Intent Classification
        topic, confidence = self.intents.predict(safe_query)

        # 4. Scope Gate
        if topic == 'out_of_scope':
            return {
                'answer': refusal_msg + ("\n\nमैं सीआरएम वर्कफ़्लो, कॉल परिणाम, कोटेशन, सर्वे, नीतियों और टूर के बारे में आपकी सहायता कर सकता हूँ।" if user_lang == 'hi' else "\n\nI can assist you with CRM workflows, call outcomes, quotes, surveys, policies, and system tours."),
                'topic': 'out_of_scope',
                'confidence': confidence,
                'is_refusal': True,
                'suggested_questions': self.get_contextual_starters(user_role, language=user_lang),
                'tour': None,
            }

        # 5. Retrieve Context
        passages = self.retriever.retrieve(safe_query, top_k=3, topic=topic, language=user_lang)

        # 6. Check Provider: Anthropic or Local
        provider = getattr(settings, 'HELPBOT_PROVIDER', 'local').lower()
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')

        answer_text = ""
        tour_info = TOUR_MAP.get(topic)

        if provider == 'anthropic' and api_key and not api_key.startswith('your-'):
            try:
                answer_text = self._call_anthropic(safe_query, passages, user_role, user_region, api_key)
            except Exception as e:
                logger.warning("Anthropic provider failed (%s), falling back to local: %s", provider, e)
                answer_text = self._generate_local_answer(safe_query, topic, passages, language=user_lang)
        else:
            answer_text = self._generate_local_answer(safe_query, topic, passages, language=user_lang)

        # Suggested follow-up questions
        suggested = self.get_topic_suggestions(topic, language=user_lang)

        return {
            'answer': answer_text,
            'topic': topic,
            'confidence': round(confidence, 3),
            'is_refusal': False,
            'suggested_questions': suggested,
            'tour': tour_info,
            'passages_count': len(passages),
        }

    def _generate_local_answer(self, query: str, topic: str, passages: List[Dict[str, Any]], language: str = 'en') -> str:
        """Deterministic, grounded extractive answer generator."""
        if not passages:
            if language == 'hi':
                return (
                    "यहाँ **" + topic + "** के लिए मानक वर्कफ़्लो जानकारी दी गई है।\n\n"
                    "कृपया नेविगेशन मेनू में संबंधित अनुभाग देखें या उत्पाद टूर (Tour) देखें।"
                )
            return (
                "Here is the standard workflow information for **" + topic.replace('_', ' ').title() + "**.\n\n"
                "Please refer to the relevant section in the navigation menu or take a guided walkthrough."
            )

        # Combine top passages cleanly
        primary = passages[0]
        content = primary['content'].strip()

        # Build clean bulleted response
        lines = content.split('\n')
        # Skip top markdown header if redundant
        body_lines = [line for line in lines if not line.startswith('# ')]
        cleaned_body = "\n".join(body_lines).strip()

        additional_notes = []
        if len(passages) > 1:
            sec_passage = passages[1]
            if sec_passage['topic'] == topic and sec_passage['title'] != primary['title']:
                prefix = "**यह भी देखें**" if language == 'hi' else "**Also see**"
                additional_notes.append(f"{prefix} ({sec_passage['title']}):\n{sec_passage['content'][:180]}...")

        tour_note = ""
        tour = TOUR_MAP.get(topic)
        if tour:
            if language == 'hi':
                tour_note = f"\n\n*सुझाव: इंटरैक्टिव **{tour['title']}** देखने के लिए नीचे दिए गए बटन पर क्लिक करें।*"
            else:
                tour_note = f"\n\n*Tip: Click **Show me how** below to take the interactive **{tour['title']}**.*"

        response = cleaned_body
        if additional_notes:
            response += "\n\n" + "\n\n".join(additional_notes)
        response += tour_note

        return response

    def _call_anthropic(self, query: str, passages: List[Dict[str, Any]], role: str, region: str, api_key: str) -> str:
        """Calls Anthropic SDK with context passages."""
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        context_blocks = "\n\n---\n\n".join([f"[{p['title']}]:\n{p['content']}" for p in passages])

        user_content = f"""User Role: {role}
User Region: {region}

Context Documents:
{context_blocks}

User Question: {query}
"""
        response = client.messages.create(
            model=getattr(settings, 'AI_MODEL', 'claude-sonnet-5-5') or 'claude-3-5-sonnet-20241022',
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_content}],
        )
        return response.content[0].text.strip()

    def get_contextual_starters(self, role: str, language: str = 'en') -> List[str]:
        if language == 'hi':
            if role == 'surveyor':
                return [
                    "साइट सर्वेक्षण के दौरान कौन सी चेकलिस्ट आवश्यक है?",
                    "छत और मीटर बॉक्स की फ़ोटो कैसे अपलोड करें?",
                    "मुझे सौंपे गए सर्वेक्षण कहाँ दिखते हैं?",
                ]
            elif role == 'manager':
                return [
                    "सीएसवी से लीड्स कैसे आयात करें?",
                    "लीड को विफल (Lost) चिह्नित करने की अनुमति किसे है?",
                    "टीम प्रदर्शन और रूपांतरण दर कैसे देखें?",
                ]
            elif role == 'admin':
                return [
                    "एसएमटीपी ईमेल सेटिंग्स कैसे जोड़ें?",
                    "भारत (IN) और ऑस्ट्रेलिया (AU) सेटिंग्स में क्या अंतर है?",
                    "हेल्प असिस्टेंट विश्लेषण और अनुत्तरित प्रश्न कहाँ दिखते हैं?",
                ]
            else:  # salesperson
                return [
                    "सीआरएम का स्वर्णिम नियम क्या है?",
                    "व्यस्त कॉलों के लिए रीट्राई लैडर कैसे काम करता है?",
                    "कोटेशन कैसे बनाएं और पीडीएफ कैसे भेजें?",
                ]

        if role == 'surveyor':
            return [
                "What checklist items are required during a site survey?",
                "How do I upload roof and electrical meter photos?",
                "Where can I see my assigned survey visits?",
            ]
        elif role == 'manager':
            return [
                "How do I import leads via CSV and round-robin assign them?",
                "Who has permission to mark a lead as Lost?",
                "How do I view team conversion performance and metrics?",
            ]
        elif role == 'admin':
            return [
                "How do I configure SMTP email settings?",
                "How to switch between India (IN) and Australia (AU) settings?",
                "Where can I see Help Assistant insights and unresolved questions?",
            ]
        else:  # salesperson
            return [
                "What is the CRM golden rule for logging calls?",
                "How does the automated retry ladder work for busy calls?",
                "How do I generate a solar quotation and send a PDF?",
            ]

    def get_topic_suggestions(self, topic: str, language: str = 'en') -> List[str]:
        if language == 'hi':
            starters_hi = {
                'golden_rule': [
                    "कॉल के तुरंत बाद विवरण क्यों दर्ज करना चाहिए?",
                    "किसी लीड को बिना अगले कदम के छोड़ने पर क्या होता है?",
                ],
                'call_outcomes': [
                    "कॉलबैक का अनुरोध परिणाम का क्या कार्य है?",
                    "साइट सर्वे अनुरोध परिणाम कब चुनें?",
                ],
                'retry_rules': [
                    "अधिकतम कितने प्रयासों के बाद लीड अनरीचेबल होती है?",
                    "व्यस्त या बंद फोन के लिए क्या अंतराल हैं?",
                ],
                'lost_rules': [
                    "क्या विक्रेता बिना प्रबंधक के लीड Lost कर सकता है?",
                    "विफल सौदों में प्रतियोगी का नाम क्यों जरूरी है?",
                ],
                'site_surveys': [
                    "सर्वेयर फ़ोटो कैसे अपलोड करता है?",
                    "सर्वे फॉर्म में छत के कौन से प्रकार होते हैं?",
                ],
                'quotes_proposals': [
                    "सब्सिडी के साथ नेट देय राशि कैसे निकाली जाती है?",
                    "कोटेशन पीडीएफ कैसे डाउनलोड करें?",
                ],
                'import_csv': [
                    "लीड आयात के लिए कौन से कॉलम आवश्यक हैं?",
                    "राउंड रॉबिन लीड आवंटन कैसे काम करता है?",
                ],
                'roles_permissions': [
                    "क्या विक्रेता किसी अन्य को लीड सौंप सकता है?",
                    "सर्वेयर के लिए कौन से फीचर प्रतिबंधित हैं?",
                ],
                'regions_compliance': [
                    "भारत और ऑस्ट्रेलिया सेटिंग्स में क्या अंतर है?",
                    "अनुमत कॉलिंग घंटे और डीएनसीआर नियम क्या हैं?",
                ],
                'notifications_app': [
                    "डेस्कटॉप पुश अलर्ट कैसे चालू करें?",
                    "लीड आवंटन की सूचना कब मिलती है?",
                ],
                'email_smtp': [
                    "जीमेल या ब्रेवो एसएमटीपी सेटिंग्स कैसे जोड़ें?",
                    "प्रातःकालीन दैनिक डाइजेस्ट किस समय आता है?",
                ],
                'ai_suggestions': [
                    "लीड स्क्रीन पर एआई कैसे सुझाव देता है?",
                    "क्या बिना एपीआई कुंजी के एआई काम करता है?",
                ],
                'tour_shortcuts': [
                    "हेल्प असिस्टेंट का कीबोर्ड शॉर्टकट क्या है?",
                    "ऑनबोर्डिंग टूर दोबारा कैसे देखें?",
                ],
                'security_privacy': [
                    "ग्राहक संपर्क विवरण कौन देख सकता है?",
                    "क्या लीड परिवर्तनों का ऑडिट लॉग रखा जाता है?",
                ],
            }
            return starters_hi.get(topic, STARTER_QUESTIONS_BY_LANG['hi'][:2])

        starters = {
            'golden_rule': [
                "Why must call outcomes be logged immediately?",
                "What happens if a lead has no scheduled next step?",
            ],
            'call_outcomes': [
                "What does 'Callback Requested' do?",
                "When should I select 'Site Survey Requested'?",
            ],
            'retry_rules': [
                "How many call attempts before a lead is marked unreachable?",
                "What are the retry intervals for busy or switched-off phones?",
            ],
            'lost_rules': [
                "Can a salesperson mark a lead lost without manager approval?",
                "Why is competitor name required for lost deals?",
            ],
            'site_surveys': [
                "How do surveyors upload photos?",
                "What roof types are recorded in the survey form?",
            ],
            'quotes_proposals': [
                "How is the net price calculated with government subsidies?",
                "How do I download or WhatsApp a quote PDF?",
            ],
            'import_csv': [
                "What are the required CSV columns for bulk leads?",
                "How does round-robin lead distribution work?",
            ],
            'roles_permissions': [
                "Can a salesperson reassign leads to someone else?",
                "What features are restricted for the surveyor role?",
            ],
            'regions_compliance': [
                "What are the differences between India and Australia configurations?",
                "What are calling hours and do-not-call compliance rules?",
            ],
            'notifications_app': [
                "How do I turn on desktop push alerts?",
                "When do lead assignment notifications fire?",
            ],
            'email_smtp': [
                "How do I configure Gmail or Brevo SMTP settings?",
                "What time does the morning digest email send?",
            ],
            'ai_suggestions': [
                "How does AI suggest recommendations on the lead screen?",
                "Does the AI assistant work without an Anthropic API key?",
            ],
            'tour_shortcuts': [
                "What is the keyboard shortcut for Help Assistant?",
                "How do I replay the onboarding product tour?",
            ],
            'security_privacy': [
                "Who can view customer contact details and phone numbers?",
                "Are audit logs kept for lead changes?",
            ],
        }
        return starters.get(topic, DEFAULT_STARTER_QUESTIONS[:2])


# Singleton instance
_helpbot_engine = None

def get_helpbot_engine() -> HelpbotEngine:
    global _helpbot_engine
    if _helpbot_engine is None:
        _helpbot_engine = HelpbotEngine()
    return _helpbot_engine
