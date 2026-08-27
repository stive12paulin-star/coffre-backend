from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.coffres.urls")),
    path("api/", include("apps.paiements.urls")),
    path("api/auth/", include("apps.comptes.urls")),
    path("api/auth/connexion/", TokenObtainPairView.as_view(), name="connexion"),
    path("api/auth/rafraichir/", TokenRefreshView.as_view(), name="rafraichir-token"),
]
