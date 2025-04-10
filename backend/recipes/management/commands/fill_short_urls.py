import uuid

from django.core.management.base import BaseCommand

from recipes.models import Recipe


class Command(BaseCommand):
    help = 'Заполняет сокращенную ссылку для уже существующих рецептов'

    def handle(self, *args, **options):
        recipes = Recipe.objects.filter(short_url__isnull=True)
        if not recipes.exists():
            self.stdout.write(
                self.style.SUCCESS('Нет рецептов без short_url.')
            )
            return

        for recipe in recipes:
            short_url = str(uuid.uuid4())[:8]
            while Recipe.objects.filter(short_url=short_url).exists():
                short_url = str(uuid.uuid4())[:8]
            recipe.short_url = short_url
            recipe.save(update_fields=['short_url'])
            self.stdout.write(
                f'Добавлен short_url для рецепта {recipe.id}: {short_url}'
            )

        self.stdout.write(self.style.SUCCESS('Short URL успешно добавлены.'))
