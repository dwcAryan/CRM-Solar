from rest_framework import serializers

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


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = [
            'id',
            'code',
            'name',
            'native_name',
            'direction',
            'is_enabled',
            'numbering_system',
            'week_start',
            'font_family_key',
            'completeness_pct',
            'review_status',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TranslationEntrySerializer(serializers.ModelSerializer):
    language_code = serializers.CharField(source='language.code', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = TranslationEntry
        fields = [
            'id',
            'language',
            'language_code',
            'namespace',
            'key',
            'english_text',
            'translated_text',
            'status',
            'is_customer_facing',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'language_code', 'updated_by_name', 'created_at', 'updated_at']


def get_localized_name(obj, request, fallback_attr='name'):
    lang = getattr(request, 'LANGUAGE_CODE', 'en') if request else 'en'
    if hasattr(obj, 'translations') and isinstance(obj.translations, dict):
        if lang in obj.translations and obj.translations[lang]:
            return obj.translations[lang]
        base_lang = lang.split('-')[0]
        if base_lang in obj.translations and obj.translations[base_lang]:
            return obj.translations[base_lang]
    return getattr(obj, fallback_attr, '')


class RegionSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class StateSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = State
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class PublicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicHoliday
        fields = '__all__'


class RoofTypeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = RoofType
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class PropertyTypeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = PropertyType
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class OutcomeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Outcome
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class LostReasonSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = LostReason
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class NurtureReasonSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = NurtureReason
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class LeadSourceSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadSource
        fields = '__all__'

    def get_display_name(self, obj):
        return get_localized_name(obj, self.context.get('request'))


class PolicySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicySettings
        fields = '__all__'
