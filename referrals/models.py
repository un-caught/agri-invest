from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from users.models import Notification

User = get_user_model()

class ReferralCode(models.Model):
    """Model for user referral codes"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_referral_code')
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generate unique referral code
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)
    
    def generate_unique_code(self):
        """Generate a unique referral code"""
        while True:
            # Generate a code based on user's name and random string
            base = self.user.first_name[:3].upper() if self.user.first_name else 'USER'
            random_part = str(uuid.uuid4())[:6].upper()
            code = f"{base}{random_part}"
            
            if not ReferralCode.objects.filter(code=code).exists():
                return code

class Referral(models.Model):
    """Model for tracking referrals"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred_by')
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='referrals')
    
    # Referral details
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.referrer.email} → {self.referred_user.email}"
    
    def activate(self):
        """Activate the referral when referred user makes their first investment"""
        if self.status == 'pending':
            self.status = 'active'
            self.activated_at = timezone.now()
            self.save()
            # Create notification for referrer
            Notification.objects.create(
                user=self.referrer,
                notification_type='referral',
                message=f"Your referral {self.referred_user.email} has made their first investment!"
            )
    
    def complete(self):
        """Mark referral as completed"""
        if self.status == 'active':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()

class ReferralEarning(models.Model):
    """Model for tracking referral earnings"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='earnings')
    investment = models.ForeignKey('investments.Investment', on_delete=models.CASCADE, related_name='referral_earnings')
    
    # Earning details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.referral.referrer.email} - ₦{self.amount}"
    
    def calculate_earning(self):
        """Calculate earning based on investment amount and commission rate"""
        return self.investment.amount * (self.commission_rate / 100)
    
    def mark_as_paid(self):
        """Mark earning as paid"""
        if self.status == 'pending':
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save()
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            # Create notification for referrer
            Notification.objects.create(
                user=self.referral.referrer,
                notification_type='earning',
                message=f"You earned ₦{self.amount} from referral {self.referral.referred_user.email}'s investment."
            )

class ReferralBonus(models.Model):
    """Model for referral bonus settings"""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Bonus conditions
    min_referrals = models.PositiveIntegerField(default=1)
    min_investment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Bonus type
    BONUS_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Investment'),
    ]
    bonus_type = models.CharField(max_length=15, choices=BONUS_TYPES, default='fixed')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Referral Bonuses"
    
    def __str__(self):
        return f"{self.name} - ₦{self.bonus_amount}"
    
    def calculate_bonus(self, investment_amount=None):
        """Calculate bonus amount"""
        if self.bonus_type == 'fixed':
            return self.bonus_amount
        elif self.bonus_type == 'percentage' and investment_amount:
            return investment_amount * (self.bonus_amount / 100)
        return 0
