from django.utils import timezone
from django.forms import ValidationError
from rest_framework import serializers
from .models import InvestmentPackage, Investment, Transaction, Portfolio, Payment, WithdrawalRequest, BankAccount
from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from referrals.models import ReferralCode, Referral

User = get_user_model()

class InvestmentPackageSerializer(serializers.ModelSerializer):
    """Serializer for InvestmentPackage model"""
    
    filled_percentage = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    
    class Meta:
        model = InvestmentPackage
        fields = [
            'id', 'name', 'description', 'category', 'risk_level', 'status',
            'min_amount', 'max_amount', 'interest_rate', 'duration_months',
            'total_slots', 'available_slots', 'filled_percentage', 'is_available',
            'features', 'image', 'location', 'start_date', 'end_date',
            'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validate package data"""
        # Ensure max_amount is greater than min_amount
        if 'min_amount' in data and 'max_amount' in data:
            if data['min_amount'] >= data['max_amount']:
                raise serializers.ValidationError(
                    "Maximum amount must be greater than minimum amount"
                )
        
        # Ensure available_slots doesn't exceed total_slots
        if 'total_slots' in data and 'available_slots' in data:
            if data['available_slots'] > data['total_slots']:
                raise serializers.ValidationError(
                    "Available slots cannot exceed total slots"
                )
        
        # Ensure end_date is after start_date
        if 'start_date' in data and 'end_date' in data:
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date"
                )
        
        return data
    
    def create(self, validated_data):
        """Create a new package with proper defaults"""
        # Set available_slots to total_slots if not provided
        if 'available_slots' not in validated_data and 'total_slots' in validated_data:
            validated_data['available_slots'] = validated_data['total_slots']
        
        # Set default features if not provided
        if 'features' not in validated_data:
            validated_data['features'] = []
        
        # Set default image if not provided
        if 'image' not in validated_data:
            validated_data['image'] = '🌱'
        
        return super().create(validated_data)

class InvestmentPackageDetailSerializer(InvestmentPackageSerializer):
    """Detailed serializer for investment package with additional info"""
    
    total_investments = serializers.SerializerMethodField()
    total_amount_invested = serializers.SerializerMethodField()
    
    class Meta(InvestmentPackageSerializer.Meta):
        fields = InvestmentPackageSerializer.Meta.fields + [
            'total_investments', 'total_amount_invested'
        ]
    
    def get_total_investments(self, obj):
        return obj.investments.count()
    
    def get_total_amount_invested(self, obj):
        return sum(inv.amount for inv in obj.investments.all())

class InvestmentSerializer(serializers.ModelSerializer):
    withdrawal_request = serializers.SerializerMethodField()
    package_name = serializers.CharField(source='package.name', read_only=True)
    package_image = serializers.CharField(source='package.image', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    total_return = serializers.ReadOnlyField()

    class Meta:
        model = Investment
        fields = [
            'id', 'package', 'package_name', 'package_image', 'amount',
            'status', 'expected_return', 'actual_return', 'investment_date',
            'start_date', 'end_date', 'completed_date', 'progress_percentage',
            'referred_by', 'is_active', 'is_completed', 'total_return',
            'user_email', 'user_first_name', 'user_last_name', 'withdrawal_request'
        ]
        read_only_fields = ['user', 'expected_return', 'completed_date']

    def get_withdrawal_request(self, obj):
        if obj.withdrawal_request:
            return WithdrawalRequestSerializer(obj.withdrawal_request).data
        return None

    def validate(self, data):
        """
        Validate that actual_return can only be set when status is completed
        and current actual_return is None
        """
        instance = self.instance
        if instance is None:
            return data

        # Check if trying to set actual_return
        if 'actual_return' in data:
            if instance.status != 'completed' and data.get('status') != 'completed':
                raise serializers.ValidationError({
                    'actual_return': "Actual return can only be set for completed investments"
                })
            
            if instance.actual_return is not None:
                raise serializers.ValidationError({
                    'actual_return': "Actual return has already been set"
                })

        return data

    def update(self, instance, validated_data):
        """
        Handle setting completed_date when status changes to completed
        """
        if 'status' in validated_data and validated_data['status'] == 'completed':
            validated_data['completed_date'] = timezone.now()
        
        return super().update(instance, validated_data)


class InvestmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new investments"""
    
    class Meta:
        model = Investment
        fields = ['id', 'package', 'amount', 'referred_by', 'status', 'expected_return', 'investment_date', 'start_date', 'end_date']
        read_only_fields = ['id', 'status', 'expected_return', 'investment_date', 'start_date', 'end_date']
    
    def validate_amount(self, value):
        user = self.context['request'].user
        
        # Check if user has completed KYC
        if not user.is_kyc_complete:
            raise serializers.ValidationError(
                "You must complete your KYC verification before making investments"
            )
        package = self.initial_data.get('package')
        if package:
            try:
                package_obj = InvestmentPackage.objects.get(id=package)
                if value < package_obj.min_amount:
                    raise serializers.ValidationError(
                        f"Amount must be at least {package_obj.min_amount}"
                    )
                if value > package_obj.max_amount:
                    raise serializers.ValidationError(
                        f"Amount cannot exceed {package_obj.max_amount}"
                    )
                if package_obj.available_slots <= 0:
                    raise serializers.ValidationError("This package is fully booked")
            except InvestmentPackage.DoesNotExist:
                raise serializers.ValidationError("Invalid package selected")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        package = validated_data['package']
        
        # Calculate dates
        from datetime import date, timedelta
        start_date = date.today()
        end_date = start_date + timedelta(days=package.duration_months * 30)
        
        # Create investment
        investment = Investment.objects.create(
            user=user,
            package=package,
            amount=validated_data['amount'],
            start_date=start_date,
            end_date=end_date,
            referred_by=validated_data.get('referred_by')
        )
        
        return investment

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""
    
    investment_package_name = serializers.CharField(source='investment.package.name', read_only=True)
    is_credit = serializers.ReadOnlyField()
    is_debit = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'investment', 'investment_package_name', 'transaction_type',
            'amount', 'status', 'payment_method', 'payment_reference',
            'created_at', 'completed_at', 'description', 'is_credit', 'is_debit'
        ]
        read_only_fields = ['user']

class PortfolioSerializer(serializers.ModelSerializer):
    """Serializer for Portfolio model"""
    
    total_portfolio_value = serializers.ReadOnlyField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Portfolio
        fields = [
            'id', 'user_email', 'user_name', 'total_invested', 'total_returns',
            'total_referral_earnings', 'active_investments_count',
            'active_investments_value', 'total_return_percentage',
            'total_portfolio_value', 'last_updated'
        ]
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

class ReferrerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']

class UserInvestmentSummarySerializer(serializers.ModelSerializer):
    """Serializer for user investment summary"""
    
    total_investments = serializers.SerializerMethodField()
    active_investments = serializers.SerializerMethodField()
    total_invested = serializers.SerializerMethodField()
    total_returns = serializers.SerializerMethodField()
    portfolio_value = serializers.SerializerMethodField()
    referred_by = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser',
            'total_investments', 'active_investments', 'total_invested', 
            'total_returns', 'portfolio_value', 'referred_by'
        ]
    
    def get_total_investments(self, obj):
        return obj.investments.count()
    
    def get_active_investments(self, obj):
        return obj.investments.filter(status='active').count()
    
    def get_total_invested(self, obj):
        return sum(inv.amount for inv in obj.investments.all())
    
    def get_total_returns(self, obj):
        return sum(inv.actual_return or 0 for inv in obj.investments.filter(status='completed'))
    
    def get_portfolio_value(self, obj):
        total_invested = self.get_total_invested(obj)
        total_returns = self.get_total_returns(obj)
        return total_invested + total_returns 

    def get_referred_by(self, obj):
        try:
            ref = getattr(obj, 'referred_by', None)
            if ref is None:
                return None
            referrer = getattr(ref, 'referrer', None)
            if referrer is None:
                return None
            return {
                'id': referrer.id,
                'email': referrer.email,
                'first_name': referrer.first_name,
                'last_name': referrer.last_name,
            }
        except Exception:
            return None

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    investment_package_name = serializers.CharField(source='investment.package.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'investment', 'investment_package_name',
            'amount', 'currency', 'status', 'paystack_reference', 
            'paystack_access_code', 'paystack_authorization_url',
            'payment_method', 'created_at', 'updated_at', 'paid_at',
            'is_successful', 'is_pending'
        ]
        read_only_fields = [
            'user', 'paystack_access_code', 
            'paystack_authorization_url', 'status', 'paid_at'
        ]

class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new payments"""
    
    class Meta:
        model = Payment
        fields = ['investment', 'amount', 'currency', 'payment_method']
    
    def validate(self, data):
        user = self.context['request'].user
        investment_data = data.get('investment')
        amount = data.get('amount')
        
        # Handle both investment ID and investment object
        if hasattr(investment_data, 'id'):
            # If investment_data is an Investment object, get its ID
            investment_id = investment_data.id
        else:
            # If investment_data is already an ID
            investment_id = investment_data
        
        # Validate investment exists and belongs to user
        try:
            investment = Investment.objects.get(id=investment_id, user=user)
        except Investment.DoesNotExist:
            raise serializers.ValidationError("Investment not found or does not belong to you")
        
        # Validate amount matches investment amount
        if amount != investment.amount:
            raise serializers.ValidationError("Payment amount must match investment amount")
        
        # Store the investment object for use in create method
        data['_investment_object'] = investment
        
        return data
    
    def create(self, validated_data):
        import time
        
        # Get the investment object from validated data
        investment = validated_data.pop('_investment_object')
        
        # Generate unique reference
        reference = f"INV_{investment.id}_{int(time.time())}"
        
        # Create payment with reference
        payment = Payment.objects.create(
            user=self.context['request'].user,
            investment=investment,
            amount=validated_data['amount'],
            currency=validated_data.get('currency', 'NGN'),
            payment_method=validated_data.get('payment_method', 'card'),
            paystack_reference=reference,
        )
        
        return payment 

class CustomUserCreateSerializer(DjoserUserCreateSerializer):
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(DjoserUserCreateSerializer.Meta):
        fields = DjoserUserCreateSerializer.Meta.fields + ('referral_code',)

    def create(self, validated_data):
        referral_code_value = validated_data.pop('referral_code', None)
        user = super().create(validated_data)

        # Auto-create a referral code for the new user
        ReferralCode.objects.get_or_create(user=user)

        # If a referral code was provided, create a Referral object
        if referral_code_value:
            try:
                ref_code = ReferralCode.objects.get(code=referral_code_value, is_active=True)
                # Prevent self-referral
                if ref_code.user != user:
                    Referral.objects.get_or_create(
                        referrer=ref_code.user,
                        referred_user=user,
                        referral_code=ref_code,
                        defaults={
                            'status': 'pending',
                            'commission_rate': 5.0,
                        }
                    )
            except ReferralCode.DoesNotExist:
                pass  # Optionally, raise a validation error
        return user 


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'bank_name', 'account_name', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    bank_account = BankAccountSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'bank_account']
        
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    investments = InvestmentSerializer(many=True, read_only=True)
    available_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'investments', 'amount', 'requested_amount', 'status', 
            'type', 'request_date', 'processed_date', 'admin_notes',
            'available_balance', 'user'
        ]
        read_only_fields = ['user', 'amount', 'status', 'request_date', 'processed_date', 'admin_notes']
    
    def get_available_balance(self, obj):
        if hasattr(obj, 'available_balance'):
            return obj.available_balance
        return None

class CreateWithdrawalRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=WithdrawalRequest.TYPE_CHOICES)
    investment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    
    def validate(self, data):
        user = self.context['request'].user
        completed_investments = Investment.objects.filter(
            user=user,
            status='completed',
            withdrawal_request__isnull=True
        )
        
        if not completed_investments.exists():
            raise serializers.ValidationError("No completed investments available for withdrawal")
        
        return data


class InvestmentForceApproveSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=255)
    
    def validate_reason(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Please provide a detailed reason for force approval")
        return value