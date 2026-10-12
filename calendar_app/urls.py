from django.urls import path

from . import views

urlpatterns = [
    path("", views.month_view, name="calendar"),
    path("<int:year>/<int:month>/", views.month_view, name="calendar_month"),
    path("<int:year>/<int:month>/<int:day>/", views.day_view, name="calendar_day"),
    path("ekle/", views.item_create, name="item_create"),
    path("oge/<int:pk>/duzenle/", views.item_edit, name="item_edit"),
    path("oge/<int:pk>/sil/", views.item_delete, name="item_delete"),
    path("oge/<int:pk>/tamamla/", views.item_toggle_done, name="item_toggle_done"),
]
