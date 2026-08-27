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

BASE_CHECKOUT_URL = "https://api-checkout.cinetpay.com/v2"
BASE_TRANSFER_URL = "https://client.cinetpay.com/v1"
BASE_SMS_URL = "https://api-notitia.cinetpay.com/sms/1"


class CinetPayError(Exception):
    pass


class CinetPayClient:
    def __init__(self):
        self.apikey = settings.CINETPAY_APIKEY
        self.site_id = settings.CINETPAY_SITE_ID
        self.apikey_sms = settings.CINETPAY_SMS_APIKEY  # compte SMS séparé du compte marchand

    # ---------------------------------------------------------------
    # ENCAISSEMENT (dépôt dans le coffre) — confirmé par la doc
    # ---------------------------------------------------------------

    def initier_paiement(self, transaction_id, montant, telephone, nom, prenom, notify_url, return_url):
        """
        Démarre un dépôt. Retourne le payment_token à utiliser pour rediriger
        l'utilisateur vers le guichet de paiement CinetPay.
        """
        payload = {
            "apikey": self.apikey,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
            "amount": int(montant),  # XOF n'a pas de sous-unité
            "currency": "XOF",
            "description": "Dépôt coffre",
            "customer_name": nom,
            "customer_surname": prenom,
            "customer_phone_number": telephone,
            "notify_url": notify_url,
            "return_url": return_url,
            "channels": "MOBILE_MONEY",
        }
        reponse = requests.post(f"{BASE_CHECKOUT_URL}/payment", json=payload, timeout=15)
        data = reponse.json()
        if data.get("code") != "201":
            raise CinetPayError(data.get("description", "Échec de l'initialisation du paiement"))
        return data["data"]["payment_token"]

    def verifier_paiement(self, transaction_id):
        """
        À appeler à chaque réception du webhook /api/webhooks/cinetpay.

        Rappel doc CinetPay : le POST reçu sur notify_url ne contient PAS le
        statut réel (anti man-in-the-middle) — seul cpm_trans_id est fiable.
        Le vrai statut ne vient QUE de cet appel de vérification.
        """
        payload = {
            "apikey": self.apikey,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
        }
        reponse = requests.post(f"{BASE_CHECKOUT_URL}/payment/check", json=payload, timeout=15)
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

    def ajouter_contact(self, telephone, nom, prenom):
        """
        Prérequis documenté : le numéro du bénéficiaire doit exister dans la
        liste de contacts CinetPay AVANT de pouvoir lui envoyer de l'argent.
        À appeler une fois par utilisateur (idempotent côté CinetPay).
        """
        token = self._obtenir_token_transfert()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"data": [{"prefix": "225", "phone": telephone, "name": nom, "surname": prenom}]}
        reponse = requests.post(
            f"{BASE_TRANSFER_URL}/transfer/contact", json=payload, headers=headers, timeout=15
        )
        return reponse.json()

    def envoyer_argent(self, telephone, montant, notify_url):
        """
        ⚠️ Par défaut, CinetPay exige une confirmation MANUELLE du marchand
        pour chaque transfert (back-office ou email). Un flux 100% automatique
        nécessite une autorisation spéciale de CinetPay (IP serveur à
        whitelister) — à demander à support@cinetpay.com avant la prod.
        En attendant cette autorisation, prévoir une file d'attente de
        validation côté admin Django pour les retraits.
        """
        token = self._obtenir_token_transfert()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "data": [{"prefix": "225", "phone": telephone, "amount": int(montant), "notify_url": notify_url}]
        }
        reponse = requests.post(
            f"{BASE_TRANSFER_URL}/transfer/money/send/contact", json=payload, headers=headers, timeout=15
        )
        return reponse.json()

    def verifier_transfert(self, transaction_id):
        """
        Vérifie le statut réel d'un retrait — même logique que pour
        l'encaissement : ne jamais se fier uniquement au webhook.
        Endpoint confirmé par la doc ; nom exact du champ de statut renvoyé
        à confirmer avec ton compte marchand.
        """
        token = self._obtenir_token_transfert()
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"transaction_id": transaction_id}  # nom de champ à confirmer
        reponse = requests.post(
            f"{BASE_TRANSFER_URL}/transfer/check/money", json=payload, headers=headers, timeout=15
        )
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
