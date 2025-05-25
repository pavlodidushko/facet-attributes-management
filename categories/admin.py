from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Category, Attribute

class CategoryAdmin(MPTTModelAdmin):
    list_display = ('name', 'parent', 'path')
    list_filter = ('parent',)
    search_fields = ('name', 'path')
    mptt_level_indent = 20
    prepopulated_fields = {'path': ('name',)}

class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_categories')
    search_fields = ('name',)
    filter_horizontal = ('categories',)
    
    def display_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    display_categories.short_description = 'Categories'

admin.site.register(Category, CategoryAdmin)
admin.site.register(Attribute, AttributeAdmin)
