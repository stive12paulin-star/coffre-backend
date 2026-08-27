from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone

from apps.comptes.models import Utilisateur


class Coffre(models.Model):
    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("debloque", "Débloqué"),
        ("cloture", "Clôturé"),
    ]

    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name="coffres"
    )
    nom = models.CharField(max_length=100)
    pin_hash = models.CharField(max_length=255)
    montant_cible = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_deblocage = models.DateField()
    retrait_anticipe_autorise = models.BooleanField(default=False)
    penalite_pourcentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="actif")

    # Dérivé du ledger (app transactions) — jamais la source de vérité,
    # juste un cache recalculé après chaque transaction validée.
    solde_cache = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "coffres"
        indexes = [
            models.Index(fields=["date_deblocage"]),  # utilisé par le job quotidien
        ]

    def definir_pin(self, pin_clair):
        self.pin_hash = make_password(pin_clair)

    def verifier_pin(self, pin_clair):
        return check_password(pin_clair, self.pin_hash)

    def est_debloquable(self):
        return timezone.now().date() >= self.date_deblocage

    def __str__(self):
        return f"{self.nom} — {self.utilisateur.telephone}"
