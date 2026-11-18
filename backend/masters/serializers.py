from rest_framework import serializers

from .models import (
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
)


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class PublicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicHoliday
        fields = '__all__'


class RoofTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoofType
        fields = '__all__'


class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = '__all__'


class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outcome
        fields = '__all__'


class LostReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LostReason
        fields = '__all__'


class NurtureReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureReason
        fields = '__all__'


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = '__all__'


class PolicySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicySettings
        fields = '__all__'
