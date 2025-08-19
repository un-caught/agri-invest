from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from investments.models import Transaction as InvestmentTransaction
from storage.models import PaymentTransaction as StorageTransaction
from ecommerce.models import Order
from django.utils.timezone import localtime
from rest_framework import status

@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_transactions(request):
    transactions = []

    # Investment transactions
    for tx in InvestmentTransaction.objects.select_related('user').all():
        transactions.append({
            'id': f"INV-{tx.id}",
            'type': 'Investment',
            'user': tx.user.get_full_name() or tx.user.username,
            'email': tx.user.email,
            'amount': tx.amount,
            'status': tx.status,
            'date': localtime(tx.created_at).strftime('%Y-%m-%d %H:%M'),
        })

    # Storage transactions
    for tx in StorageTransaction.objects.select_related('investment__user').all():
        transactions.append({
            'id': f"STO-{tx.id}",
            'type': 'Storage',
            'user': tx.investment.user.get_full_name() or tx.investment.user.username,
            'email': tx.investment.user.email,
            'amount': tx.amount,
            'status': tx.status,
            'date': localtime(tx.created_at).strftime('%Y-%m-%d %H:%M'),
        })

    # E-commerce orders
    for order in Order.objects.all():
        transactions.append({
            'id': f"ORD-{order.id}",
            'type': 'E-commerce',
            'user': f"{order.user.first_name} {order.user.last_name}".strip() or order.user.username,
            'email': order.email,
            'amount': order.total_amount,
            'status': order.status,
            'date': localtime(order.created_at).strftime('%Y-%m-%d %H:%M'),
        })

    # Sort by date descending
    transactions.sort(key=lambda x: x['date'], reverse=True)

    return Response(transactions)



@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_transaction(request, pk):
    """
    Update a transaction (investment, storage, or e-commerce) based on ID prefix.
    Expected payload: {"amount": ..., "status": "..."}
    """
    try:
        # Determine type by prefix
        if pk.startswith("INV-"):
            tx_id = pk.replace("INV-", "")
            transaction = InvestmentTransaction.objects.get(id=tx_id)
            if "amount" in request.data:
                transaction.amount = request.data["amount"]
            if "status" in request.data:
                transaction.status = request.data["status"]
            transaction.save()
            return Response({"message": "Investment transaction updated successfully"})

        elif pk.startswith("STO-"):
            tx_id = pk.replace("STO-", "")
            transaction = StorageTransaction.objects.get(id=tx_id)
            if "amount" in request.data:
                transaction.amount = request.data["amount"]
            if "status" in request.data:
                transaction.status = request.data["status"]
            transaction.save()
            return Response({"message": "Storage transaction updated successfully"})

        elif pk.startswith("ORD-"):
            tx_id = pk.replace("ORD-", "")
            order = Order.objects.get(id=tx_id)
            if "amount" in request.data:
                order.total_amount = request.data["amount"]
            if "status" in request.data:
                order.status = request.data["status"]
            order.save()
            return Response({"message": "E-commerce order updated successfully"})

        else:
            return Response({"error": "Invalid transaction ID format"}, status=status.HTTP_400_BAD_REQUEST)

    except (InvestmentTransaction.DoesNotExist, StorageTransaction.DoesNotExist, Order.DoesNotExist):
        return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
