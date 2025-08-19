# # your_app/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.utils import timezone
# from datetime import timedelta
# from .models import Payment

# @receiver(post_save, sender=Payment)
# def cleanup_old_payments(sender, instance, created, **kwargs):
#     """
#     Clean up pending payments older than 24 hours whenever a new payment is created
#     """
#     if created:  # Only run when new payment is created
#         cutoff = timezone.now() - timedelta(hours=24)
        
#         # Get old pending payments
#         old_payments = Payment.objects.filter(
#             status='pending',
#             created_at__lt=cutoff
#         )
        
#         # Mark them as failed
#         for payment in old_payments:
#             payment.status = 'failed'
#             payment.save(update_fields=['status'])
            
#             # Cancel associated investment if exists
#             if hasattr(payment, 'investment'):
#                 payment.investment.status = 'cancelled'
#                 payment.investment.save(update_fields=['status'])