from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Utilisateur
from apps.coffres.models import Coffre


class RetraitViewTests(TestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="0700000004", mot_de_passe="motdepasse123",
            nom_complet="Test Retrait", operateur_mobile_money="moov",
        )
        self.coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Verrouillé",
            date_deblocage=date.today() + timedelta(days=5),
            solde_cache=10000,
        )
        self.coffre.definir_pin("1234")
        self.coffre.save()

        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.utilisateur)

    def test_retrait_refuse_si_pin_incorrect(self):
        url = reverse("coffre-retraits", kwargs={"pk": self.coffre.id})
        reponse = self.client_api.post(url, {"pin": "0000", "montant": 1000})
        self.assertEqual(reponse.status_code, 403)

    def test_retrait_refuse_si_coffre_encore_verrouille(self):
        url = reverse("coffre-retraits", kwargs={"pk": self.coffre.id})
        reponse = self.client_api.post(url, {"pin": "1234", "montant": 1000})
        self.assertEqual(reponse.status_code, 403)

    def test_retrait_refuse_si_montant_superieur_au_solde(self):
        self.coffre.date_deblocage = date.today()
        self.coffre.save()
        url = reverse("coffre-retraits", kwargs={"pk": self.coffre.id})
        reponse = self.client_api.post(url, {"pin": "1234", "montant": 999999})
        self.assertEqual(reponse.status_code, 400)
