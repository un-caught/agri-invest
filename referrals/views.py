from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import ReferralCode, Referral, ReferralEarning, ReferralBonus
from .serializers import (
    ReferralCodeSerializer,
    ReferralSerializer,
    ReferralEarningSerializer,
    ReferralBonusSerializer,
    ReferralStatsSerializer
)

class ReferralCodeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing referral codes"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralCodeSerializer
    
    def get_queryset(self):
        return ReferralCode.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_code(self, request):
        """Get current user's referral code"""
        try:
            referral_code = ReferralCode.objects.get(user=request.user)
            serializer = self.get_serializer(referral_code)
            return Response(serializer.data)
        except ReferralCode.DoesNotExist:
            # Create referral code if it doesn't exist
            referral_code = ReferralCode.objects.create(user=request.user)
            serializer = self.get_serializer(referral_code)
            return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate referral code"""
        referral_code = self.get_object()
        referral_code.code = referral_code.generate_unique_code()
        referral_code.save()
        serializer = self.get_serializer(referral_code)
        return Response(serializer.data)

class ReferralViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing referrals"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralSerializer
    
    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get referral statistics"""
        referrals = self.get_queryset()
        
        total_referrals = referrals.count()
        active_referrals = referrals.filter(status='active').count()
        completed_referrals = referrals.filter(status='completed').count()
        pending_referrals = referrals.filter(status='pending').count()
        
        # Calculate total earnings
        total_earnings = ReferralEarning.objects.filter(
            referral__referrer=request.user,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate pending earnings
        pending_earnings = ReferralEarning.objects.filter(
            referral__referrer=request.user,
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # This month earnings
        this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_earnings = ReferralEarning.objects.filter(
            referral__referrer=request.user,
            status='paid',
            paid_at__gte=this_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_referrals': total_referrals,
            'active_referrals': active_referrals,
            'completed_referrals': completed_referrals,
            'pending_referrals': pending_referrals,
            'total_earnings': total_earnings,
            'pending_earnings': pending_earnings,
            'this_month_earnings': this_month_earnings,
        })
    
    @action(detail=False, methods=['get'])
    def earnings_chart(self, request):
        """Get earnings data for charts"""
        # Get earnings for last 6 months
        earnings_data = []
        for i in range(6):
            month_date = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_earnings = ReferralEarning.objects.filter(
                referral__referrer=request.user,
                status='paid',
                paid_at__year=month_date.year,
                paid_at__month=month_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            month_referrals = Referral.objects.filter(
                referrer=request.user,
                created_at__year=month_date.year,
                created_at__month=month_date.month
            ).count()
            
            earnings_data.append({
                'month': month_date.strftime('%b'),
                'earnings': float(month_earnings),
                'referrals': month_referrals,
            })
        
        return Response(earnings_data[::-1])  # Reverse to show oldest first

class ReferralEarningViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing referral earnings"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralEarningSerializer
    
    def get_queryset(self):
        return ReferralEarning.objects.filter(referral__referrer=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent earnings"""
        recent_earnings = self.get_queryset().order_by('-created_at')[:10]
        serializer = self.get_serializer(recent_earnings, many=True)
        return Response(serializer.data)

class ReferralBonusViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing referral bonuses"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralBonusSerializer
    queryset = ReferralBonus.objects.filter(is_active=True)

# Additional utility views
from rest_framework.views import APIView

class ValidateReferralCodeView(APIView):
    """Validate referral code during registration"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        code = request.data.get('code')
        
        if not code:
            return Response({'error': 'Referral code is required'}, status=400)
        
        try:
            referral_code = ReferralCode.objects.get(code=code, is_active=True)
            return Response({
                'valid': True,
                'referrer_name': f"{referral_code.user.first_name} {referral_code.user.last_name}".strip() or referral_code.user.email
            })
        except ReferralCode.DoesNotExist:
            return Response({'valid': False, 'error': 'Invalid referral code'}, status=400)

class ReferralDashboardView(APIView):
    """Get comprehensive referral dashboard data"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get or create referral code
        referral_code, created = ReferralCode.objects.get_or_create(user=user)
        
        # Get referral statistics
        referrals = Referral.objects.filter(referrer=user)
        total_referrals = referrals.count()
        active_referrals = referrals.filter(status='active').count()
        
        # Calculate earnings
        total_earnings = ReferralEarning.objects.filter(
            referral__referrer=user,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        pending_earnings = ReferralEarning.objects.filter(
            referral__referrer=user,
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get recent referrals
        recent_referrals = referrals.order_by('-created_at')[:5]
        
        # Get recent earnings
        recent_earnings = ReferralEarning.objects.filter(
            referral__referrer=user
        ).order_by('-created_at')[:5]
        
        return Response({
            'referral_code': ReferralCodeSerializer(referral_code).data,
            'stats': {
                'total_referrals': total_referrals,
                'active_referrals': active_referrals,
                'total_earnings': total_earnings,
                'pending_earnings': pending_earnings,
            },
            'recent_referrals': ReferralSerializer(recent_referrals, many=True).data,
            'recent_earnings': ReferralEarningSerializer(recent_earnings, many=True).data,
        })
