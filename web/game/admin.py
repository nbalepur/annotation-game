from django.contrib import admin
from django.utils.html import format_html
from .models import *

# Register your models here.
admin.site.register(Question)
admin.site.register(QuestionFeedback)
admin.site.register(User)
admin.site.register(Room)
admin.site.register(Message)

def unban_players(modeladmin, request, queryset):
    for player in queryset:
        player.unban()
        player.save()
        
unban_players.short_description = "Unban players"

class PlayerAdmin(admin.ModelAdmin):
    actions = [unban_players]

admin.site.register(Player, PlayerAdmin)