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
        
class InventoryValueAPI(APIView):
    """
    API to get total inventory value information for all products (average_cost * quantity)
    """
    def get(self, request):
        shop_id = request.query_params.get('shop_id')
        product_id = request.query_params.get('product_id')
        min_quantity = request.query_params.get('min_quantity')
        max_quantity = request.query_params.get('max_quantity')
        min_value = request.query_params.get('min_value')
        max_value = request.query_params.get('max_value')
        
        if not shop_id:
            return Response(
                {'error': 'shop_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start with base query for the shop
        query = Stock.objects.filter(shop_id=shop_id).select_related('product', 'shop')
        
        # Apply filters if provided
        if product_id:
            query = query.filter(product_id=product_id)
        
        if min_quantity:
            try:
                query = query.filter(quantity__gte=int(min_quantity))
            except ValueError:
                pass
                
        if max_quantity:
            try:
                query = query.filter(quantity__lte=int(max_quantity))
            except ValueError:
                pass
        
        # Get all filtered products for the shop
        stocks = list(query)
        
        # Apply value-based filters (need to be done in Python since it's a computed value)
        if min_value or max_value:
            filtered_stocks = []
            for stock in stocks:
                value = stock.average_cost * stock.quantity
                
                if min_value and value < float(min_value):
                    continue
                    
                if max_value and value > float(max_value):
                    continue
                    
                filtered_stocks.append(stock)
            
            stocks = filtered_stocks
        
        # Calculate total inventory value
        total_value = sum(stock.average_cost * stock.quantity for stock in stocks)
        
        # Get shop name
        shop_name = stocks[0].shop.name if stocks else "Unknown Shop"
        
        # Get individual product inventory values
        product_values = []
        for stock in stocks:
            product_values.append({
                'id': stock.id,
                'product_id': stock.product_id,
                'product_name': stock.product.name,
                'quantity': stock.quantity,
                'average_cost': str(stock.average_cost),
                'selling_price': str(stock.selling_price),
                'inventory_value': str(stock.average_cost * stock.quantity)
            })
        
        return Response({
            'total_inventory_value': str(total_value),
            'products': product_values,
            'shop_id': shop_id,
            'shop_name': shop_name,
            'total_products': len(product_values)
        })