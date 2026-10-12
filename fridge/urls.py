from django.urls import path

from . import views

urlpatterns = [
    path("", views.fridge_list, name="fridge"),
    path("ekle/", views.food_create, name="food_create"),
    path("<int:pk>/duzenle/", views.food_edit, name="food_edit"),
    path("<int:pk>/tuketildi/", views.food_consume, name="food_consume"),
    path("<int:pk>/bugun-actim/", views.food_open_today, name="food_open_today"),
    path("<int:pk>/sil/", views.food_delete, name="food_delete"),
]
