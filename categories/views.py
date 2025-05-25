from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect

from .models import Category, Attribute
from .forms import CategoryForm, AttributeForm


class CategoryListView(ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return Category.objects.filter(level=0)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the first category's attributes if none is selected
        first_category = self.get_queryset().first()
        context['selected_category'] = first_category
        if first_category:
            context['attributes'] = first_category.attributes.all()
            context['available_attributes'] = Attribute.objects.exclude(
                id__in=first_category.attributes.values_list('id', flat=True)
            )
        return context


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'categories/category_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attributes'] = self.object.attributes.all()
        context['children'] = self.object.get_children()
        return context


class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent_pk'] = self.request.GET.get('parent')
        return kwargs


class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    
    def get_success_url(self):
        return reverse_lazy('category_detail', kwargs={'pk': self.object.pk})


class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'categories/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')


class AttributeListView(ListView):
    model = Attribute
    template_name = 'categories/attribute_list.html'
    context_object_name = 'attributes'
    paginate_by = 20
    ordering = '-pk'


class AttributeCreateView(CreateView):
    model = Attribute
    form_class = AttributeForm
    template_name = 'categories/attribute_form.html'
    success_url = reverse_lazy('attribute_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Attribute "{self.object.name}" created successfully.')
        return response


class AttributeUpdateView(UpdateView):
    model = Attribute
    form_class = AttributeForm
    template_name = 'categories/attribute_form.html'
    success_url = reverse_lazy('attribute_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Attribute "{self.object.name}" updated successfully.')
        return response


class AttributeDeleteView(DeleteView):
    model = Attribute
    success_url = reverse_lazy('attribute_list')
    
    def delete(self, request, *args, **kwargs):
        attribute = self.get_object()
        name = attribute.name
        attribute.delete()  # Perform the deletion directly
        messages.success(request, f'Attribute "{name}" deleted successfully.')
        return HttpResponseRedirect(self.success_url)


class AttributeDetailView(DetailView):
    model = Attribute
    template_name = 'attributes/attribute_detail.html'
    context_object_name = 'attribute'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assigned_categories'] = self.object.categories.all()
        context['available_categories'] = Category.objects.exclude(
            id__in=self.object.categories.values_list('id', flat=True)
        )
        return context


def manage_category_attributes(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        attribute_ids = request.POST.getlist('attributes')
        with transaction.atomic():
            
            category.attributes.clear()

            for attribute_id in attribute_ids:
                attribute = Attribute.objects.get(pk=attribute_id)
                category.attributes.add(attribute)
                
                for ancestor in category.get_ancestors(include_self=False):
                    ancestor.attributes.add(attribute)

            for descendant in category.get_descendants():
                descendant.attributes.add(*category.attributes.all())
            
            messages.success(request, 'Attributes updated successfully.')
            return redirect('category_detail', pk=category.pk)
    
    available_attributes = Attribute.objects.exclude(
        id__in=category.attributes.all().values_list('id', flat=True)
    )
    
    context = {
        'category': category,
        'available_attributes': available_attributes,
    }
    return render(request, 'categories/manage_category_attributes.html', context)
  
def category_add_attribute(request, category_pk, attribute_pk):
    category = get_object_or_404(Category, pk=category_pk)
    attribute = get_object_or_404(Attribute, pk=attribute_pk)
    
    if request.method == 'POST':
        category.attributes.add(attribute)
        messages.success(request, f"Added '{attribute.name}' to '{category.name}'")
    
    # Redirect back to the previous page
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'category_detail', pk=category.pk)

def category_remove_attribute(request, category_pk, attribute_pk):
    category = get_object_or_404(Category, pk=category_pk)
    attribute = get_object_or_404(Attribute, pk=attribute_pk)
    
    if request.method == 'POST':
        category.attributes.remove(attribute)
        messages.success(request, f"Removed '{attribute.name}' from '{category.name}'")
    
    # Redirect back to the previous page
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'category_detail', pk=category.pk)
