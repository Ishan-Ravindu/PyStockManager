from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventory.api.serializers import StockSerializer
from inventory.models.stock import Stock

class StockAPI(APIView):
    """
    API to get product stock information
    """
    def get(self, request):
        shop_id = request.query_params.get('shop_id')
        product_id = request.query_params.get('product_id')
        
        if not shop_id:
            return Response(
                {'error': 'shop_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if product_id:
            # Single product mode
            try:
                stock = Stock.objects.get(shop_id=shop_id, product_id=product_id)
                serializer = StockSerializer(stock)
                return Response(serializer.data)
            except Stock.DoesNotExist:
                return Response(
                    {'quantity': 0, 'product_id': product_id, 'product_name': 'Unknown', 'product_code': ''},
                    status=status.HTTP_200_OK
                )
        else:
            # All products for shop mode
            stocks = Stock.objects.filter(shop_id=shop_id).select_related('product')
            serializer = StockSerializer(stocks, many=True)
            
            # Convert to {product_id: quantity} format for frontend
            data = {item['product_id']: item for item in serializer.data}
            return Response(data)