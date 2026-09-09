import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def envoyer_sms_africastalking(telephone, message):
    """
    Envoie un SMS via Africa's Talking (application production "MonCoffre").

    Tant que AT_API_KEY / AT_USERNAME ne sont pas configurees sur Render,
    le SMS est simule et le code est ecrit dans les logs au lieu d'etre
    reellement envoye.
    """
    username = getattr(settings, "AT_USERNAME", "")
    api_key = getattr(settings, "AT_API_KEY", "")

    if not username or not api_key:
        logger.warning(f"[SMS SIMULE - Africa's Talking pas configure] to={telephone} message={message}")
        return {"simule": True, "to": telephone, "message": message}

    import africastalking

    africastalking.initialize(username, api_key)
    sms = africastalking.SMS
    return sms.send(message, [telephone])
