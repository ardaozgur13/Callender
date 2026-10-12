from django.urls import path

from . import views

urlpatterns = [
    path("", views.family_list, name="family_list"),
    path("<int:family_id>/", views.family_detail, name="family_detail"),
    path("<int:family_id>/ayril/", views.family_leave, name="family_leave"),
    path("<int:family_id>/sil/", views.family_delete, name="family_delete"),
    path("baglam/", views.switch_context, name="switch_context"),
]
