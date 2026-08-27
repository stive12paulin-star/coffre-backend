from datetime import date, timedelta

from django.test import TestCase

from apps.comptes.models import Utilisateur
from apps.coffres.models import Coffre


class CoffreModelTests(TestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user(
            telephone="0700000001", mot_de_passe="motdepasse123",
            nom_complet="Test User", operateur_mobile_money="orange",
        )

    def test_pin_est_hashe_et_verifiable(self):
        coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Vacances",
            date_deblocage=date.today() + timedelta(days=30),
        )
        coffre.definir_pin("1234")
        coffre.save()

        self.assertNotEqual(coffre.pin_hash, "1234")  # jamais stocké en clair
        self.assertTrue(coffre.verifier_pin("1234"))
        self.assertFalse(coffre.verifier_pin("0000"))

    def test_coffre_non_debloquable_avant_la_date(self):
        coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Futur",
            date_deblocage=date.today() + timedelta(days=1),
            pin_hash="peu importe",
        )
        self.assertFalse(coffre.est_debloquable())

    def test_coffre_debloquable_le_jour_meme(self):
        coffre = Coffre.objects.create(
            utilisateur=self.utilisateur, nom="Aujourd'hui",
            date_deblocage=date.today(),
            pin_hash="peu importe",
        )
        self.assertTrue(coffre.est_debloquable())
