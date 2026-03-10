from django.urls import path
from . import views

urlpatterns = [
    path('api/sessions/<str:session_id>/summary/', views.session_summary, name='session_summary'),
]
