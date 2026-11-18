from rest_framework import serializers

from .models import Notification, NotificationPreference, PushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'message',
            'link',
            'is_read',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'in_app_enabled',
            'browser_enabled',
            'push_enabled',
            'email_enabled',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
        ]
        read_only_fields = ['id']


class PushSubscriptionSerializer(serializers.ModelSerializer):
    keys = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = PushSubscription
        fields = [
            'id',
            'endpoint',
            'keys',
            'user_agent',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        keys = validated_data.pop('keys', {})
        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')
        endpoint = validated_data.get('endpoint')
        user = self.context['request'].user
        user_agent = validated_data.get('user_agent', '')

        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': user_agent,
            }
        )
        return subscription
