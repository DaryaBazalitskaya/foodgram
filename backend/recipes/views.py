from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from .models import Recipe


def recipe_redirect(request, short_url):
    """Перенаправление с короткой ссылки на страницу рецепта."""
    recipe = get_object_or_404(Recipe, short_url=short_url)
    return HttpResponseRedirect(
        f'{settings.API_URL_PREFIX}recipes/{recipe.pk}/'
    )
