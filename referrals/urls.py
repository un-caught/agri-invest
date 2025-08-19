from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'codes', views.ReferralCodeViewSet, basename='referral-code')
router.register(r'referrals', views.ReferralViewSet, basename='referral')
router.register(r'earnings', views.ReferralEarningViewSet, basename='referral-earning')
router.register(r'bonuses', views.ReferralBonusViewSet, basename='referral-bonus')

urlpatterns = [
    path('', include(router.urls)),
    path('validate-code/', views.ValidateReferralCodeView.as_view(), name='validate-referral-code'),
    path('dashboard/', views.ReferralDashboardView.as_view(), name='referral-dashboard'),
] 