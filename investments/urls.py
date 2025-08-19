from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'packages', views.InvestmentPackageViewSet, basename='package')
router.register(r'investments', views.InvestmentViewSet, basename='investment')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'portfolio', views.PortfolioViewSet, basename='portfolio')
router.register(r'payments', views.PaymentViewSet, basename='payment')

# Admin routes
router.register(r'admin/users', views.AdminUserViewSet, basename='admin-user')
router.register(r'admin/investments', views.AdminInvestmentViewSet, basename='admin-investment')
router.register(r'admin/packages', views.AdminPackageViewSet, basename='admin-package')
router.register(r'admin/transactions', views.AdminTransactionViewSet, basename='admin-transaction')
router.register(r'withdrawals', views.WithdrawalRequestViewSet, basename='withdrawal')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    # Payment routes
    path('payment/webhook/', views.PaystackWebhookView.as_view(), name='paystack-webhook'),
    path('investments/withdrawable/', views.InvestmentViewSet.as_view({'get': 'withdrawable'}), name='investment-withdrawable'),
    path('<int:investment_id>/payment_status/', views.payment_status, name='payment-status'),
    path('api/investments/<int:pk>/complete/', 
         views.InvestmentViewSet.as_view({'post': 'complete'}), 
         name='investment-complete'),
    path('admin/withdrawals/<int:withdrawal_id>/<str:action>/', 
         views.process_withdrawal, 
         name='process-withdrawal'),
    # urls.py
    path('admin/withdrawals/notes/<int:withdrawal_id>/', views.update_withdrawal_notes, name='update-withdrawal-notes'),
    # path('withdraw/paystack/webhook/', views.paystack_webhook, name="paystacks-webhook"),
]

