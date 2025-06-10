from django.db import connection, models, transaction
from django.urls import reverse
from django.db.models import Prefetch
from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    name = models.CharField(max_length=255, unique=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    path = models.CharField(max_length=255, unique=True, editable=False)
    
    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['path']),
            models.Index(fields=['parent']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.parent:
                self.path = f"{self.parent.path}__{self.name.replace(' ', '_')}"
            else:
                self.path = self.name.replace(' ', '_')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'pk': self.pk})
    
    @property
    def ancestors_with_self(self):
        return self.get_ancestors(include_self=True)
    
    @property
    def descendants_with_self(self):
        return self.get_descendants(include_self=True)

    def add_attribute(self, attribute):
        """Add attribute to this category and all ancestors"""
        with transaction.atomic():
            self.attributes.add(attribute)
            
            for ancestor in self.get_ancestors(include_self=False):
                ancestor.attributes.add(attribute)


    def remove_attribute(self, attribute):
        """Remove attribute from this category and descendants where no other ancestor has it"""
        with transaction.atomic():
            self.attributes.remove(attribute)
            
            for descendant in self.get_descendants(include_self=False):
                descendant.attributes.remove(attribute)

    def update_paths_for_subtree(self):
        """Efficient path updates using PostgreSQL CTE for large datasets"""
        if not connection.vendor == 'postgresql':
            return self._fallback_update_paths()
            
        with transaction.atomic():
            if self.parent:
                self.path = f"{self.parent.path}__{self.name.replace(' ', '_')}"
            else:
                self.path = self.name.replace(' ', '_')
            self.save()

            with connection.cursor() as cursor:
                cursor.execute("""
                    WITH RECURSIVE descendants AS (
                        SELECT id, name, parent_id
                        FROM categories_category
                        WHERE id = %s
                        
                        UNION ALL
                        
                        SELECT c.id, c.name, c.parent_id
                        FROM categories_category c
                        JOIN descendants d ON c.parent_id = d.id
                    )
                    UPDATE categories_category cat
                    SET path = 
                        CASE 
                            WHEN cat.parent_id IS NULL THEN cat.name
                            ELSE CONCAT(
                                (SELECT path FROM categories_category WHERE id = cat.parent_id),
                                '__',
                                REPLACE(cat.name, ' ', '_')
                            )
                        END
                    FROM descendants d
                    WHERE cat.id = d.id AND d.id != %s
                """, [self.id, self.id])

    def synchronize_attributes_with_ancestors(self):
        """Efficiently sync attributes from descendants to ancestors."""
        with transaction.atomic():
            current_attrs = set(self.get_descendants(include_self=True).prefetch_related(
                Prefetch('attributes', queryset=Attribute.objects.only('id'))
            ).values_list('attributes__id', flat=True))

            for ancestor in self.get_ancestors(include_self=False):
                ancestor_attrs = set(a.id for a in ancestor.attributes.all())

                missing_attrs = current_attrs - ancestor_attrs

                if missing_attrs:
                    ancestor.attributes.add(*Attribute.objects.filter(id__in=missing_attrs))


class Attribute(models.Model):
    name = models.CharField(max_length=255)
    categories = models.ManyToManyField(Category, related_name='attributes')
    
    class Meta:
        unique_together = ('name',)
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for category in self.categories.all():
            for descendant in category.get_descendants():
                if self not in descendant.attributes.all():
                    descendant.attributes.add(self)
    
    def delete(self, *args, **kwargs):
        categories = list(self.categories.all())
        super().delete(*args, **kwargs)
        
        for category in categories:
            self._cleanup_after_deletion(category)
    
    def _cleanup_after_deletion(self, category):
        for descendant in category.get_descendants():
            has_ancestor_with_attribute = any(
                self in ancestor.attributes.all()
                for ancestor in descendant.get_ancestors(include_self=True)
            )
            if not has_ancestor_with_attribute:
                Attribute.categories.through.objects.filter(
                    attribute_id=self.id,
                    category_id=descendant.id
                ).delete()

