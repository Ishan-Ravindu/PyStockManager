from rest_framework import serializers
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords

User = get_user_model()

class HistoryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class GenericHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    history_id = serializers.IntegerField()
    history_date = serializers.DateTimeField()
    history_type = serializers.CharField(max_length=1)
    history_user = serializers.SerializerMethodField()
    history_change_reason = serializers.CharField(allow_null=True)
    model_name = serializers.SerializerMethodField()
    instance_name = serializers.SerializerMethodField()
    changed_fields = serializers.SerializerMethodField()
    
    def get_history_user(self, obj):
        if obj.history_user:
            return HistoryUserSerializer(obj.history_user).data
        return None
    
    def get_model_name(self, obj):
        return obj.__class__._meta.model.__module__ + '.' + obj.__class__._meta.model.__name__
    
    def get_instance_name(self, obj):
        # Try to get a meaningful representation of the instance
        try:
            if hasattr(obj, 'get_absolute_url'):
                return obj.get_absolute_url()
            elif hasattr(obj, '__str__'):
                return str(obj)
            else:
                return f"{obj.__class__.__name__} #{obj.id}"
        except:
            return f"{obj.__class__.__name__} #{obj.id}"
    
    def get_changed_fields(self, obj):
        # For create operations, all fields are "changed"
        if obj.history_type == '+':
            fields = {}
            for field_name in obj._meta.fields:
                if field_name.name not in ['history_id', 'history_date', 'history_change_reason', 
                                          'history_type', 'history_user_id']:
                    try:
                        value = getattr(obj, field_name.name, None)
                        # Convert complex objects to their string representation
                        if value is not None:
                            if hasattr(value, '__class__') and not isinstance(value, (str, int, float, bool, type(None))):
                                value = str(value)
                        fields[field_name.name] = {
                            'old_value': None,
                            'new_value': value
                        }
                    except Exception as e:
                        fields[field_name.name] = {
                            'old_value': None,
                            'new_value': f"Error retrieving value: {str(e)}"
                        }
            return fields
        
        # For delete operations, no need to show changed fields
        elif obj.history_type == '-':
            return {}
        
        # For update operations, try to find previous version to show changes
        elif obj.history_type == '~':
            try:
                # Get the previous historical record for this instance
                prev_record = obj.__class__.objects.filter(
                    id=obj.id,
                    history_date__lt=obj.history_date
                ).order_by('-history_date').first()
                
                changes = {}
                if prev_record:
                    # Compare fields with previous version
                    for field_name in obj._meta.fields:
                        if field_name.name not in ['history_id', 'history_date', 'history_change_reason', 
                                                  'history_type', 'history_user_id']:
                            try:
                                old_value = getattr(prev_record, field_name.name, None)
                                new_value = getattr(obj, field_name.name, None)
                                
                                # Convert complex objects to their string representation
                                if old_value is not None and hasattr(old_value, '__class__') and not isinstance(old_value, (str, int, float, bool, type(None))):
                                    old_value = str(old_value)
                                if new_value is not None and hasattr(new_value, '__class__') and not isinstance(new_value, (str, int, float, bool, type(None))):
                                    new_value = str(new_value)
                                
                                # Only include fields that changed
                                if old_value != new_value:
                                    changes[field_name.name] = {
                                        'old_value': old_value,
                                        'new_value': new_value
                                    }
                            except Exception as e:
                                changes[field_name.name] = {
                                    'error': f"Error comparing values: {str(e)}"
                                }
                return changes
            except Exception as e:
                # If there's any error in determining changes, return empty dict
                return {'error': str(e)}