import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Coffre
from .serializers import CoffreSerializer
from apps.transactions.models import Transaction, VerificationOtp
from apps.transactions.services import generer_otp, envoyer_sms
from apps.paiements.services.cinetpay_client import CinetPayClient, CinetPayError


class CoffreViewSet(viewsets.ModelViewSet):
    serializer_class = CoffreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Coffre.objects.filter(utilisateur=self.request.user)

    def perform_create(self, serializer):
        coffre = serializer.save(utilisateur=self.request.user)
        coffre.definir_pin(self.request.data.get("pin"))
        coffre.save()

    def perform_update(self, serializer):
        coffre = self.get_object()
        nouvelle_date = serializer.validated_data.get("date_deblocage")
        if nouvelle_date and nouvelle_date < coffre.date_deblocage:
            raise ValidationError("La date de déblocage ne peut pas être avancée.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        coffre = self.get_object()
        if coffre.solde_cache != 0:
            return Response({"erreur": "Le coffre doit être vide pour être clôturé."}, status=400)
        return super().destroy(request, *args, **kwargs)

    # -----------------------------------------------------------
    # DÉPÔT — encaissement CinetPay
    # -----------------------------------------------------------
    @action(detail=True, methods=["post"])
    def depots(self, request, pk=None):
        coffre = self.get_object()
        montant = Decimal(str(request.data["montant"]))
        telephone = request.data["numero_telephone"]
        operateur = request.data["operateur"]

        reference = f"depot-{uuid.uuid4().hex[:16]}"
        transaction = Transaction.objects.create(
            coffre=coffre, type="depot", montant=montant,
            operateur=operateur, numero_telephone=telephone,
            reference_agregateur=reference,
        )

        try:
            payment_token = CinetPayClient().initier_paiement(
                transaction_id=reference,
                montant=montant,
                telephone=telephone,
                nom=request.user.nom_complet.split()[0],
                prenom=" ".join(request.user.nom_complet.split()[1:]) or "-",
                email=request.user.email,
                notify_url=f"{settings.BASE_URL}/api/webhooks/cinetpay",
                success_url=f"{settings.FRONTEND_URL}/coffres/{coffre.id}?paiement=succes",
                failed_url=f"{settings.FRONTEND_URL}/coffres/{coffre.id}?paiement=echec",
            )
        except CinetPayError as e:
            transaction.statut = "echouee"
            transaction.save()
            return Response({"erreur": str(e)}, status=502)

        # statut reste "en_attente" — confirmé uniquement par le webhook
        return Response({"transaction_id": transaction.id, "payment_token": payment_token}, status=201)

    # -----------------------------------------------------------
    # RETRAIT — étape 1 : PIN + éligibilité, envoi de l'OTP
    # -----------------------------------------------------------
    @action(detail=True, methods=["post"])
    def retraits(self, request, pk=None):
        coffre = self.get_object()
        pin = request.data.get("pin", "")
        montant = Decimal(str(request.data["montant"]))

        if not coffre.verifier_pin(pin):
            return Response({"erreur": "PIN incorrect."}, status=403)
        if not coffre.est_debloquable() and not coffre.retrait_anticipe_autorise:
            return Response({"erreur": "Coffre encore verrouillé."}, status=403)
        if montant > coffre.solde_cache:
            return Response({"erreur": "Solde insuffisant."}, status=400)

        reference = f"retrait-{uuid.uuid4().hex[:16]}"
        transaction = Transaction.objects.create(
            coffre=coffre, type="retrait", montant=montant,
            operateur=request.user.operateur_mobile_money,
            numero_telephone=request.user.telephone,
            reference_agregateur=reference,
        )
        code = generer_otp()
        VerificationOtp.objects.create(
            transaction=transaction,
            code_hash=make_password(code),
            expire_a=timezone.now() + timezone.timedelta(minutes=5),
        )
        envoyer_sms(request.user.telephone, f"Code de confirmation de retrait : {code}")

        return Response({"transaction_id": transaction.id}, status=201)

    # -----------------------------------------------------------
    # RETRAIT — étape 2 : confirmation OTP, déclenchement du transfert
    # -----------------------------------------------------------
    @action(
        detail=True, methods=["post"],
        url_path=r"retraits/(?P<transaction_id>[^/.]+)/confirmer",
    )
    def confirmer_retrait(self, request, pk=None, transaction_id=None):
        coffre = self.get_object()
        transaction = coffre.transactions.get(id=transaction_id, type="retrait", statut="en_attente")
        verification = transaction.verifications_otp.filter(utilise=False).latest("id")

        if timezone.now() > verification.expire_a:
            return Response({"erreur": "Code expiré."}, status=400)
        if not check_password(request.data.get("code_otp", ""), verification.code_hash):
            return Response({"erreur": "Code incorrect."}, status=403)

        verification.utilise = True
        verification.save()

        client = CinetPayClient()
        try:
            resultat = client.envoyer_argent(
                transaction_id=transaction.reference_agregateur,
                telephone=transaction.numero_telephone,
                montant=transaction.montant,
                operateur=transaction.operateur,
                notify_url=f"{settings.BASE_URL}/api/webhooks/cinetpay",
            )
        except CinetPayError as e:
            transaction.statut = "echouee"
            transaction.save()
            return Response({"erreur": str(e)}, status=502)

        # Même logique que le dépôt : la confirmation définitive et le
        # débit du solde arrivent par webhook, pas ici (voir paiements/views.py)
        transaction.donnees_brutes = resultat
        transaction.save()

        return Response({"transaction_id": transaction.id, "statut": "en_attente"}, status=202)
