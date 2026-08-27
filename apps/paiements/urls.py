from django.urls import path

from .views import WebhookCinetPayView

urlpatterns = [
    path("webhooks/cinetpay/", WebhookCinetPayView.as_view(), name="webhook-cinetpay"),
]
