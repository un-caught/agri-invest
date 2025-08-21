from asyncio.log import logger
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from social_django.utils import load_strategy, load_backend
from social_core.exceptions import MissingBackend, AuthTokenError, AuthForbidden
from django.conf import settings
import json
import requests
from urllib.parse import urlencode
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from .models import Notification
from .serializers import NotificationSerializer, UserSerializer ,UserCreateSerializer, UserUpdateSerializer, UserKYCStatusSerializer
from referrals.models import ReferralCode, Referral  # Ensure correct import
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from investments.models import Investment
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce

from django.conf import settings



@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_login(request):
    """
    Initiate Google OAuth login - redirect directly to Google
    """
    try:
        # Build Google OAuth URL manually
        params = {
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE),
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
        
        print(f"Debug - Generated auth URL: {auth_url}")
        
        # Redirect directly to Google OAuth
        return redirect(auth_url)
    except Exception as e:
        print(f"Debug - Error in google_oauth_login: {e}")
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """
    Handle Google OAuth callback and return JWT tokens
    """
    try:
        # Debug: Print request parameters
        print(f"Debug - Request GET params: {request.GET}")
        print(f"Debug - Request method: {request.method}")
        
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        if not code:
            return Response({'error': 'No authorization code received'}, status=400)
        
        # Exchange code for access token
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
        }
        
        print(f"Debug - Exchanging code for token...")
        token_response = requests.post(token_url, data=token_data)
        
        if not token_response.ok:
            print(f"Debug - Token exchange failed: {token_response.text}")
            return Response({'error': 'Failed to exchange code for token'}, status=400)
        
        token_info = token_response.json()
        access_token = token_info.get('access_token')
        
        if not access_token:
            return Response({'error': 'No access token received'}, status=400)
        
        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print(f"Debug - Getting user info...")
        user_response = requests.get(user_info_url, headers=headers)
        
        if not user_response.ok:
            print(f"Debug - User info request failed: {user_response.text}")
            return Response({'error': 'Failed to get user info'}, status=400)
        
        user_info = user_response.json()
        print(f"Debug - User info: {user_info}")
        
        # Get or create user
        User = get_user_model()
        
        email = user_info.get('email')
        if not email:
            return Response({'error': 'No email received from Google'}, status=400)
        
        # Try to get existing user
        try:
            user = User.objects.get(email=email)
            print(f"Debug - Found existing user: {user.email}")
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                email=email,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
                is_active=True,
                is_verified=True,  # Google users are pre-verified
            )
            print(f"Debug - Created new user: {user.email}")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        }
        
        print(f"Debug - Response data: {response_data}")
        return Response(response_data)
            
    except Exception as e:
        print(f"Debug - General error: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': 'An error occurred during authentication'}, status=500)

def custom_activation(request, uid, token):
    """
    Custom activation view that redirects to frontend
    """
    try:
        # Import here to avoid circular imports
        from djoser.utils import decode_uid
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Decode the user ID
        user_id = decode_uid(uid)
        user = User.objects.get(id=user_id)
        
        # Activate the user
        user.is_active = True
        user.is_verified = True
        user.save()
        
        print(f"User {user.email} activated successfully")
        
        # Success - redirect to frontend login with success message
        # return redirect('http://localhost:5173/login?activated=true')
        return redirect(f'{settings.FRONTEND_URL}/login?activated=true')
            
    except Exception as e:
        print(f"Activation error: {e}")
        # return redirect('http://localhost:5173/login?activated=false')
        return redirect(f'{settings.FRONTEND_URL}/login?activated=false')

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        # Mark as read when updated
        instance = serializer.save()
        if not instance.is_read:
            instance.mark_as_read()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_referral_code(request):
    user = request.user
    if hasattr(user, 'referred_by'):
        return Response({'error': 'You already have a referral.'}, status=400)
    # Remove the check that blocks after investing
    code = request.data.get('referral_code')
    if not code:
        return Response({'error': 'Referral code is required.'}, status=400)
    try:
        ref_code = ReferralCode.objects.get(code=code, is_active=True)  # type: ignore
        if ref_code.user == user:
            return Response({'error': 'You cannot refer yourself.'}, status=400)
        Referral.objects.get_or_create(  # type: ignore
            referrer=ref_code.user,
            referred_user=user,
            referral_code=ref_code,
            defaults={
                'status': 'pending',
                'commission_rate': 5.0,
            }
        )
        return Response({'success': 'Referral code applied successfully.'})
    except ReferralCode.DoesNotExist:  # type: ignore
        return Response({'error': 'Invalid referral code.'}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_kyc(request):
    user = request.user
    data = request.data
    
    required_fields = [
        'phone', 'date_of_birth', 'gender', 
        'id_type', 'id_number', 'address',
        'occupation', 'nationality'
    ]
    
    # Validate required fields
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return Response(
            {'error': f'Missing required fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Update user fields
        user.phone = data['phone']
        user.date_of_birth = data['date_of_birth']
        user.gender = data['gender']
        user.id_type = data['id_type']
        user.id_number = data['id_number']
        user.address = data['address']
        user.occupation = data['occupation']
        user.nationality = data['nationality']
        user.is_kyc_complete = True
        
        user.save()
        
        return Response(
            {'success': 'KYC information submitted successfully'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    Get current user's profile information
    """
    user = request.user
    
    try:
        
        # Get user's investments if you have an Investment model
        investments = []
        if hasattr(user, 'investments'):
            investments = [
                {
                    'id': inv.id,
                    'amount': str(inv.amount) if hasattr(inv, 'amount') else None,
                    'date_created': inv.created_at.isoformat() if hasattr(inv, 'created_at') else None,
                    # Add other investment fields as needed
                }
                for inv in user.investments.all()
            ]
        
        profile_data = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            
            # KYC Information
            'is_kyc_complete': user.is_kyc_complete,
            'phone': getattr(user, 'phone', ''),
            'date_of_birth': user.date_of_birth.isoformat() if getattr(user, 'date_of_birth', None) else None,
            'gender': getattr(user, 'gender', ''),
            'id_type': getattr(user, 'id_type', ''),
            'id_number': getattr(user, 'id_number', ''),
            'address': getattr(user, 'address', ''),
            'occupation': getattr(user, 'occupation', ''),
            'nationality': getattr(user, 'nationality', ''),
            
            # Other Data
            'investments': investments,
        }
        
        return Response(profile_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch profile: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
User = get_user_model()

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filtering
        role = request.query_params.get('role', None)
        if role == 'admin':
            queryset = queryset.filter(is_superuser=True)
        elif role == 'staff':
            queryset = queryset.filter(is_staff=True, is_superuser=False)
        elif role == 'user':
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        
        status = request.query_params.get('status', None)
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        kyc_status = request.query_params.get('kyc_status', None)
        if kyc_status == 'verified':
            queryset = queryset.filter(is_kyc_complete=True)
        elif kyc_status == 'unverified':
            queryset = queryset.filter(is_kyc_complete=False)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_kyc_status(self, request, pk=None):
        user = self.get_object()
        serializer = UserKYCStatusSerializer(data=request.data)
        if serializer.is_valid():
            user.is_kyc_complete = serializer.validated_data['is_kyc_complete']
            user.save()
            return Response({'status': 'KYC status updated'})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def force_password_reset(self, request, pk=None):
        user = self.get_object()
        new_password = get_random_string(12)
        user.set_password(new_password)
        user.save()
        
        # Send email with new password
        send_mail(
            'Your password has been reset',
            f'Your new password is: {new_password}\n\nPlease change it after logging in.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response({'status': 'password reset initiated'})

    @action(detail=True, methods=['post'])
    def impersonate(self, request, pk=None):
        user = self.get_object()
        if user.is_superuser:
            return Response(
                {'error': 'Cannot impersonate other admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate a token for impersonation (you'll need to implement this)
        # token = generate_impersonation_token(user)
        # return Response({'token': token})
        
        # For now, just return user details
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'admin_users': User.objects.filter(is_superuser=True).count(),
            'kyc_verified': User.objects.filter(is_kyc_complete=True).count(),
            'total_active_investments': Investment.objects.filter(status='active').count(),
            'total_completed_investments': Investment.objects.filter(status='completed').count(),
            'total_investment_value': Investment.objects.aggregate(
                total=Coalesce(Sum('amount'), Decimal(0))
            )['total']
        }
        return Response(stats)

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Annotate with investment stats
        queryset = queryset.annotate(
            active_investments_count=Count(
                'investments',
                filter=Q(investments__status='active')
            ),
            completed_investments_count=Count(
                'investments',
                filter=Q(investments__status='completed')
            ),
            total_invested=Coalesce(
                Sum('investments__amount'),
                Decimal(0)
            )
        )
        
        # Existing filtering logic
        role = self.request.query_params.get('role')
        if role == 'admin':
            queryset = queryset.filter(is_superuser=True)
        elif role == 'staff':
            queryset = queryset.filter(is_staff=True, is_superuser=False)
        elif role == 'user':
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        
        status = self.request.query_params.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        kyc_status = self.request.query_params.get('kyc_status')
        if kyc_status == 'verified':
            queryset = queryset.filter(is_kyc_complete=True)
        elif kyc_status == 'unverified':
            queryset = queryset.filter(is_kyc_complete=False)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(phone__icontains=search)
            )
            
        return queryset


from investments.models import BankAccount
from investments.serializers import BankAccountSerializer

# @api_view(['GET', 'POST', 'PUT', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def bank_account(request):
#     user = request.user
    
#     try:
#         if request.method == 'GET':
#             # Get existing bank account
#             try:
#                 account = BankAccount.objects.get(user=user)
#                 serializer = BankAccountSerializer(account)
#                 return Response(serializer.data)
#             except BankAccount.DoesNotExist:
#                 return Response({'account': None})
                
#         elif request.method in ['POST', 'PUT', 'PATCH']:
#             # Create or update bank account
#             data = request.data.copy()
#             data['user'] = user.id
            
#             # Validate required fields
#             if not all([data.get('account_number'), data.get('bank_name')]):
#                 return Response(
#                     {'error': 'Account number and bank name are required'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             try:
#                 account = BankAccount.objects.get(user=user)
#                 serializer = BankAccountSerializer(account, data=data)
#             except BankAccount.DoesNotExist:
#                 serializer = BankAccountSerializer(data=data)
                
#             if serializer.is_valid():
#                 serializer.save()
#                 return Response(serializer.data)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
#     except Exception as e:
#         return Response(
#             {'error': str(e)},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )

@api_view(['GET', 'POST', 'PATCH'])
@permission_classes([IsAuthenticated])
def bank_account(request):
    user = request.user
    
    try:
        if request.method == 'GET':
            try:
                account = BankAccount.objects.get(user=user)
                serializer = BankAccountSerializer(account)
                return Response(serializer.data)
            except BankAccount.DoesNotExist:
                return Response({'exists': False}, status=status.HTTP_200_OK)  # Changed from 404 to 200
                
        elif request.method == 'POST':
            # Check if account exists
            if BankAccount.objects.filter(user=user).exists():
                return Response(
                    {'error': 'Bank account already exists. Use PATCH to update.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate required fields
            required_fields = ['account_number', 'bank_name']
            if not all(field in request.data for field in required_fields):
                return Response(
                    {'error': f'Missing required fields: {", ".join(required_fields)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new account with user
            data = request.data.copy()
            data['user'] = user.id  # Ensure user_id is set
            
            serializer = BankAccountSerializer(data=data)
            if serializer.is_valid():
                serializer.save(user=user)  # Explicitly set user
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'PATCH':
            try:
                account = BankAccount.objects.get(user=user)
                serializer = BankAccountSerializer(
                    account, 
                    data=request.data, 
                    partial=True
                )
                
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
            except BankAccount.DoesNotExist:
                return Response(
                    {'error': 'Bank account not found. Use POST to create.'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
    except Exception as e:
        logger.error(f"Bank account error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

from django.views.generic import TemplateView

class FrontendAppView(TemplateView):
    template_name = "index.html"
