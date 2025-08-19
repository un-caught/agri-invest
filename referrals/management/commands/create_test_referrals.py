from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from referrals.models import ReferralCode, Referral, ReferralEarning, ReferralBonus
from investments.models import InvestmentPackage, Investment
from decimal import Decimal
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test referral data for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of test users to create'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        
        self.stdout.write(f"Creating {num_users} test users with referral data...")
        
        # Create test users
        users = []
        for i in range(num_users):
            user = User.objects.create_user(
                email=f'testuser{i+1}@example.com',
                first_name=f'Test{i+1}',
                last_name='User',
                password='testpass123',
                is_active=True,
                is_verified=True,
            )
            users.append(user)
            self.stdout.write(f"Created user: {user.email}")
        
        # Create referral codes for all users
        referral_codes = []
        for user in users:
            referral_code = ReferralCode.objects.create(user=user)
            referral_codes.append(referral_code)
            self.stdout.write(f"Created referral code: {referral_code.code} for {user.email}")
        
        # Create some referrals (user 1 refers user 2, user 2 refers user 3, etc.)
        referrals = []
        for i in range(len(users) - 1):
            referrer = users[i]
            referred_user = users[i + 1]
            
            referral = Referral.objects.create(
                referrer=referrer,
                referred_user=referred_user,
                referral_code=referral_codes[i],
                status='active',
                commission_rate=Decimal('5.00'),
                activated_at=date.today() - timedelta(days=random.randint(1, 30))
            )
            referrals.append(referral)
            self.stdout.write(f"Created referral: {referrer.email} → {referred_user.email}")
        
        # Create some investment packages if they don't exist
        packages = []
        if not InvestmentPackage.objects.exists():
            package_data = [
                {
                    'name': 'Maize Farming Investment',
                    'description': 'High-yield maize farming with modern techniques',
                    'category': 'grains',
                    'risk_level': 'medium',
                    'min_amount': Decimal('100000'),
                    'max_amount': Decimal('1000000'),
                    'interest_rate': Decimal('15.00'),
                    'duration_months': 6,
                    'total_slots': 100,
                    'available_slots': 80,
                    'features': ['Organic farming', 'Insurance coverage', 'Regular updates'],
                    'image': '🌽',
                    'location': 'Kaduna State',
                    'start_date': date.today(),
                    'end_date': date.today() + timedelta(days=180),
                },
                {
                    'name': 'Fish Farming Enterprise',
                    'description': 'Sustainable aquaculture with premium fish species',
                    'category': 'aquaculture',
                    'risk_level': 'low',
                    'min_amount': Decimal('50000'),
                    'max_amount': Decimal('500000'),
                    'interest_rate': Decimal('12.00'),
                    'duration_months': 4,
                    'total_slots': 50,
                    'available_slots': 30,
                    'features': ['Water quality monitoring', 'Expert management', 'Market access'],
                    'image': '🐟',
                    'location': 'Lagos State',
                    'start_date': date.today(),
                    'end_date': date.today() + timedelta(days=120),
                }
            ]
            
            for data in package_data:
                package = InvestmentPackage.objects.create(**data)
                packages.append(package)
                self.stdout.write(f"Created package: {package.name}")
        else:
            packages = list(InvestmentPackage.objects.all()[:2])
        
        # Create some investments and referral earnings
        for i, referral in enumerate(referrals):
            if packages:
                package = random.choice(packages)
                amount = Decimal(random.randint(100000, 500000))
                
                investment = Investment.objects.create(
                    user=referral.referred_user,
                    package=package,
                    amount=amount,
                    status='active',
                    start_date=date.today() - timedelta(days=random.randint(1, 30)),
                    end_date=date.today() + timedelta(days=package.duration_months * 30),
                    referred_by=referral.referrer,
                )
                
                # Create referral earning
                earning_amount = amount * (referral.commission_rate / 100)
                ReferralEarning.objects.create(
                    referral=referral,
                    investment=investment,
                    amount=earning_amount,
                    commission_rate=referral.commission_rate,
                    status='paid' if random.choice([True, False]) else 'pending',
                    paid_at=date.today() - timedelta(days=random.randint(1, 15)) if random.choice([True, False]) else None,
                )
                
                self.stdout.write(f"Created investment: {investment.amount} for {investment.user.email}")
        
        # Create some referral bonuses
        bonus_data = [
            {
                'name': 'First Referral Bonus',
                'description': 'Get a bonus for your first successful referral',
                'min_referrals': 1,
                'min_investment_amount': Decimal('100000'),
                'bonus_amount': Decimal('5000'),
                'bonus_type': 'fixed',
            },
            {
                'name': 'High Value Referral',
                'description': 'Bonus for referrals with high investment amounts',
                'min_referrals': 1,
                'min_investment_amount': Decimal('500000'),
                'bonus_amount': Decimal('10.00'),
                'bonus_type': 'percentage',
            }
        ]
        
        for data in bonus_data:
            bonus, created = ReferralBonus.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f"Created bonus: {bonus.name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test referral data:\n'
                f'- {len(users)} users\n'
                f'- {len(referral_codes)} referral codes\n'
                f'- {len(referrals)} referrals\n'
                f'- {Investment.objects.count()} investments\n'
                f'- {ReferralEarning.objects.count()} referral earnings'
            )
        ) 