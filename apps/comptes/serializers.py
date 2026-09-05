from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Utilisateur


class InscriptionSerializer(serializers.Serializer):
    nom_complet = serializers.CharField(max_length=150)
    telephone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True, validators=[validate_password])
    operateur_mobile_money = serializers.ChoiceField(choices=Utilisateur.OPERATEUR_CHOICES)

    def validate_telephone(self, value):
        if Utilisateur.objects.filter(telephone=value).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return value
