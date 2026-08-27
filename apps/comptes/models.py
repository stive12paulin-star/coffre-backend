from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UtilisateurManager(BaseUserManager):
    def create_user(self, telephone, mot_de_passe=None, **extra_fields):
        if not telephone:
            raise ValueError("Le numéro de téléphone est obligatoire")
        utilisateur = self.model(telephone=telephone, **extra_fields)
        utilisateur.set_password(mot_de_passe)  # hashage géré nativement par Django
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, telephone, mot_de_passe=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(telephone, mot_de_passe, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    Remplace le User par défaut de Django : on se connecte par téléphone,
    pas par email/username. Le champ mot de passe (hashé) est déjà fourni
    par AbstractBaseUser — pas besoin de le redéfinir manuellement.
    """

    OPERATEUR_CHOICES = [
        ("orange", "Orange Money"),
        ("mtn", "MTN MoMo"),
        ("moov", "Moov Money"),
        ("wave", "Wave"),
    ]
    STATUT_KYC_CHOICES = [
        ("en_attente", "En attente"),
        ("verifie", "Vérifié"),
        ("rejete", "Rejeté"),
    ]

    nom_complet = models.CharField(max_length=150)
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    operateur_mobile_money = models.CharField(max_length=20, choices=OPERATEUR_CHOICES)
    statut_kyc = models.CharField(max_length=20, choices=STATUT_KYC_CHOICES, default="en_attente")
    telephone_verifie = models.BooleanField(default=False)
    otp_verification_hash = models.CharField(max_length=255, null=True, blank=True)
    otp_verification_expire = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # accès à l'admin Django

    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = "telephone"
    REQUIRED_FIELDS = ["nom_complet"]

    class Meta:
        db_table = "utilisateurs"

    def __str__(self):
        return f"{self.nom_complet} ({self.telephone})"
