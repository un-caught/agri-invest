from django.core.management.base import BaseCommand
from users.models import User
from referrals.models import ReferralCode

class Command(BaseCommand):
    help = 'Generate referral codes for all users who do not have one.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0
        for user in users:
            if not hasattr(user, 'user_referral_code'):
                ReferralCode.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f"Created referral code for {user.email}"))
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Done. Created {created_count} referral codes.")) 