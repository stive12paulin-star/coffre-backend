from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Utilisateur
from .serializers import InscriptionSerializer
from apps.transactions.services import envoyer_sms, generer_otp


class InscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data

        utilisateur = Utilisateur.objects.create_user(
            telephone=donnees["telephone"],
            mot_de_passe=donnees["mot_de_passe"],
            nom_complet=donnees["nom_complet"],
            operateur_mobile_money=donnees["operateur_mobile_money"],
        )

        code = generer_otp()
        utilisateur.otp_verification_hash = make_password(code)
        utilisateur.otp_verification_expire = timezone.now() + timezone.timedelta(minutes=10)
        utilisateur.save()

        envoyer_sms(utilisateur.telephone, f"Code de vérification : {code}")

        return Response(
            {"message": "Compte créé. Code de vérification envoyé par SMS."}, status=201
        )


class VerifierTelephoneView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        telephone = request.data.get("telephone")
        code = request.data.get("code_otp", "")

        try:
            utilisateur = Utilisateur.objects.get(telephone=telephone, telephone_verifie=False)
        except Utilisateur.DoesNotExist:
            return Response({"erreur": "Compte introuvable ou déjà vérifié."}, status=404)

        if not utilisateur.otp_verification_hash or timezone.now() > utilisateur.otp_verification_expire:
            return Response({"erreur": "Code expiré, demande un nouvel envoi."}, status=400)
        if not check_password(code, utilisateur.otp_verification_hash):
            return Response({"erreur": "Code incorrect."}, status=403)

        utilisateur.telephone_verifie = True
        utilisateur.otp_verification_hash = None
        utilisateur.otp_verification_expire = None
        utilisateur.save()

        return Response({"message": "Téléphone vérifié."}, status=200)


class RenvoyerOtpView(APIView):
    """
    Renvoi du code, utile si le premier (valable 10 min) a expiré.
    Pas de limite de débit pour l'instant — à ajouter (DRF throttling)
    avant la mise en production pour éviter le spam SMS.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        telephone = request.data.get("telephone")

        try:
            utilisateur = Utilisateur.objects.get(telephone=telephone, telephone_verifie=False)
        except Utilisateur.DoesNotExist:
            return Response({"erreur": "Compte introuvable ou déjà vérifié."}, status=404)

        code = generer_otp()
        utilisateur.otp_verification_hash = make_password(code)
        utilisateur.otp_verification_expire = timezone.now() + timezone.timedelta(minutes=10)
        utilisateur.save()

        envoyer_sms(utilisateur.telephone, f"Nouveau code de vérification : {code}")

        return Response({"message": "Nouveau code envoyé."}, status=200)
