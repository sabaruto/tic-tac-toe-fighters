from django.contrib import admin
from .models import Fighter, Game, Node, Pool, User


class NodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'type')


class FighterAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'decider')


class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'state')

class PoolAdmin(admin.ModelAdmin):
    list_display = ('id', 'generation')

class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email')


admin.site.register(Node, NodeAdmin)
admin.site.register(Fighter, FighterAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Pool, PoolAdmin)
admin.site.register(User, UserAdmin)