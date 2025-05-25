from django import forms
from .models import Category, Attribute


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, parent_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        if parent_pk:
            self.fields['parent'].initial = parent_pk
        self.fields['parent'].required = False
        self.fields['parent'].queryset = Category.objects.all()
        
        self.fields['parent'].label_from_instance = lambda obj: (
            f"{'---' * obj.level} {obj.name}" if obj.level > 0 else obj.name
        )


class AttributeForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Attribute
        fields = ['name', 'categories']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['categories'].initial = self.instance.categories.all()
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.categories.set(self.cleaned_data['categories'])
        return instance
