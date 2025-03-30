from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Follow

UserAdmin.fieldsets += (
    ('Extra Fields', {'fields': ('avatar',)}),
)
UserAdmin.search_fields = ('email', 'username')
UserAdmin.ordering = ('username',)


class FollowAdmin(admin.ModelAdmin):

    list_display = ('user', 'following')
    search_fields = ('user__username',)


admin.site.register(CustomUser, UserAdmin)
admin.site.register(Follow, FollowAdmin)

admin.site.empty_value_display = 'Не задано'
