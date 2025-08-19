from django.urls import path
from . import views

urlpatterns = [
    path('all-transactions/', views.all_transactions, name='all-transactions'),
    path("transactions/<str:pk>/", views.update_transaction, name="update-transaction"),
]
