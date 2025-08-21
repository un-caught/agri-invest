import requests
import uuid
from django.conf import settings
from decimal import Decimal
from ..models import PaymentTransaction


class PaymentService:
    """Service class for handling payment operations with Paystack"""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = 'https://api.paystack.co'
        
    def get_headers(self):
        """Get headers for Paystack API requests"""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def generate_reference(self):
        """Generate unique payment reference"""
        return f"AGR_{uuid.uuid4().hex[:12].upper()}"
    
    def create_payment(self, investment):
        """Create payment transaction and initialize payment with Paystack"""
        
        # Generate unique reference
        reference = self.generate_reference()
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction.objects.create(
            investment=investment,
            reference=reference,
            amount=investment.total_investment_amount,
            payment_gateway='paystack'
        )
        callback_url = getattr(settings, 'PAYMENT_CALLBACK_URL', '')
        if not callback_url:
            # callback_url = 'http://localhost:5173/storage'  # Fallback to frontend URL
            callback_url = (f'{settings.FRONTEND_URL}/storage')  # Fallback to frontend URL
        # Prepare payment data for Paystack


        payment_data = {
            'email': investment.customer_email,
            'amount': int(investment.total_investment_amount * 100),  # Paystack expects kobo
            'reference': reference,
            'currency': 'NGN',
            'callback_url': callback_url,
            'success_url': callback_url,  # Add success_url
            'cancel_url': callback_url, 
            # 'callback_url': getattr(settings, 'PAYMENT_CALLBACK_URL', ''),
            'metadata': {
                'investment_id': str(investment.id),
                'customer_name': investment.customer_name,
                'product_name': investment.product_name,
                'quantity_bags': investment.quantity_bags,
                'custom_fields': [
                    {
                        'display_name': 'Investment ID',
                        'variable_name': 'investment_id',
                        'value': str(investment.id)
                    },
                    {
                        'display_name': 'Product',
                        'variable_name': 'product_name',
                        'value': investment.product_name
                    }
                ]
            }
        }
        
        try:
            # Initialize payment with Paystack
            response = requests.post(
                f'{self.base_url}/transaction/initialize',
                json=payment_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status']:
                    # Update payment transaction with payment URL
                    payment_transaction.payment_url = data['data']['authorization_url']
                    payment_transaction.gateway_reference = data['data']['reference']
                    payment_transaction.save()
                    
                    return payment_transaction
                else:
                    raise Exception(f"Paystack error: {data.get('message', 'Unknown error')}")
            else:
                raise Exception(f"HTTP error: {response.status_code}")
                
        except requests.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            # If payment initialization fails, clean up
            payment_transaction.status = 'failed'
            payment_transaction.save()
            raise e
    
    def verify_payment(self, reference):
        """Verify payment status with Paystack"""
        try:
            response = requests.get(
                f'{self.base_url}/transaction/verify/{reference}',
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] and data['data']['status'] == 'success':
                    return {
                        'status': 'success',
                        'data': data['data']
                    }
                else:
                    return {
                        'status': 'failed',
                        'message': data.get('message', 'Payment verification failed')
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP error: {response.status_code}'
                }
                
        except requests.RequestException as e:
            return {
                'status': 'error',
                'message': f'Network error: {str(e)}'
            }
    
    def get_payment_status(self, reference):
        """Get current payment status"""
        try:
            payment_transaction = PaymentTransaction.objects.get(reference=reference)
            
            # If already successful, return cached status
            if payment_transaction.status == 'successful':
                return {
                    'status': 'successful',
                    'payment_transaction': payment_transaction
                }
            
            # Otherwise, verify with Paystack
            verification_result = self.verify_payment(reference)
            
            if verification_result['status'] == 'success':
                payment_transaction.status = 'successful'
                payment_transaction.gateway_reference = verification_result['data']['id']
                payment_transaction.save()
            
            return {
                'status': payment_transaction.status,
                'payment_transaction': payment_transaction
            }
            
        except PaymentTransaction.DoesNotExist:
            return {
                'status': 'not_found',
                'message': 'Payment transaction not found'
            }
    
    def refund_payment(self, reference, amount=None, reason=""):
        """Initiate refund for a payment"""
        try:
            payment_transaction = PaymentTransaction.objects.get(reference=reference)
            
            if payment_transaction.status != 'successful':
                return {
                    'status': 'error',
                    'message': 'Can only refund successful payments'
                }
            
            refund_amount = amount or payment_transaction.amount
            
            refund_data = {
                'transaction': payment_transaction.gateway_reference,
                'amount': int(refund_amount * 100),  # Convert to kobo
                'currency': 'NGN',
                'customer_note': reason,
                'merchant_note': f'Refund for investment {payment_transaction.investment.id}'
            }
            
            response = requests.post(
                f'{self.base_url}/refund',
                json=refund_data,
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status']:
                    return {
                        'status': 'success',
                        'refund_id': data['data']['id'],
                        'message': 'Refund initiated successfully'
                    }
                else:
                    return {
                        'status': 'error',
                        'message': data.get('message', 'Refund failed')
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP error: {response.status_code}'
                }
                
        except PaymentTransaction.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Payment transaction not found'
            }
        except requests.RequestException as e:
            return {
                'status': 'error',
                'message': f'Network error: {str(e)}'
            }