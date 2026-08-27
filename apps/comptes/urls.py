from django.urls import path

from .views import InscriptionView, RenvoyerOtpView, VerifierTelephoneView

urlpatterns = [
    path("inscription/", InscriptionView.as_view(), name="inscription"),
    path("verifier-telephone/", VerifierTelephoneView.as_view(), name="verifier-telephone"),
    path("renvoyer-otp/", RenvoyerOtpView.as_view(), name="renvoyer-otp"),
    # La connexion n'a pas besoin de vue custom : voir config/urls.py,
    # qui branche directement TokenObtainPairView de simplejwt.
]
