import secrets

from django.contrib.auth.hashers import make_password
from django.db.models import Sum, Case, When, DecimalField, F


def generer_otp(longueur=6):
    """Code numérique aléatoire cryptographiquement sûr (module secrets, pas random)."""
    return "".join(secrets.choice("0123456789") for _ in range(longueur))


def envoyer_sms(telephone, message):
    """
    Envoie un SMS via Africa's Talking (remplace CinetPay, dont le compte
    SMS ne peut pas être activé sans structure légalement enregistrée).
    """
    from .africastalking_client import envoyer_sms_africastalking

    return envoyer_sms_africastalking(telephone, message)


def calculer_solde(coffre):
    """
    Recalcule le solde depuis le ledger (source de vérité), à comparer à
    coffre.solde_cache pour détecter toute dérive.
    """
    from .models import Transaction  # import local pour éviter les imports circulaires
