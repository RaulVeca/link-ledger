# file_handler/management/commands/load_initial_data.py
from django.core.management.base import BaseCommand
from file_handler.models import Country, Currency

class Command(BaseCommand):
    help = 'Load initial reference data'
    
    def handle(self, *args, **options):
        # Countries
        countries = [
            ('RO', 'Romania'),
            ('IT', 'Italy'),
            ('US', 'United States'),
            ('DE', 'Germany'),
            ('LU', 'Luxembourg'),
        ]
        for code, name in countries:
            Country.objects.get_or_create(code=code, defaults={'name': name})
        
        # Currencies
        currencies = [
            ('EUR', 'Euro', '€'),
            ('USD', 'US Dollar', '$'),
            ('RON', 'Romanian Leu', 'lei'),
        ]
        for code, name, symbol in currencies:
            Currency.objects.get_or_create(
                code=code, 
                defaults={'name': name, 'symbol': symbol}
            )
        
        self.stdout.write(self.style.SUCCESS('Initial data loaded'))