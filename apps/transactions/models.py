from django.db import models

from apps.coffres.models import Coffre


class Transaction(models.Model):
    """Le grand livre (ledger) — source de vérité du solde d'un coffre."""

    TYPE_CHOICES = [
        ("depot", "Dépôt"),
        ("retrait", "Retrait"),
        ("penalite", "Pénalité"),
    ]
    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("reussie", "Réussie"),
        ("echouee", "Échouée"),
    ]
    OPERATEUR_CHOICES = [
        ("orange", "Orange Money"),
        ("mtn", "MTN MoMo"),
        ("moov", "Moov Money"),
        ("wave", "Wave"),
    ]

    coffre = models.ForeignKey(Coffre, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=14, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="en_attente")
    operateur = models.CharField(max_length=20, choices=OPERATEUR_CHOICES)
    numero_telephone = models.CharField(max_length=20)

    # unique=True : empêche le double crédit si CinetPay renvoie le même webhook deux fois
    reference_agregateur = models.CharField(max_length=100, unique=True, null=True, blank=True)
    donnees_brutes = models.JSONField(null=True, blank=True)

    date_transaction = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["coffre", "statut"]),
        ]

    def __str__(self):
        return f"{self.type} {self.montant} FCFA — {self.statut}"


class VerificationOtp(models.Model):
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="verifications_otp"
    )
    code_hash = models.CharField(max_length=255)
    expire_a = models.DateTimeField()
    utilise = models.BooleanField(default=False)

    class Meta:
        db_table = "verifications_otp"

    def __str__(self):
        return f"OTP pour transaction #{self.transaction_id}"
