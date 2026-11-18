from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    allowed_regions = serializers.SlugRelatedField(many=True, read_only=True, slug_field='code')
    default_region = serializers.CharField(source='default_region.code', read_only=True, default='')

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'is_active',
            'date_joined',
            'allowed_regions',
            'default_region',
            'default_timezone',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'is_active',
            'password',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
