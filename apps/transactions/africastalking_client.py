import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _normaliser_numero_ci(telephone):
    """
    Normalise un numero ivoirien au format international E.164 requis
    par Africa's Talking. Exemple : "0702664467" -> "+225702664467".
    Ne touche pas aux numeros deja au format international.
    """
    telephone = telephone.strip().replace(" ", "")
    if telephone.startswith("+"):
        return telephone
    if telephone.startswith("00"):
        return "+" + telephone[2:]
    if telephone.startswith("0"):
        return "+225" + telephone[1:]
    return "+225" + telephone


def envoyer_sms_africastalking(telephone, message):
    """
    Envoie un SMS via Africa's Talking (application production "MonCoffre").

    Tant que AT_API_KEY / AT_USERNAME ne sont pas configurees sur Render,
    le SMS est simule et le code est ecrit dans les logs au lieu d'etre
    reellement envoye.
    """
    username = getattr(settings, "AT_USERNAME", "")
    api_key = getattr(settings, "AT_API_KEY", "")
    telephone_e164 = _normaliser_numero_ci(telephone)

    if not username or not api_key:
        logger.warning(f"[SMS SIMULE - Africa's Talking pas configure] to={telephone_e164} message={message}")
        return {"simule": True, "to": telephone_e164, "message": message}

    import africastalking

    africastalking.initialize(username, api_key)
    sms = africastalking.SMS
    resultat = sms.send(message, [telephone_e164])
    logger.warning(f"[DEBUG AFRICASTALKING] reponse complete : {resultat}")
    return resultat
