from rest_framework import serializers
from .models import Notification
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'message', 'is_read', 'created_at', 'read_at']
        



User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    active_investments_count = serializers.IntegerField(read_only=True)
    completed_investments_count = serializers.IntegerField(read_only=True)
    total_invested = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    kyc_status_display = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'gender', 'id_type', 'id_number',
            'address', 'occupation', 'nationality', 'is_kyc_complete',
            'is_active', 'is_staff', 'is_verified', 
            'referral_code', 'date_joined', 'last_login',
             'active_investments_count',
            'completed_investments_count', 'total_invested', 'kyc_status_display'
        ]
        read_only_fields = ['date_joined', 'last_login', 'referral_code',
        'active_investments_count', 'completed_investments_count', 'total_invested']

    def get_kyc_status_display(self, obj):
        return "Verified" if obj.is_kyc_complete else "Not Verified"

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'password',
            'confirm_password', 'is_active', 'is_staff', 'is_verified'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'password',
            'confirm_password', 'is_active', 'is_staff', 'is_verified',
            'date_of_birth', 'gender', 'id_type', 'id_number', 'address',
            'occupation', 'nationality', 'is_kyc_complete'
        ]
        read_only_fields = ['email']

    def validate(self, data):
        if 'password' in data and 'confirm_password' not in data:
            raise serializers.ValidationError("Must confirm password when changing it")
        if 'password' in data and 'confirm_password' in data:
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("Passwords don't match")
        return data

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
            validated_data.pop('confirm_password')
        return super().update(instance, validated_data)

class UserKYCStatusSerializer(serializers.Serializer):
    is_kyc_complete = serializers.BooleanField(required=True)