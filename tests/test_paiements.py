from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Utilisateur
from apps.coffres.models import Coffre
from apps.transactions.models import Transaction


class WebhookIdempotenceTests(TestCase):
    """
    Le test le plus important du projet : CinetPay peut renvoyer le même
    webhook plusieurs fois (retry réseau, etc.). S'il crédite le coffre à
    chaque appel, c'est de l'argent créé à partir de rien.
    """

    def setUp(self):
        self.client_api = APIClient()
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="0700000003", mot_de_passe="motdepasse123",
            nom_complet="Test Webhook", operateur_mobile_money="orange",
        )
        self.coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Test",
            date_deblocage=date.today() + timedelta(days=10),
            pin_hash="peu importe",
        )
        self.transaction = Transaction.objects.create(
            coffre=self.coffre, type="depot", montant=10000,
            statut="en_attente", operateur="orange",
            numero_telephone="0700000003",
            reference_agregateur="depot-test-123",
        )

    @patch("apps.paiements.services.cinetpay_client.CinetPayClient.verifier_paiement")
    def test_webhook_appele_deux_fois_ne_credite_qu_une_fois(self, mock_verifier):
        mock_verifier.return_value = {"data": {"status": "ACCEPTED"}}

        url = reverse("webhook-cinetpay")
        payload = {"cpm_trans_id": "depot-test-123"}

        self.client_api.post(url, payload)
        self.client_api.post(url, payload)  # le même webhook arrive deux fois

        self.coffre.refresh_from_db()
        self.assertEqual(self.coffre.solde_cache, 10000)  # jamais 20000
        # le 2e appel doit être court-circuité par le check "statut == reussie"
        self.assertEqual(mock_verifier.call_count, 1)

    @patch("apps.paiements.services.cinetpay_client.CinetPayClient.verifier_paiement")
    def test_paiement_refuse_par_cinetpay_ne_credite_pas(self, mock_verifier):
        mock_verifier.return_value = {"data": {"status": "REFUSED"}}

        url = reverse("webhook-cinetpay")
        self.client_api.post(url, {"cpm_trans_id": "depot-test-123"})

        self.coffre.refresh_from_db()
        self.transaction.refresh_from_db()
        self.assertEqual(self.coffre.solde_cache, 0)
        self.assertEqual(self.transaction.statut, "echouee")
