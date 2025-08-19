# Generated manually for initial investment models

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvestmentPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('category', models.CharField(choices=[('grains', 'Grains'), ('cash_crops', 'Cash Crops'), ('livestock', 'Livestock'), ('aquaculture', 'Aquaculture'), ('processing', 'Processing'), ('horticulture', 'Horticulture')], max_length=20)),
                ('risk_level', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=10)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('completed', 'Completed'), ('suspended', 'Suspended')], default='active', max_length=15)),
                ('min_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('max_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('duration_months', models.PositiveIntegerField()),
                ('total_slots', models.PositiveIntegerField()),
                ('available_slots', models.PositiveIntegerField()),
                ('features', models.JSONField(default=list)),
                ('image', models.CharField(default='🌱', max_length=10)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('failed', 'Failed')], default='pending', max_length=15)),
                ('expected_return', models.DecimalField(decimal_places=2, max_digits=12)),
                ('actual_return', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('investment_date', models.DateTimeField(auto_now_add=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('completed_date', models.DateTimeField(blank=True, null=True)),
                ('progress_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to='investments.investmentpackage')),
                ('referred_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referred_investments', to='users.user')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to='users.user')),
            ],
            options={
                'ordering': ['-investment_date'],
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('investment', 'Investment'), ('withdrawal', 'Withdrawal'), ('return', 'Return'), ('referral_bonus', 'Referral Bonus'), ('refund', 'Refund')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=15)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('payment_reference', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('investment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='investments.investment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='users.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_invested', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_returns', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_referral_earnings', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('active_investments_count', models.PositiveIntegerField(default=0)),
                ('active_investments_value', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_return_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='portfolio', to='users.user')),
            ],
            options={
                'verbose_name_plural': 'Portfolios',
            },
        ),
    ] 