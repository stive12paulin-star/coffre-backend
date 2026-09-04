"""
Client CinetPay — app paiements/services/cinetpay_client.py

Sources : documentation officielle docs.cinetpay.com (Checkout + Transfert).

⚠️ Le module Checkout (encaissement) est documenté de façon complète et fiable.
Le module Transfert (retrait) confirme le FLUX (auth → token, ajout de contact
obligatoire avant envoi, confirmation manuelle par défaut) mais certains noms
exacts de champs JSON n'étaient pas visibles dans la documentation publique —
à confirmer dans l'onglet "Intégrations" de ton compte marchand une fois
inscrit, ou auprès de support@cinetpay.com avant la mise en production.
"""

import requests
from django.conf import settings

BASE_URL = "https://api.cinetpay.net"
BASE_CHECKOUT_URL = BASE_URL
BASE_TRANSFER_URL = BASE_URL
BASE_SMS_URL = BASE_URL
CODES_OPERATEURS = {
    "orange": "OM_CI",
    "mtn": "MTN_CI",
    "moov": "MOOV_CI",
    "wave": "WAVE_CI",
}


class CinetPayError(Exception):
    pass


class CinetPayClient:
    def __init__(self):
        self.api_key = settings.CINETPAY_APIKEY
        self.api_password = settings.CINETPAY_API_PASSWORD
        self.apikey_sms = settings.CINETPAY_SMS_APIKEY
        self._token = None

    def _obtenir_token(self):
        if self._token:
            return self._token
        payload = {"api_key": self.api_key, "api_password": self.api_password}
        reponse = requests.post(f"{BASE_URL}/v1/oauth/login", json=payload, timeout=15)
        data = reponse.json()
        self._token = data["access_token"]  # nom exact du champ a confirmer
        return self._token

    # ---------------------------------------------------------------
    # ENCAISSEMENT (dépôt dans le coffre) — confirmé par la doc
    # ---------------------------------------------------------------

   def initier_paiement(self, transaction_id, montant, telephone, nom, prenom, email, notify_url, success_url, failed_url):
    """
    Demarre un depot. Retourne payment_url pour rediriger
    l'utilisateur vers le guichet de paiement CinetPay.
    """
    token = self._obtenir_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "currency": "XOF",
        "merchant_transaction_id": transaction_id,
        "amount": int(montant),
        "lang": "fr",
        "designation": "Depot coffre",
        "client_first_name": prenom,
        "client_last_name": nom,
        "client_email": email,
        "client_phone_number": telephone,
        "success_url": success_url,
        "failed_url": failed_url,
        "notify_url": notify_url,
        "direct_pay": False,
    }
    reponse = requests.post(f"{BASE_URL}/v1/payment", json=payload, headers=headers, timeout=15)
    data = reponse.json()
    if data.get("code") != 200:
        raise CinetPayError(data.get("status"), "Echec de l'initialisation du paiement")
    return data["payment_url"]


   def verifier_paiement(self, transaction_id):
    """
    A appeler a chaque reception du webhook /api/webhooks/cinetpay.
    Verifie le vrai statut via l'API (GET), ne jamais se fier
    uniquement au webhook.
    """
    token = self._obtenir_token()
    headers = {"Authorization": f"Bearer {token}"}
    reponse = requests.get(f"{BASE_URL}/v1/payment/{transaction_id}", headers=headers, timeout=15)
    return reponse.json()

    # ---------------------------------------------------------------
    # TRANSFERT (retrait depuis le coffre) — flux confirmé,
    # champs exacts à vérifier avec ton compte marchand
    # ---------------------------------------------------------------

    def _obtenir_token_transfert(self):
        payload = {
            "apikey": self.apikey,
            "password": settings.CINETPAY_TRANSFER_PASSWORD,  # nom de champ à confirmer
        }
        reponse = requests.post(f"{BASE_TRANSFER_URL}/auth/login", data=payload, timeout=15)
        data = reponse.json()
        if data.get("code") != 0:
            raise CinetPayError(data.get("description", "Échec d'authentification transfert"))
        return data["data"]["token"]

def envoyer_argent(self, transaction_id, telephone, montant, operateur, notify_url):
    """
    Effectue un retrait/transfert vers mobile money.
    'operateur' = la valeur stockee sur l'utilisateur (orange/mtn/moov/wave).
    Plus besoin d'ajouter le contact au prealable (nouveau systeme).
    """
    token = self._obtenir_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "currency": "XOF",
        "payment_method": CODES_OPERATEURS.get(operateur, "OM_CI"),
        "merchant_transaction_id": transaction_id,
        "amount": int(montant),
        "phone_number": telephone,
        "reason": "Retrait coffre",
        "notify_url": notify_url,
    }
    reponse = requests.post(f"{BASE_URL}/v1/transfer", json=payload, headers=headers, timeout=15)
    return reponse.json()

   def verifier_transfert(self, transaction_id):
    """
    Verifie le statut reel d'un retrait - meme logique que pour
    l'encaissement : ne jamais se fier uniquement au webhook.
    """
    token = self._obtenir_token()
    headers = {"Authorization": f"Bearer {token}"}
    reponse = requests.get(f"{BASE_URL}/v1/transfer/{transaction_id}", headers=headers, timeout=15)
    return reponse.json()

    # ---------------------------------------------------------------
    # SMS (OTP inscription et retraits) — confirmé par la doc
    # ---------------------------------------------------------------

    def envoyer_sms(self, telephone, message, expediteur="COFFRE"):
        """
        Nécessite un compte SMS CinetPay (distinct du compte marchand,
        demandé à hello@cinetpay.com). Le nom d'expéditeur est en général
        soumis à validation par CinetPay avant la mise en production.
        """
        headers = {
            "Authorization": f"App {self.apikey_sms}",
            "Content-Type": "application/json",
        }
        payload = {"from": expediteur, "to": [telephone], "text": message}
        reponse = requests.post(f"{BASE_SMS_URL}/text/single", json=payload, headers=headers, timeout=15)
        return reponse.json()
