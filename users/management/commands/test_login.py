from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User

class Command(BaseCommand):
    help = 'Test user login and JWT token creation'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email')
        parser.add_argument('password', type=str, help='User password')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        
        self.stdout.write(f"Testing login for: {email}")
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f"✓ User found: {user.email}")
            self.stdout.write(f"  - is_active: {user.is_active}")
            self.stdout.write(f"  - is_verified: {user.is_verified}")
            self.stdout.write(f"  - is_staff: {user.is_staff}")
            self.stdout.write(f"  - is_superuser: {user.is_superuser}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ User not found: {email}"))
            return
        
        # Test authentication
        authenticated_user = authenticate(email=email, password=password)
        if authenticated_user:
            self.stdout.write(self.style.SUCCESS("✓ Authentication successful"))
            
            # Test JWT token creation
            try:
                refresh = RefreshToken.for_user(authenticated_user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                
                self.stdout.write(self.style.SUCCESS("✓ JWT tokens created successfully"))
                self.stdout.write(f"  - Access token: {access_token[:50]}...")
                self.stdout.write(f"  - Refresh token: {refresh_token[:50]}...")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ JWT token creation failed: {e}"))
        else:
            self.stdout.write(self.style.ERROR("✗ Authentication failed - invalid credentials")) 