from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("aydinlatma-metni/", views.privacy_notice, name="privacy_notice"),
    path("gizlilik/", views.privacy_policy, name="privacy_policy"),
    path("kullanim-kosullari/", views.terms, name="terms"),
]
