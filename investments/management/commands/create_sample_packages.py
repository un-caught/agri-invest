from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from investments.models import InvestmentPackage

class Command(BaseCommand):
    help = 'Create sample investment packages'

    def handle(self, *args, **options):
        # Sample investment packages data
        packages_data = [
            {
                'name': 'Maize Farming Project',
                'description': 'High-yield maize cultivation with modern farming techniques and irrigation systems.',
                'category': 'grains',
                'risk_level': 'low',
                'min_amount': 500000,
                'max_amount': 5000000,
                'interest_rate': 25.00,
                'duration_months': 6,
                'total_slots': 100,
                'available_slots': 45,
                'features': [
                    'Modern irrigation systems',
                    'Quality seed selection',
                    'Expert farm management',
                    'Insurance coverage',
                    'Regular progress updates',
                ],
                'image': '🌽',
                'location': 'Kaduna State, Nigeria',
            },
            {
                'name': 'Rice Farming Initiative',
                'description': 'Premium rice cultivation with advanced technology and water management.',
                'category': 'grains',
                'risk_level': 'medium',
                'min_amount': 300000,
                'max_amount': 3000000,
                'interest_rate': 30.00,
                'duration_months': 8,
                'total_slots': 80,
                'available_slots': 32,
                'features': [
                    'Advanced rice varieties',
                    'Water management systems',
                    'Pest control measures',
                    'Quality assurance',
                    'Market access guarantee',
                ],
                'image': '🌾',
                'location': 'Kebbi State, Nigeria',
            },
            {
                'name': 'Cassava Processing Plant',
                'description': 'Cassava farming and processing for value addition and export.',
                'category': 'processing',
                'risk_level': 'medium',
                'min_amount': 1000000,
                'max_amount': 10000000,
                'interest_rate': 35.00,
                'duration_months': 12,
                'total_slots': 50,
                'available_slots': 18,
                'features': [
                    'End-to-end processing',
                    'Value addition',
                    'Export opportunities',
                    'Technology integration',
                    'Quality certification',
                ],
                'image': '🥔',
                'location': 'Ondo State, Nigeria',
            },
            {
                'name': 'Poultry Farming Project',
                'description': 'Modern poultry farming with automated systems and climate control.',
                'category': 'livestock',
                'risk_level': 'low',
                'min_amount': 200000,
                'max_amount': 2000000,
                'interest_rate': 28.00,
                'duration_months': 4,
                'total_slots': 60,
                'available_slots': 28,
                'features': [
                    'Automated feeding systems',
                    'Climate control',
                    'Disease prevention',
                    'Quality feed supply',
                    'Market connections',
                ],
                'image': '🐔',
                'location': 'Ogun State, Nigeria',
            },
            {
                'name': 'Fish Farming Enterprise',
                'description': 'Aquaculture project with sustainable practices and quality monitoring.',
                'category': 'aquaculture',
                'risk_level': 'medium',
                'min_amount': 400000,
                'max_amount': 4000000,
                'interest_rate': 32.00,
                'duration_months': 10,
                'total_slots': 40,
                'available_slots': 22,
                'features': [
                    'Sustainable aquaculture',
                    'Quality fish feed',
                    'Water quality monitoring',
                    'Disease management',
                    'Processing facilities',
                ],
                'image': '🐟',
                'location': 'Lagos State, Nigeria',
            },
            {
                'name': 'Cocoa Farming Project',
                'description': 'Premium cocoa cultivation for export markets with organic certification.',
                'category': 'cash_crops',
                'risk_level': 'high',
                'min_amount': 800000,
                'max_amount': 8000000,
                'interest_rate': 40.00,
                'duration_months': 18,
                'total_slots': 30,
                'available_slots': 15,
                'features': [
                    'Premium cocoa varieties',
                    'Organic certification',
                    'Export market access',
                    'Quality control',
                    'Long-term contracts',
                ],
                'image': '🍫',
                'location': 'Cross River State, Nigeria',
            },
        ]

        # Create packages
        created_count = 0
        for package_data in packages_data:
            # Set dates
            start_date = date.today()
            end_date = start_date + timedelta(days=package_data['duration_months'] * 30)
            
            package, created = InvestmentPackage.objects.get_or_create(
                name=package_data['name'],
                defaults={
                    **package_data,
                    'start_date': start_date,
                    'end_date': end_date,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created package: {package.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Package already exists: {package.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new investment packages')
        ) 