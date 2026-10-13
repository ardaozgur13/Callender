from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_page, name="home_page"),
    path("is-ekle/", views.chore_create, name="chore_create"),
    path("is/<int:pk>/duzenle/", views.chore_edit, name="chore_edit"),
    path("is/<int:pk>/sil/", views.chore_delete, name="chore_delete"),
    path("is/<int:pk>/yaptim/", views.chore_toggle, name="chore_toggle"),
    path("durum/<str:kind>/", views.status_change, name="status_change"),
]
