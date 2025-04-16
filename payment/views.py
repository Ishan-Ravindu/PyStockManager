from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def get_object_options(request):
    ct_id = request.GET.get('content_type')
    if not ct_id:
        return JsonResponse({'results': []})

    try:
        content_type = ContentType.objects.get(pk=ct_id)
        model = content_type.model_class()
        objects = model.objects.all()
        results = [{'id': obj.pk, 'text': str(obj)} for obj in objects]
        return JsonResponse({'results': results})
    except Exception:
        return JsonResponse({'results': []})
