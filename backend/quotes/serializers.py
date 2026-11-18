from rest_framework import serializers

from .models import Quote


class QuoteSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    region_code = serializers.CharField(source='region.code', read_only=True)

    class Meta:
        model = Quote
        fields = [
            'id',
            'lead',
            'lead_name',
            'region',
            'region_code',
            'version',
            'system_size_kw',
            'battery_kwh',
            'brand',
            'currency',
            'currency_symbol',
            'price',
            'tax_included',
            'tax_rate',
            'tax_amount',
            'incentive_label',
            'incentive_amount',
            'subsidy_amount',
            'status',
            'notes',
            'remark',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'version', 'created_at']


class CreateQuoteInputSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField(required=True)
    system_size_kw = serializers.DecimalField(max_digits=8, decimal_places=2, required=True)
    battery_kwh = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    brand = serializers.CharField(max_length=100, required=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    incentive_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    subsidy_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    tax_included = serializers.BooleanField(required=False, default=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class ReviseQuoteInputSerializer(serializers.Serializer):
    system_size_kw = serializers.DecimalField(max_digits=8, decimal_places=2, required=True)
    battery_kwh = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    brand = serializers.CharField(max_length=100, required=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    incentive_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    subsidy_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    tax_included = serializers.BooleanField(required=False, default=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class RejectQuoteInputSerializer(serializers.Serializer):
    lost_reason_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
