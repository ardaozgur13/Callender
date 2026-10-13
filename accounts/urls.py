from django.urls import path

from . import views

urlpatterns = [
    path("giris/", views.LoginView.as_view(), name="login"),
    path("kayit/", views.register, name="register"),
    path("cikis/", views.logout_view, name="logout"),
    path("ayarlar/", views.account_settings, name="settings"),
    path("ayarlar/hesabi-sil/", views.delete_account, name="delete_account"),
    path("ayarlar/verilerim.json", views.export_data, name="export_data"),
]
