from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import StoragePlan, StorageInvestment, PaymentTransaction, StorageUpdate


admin.site.register(StoragePlan)
admin.site.register(StorageInvestment)
admin.site.register(PaymentTransaction)
admin.site.register(StorageUpdate)

# @admin.register(StoragePlan)
# class StoragePlanAdmin(admin.ModelAdmin):
#     list_display = [
#         'product_name', 'buying_price_per_bag', 'projected_selling_price', 
#         'roi_percentage', 'available_quantity', 'is_active', 'storage_due_date'
#     ]
#     list_filter = ['is_active', 'created_at', 'storage_due_date']
#     search_fields = ['product_name', 'description']
#     readonly_fields = ['id', 'roi_percentage', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Product Information', {
#             'fields': ('product_name', 'product_image', 'description')
#         }),
#         ('Pricing', {
#             'fields': ('buying_price_per_bag', 'projected_selling_price', 'storage_cost_per_bag')
#         }),
#         ('Availability', {
#             'fields': ('available_quantity', 'minimum_quantity', 'maximum_quantity', 'is_active')
#         }),
#         ('Timeline', {
#             'fields': ('storage_due_date',)
#         }),
#         ('System Info', {
#             'fields': ('id', 'roi_percentage', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def roi_percentage(self, obj):
#         return f"{obj.roi_percentage}%"
#     roi_percentage.short_description = "ROI %"


# class StorageUpdateInline(admin.TabularInline):
#     model = StorageUpdate
#     extra = 0
#     readonly_fields = ['id', 'created_at']
#     fields = ['update_type', 'title', 'message', 'current_market_price', 'created_at']


# class PaymentTransactionInline(admin.StackedInline):
#     model = PaymentTransaction
#     extra = 0
#     readonly_fields = ['id', 'reference', 'gateway_reference', 'payment_url', 'created_at', 'updated_at']
#     fields = [
#         'reference', 'amount', 'status', 'payment_method', 'payment_gateway',
#         'gateway_reference', 'payment_url', 'paid_at'
#     ]


# @admin.register(StorageInvestment)
# class InvestmentAdmin(admin.ModelAdmin):
#     list_display = [
#         'customer_name', 'product_name', 'quantity_bags', 
#         'total_investment_amount', 'status', 'purchase_date', 'due_date'
#     ]
#     list_filter = ['status', 'purchase_date', 'due_date', 'storage_plan__product_name']
#     search_fields = ['customer_name', 'customer_email', 'storage_plan__product_name']
#     readonly_fields = [
#         'id', 'roi_percentage', 'days_remaining', 'progress_percentage',
#         'created_at', 'updated_at'
#     ]
    
#     fieldsets = (
#         ('Customer Information', {
#             'fields': ('user', 'customer_name', 'customer_email', 'customer_phone')
#         }),
#         ('Investment Details', {
#             'fields': (
#                 'storage_plan', 'quantity_bags', 'price_per_bag', 
#                 'total_investment_amount', 'projected_selling_price_per_bag', 
#                 'projected_returns'
#             )
#         }),
#         ('Status & Timeline', {
#             'fields': ('status', 'purchase_date', 'due_date', 'completion_date')
#         }),
#         ('Payment Information', {
#             'fields': ('payment_reference', 'payment_status', 'payment_date')
#         }),
#         ('Calculated Fields', {
#             'fields': ('roi_percentage', 'days_remaining', 'progress_percentage'),
#             'classes': ('collapse',)
#         }),
#         ('System Info', {
#             'fields': ('id', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     inlines = [PaymentTransactionInline, StorageUpdateInline]
    
#     def product_name(self, obj):
#         return obj.storage_plan.product_name
#     product_name.short_description = "Product"
    
#     def roi_percentage(self, obj):
#         return f"{obj.roi_percentage}%"
#     roi_percentage.short_description = "ROI %"
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('user', 'storage_plan')


# @admin.register(PaymentTransaction)
# class PaymentTransactionAdmin(admin.ModelAdmin):
#     list_display = [
#         'reference', 'investment_customer', 'amount', 'status', 
#         'payment_gateway', 'created_at'
#     ]
#     list_filter = ['status', 'payment_gateway', 'created_at']
#     search_fields = ['reference', 'gateway_reference', 'investment__customer_name']
#     readonly_fields = ['id', 'created_at', 'updated_at']
    
#     fieldsets = (
#         ('Transaction Details', {
#             'fields': ('investment', 'reference', 'amount', 'status')
#         }),
#         ('Payment Gateway', {
#             'fields': ('payment_gateway', 'payment_method', 'gateway_reference', 'payment_url')
#         }),
#         ('Timeline', {
#             'fields': ('paid_at', 'created_at', 'updated_at')
#         }),
#         ('System Info', {
#             'fields': ('id',),
#             'classes': ('collapse',)
#         })
#     )
    
#     def investment_customer(self, obj):
#         return obj.investment.customer_name
#     investment_customer.short_description = "Customer"
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('investment')


# @admin.register(StorageUpdate)
# class StorageUpdateAdmin(admin.ModelAdmin):
#     list_display = [
#         'investment_customer', 'update_type', 'title', 
#         'current_market_price', 'created_at'
#     ]
#     list_filter = ['update_type', 'created_at']
#     search_fields = ['investment__customer_name', 'title', 'message']
#     readonly_fields = ['id', 'created_at']
    
#     fieldsets = (
#         ('Update Information', {
#             'fields': ('investment', 'update_type', 'title', 'message')
#         }),
#         ('Market Data', {
#             'fields': ('current_market_price', 'image')
#         }),
#         ('System Info', {
#             'fields': ('id', 'created_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def investment_customer(self, obj):
#         return obj.investment.customer_name
#     investment_customer.short_description = "Customer"
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('investment')


# # Custom admin actions
# @admin.action(description='Mark selected investments as active')
# def make_active(modeladmin, request, queryset):
#     queryset.update(status='active')

# @admin.action(description='Mark selected investments as matured')
# def make_matured(modeladmin, request, queryset):
#     queryset.update(status='matured')

# # Add actions to Investment admin
# InvestmentAdmin.actions = [make_active, make_matured]