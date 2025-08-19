from datetime import timezone
import requests
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import StoragePlan, StorageInvestment, PaymentTransaction, StorageUpdate
from decimal import Decimal

class StoragePlanSerializer(serializers.ModelSerializer):
    roi_percentage = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    product_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = StoragePlan
        fields = [
            'id', 'product_name', 'product_image', 'description',
            'buying_price_per_bag', 'projected_selling_price', 'storage_due_date',
            'available_quantity', 'minimum_quantity', 'maximum_quantity',
            'is_active', 'roi_percentage', 'is_available', 'created_at'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.product_image:
            data['product_image'] = request.build_absolute_uri(instance.product_image.url)
        return data

    def update(self, instance, validated_data):
        # Handle the image field separately
        product_image = validated_data.pop('product_image', None)
        
        if product_image is not None:
            # If a new image was provided, update it
            instance.product_image = product_image
        # If product_image is None (not provided in the update), keep the existing one
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class StorageUpdateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = StorageUpdate
        fields = [
            'id', 'update_type', 'title', 'message', 
            'current_market_price', 'image', 'created_at'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.image:
            data['image'] = request.build_absolute_uri(instance.image.url)
        return data
    
    def update(self, instance, validated_data):
        # Handle the image field separately
        product_image = validated_data.pop('product_image', None)
        
        if product_image is not None:
            # If a new image was provided, update it
            instance.product_image = product_image
        # If product_image is None (not provided in the update), keep the existing one
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class InvestmentSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField()
    product_image = serializers.ReadOnlyField()
    roi_percentage = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    updates = StorageUpdateSerializer(many=True, read_only=True)
    storage_plan_details = StoragePlanSerializer(source='storage_plan', read_only=True)

    class Meta:
        model = StorageInvestment
        fields = [
            'id', 'product_name', 'product_image', 'customer_name', 
            'customer_email', 'customer_phone', 'quantity_bags', 
            'price_per_bag', 'total_investment_amount', 
            'projected_selling_price_per_bag', 'projected_returns',
            'status', 'purchase_date', 'due_date', 'completion_date',
            'payment_reference', 'payment_status', 'roi_percentage',
            'days_remaining', 'progress_percentage', 'updates',
            'storage_plan_details', 'created_at'
        ]


class InvestmentCreateSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    quantity_bags = serializers.IntegerField(min_value=1)
    customer_name = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate(self, data):
        try:
            storage_plan = StoragePlan.objects.get(id=data['plan_id'])
        except StoragePlan.DoesNotExist:
            raise serializers.ValidationError("Storage plan not found")

        if not storage_plan.is_available:
            raise serializers.ValidationError("Storage plan is not available")

        quantity = data['quantity_bags']
        
        if quantity < storage_plan.minimum_quantity:
            raise serializers.ValidationError(
                f"Minimum quantity is {storage_plan.minimum_quantity} bags"
            )

        if quantity > storage_plan.maximum_quantity:
            raise serializers.ValidationError(
                f"Maximum quantity is {storage_plan.maximum_quantity} bags"
            )

        if quantity > storage_plan.available_quantity:
            raise serializers.ValidationError(
                f"Only {storage_plan.available_quantity} bags available"
            )

        data['storage_plan'] = storage_plan
        return data

    def create(self, validated_data):
        # Extract the storage_plan object and other fields separately
        storage_plan = validated_data.pop('storage_plan')
        plan_id = validated_data.pop('plan_id')  # Remove plan_id as it's not a model field
        quantity = validated_data['quantity_bags']
        
        # Reserve the quantity
        if not storage_plan.reserve_quantity(quantity):
            raise serializers.ValidationError("Unable to reserve quantity")

        # Calculate investment amounts
        total_investment = storage_plan.buying_price_per_bag * quantity
        projected_returns = storage_plan.projected_selling_price * quantity

        # Create investment with explicit field mapping
        investment = StorageInvestment.objects.create(
            user=self.context['request'].user,
            storage_plan=storage_plan,
            customer_name=validated_data['customer_name'],
            customer_email=validated_data['customer_email'],
            customer_phone=validated_data.get('customer_phone', ''),
            quantity_bags=quantity,
            price_per_bag=storage_plan.buying_price_per_bag,
            total_investment_amount=total_investment,
            projected_selling_price_per_bag=storage_plan.projected_selling_price,
            projected_returns=projected_returns,
            due_date=storage_plan.storage_due_date,
            status='pending'
        )

        return investment




class PaymentTransactionSerializer(serializers.ModelSerializer):
    investment_details = InvestmentSerializer(source='investment', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'reference', 'amount', 'status', 'payment_method',
            'payment_gateway', 'gateway_reference', 'payment_url',
            'paid_at', 'created_at', 'investment_details'
        ]


class DashboardStatsSerializer(serializers.Serializer):
    total_investments = serializers.IntegerField()
    total_invested_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_projected_returns = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_investments = serializers.IntegerField()
    pending_investments = serializers.IntegerField()
    matured_investments = serializers.IntegerField()
    completed_investments = serializers.IntegerField()
    average_roi = serializers.DecimalField(max_digits=5, decimal_places=2)