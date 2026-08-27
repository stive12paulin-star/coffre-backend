from django.contrib import admin

from .models import Coffre


@admin.register(Coffre)
class CoffreAdmin(admin.ModelAdmin):
    list_display = ["nom", "utilisateur", "statut", "date_deblocage", "solde_cache", "date_creation"]
    list_filter = ["statut", "retrait_anticipe_autorise"]
    search_fields = ["nom", "utilisateur__telephone", "utilisateur__nom_complet"]
    readonly_fields = ["solde_cache", "date_creation", "date_maj"]  # jamais modifié à la main
    date_hierarchy = "date_deblocage"
