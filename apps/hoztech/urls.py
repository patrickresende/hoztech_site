from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contato/', views.contato, name='contato'),
    path('privacy-modal/', views.privacy_modal, name='privacy_modal'),
    path('api/cookies/preferences/', views.update_cookie_preferences, name='update_cookie_preferences'),
    path('api/cookies/preferences/<uuid:client_id>/', views.get_cookie_preferences, name='get_cookie_preferences'),
    path('api/cookies/export/', views.export_cookie_preferences, name='export_cookie_preferences'),
]