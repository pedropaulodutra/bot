from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, BotControl

# Define um "inline" para o UserProfile, para que ele apareça dentro do User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile (API Keys & Telegram)'

# Define uma nova classe UserAdmin que sabe como salvar o perfil e o controle do bot
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    # Sobrescreve o método save_model
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Garante que o perfil seja salvo corretamente
        obj.userprofile.save()
        # Garante que um BotControl seja criado para o novo usuário
        BotControl.objects.get_or_create(user=obj)

# Re-registra o UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)