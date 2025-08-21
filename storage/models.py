from django.db import models

from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

User = get_user_model()

class StoragePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=200)
    # product_image = models.ImageField(upload_to='storage_plans/', blank=True, null=True)
    product_image = CloudinaryField('image', blank=True, null=True)
    description = models.TextField()
    buying_price_per_bag = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    projected_selling_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    storage_due_date = models.DateField()
    available_quantity = models.PositiveIntegerField(default=0)
    minimum_quantity = models.PositiveIntegerField(default=1)
    maximum_quantity = models.PositiveIntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    storage_cost_per_bag = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Storage Plan"
        verbose_name_plural = "Storage Plans"

    def __str__(self):
        return f"{self.product_name} - ₦{self.buying_price_per_bag}/bag"

    @property
    def roi_percentage(self):
        """Calculate Return on Investment percentage"""
        if self.buying_price_per_bag > 0:
            return round(((self.projected_selling_price - self.buying_price_per_bag) / self.buying_price_per_bag) * 100, 1)
        return 0

    @property
    def is_available(self):
        """Check if plan is still available for investment"""
        return self.is_active and self.available_quantity > 0

    def reserve_quantity(self, quantity):
        """Reserve quantity for purchase"""
        if self.available_quantity >= quantity:
            self.available_quantity -= quantity
            self.save()
            return True
        return False

    def release_quantity(self, quantity):
        """Release reserved quantity back to available"""
        self.available_quantity += quantity
        self.save()


class StorageInvestment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active Storage'),
        ('matured', 'Ready for Sale'),
        ('completed', 'Sold & Paid'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='storageinvestments')
    storage_plan = models.ForeignKey(StoragePlan, on_delete=models.CASCADE, related_name='storageinvestments')
    
    # Customer Information
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Investment Details
    quantity_bags = models.PositiveIntegerField()
    price_per_bag = models.DecimalField(max_digits=12, decimal_places=2)
    total_investment_amount = models.DecimalField(max_digits=15, decimal_places=2)
    projected_selling_price_per_bag = models.DecimalField(max_digits=12, decimal_places=2)
    projected_returns = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Status and Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    purchase_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    matured_date = models.DateTimeField(blank=True, null=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    
    # Payment Information
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Investment"
        verbose_name_plural = "Investments"

    def __str__(self):
        return f"{self.customer_name} - {self.storage_plan.product_name} ({self.quantity_bags} bags)"

    @property
    def product_name(self):
        return self.storage_plan.product_name

    @property
    def product_image(self):
        return self.storage_plan.product_image.url if self.storage_plan.product_image else None

    @property
    def roi_percentage(self):
        """Calculate actual ROI percentage"""
        if self.total_investment_amount > 0:
            return round(((self.projected_returns - self.total_investment_amount) / self.total_investment_amount) * 100, 1)
        return 0

    @property
    def days_remaining(self):
        """Calculate days remaining until due date"""
        from datetime import date
        if self.due_date:
            diff = self.due_date - date.today()
            return max(0, diff.days)
        return 0

    @property
    def progress_percentage(self):
        """Calculate storage progress percentage"""
        from datetime import date
        if self.purchase_date and self.due_date:
            total_days = (self.due_date - self.purchase_date.date()).days
            elapsed_days = (date.today() - self.purchase_date.date()).days
            if total_days > 0:
                return min(100, max(0, (elapsed_days / total_days) * 100))
        return 0

    def save(self, *args, **kwargs):
        from datetime import date
        # Calculate projected returns if not set
        if not self.projected_returns:
            self.projected_returns = self.quantity_bags * self.projected_selling_price_per_bag
        
        # Set due date from storage plan if not set
        if not self.due_date and self.storage_plan:
            self.due_date = self.storage_plan.storage_due_date

        # Auto-update status based on dates
        today = date.today()
        if self.due_date:
            if self.status == 'active' and today >= self.due_date:
                self.status = 'matured'
            elif self.status == 'pending' and today >= self.due_date:
                self.status = 'cancelled'
                
            
        super().save(*args, **kwargs)


class PaymentTransaction(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investment = models.OneToOneField(StorageInvestment, on_delete=models.CASCADE, related_name='payment_transaction')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    payment_gateway = models.CharField(max_length=50, default='paystack')
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_url = models.URLField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"


class StorageUpdate(models.Model):
    UPDATE_TYPES = [
        ('storage_start', 'Storage Started'),
        ('quality_check', 'Quality Check'),
        ('price_update', 'Price Update'),
        ('maturity', 'Product Matured'),
        ('sale_complete', 'Sale Completed'),
        ('general', 'General Update'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investment = models.ForeignKey(StorageInvestment, on_delete=models.CASCADE, related_name='updates')
    update_type = models.CharField(max_length=20, choices=UPDATE_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    current_market_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    # image = models.ImageField(upload_to='storage_updates/', blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.investment.customer_name} - {self.title}"