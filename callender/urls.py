from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("takvim/", include("calendar_app.urls")),
    path("aile/", include("families.urls")),
    path("buzdolabi/", include("fridge.urls")),
    path("ev/", include("home.urls")),
    path("", include("core.urls")),
]
