import defusedcsv.csv as defusedcsv
import io
import json
import re
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from accounts.permissions import HasPermission, IsAdmin
from leads.import_service import sanitize_csv_cell
from leads.models import AuditLog

from .models import (
    Language,
    LeadSource,
    LostReason,
    NurtureReason,
    Outcome,
    PolicySettings,
    PropertyType,
    PublicHoliday,
    Region,
    RoofType,
    State,
    TranslationEntry,
)
from .serializers import (
    LanguageSerializer,
    LeadSourceSerializer,
    LostReasonSerializer,
    NurtureReasonSerializer,
    OutcomeSerializer,
    PolicySettingsSerializer,
    PropertyTypeSerializer,
    PublicHolidaySerializer,
    RegionSerializer,
    RoofTypeSerializer,
    StateSerializer,
    TranslationEntrySerializer,
)


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all().order_by('sort_order', 'code')
    serializer_class = RegionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'calling_hours_policy', 'currency']
    search_fields = ['code', 'name', 'currency', 'default_timezone']
    ordering_fields = ['sort_order', 'code', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = StateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['code', 'name', 'default_timezone']
    ordering_fields = ['sort_order', 'name', 'code']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PublicHolidayViewSet(viewsets.ModelViewSet):
    queryset = PublicHoliday.objects.all().order_by('region', 'date')
    serializer_class = PublicHolidaySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'date']
    search_fields = ['name']
    ordering_fields = ['date', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class RoofTypeViewSet(viewsets.ModelViewSet):
    queryset = RoofType.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = RoofTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PropertyTypeViewSet(viewsets.ModelViewSet):
    queryset = PropertyType.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = PropertyTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class OutcomeViewSet(viewsets.ModelViewSet):
    queryset = Outcome.objects.all().order_by('stage', 'sort_order', 'id')
    serializer_class = OutcomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['stage', 'is_terminal', 'is_active', 'requires_lost_reason', 'requires_nurture_reason']
    search_fields = ['name', 'default_status', 'default_next_action']
    ordering_fields = ['sort_order', 'id', 'name', 'stage']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class LostReasonViewSet(viewsets.ModelViewSet):
    queryset = LostReason.objects.all().order_by('sort_order', 'name')
    serializer_class = LostReasonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class NurtureReasonViewSet(viewsets.ModelViewSet):
    queryset = NurtureReason.objects.all().order_by('sort_order', 'name')
    serializer_class = NurtureReasonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all().order_by('sort_order', 'name')
    serializer_class = LeadSourceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PolicySettingsViewSet(viewsets.ModelViewSet):
    queryset = PolicySettings.objects.all()
    serializer_class = PolicySettingsSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


# ==============================================================================
# PHASE 14L: LANGUAGE & TRANSLATION MANAGEMENT
# ==============================================================================

SCRIPT_OR_EVENT_REGEX = re.compile(
    r'(<\s*(script|iframe|embed|object|link|style|meta|form|input|button|svg|math|base|applet)[\s/>]|javascript:|data:\s*text/html|on\w+\s*=)',
    re.IGNORECASE,
)


def sanitize_and_validate_translation(english_text: str, translated_text: str) -> str:
    if not translated_text:
        return translated_text
    if len(translated_text) > 5000:
        raise ValidationError("Translation string exceeds maximum permitted length of 5,000 characters.")
    # Reject dangerous script injection / event handlers
    if SCRIPT_OR_EVENT_REGEX.search(translated_text):
        raise ValidationError("Unsafe HTML tags or event handlers detected in translation text.")
    # Validate ICU / format-string placeholder parity: {name}, {count}, etc.
    if english_text:
        en_placeholders = set(re.findall(r'\{([a-zA-Z0-9_]+)\}', english_text))
        tr_placeholders = set(re.findall(r'\{([a-zA-Z0-9_]+)\}', translated_text))
        if en_placeholders != tr_placeholders:
            diff = en_placeholders ^ tr_placeholders
            raise ValidationError(f"Placeholder mismatch: {diff}. Both English and translated text must share identical {{placeholders}}.")
    return translated_text


def recalculate_language_completeness(language: Language):
    en_lang = Language.objects.filter(code='en').first()
    if not en_lang:
        return
    total_keys = TranslationEntry.objects.filter(language=en_lang).count()
    if total_keys == 0:
        return
    if language.code == 'en':
        language.completeness_pct = 100.0
        language.save(update_fields=['completeness_pct'])
        return

    translated_count = (
        TranslationEntry.objects.filter(
            language=language,
            status__in=['draft', 'reviewed', 'approved'],
        )
        .exclude(translated_text='')
        .count()
    )
    pct = round((translated_count / total_keys) * 100, 1)
    language.completeness_pct = min(100.0, pct)
    language.save(update_fields=['completeness_pct'])


class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.filter(is_active=True).order_by('sort_order', 'code')
    serializer_class = LanguageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_enabled', 'review_status']
    search_fields = ['code', 'name', 'native_name']
    ordering_fields = ['sort_order', 'code', 'name', 'completeness_pct']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [HasPermission('i18n.manage')()]

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('i18n.manage')])
    def toggle_enabled(self, request, pk=None):
        language = self.get_object()
        language.is_enabled = not language.is_enabled
        language.save(update_fields=['is_enabled', 'updated_at'])

        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            user_name=request.user.get_full_name() if request.user.is_authenticated else 'System',
            action='LANGUAGE_TOGGLED',
            details=f"Language '{language.code}' enabled={language.is_enabled}",
            reason=f"Admin toggled {language.name} status",
            ip_address=request.META.get('REMOTE_ADDR'),
            message_code='LANGUAGE_TOGGLED',
            params={'code': language.code, 'enabled': language.is_enabled},
        )
        return Response({'status': 'ok', 'is_enabled': language.is_enabled, 'code': language.code})


class TranslationViewSet(viewsets.ModelViewSet):
    queryset = TranslationEntry.objects.all().order_by('language__sort_order', 'namespace', 'key')
    serializer_class = TranslationEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['language', 'namespace', 'status', 'is_customer_facing']
    search_fields = ['key', 'english_text', 'translated_text']
    ordering_fields = ['namespace', 'key', 'status', 'updated_at']

    def get_queryset(self):
        qs = super().get_queryset()
        lang_code = self.request.query_params.get('language__code') or self.request.query_params.get('lang')
        if lang_code:
            qs = qs.filter(language__code=lang_code)
        return qs

    def get_permissions(self):
        if self.action in ['bundle']:
            return [permissions.AllowAny()]
        if self.action in ['list', 'retrieve', 'export']:
            return [HasPermission('i18n.view')()]
        return [HasPermission('i18n.manage')()]

    def perform_update(self, serializer):
        english_text = serializer.instance.english_text
        new_translated = serializer.validated_data.get('translated_text', serializer.instance.translated_text)
        sanitized = sanitize_and_validate_translation(english_text, new_translated)

        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(translated_text=sanitized, updated_by=user)
        recalculate_language_completeness(instance.language)

        AuditLog.objects.create(
            user=user,
            user_name=user.get_full_name() if user else 'System',
            action='TRANSLATION_UPDATED',
            details=f"Updated key '{instance.namespace}:{instance.key}' for lang '{instance.language.code}'",
            reason="Translation edited",
            ip_address=self.request.META.get('REMOTE_ADDR'),
            message_code='TRANSLATION_UPDATED',
            params={'key': f"{instance.namespace}:{instance.key}", 'lang': instance.language.code},
        )

    @action(detail=False, methods=['get'])
    def bundle(self, request):
        """
        Returns full nested dictionary of translations for a target language:
        { "common": { "buttons.save": "सुरक्षित करें" }, ... }
        Falls back to English if translation is missing.
        """
        lang_code = request.query_params.get('lang', 'en')
        lang = Language.objects.filter(code=lang_code, is_active=True).first()
        if not lang:
            lang = Language.objects.filter(code='en').first()

        # Build bundle dictionary
        bundle_data = {}
        entries = TranslationEntry.objects.filter(language=lang)
        for entry in entries:
            if entry.namespace not in bundle_data:
                bundle_data[entry.namespace] = {}
            bundle_data[entry.namespace][entry.key] = entry.translated_text or entry.english_text

        # If non-English, fill missing keys with English defaults
        if lang and lang.code != 'en':
            en_entries = TranslationEntry.objects.filter(language__code='en')
            for en_e in en_entries:
                if en_e.namespace not in bundle_data:
                    bundle_data[en_e.namespace] = {}
                if en_e.key not in bundle_data[en_e.namespace]:
                    bundle_data[en_e.namespace][en_e.key] = en_e.translated_text or en_e.english_text

        return Response(bundle_data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Exports all translations for a given language in JSON or CSV format.
        """
        lang_code = request.query_params.get('lang', 'hi')
        export_fmt = request.query_params.get('format', 'json').lower()

        lang = Language.objects.filter(code=lang_code).first()
        if not lang:
            return Response({'error': f"Language '{lang_code}' not found."}, status=status.HTTP_404_NOT_FOUND)

        entries = TranslationEntry.objects.filter(language=lang).order_by('namespace', 'key')

        if export_fmt == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="translations_{lang_code}.csv"'
            writer = defusedcsv.writer(response)
            writer.writerow(['namespace', 'key', 'english_text', 'translated_text', 'status', 'is_customer_facing'])
            for e in entries:
                writer.writerow([
                    sanitize_csv_cell(e.namespace),
                    sanitize_csv_cell(e.key),
                    sanitize_csv_cell(e.english_text),
                    sanitize_csv_cell(e.translated_text),
                    sanitize_csv_cell(e.status),
                    sanitize_csv_cell(e.is_customer_facing),
                ])
            return response

        # JSON export
        data = [
            {
                'namespace': e.namespace,
                'key': e.key,
                'english_text': e.english_text,
                'translated_text': e.translated_text,
                'status': e.status,
                'is_customer_facing': e.is_customer_facing,
            }
            for e in entries
        ]
        return Response(data)

    @action(detail=False, methods=['post'], url_path='import')
    def import_translations(self, request):
        """
        Imports translations from JSON payload or CSV file.
        Enforces 5MB size limit and 5,000 rows max limit.
        """
        lang_code = request.query_params.get('lang') or request.data.get('lang')
        if not lang_code:
            return Response({'error': "Parameter 'lang' is required."}, status=status.HTTP_400_BAD_REQUEST)

        language = Language.objects.filter(code=lang_code).first()
        if not language:
            return Response({'error': f"Language '{lang_code}' does not exist."}, status=status.HTTP_404_NOT_FOUND)

        rows = []
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            if uploaded_file.size > 5 * 1024 * 1024:
                return Response({'error': "Import file exceeds maximum size limit of 5MB."}, status=status.HTTP_400_BAD_REQUEST)
            content = uploaded_file.read().decode('utf-8', errors='replace')
            if uploaded_file.name.endswith('.csv'):
                reader = defusedcsv.DictReader(io.StringIO(content))
                rows = list(reader)
            else:
                try:
                    rows = json.loads(content)
                except Exception as err:
                    return Response({'error': f"Invalid JSON format: {err}"}, status=status.HTTP_400_BAD_REQUEST)
        elif 'items' in request.data:
            rows = request.data['items']
        elif isinstance(request.data, list):
            rows = request.data
        else:
            return Response({'error': "No file or data provided for import."}, status=status.HTTP_400_BAD_REQUEST)

        if len(rows) > 5000:
            return Response({'error': f"Row count ({len(rows)}) exceeds 5,000 rows limit."}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        created_count = 0
        user = request.user if request.user.is_authenticated else None

        for item in rows:
            ns = item.get('namespace')
            key = item.get('key')
            en_text = item.get('english_text', '')
            tr_text = item.get('translated_text', '')
            item_status = item.get('status', 'draft')
            is_cust = item.get('is_customer_facing', False)

            if not ns or not key:
                continue

            try:
                clean_tr = sanitize_and_validate_translation(en_text, tr_text)
            except ValidationError:
                continue

            entry, created = TranslationEntry.objects.update_or_create(
                language=language,
                namespace=ns,
                key=key,
                defaults={
                    'english_text': en_text,
                    'translated_text': clean_tr,
                    'status': item_status,
                    'is_customer_facing': is_cust,
                    'updated_by': user,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        recalculate_language_completeness(language)

        AuditLog.objects.create(
            user=user,
            user_name=user.get_full_name() if user else 'System',
            action='TRANSLATIONS_IMPORTED',
            details=f"Imported translations for '{language.code}': {created_count} created, {updated_count} updated",
            reason=f"Bulk translation import for {language.name}",
            ip_address=request.META.get('REMOTE_ADDR'),
            message_code='TRANSLATIONS_IMPORTED',
            params={'lang': language.code, 'created': created_count, 'updated': updated_count},
        )

        return Response({
            'status': 'ok',
            'created_count': created_count,
            'updated_count': updated_count,
            'completeness_pct': language.completeness_pct,
        })

    @action(detail=False, methods=['post'])
    def translate_missing(self, request):
        """
        Drafts missing translations using the glossary and safe template filling.
        Marks all generated entries with status='draft' (needs review).
        """
        lang_code = request.data.get('lang') or request.query_params.get('lang', 'hi')
        language = Language.objects.filter(code=lang_code).first()
        if not language:
            return Response({'error': f"Language '{lang_code}' not found."}, status=status.HTTP_404_NOT_FOUND)

        from .management.commands.translate_missing import draft_missing_for_language
        drafted_count = draft_missing_for_language(language, user=request.user if request.user.is_authenticated else None)

        return Response({
            'status': 'ok',
            'drafted_count': drafted_count,
            'completeness_pct': language.completeness_pct,
        })
