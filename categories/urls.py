from django.urls import path
from .views import (
    CategoryListView, CategoryDetailView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    AttributeListView, AttributeCreateView, AttributeUpdateView, AttributeDeleteView, AttributeDetailView, 
    manage_category_attributes, category_add_attribute, category_remove_attribute
)
from .api import (
    create_category, 
    update_category, 
    delete_category,
    search_categories, 
    category_tree, 
    category_attributes, 
    category_add_attribute as api_category_add_attribute, 
    category_add_attribute_by_name as api_category_add_attribute_by_name,
    category_remove_attribute as api_category_remove_attribute, 
    search_attributes
)

urlpatterns = [
    # Category URLs
    path('', CategoryListView.as_view(), name='category_list_home'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/add/', CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    path('categories/<int:pk>/attributes/', manage_category_attributes, name='manage_category_attributes'),
    
    # Attribute URLs
    path('attributes/', AttributeListView.as_view(), name='attribute_list'),
    path('attributes/add/', AttributeCreateView.as_view(), name='attribute_add'),
    path('attributes/<int:pk>/', AttributeDetailView.as_view(), name='attribute_detail'),
    path('attributes/<int:pk>/edit/', AttributeUpdateView.as_view(), name='attribute_edit'),
    path('attributes/<int:pk>/delete/', AttributeDeleteView.as_view(), name='attribute_delete'),
    
    path('api/categories/create/', create_category, name='api_create_category'),
    path('api/categories/tree/', category_tree, name='category_tree'),
    path('api/categories/<int:pk>/attributes/', category_attributes, name='category_attributes'),
    path('api/categories/search/', search_categories, name='api_search_categories'),
    path('api/categories/<int:pk>/update/', update_category, name='api_update_category'),
    path('api/categories/<int:pk>/delete/', delete_category, name='api_delete_category'),

    # Attribute-Category Relationship URLs
    path('categories/<int:category_pk>/add-attribute/<int:attribute_pk>/', 
         category_add_attribute, name='category_add_attribute'),
    path('categories/<int:category_pk>/remove-attribute/<int:attribute_pk>/', 
         category_remove_attribute, name='category_remove_attribute'),
    
    path('api/categories/<int:category_pk>/add-attribute/<int:attribute_pk>/', 
         api_category_add_attribute, name='api_add_category_attribute'),
    path('api/categories/<int:category_pk>/add-attribute-by-name/',
         api_category_add_attribute_by_name, name='category_add_attribute_by_name'),
    path('api/categories/<int:category_pk>/remove-attribute/<int:attribute_pk>/', 
         api_category_remove_attribute, name='api_remove_category_attribute'),
    
    path('api/attributes/search/', search_attributes, name='search_attributes'),
]
