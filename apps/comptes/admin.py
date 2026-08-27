from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    model = Utilisateur
    list_display = [
        "telephone", "nom_complet", "operateur_mobile_money",
        "statut_kyc", "telephone_verifie", "date_creation",
    ]
    list_filter = ["statut_kyc", "operateur_mobile_money", "telephone_verifie"]
    search_fields = ["telephone", "nom_complet", "email"]
    ordering = ["-date_creation"]

    fieldsets = (
        (None, {"fields": ("telephone", "password")}),
        ("Informations personnelles", {"fields": ("nom_complet", "email", "operateur_mobile_money")}),
        ("Vérification & KYC", {"fields": ("telephone_verifie", "statut_kyc")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("telephone", "nom_complet", "operateur_mobile_money", "password1", "password2"),
        }),
    )
