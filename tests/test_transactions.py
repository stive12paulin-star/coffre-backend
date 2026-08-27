from datetime import date, timedelta

from django.test import TestCase

from apps.comptes.models import Utilisateur
from apps.coffres.models import Coffre
from apps.transactions.models import Transaction
from apps.transactions.services import calculer_solde


class LedgerTests(TestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="0700000002", mot_de_passe="motdepasse123",
            nom_complet="Test Ledger", operateur_mobile_money="mtn",
        )
        self.coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Test",
            date_deblocage=date.today() + timedelta(days=10),
            pin_hash="peu importe",
        )

    def _creer_transaction(self, type_, montant, statut="reussie"):
        return Transaction.objects.create(
            coffre=self.coffre, type=type_, montant=montant, statut=statut,
            operateur="mtn", numero_telephone="0700000002",
        )

    def test_solde_ignore_les_transactions_non_reussies(self):
        self._creer_transaction("depot", 10000, statut="en_attente")
        self._creer_transaction("depot", 5000, statut="echouee")
        self.assertEqual(calculer_solde(self.coffre), 0)

    def test_solde_additionne_depots_et_soustrait_retraits(self):
        self._creer_transaction("depot", 10000)
        self._creer_transaction("depot", 5000)
        self._creer_transaction("retrait", 3000)
        self.assertEqual(calculer_solde(self.coffre), 12000)
