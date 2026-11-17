from rest_framework import serializers

from .models import LeadSource, LostReason, NurtureReason, Outcome, PolicySettings


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
