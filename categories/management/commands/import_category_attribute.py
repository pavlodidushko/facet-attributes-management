import os
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from mptt.models import MPTTModel, TreeForeignKey
from categories.models import Category, Attribute

class Command(BaseCommand):
    help = 'Imports category attributes from CSV files in a directory'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing the CSV files')

    def handle(self, *args, **options):
        directory = options['directory']
        
        if not os.path.isdir(directory):
            self.stderr.write(self.style.ERROR(f"Directory '{directory}' does not exist"))
            return

        self.process_files(directory)

    def process_files(self, directory):
        csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]
        
        if not csv_files:
            self.stdout.write(self.style.WARNING("No CSV files found in directory"))
            return

        with transaction.atomic():
            for filename in csv_files:
                self.process_file(os.path.join(directory, filename))

    def process_file(self, filepath):
        filename = os.path.basename(filepath)
        self.stdout.write(f"Processing file: {filename}")

        try:
            category_path = self.parse_category_path(filename)
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Skipping {filename}: {str(e)}"))
            return

        try:
            category = self.get_or_create_categories(category_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing categories for {filename}: {str(e)}"))
            return

        try:
            with open(filepath, 'r') as csvfile:
                reader = csv.reader(csvfile)
                next(reader) 
                
                for row in reader:
                    if not row:
                        continue
                    
                    attr_name = row[0].strip()
                    if not attr_name:
                        continue
                    
                    attribute, created = Attribute.objects.get_or_create(name=attr_name)
                    
                    if not category.attributes.filter(id=attribute.id).exists():
                        category.attributes.add(attribute)
                        self.stdout.write(f"  Added attribute '{attr_name}' to category '{category.name}'")

                category.synchronize_attributes_with_ancestors()

            self.stdout.write(f"Processed file: {filename}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading {filename}: {str(e)}"))
            raise

    def parse_category_path(self, filename):
        """Convert filename to category path"""
        if not filename.endswith('.csv'):
            raise ValueError("File is not a CSV")
        
        # Remove .csv extension
        base_name = filename[:-4]
        
        base_name = base_name.replace('___', '###')
        
        path_components = base_name.split('__')
        
        if not path_components:
            raise ValueError("Filename doesn't contain valid category path")
        
        return [comp.replace('_', ' ').replace('###', '___') for comp in path_components]

    def get_or_create_categories(self, path_components):
        """Get or create categories in the path, return the leaf category"""
        parent = None
        current_path = []
        
        for component in path_components:
            current_path.append(component)
            path_str = '__'.join(current_path)
            path_str = path_str.replace(' ', '_')
            
            category = Category.objects.filter(name=component).first()
            
            if not category:
                category = Category(
                    name=component,
                    parent=parent,
                    path=path_str
                )
                category.save()
                self.stdout.write(f"Created category: {path_str}")
            else:
                if category.path != path_str:
                    category.path = path_str
                    category.save()
            
            parent = category
        
        return category