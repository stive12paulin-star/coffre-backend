import logging

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.transactions.models import Transaction
from .services.cinetpay_client import CinetPayClient

logger = logging.getLogger(__name__)


class WebhookCinetPayView(APIView):
    """
    Reçoit les notifications CinetPay pour les dépôts (checkout) ET les
    retraits (transfert) — même URL, distinguée ici via transaction.type.

    Rappel : le POST reçu ne contient PAS le vrai statut (anti man-in-the-
    middle, cf. doc CinetPay). On ne fait confiance qu'à
    merchant_transaction_id pour retrouver la transaction, puis on rappelle
    l'API pour la vérité.
    """
    permission_classes = [AllowAny]  # CinetPay n'envoie pas de JWT

    def post(self, request):
        logger.warning(f"[DEBUG WEBHOOK] contenu brut recu : {request.data}")

        reference = (
            request.data.get("merchant_transaction_id")
            or request.data.get("cpm_trans_id")  # ancien systeme, au cas ou
            or request.POST.get("cpm_trans_id")
        )
        if not reference:
            return Response(status=400)

        try:
            transaction = Transaction.objects.get(reference_agregateur=reference)
        except Transaction.DoesNotExist:
            return Response(status=404)

        # Idempotence : un webhook peut arriver plusieurs fois
        if transaction.statut == "reussie":
            return Response(status=200)

        client = CinetPayClient()

        if transaction.type == "depot":
            resultat = client.verifier_paiement(reference)
            statut_recu = resultat.get("data", {}).get("status")
            reussi = statut_recu in ("SUCCESS", "ACCEPTED")
        else:  # retrait
            resultat = client.verifier_transfert(reference)
            statut_recu = resultat.get("data", {}).get("status")
            reussi = statut_recu in ("SUCCESS", "VAL", "COMPLETED")

        logger.warning(f"[DEBUG WEBHOOK] statut recu de CinetPay : {statut_recu} (type={transaction.type})")

        transaction.donnees_brutes = resultat

        if reussi:
            transaction.statut = "reussie"
            coffre = transaction.coffre
            if transaction.type == "depot":
                coffre.solde_cache += transaction.montant
            else:
                coffre.solde_cache -= transaction.montant
            coffre.save()
        else:
            transaction.statut = "echouee"

        transaction.save()
        return Response(status=200)
