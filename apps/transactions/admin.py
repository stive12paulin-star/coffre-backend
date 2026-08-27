from django.contrib import admin

from .models import Transaction, VerificationOtp


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "coffre", "type", "montant", "statut", "operateur", "date_transaction"]
    list_filter = ["type", "statut", "operateur"]
    search_fields = ["reference_agregateur", "numero_telephone", "coffre__nom"]
    readonly_fields = ["donnees_brutes", "date_transaction"]
    date_hierarchy = "date_transaction"

    def has_add_permission(self, request):
        # Les transactions ne se créent jamais à la main : uniquement via
        # l'API + le webhook CinetPay.
        return False


@admin.register(VerificationOtp)
class VerificationOtpAdmin(admin.ModelAdmin):
    list_display = ["transaction", "expire_a", "utilise"]
    readonly_fields = ["code_hash"]
