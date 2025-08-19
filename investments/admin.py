from django.contrib import admin
from .models import InvestmentPackage, Investment, Transaction, Portfolio, Payment, WithdrawalRequest, BankAccount

admin.site.register(InvestmentPackage)
admin.site.register(Investment)
admin.site.register(Transaction)
admin.site.register(Portfolio)
admin.site.register(Payment)
admin.site.register(WithdrawalRequest)
admin.site.register(BankAccount)
