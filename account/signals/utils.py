def save_balance(account, amount_delta):
    account.balance += amount_delta
    account.save(update_fields=['balance'])

def safe_get_original(instance, model_name, fields):
    from django.apps import apps
    try:
        model = apps.get_model('account', model_name)
        original = model.objects.get(pk=instance.pk)
        for field in fields:
            setattr(instance, f'_original_{field}', getattr(original, field))
    except model.DoesNotExist:
        for field in fields:
            setattr(instance, f'_original_{field}', None)
