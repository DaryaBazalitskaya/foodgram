from django.contrib import admin

from .models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Tag)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    extra = 0


class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
    )
    list_editable = ('measurement_unit',)
    search_fields = ('name',)
    list_filter = ('name',)
    list_display_links = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    list_editable = ('slug',)
    search_fields = ('name',)
    list_filter = ('name',)
    list_display_links = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    inlines = (RecipeIngredientInline,)
    list_display = (
        'name',
        'author',
        'favorite_amount'
    )
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    list_display_links = ('name',)

    @admin.display(description='Добавления в избранное')
    def favorite_amount(self, obj):
        """Количество добавлений в избранное."""
        return Favorites.objects.filter(recipe=obj).count()


class FavoritesAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )
    search_fields = ('recipe',)
    list_filter = ('user',)
    list_display_links = ('user',)


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )
    search_fields = ('recipe',)
    list_filter = ('user',)
    list_display_links = ('user',)


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Favorites, FavoritesAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Tag, TagAdmin)

admin.site.empty_value_display = 'Не задано'
