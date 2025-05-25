from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.db import transaction
from .models import Category, Attribute


@require_http_methods(["POST"])
def create_category(request):
    try:
        data = request.POST
        name = data.get('name')
        parent_id = data.get('parent_id')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'}, status=400)
        
        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)
        
        category = Category.objects.create(
            name=name,
            parent=parent
        )
        
        if parent:
            category.path = f"{parent.path}__{name.replace(' ', '_')}"
        else:
            category.path = name.replace(' ', '_')
        category.save()
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'path': category.path,
                'parent_id': parent.id if parent else None
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def update_category(request, pk):
    try:
        category = get_object_or_404(Category, pk=pk)
        data = request.POST
        new_name = data.get('name')
        parent_id = data.get('parent_id')
        
        if not new_name:
            return JsonResponse({'success': False, 'error': 'Category name is required'}, status=400)
        
        new_parent = None
        if parent_id:
            new_parent = get_object_or_404(
                Category.objects.only('id', 'path'),
                id=parent_id
            )
        
        old_name = category.name
        name_changed = new_name != old_name
        parent_changed = new_parent != category.parent
        
        if not name_changed and not parent_changed:
            return JsonResponse({'success': False, 'error': 'No changes detected'}, status=400)
        
        category = Category.objects.only('name', 'path', 'parent_id').get(pk=pk)
        
        with transaction.atomic():
            if name_changed:
                category.name = new_name
            if parent_changed:
                category.parent = new_parent
            
            if name_changed or parent_changed:
                category.save()
                
                if name_changed or parent_changed:
                    category.update_paths_for_subtree()
                
                if parent_changed:
                    category.synchronize_attributes_with_ancestors()
        
        return JsonResponse({
            'success': True,
            'message': f"Category updated successfully",
            'category': {
                'id': category.id,
                'name': category.name,
                'parent_id': category.parent_id
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["DELETE"])
def delete_category(request, pk):
    try:
        category = get_object_or_404(Category, pk=pk)
        # Delete all descendants and their attribute associations
        descendants = category.get_descendants()
        for desc in descendants:
            desc.attributes.clear()
            desc.delete()
        # Delete attribute associations for the category itself
        category.attributes.clear()
        category.delete()
        return JsonResponse({'success': True, 'message': f"Category deleted successfully"})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    

def search_categories(request):
    query = request.GET.get('q', '')
    exclude_id = request.GET.get('exclude', '')
    
    categories = Category.objects.all()
    
    if query:
        categories = categories.filter(name__icontains=query)
    
    if exclude_id:
        try:
            exclude_category = Category.objects.get(id=exclude_id)
            descendants = exclude_category.get_descendants()
            categories = categories.exclude(
                Q(id=exclude_id) | 
                Q(id__in=descendants.values_list('id', flat=True))
            )
        except Category.DoesNotExist:
            pass
    
    results = []
    for cat in categories[:100]:
        path_parts = cat.path.split('__')
        display_path = ' → '.join(path_parts)
        results.append({
            'id': str(cat.id),
            'text': cat.name,
            'path': display_path
        })
    
    return JsonResponse({'results': results})


def category_tree(request):
    """Returns category data in jstree format with attribute info"""
    parent_id = request.GET.get('id', '')
    if parent_id == '#':
        parent_id = ''
    
    categories = Category.objects.filter(parent__id=parent_id) if parent_id else Category.objects.filter(parent__isnull=True)
    
    data = []
    for category in categories:
        data.append({
            'id': str(category.id),
            'text': category.name,
            'children': category.get_children().exists(),
            'type': 'default',
            'data': {
                'attribute_count': category.attributes.count()
            }
        })
    
    return JsonResponse(data, safe=False)


def category_attributes(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    return JsonResponse({
        'attributes': list(category.attributes.values('id', 'name')),
        'available_attributes': list(Attribute.objects.exclude(
            categories=category
        ).values('id', 'name'))
    })


def category_add_attribute(request, category_pk, attribute_pk):
    category = get_object_or_404(Category, pk=category_pk)
    attribute = get_object_or_404(Attribute, pk=attribute_pk)
    
    category.add_attribute(attribute)
    
    return JsonResponse({
        'success': True,
        'message': f"Added '{attribute.name}' to '{category.name}' and its subcategories",
        'attribute': {
            'id': attribute.id,
            'name': attribute.name
        }
    })


@require_http_methods(["POST"])
def category_add_attribute_by_name(request, category_pk):
    """
    Add an attribute to a category by attribute name (creates attribute if needed).
    Expects JSON body: {"name": "Attribute Name"}
    """
    category = get_object_or_404(Category, pk=category_pk)
    data = request.POST
    attr_name = data.get('name', '').strip()
    if not attr_name:
        return JsonResponse({'success': False, 'error': 'Attribute name is required'}, status=400)

    attribute, created = Attribute.objects.get_or_create(name=attr_name)
    category.add_attribute(attribute)

    return JsonResponse({
        'success': True,
        'message': f"Added '{attribute.name}' to '{category.name}' and synchronized with ancestors",
        'attribute': {
            'id': attribute.id,
            'name': attribute.name
        },
        'created': created
    })


@require_http_methods(["POST"])
def category_remove_attribute(request, category_pk, attribute_pk):
    category = get_object_or_404(Category, pk=category_pk)
    attribute = get_object_or_404(Attribute, pk=attribute_pk)
    
    category.remove_attribute(attribute)
    
    return JsonResponse({
        'success': True,
        'message': f"Removed '{attribute.name}' from '{category.name}' and applicable subcategories",
        'attribute': {
            'id': attribute.id,
            'name': attribute.name
        }
    })

def search_attributes(request):
    """Search attributes by category name."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'success': False, 'error': 'Category name query is required'}, status=400)

    attributes = Attribute.objects.filter(categories__path__icontains=query).distinct()

    results = [
        {'id': attr.id, 'name': attr.name}
        for attr in attributes
    ]

    return JsonResponse({'success': True, 'attributes': results})
