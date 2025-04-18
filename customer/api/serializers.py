from rest_framework import serializers

from customer.models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'mobile_number', 'address', 'email', 
            'credit', 'credit_limit', 'credit_period', 'whole_sale', 
            'black_list'
        ]
