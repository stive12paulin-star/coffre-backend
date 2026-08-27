from rest_framework import serializers

from .models import Coffre


class CoffreSerializer(serializers.ModelSerializer):
    solde = serializers.DecimalField(source="solde_cache", max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Coffre
        fields = [
            "id", "nom", "montant_cible", "date_deblocage",
            "retrait_anticipe_autorise", "penalite_pourcentage",
            "statut", "solde", "date_creation",
        ]
        read_only_fields = ["id", "statut", "solde", "date_creation"]
        # le champ "pin" n'est jamais sérialisé : il arrive en clair à la
        # création via request.data, la vue le hashe, il n'est ni lu ni renvoyé
