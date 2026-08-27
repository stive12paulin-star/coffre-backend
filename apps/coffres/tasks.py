from celery import shared_task
from django.utils import timezone

from .models import Coffre
from apps.transactions.services import envoyer_sms


@shared_task
def notifier_coffres_debloques():
    """
    Cherche les coffres actifs dont la date_deblocage est atteinte,
    notifie l'utilisateur par SMS, et passe leur statut à "debloque".

    Ne transfère jamais d'argent : le retrait effectif reste une action
    volontaire de l'utilisateur (PIN + OTP), voir coffres/views.py.
    """
    aujourdhui = timezone.now().date()

    # list() : on fige la liste avant de modifier les statuts, sinon le
    # queryset filtré (statut="actif") se vide au fur et à mesure de la boucle
    coffres_a_debloquer = list(
        Coffre.objects.filter(statut="actif", date_deblocage__lte=aujourdhui)
    )

    for coffre in coffres_a_debloquer:
        envoyer_sms(
            coffre.utilisateur.telephone,
            f"Ton coffre « {coffre.nom} » est débloqué. Tu peux retirer ton solde.",
        )
        coffre.statut = "debloque"
        coffre.save(update_fields=["statut"])

    return f"{len(coffres_a_debloquer)} coffre(s) débloqué(s)"
