from rest_framework.routers import DefaultRouter

from .views import CoffreViewSet

router = DefaultRouter()
router.register(r"coffres", CoffreViewSet, basename="coffre")

# Génère automatiquement, entre autres :
#   POST /coffres/{pk}/depots/
#   POST /coffres/{pk}/retraits/
#   POST /coffres/{pk}/retraits/{transaction_id}/confirmer/
urlpatterns = router.urls
