# ecommerce/serializers.py
from rest_framework import serializers
from .models import Product, Order, OrderItem, Cart, CartItem

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'image': {'required': False}  # Make image not required for updates
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.image:
            data['image'] = request.build_absolute_uri(instance.image.url)
        return data

    def update(self, instance, validated_data):
        # Handle the image separately
        image = validated_data.pop('image', None)
        
        if image is not None:
            # If a new image was provided, update it
            instance.image = image
        # If image is None (not provided in the update), keep the existing one
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
        required=False  # Not required for updates if not changing product
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_id', 'quantity', 'price']
        extra_kwargs = {
            'price': {'read_only': True}  # Typically price shouldn't be editable
        }


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    # Add writeable fields for order items if you want to update them
    order_items = OrderItemSerializer(
        many=True, 
        write_only=True, 
        required=False,
        source='items'
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'reference', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'address', 'city', 'state', 'full_address',
            'total_amount', 'status', 'created_at', 'items', 'order_items'
        ]
        extra_kwargs = {
            'reference': {'read_only': True},
            'created_at': {'read_only': True},
            'full_address': {'read_only': True},
            'total_amount': {'read_only': True},  # Should be calculated
        }
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def update(self, instance, validated_data):
        # Handle order items if provided
        items_data = validated_data.pop('items', None)
        
        # Update order fields
        instance = super().update(instance, validated_data)
        
        if items_data is not None:
            # Clear existing items and create new ones
            instance.items.all().delete()
            for item_data in items_data:
                OrderItem.objects.create(order=instance, **item_data)
        
        # Recalculate total amount (if items were updated)
        instance.total_amount = instance.total_amount
        instance.save()
        
        return instance
    
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        write_only=True,
        source='product'
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'updated_at']
        read_only_fields = ['user']