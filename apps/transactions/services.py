import secrets

from django.contrib.auth.hashers import make_password
from django.db.models import Sum, Case, When, DecimalField, F


def generer_otp(longueur=6):
    """Code numérique aléatoire cryptographiquement sûr (module secrets, pas random)."""
    return "".join(secrets.choice("0123456789") for _ in range(longueur))


def envoyer_sms(telephone, message):
    """
    Envoie un SMS via le compte SMS CinetPay (distinct du compte marchand).

    En local (DEBUG=True) sans CINETPAY_SMS_APIKEY configurée, affiche le
    message dans la console au lieu d'échouer — permet de tester le parcours
    inscription/OTP sans attendre l'ouverture du compte SMS chez CinetPay.
    """
    from django.conf import settings

    if settings.DEBUG and not settings.CINETPAY_SMS_APIKEY:
        print(f"[SMS simulé — DEBUG] à {telephone} : {message}")
        return {"simule": True}

    from apps.paiements.services.cinetpay_client import CinetPayClient

    return CinetPayClient().envoyer_sms(telephone, message)


def calculer_solde(coffre):
    """
    Recalcule le solde depuis le ledger (source de vérité), à comparer à
    coffre.solde_cache pour détecter toute dérive.
    """
    from .models import Transaction  # import local pour éviter les imports circulaires

    total = Transaction.objects.filter(coffre=coffre, statut="reussie").aggregate(
        solde=Sum(
            Case(
                When(type="depot", then="montant"),
                When(type__in=["retrait", "penalite"], then=-1 * F("montant")),
                output_field=DecimalField(),
            )
        )
    )["solde"]
    return total or 0
