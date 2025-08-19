from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from django.forms import ValidationError
from referrals.models import Referral, ReferralEarning

User = get_user_model()

class InvestmentPackage(models.Model):
    """Model for investment packages/opportunities"""
    
    CATEGORY_CHOICES = [
        ('grains', 'Grains'),
        ('cash_crops', 'Cash Crops'),
        ('livestock', 'Livestock'),
        ('aquaculture', 'Aquaculture'),
        ('processing', 'Processing'),
        ('horticulture', 'Horticulture'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    
    # Financial details
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    duration_months = models.PositiveIntegerField()
    
    # Capacity
    total_slots = models.PositiveIntegerField()
    available_slots = models.PositiveIntegerField()
    
    # Features and details
    features = models.JSONField(default=list)
    image = models.CharField(max_length=10, default='🌱')  # Emoji or icon
    location = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def filled_percentage(self):
        """Calculate the percentage of slots filled"""
        if self.total_slots == 0:
            return 0
        return ((self.total_slots - self.available_slots) / self.total_slots) * 100
    
    @property
    def is_available(self):
        """Check if the package is available for investment"""
        return self.status == 'active' and self.available_slots > 0

class Investment(models.Model):
    """Model for user investments"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    package = models.ForeignKey(InvestmentPackage, on_delete=models.CASCADE, related_name='investments')
    
    # Investment details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Returns
    expected_return = models.DecimalField(max_digits=12, decimal_places=2)
    actual_return = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Dates
    investment_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Progress tracking
    progress_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    withdrawal_request = models.ForeignKey(
        'WithdrawalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investment_withdrawals'
    )
    
    # Referral tracking
    referred_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='referred_investments'
    )
    
    class Meta:
        ordering = ['-investment_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.package.name} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Calculate expected return on save
        if not self.expected_return:
            package = self.package
            if package:
                self.expected_return = self.amount * (package.interest_rate / 100)
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Referral logic: Only on creation
        if is_new:
            # Check if this user has a pending referral
            try:
                referral = Referral.objects.get(referred_user=self.user, status='pending')
                # Activate referral
                referral.activate()
                # Create referral earning for this investment
                earning_amount = self.amount * (referral.commission_rate / 100)
                ReferralEarning.objects.create(
                    referral=referral,
                    investment=self,
                    amount=earning_amount,
                    commission_rate=referral.commission_rate,
                    status='pending',
                )
            except Referral.DoesNotExist:
                pass
    
    @property
    def is_active(self):
        """Check if investment is currently active"""
        return self.status == 'active'
    
    @property
    def is_completed(self):
        """Check if investment is completed"""
        return self.status == 'completed'
    
    @property
    def total_return(self):
        """Calculate total return (principal + interest)"""
        return self.amount + (self.actual_return or self.expected_return)
    
    # def clean(self):
    #     # Validate investment state
    #     if self.status == 'active':
    #         # Check for existing active investments in same package
    #         existing = Investment.objects.filter(
    #             user=self.user,
    #             package=self.package,
    #             status='active'
    #         ).exclude(id=self.id)
            
    #         if existing.exists():
    #             raise ValidationError('You already have an active investment in this package')

    def can_withdraw(self):
        """Check if investment is eligible for withdrawal"""
        return (
            self.status == 'completed' and 
            not self.withdrawal_request and
            self.actual_return is not None
        )

    def get_latest_payment(self):
        """Get the most recent payment for this investment"""
        return self.payments.order_by('-created_at').first()

class Transaction(models.Model):
    """Model for investment transactions"""
    
    TYPE_CHOICES = [
        ('investment', 'Investment'),
        ('withdrawal', 'Withdrawal'),
        ('return', 'Return'),
        ('referral_bonus', 'Referral Bonus'),
        ('refund', 'Refund'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Payment details
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Description
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount}"
    
    @property
    def is_credit(self):
        """Check if transaction adds money to user account"""
        return self.transaction_type in ['return', 'referral_bonus', 'refund']
    
    @property
    def is_debit(self):
        """Check if transaction removes money from user account"""
        return self.transaction_type in ['investment', 'withdrawal']

class Portfolio(models.Model):
    """Model for user portfolio summary"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='portfolio')
    
    # Portfolio totals
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_returns = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_referral_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Active investments
    active_investments_count = models.PositiveIntegerField(default=0)
    active_investments_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Performance
    total_return_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Last updated
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Portfolios"
    
    def __str__(self):
        return f"Portfolio - {self.user.email}"
    
    @property
    def total_portfolio_value(self):
        """Calculate total portfolio value"""
        return self.total_invested + self.total_returns + self.total_referral_earnings
    
    def update_portfolio(self):
        """Update portfolio based on current investments and transactions"""
        # Calculate totals from investments
        investments = self.user.investments.all()
        self.total_invested = sum(inv.amount for inv in investments)
        self.total_returns = sum(inv.actual_return or 0 for inv in investments if inv.is_completed)
        
        # Calculate active investments
        active_investments = investments.filter(status='active')
        self.active_investments_count = active_investments.count()
        self.active_investments_value = sum(inv.amount for inv in active_investments)
        
        # Calculate referral earnings
        referral_transactions = self.user.transactions.filter(
            transaction_type='referral_bonus',
            status='completed'
        )
        self.total_referral_earnings = sum(t.amount for t in referral_transactions)
        
        # Calculate return percentage
        if self.total_invested > 0:
            self.total_return_percentage = (self.total_returns / self.total_invested) * 100
        
        self.save()

class Payment(models.Model):
    """Model for payment transactions via Paystack"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Paystack details
    paystack_reference = models.CharField(max_length=100, unique=True)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    paystack_authorization_url = models.URLField(blank=True)
    
    # Payment method
    payment_method = models.CharField(max_length=50, default='card')  # card, bank, etc.
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} - {self.status}"
    
    @property
    def is_successful(self):
        return self.status == 'success'
    
    @property
    def is_pending(self):
        return self.status == 'pending'



# Add to models.py
class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('full', 'Full Amount (Principal + Interest)'),
        ('interest', 'Interest Only'),
        ('reinvest', 'Reinvest Interest'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    investments = models.ManyToManyField(Investment, related_name='withdrawal_requests', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    request_date = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.requested_amount:
            self.requested_amount = self.amount
        super().save(*args, **kwargs)


class BankAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_account')
    account_number = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=30)  
    account_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ['user', 'account_number']

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"
