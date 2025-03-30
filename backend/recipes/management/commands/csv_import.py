from csv import DictReader

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):

    help = 'Импорт сsv-файлов в базу данных'

    def handle(self, *args, **options):
        for row in DictReader(
            open('data/ingredients.csv', encoding='utf-8')
        ):
            ingredient = Ingredient(
                name=row['name'],
                measurement_unit=row['measurement_unit']
            )
            ingredient.save()
            print('Ингредиенты загружены в базу данных.')
