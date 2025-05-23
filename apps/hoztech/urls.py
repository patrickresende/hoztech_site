from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contato/', views.contato, name='contato'),
    path('privacy-modal/', views.privacy_modal, name='privacy_modal'),
    path('api/cookies/preferences/', views.update_cookie_preferences, name='update_cookie_preferences'),
    path('api/cookies/preferences/<uuid:client_id>/', views.get_cookie_preferences, name='get_cookie_preferences'),
    path('api/cookies/export/', views.export_cookie_preferences, name='export_cookie_preferences'),
    path('privacy/', views.privacy_modal, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path('admin-auth-user/', views.AdminLoginView.as_view(), name='admin_login'),
    path('admin-auth-user/2fa/', views.Admin2FAVerifyView.as_view(), name='admin_2fa_verify'),
    path('admin-auth-user/2fa/settings/', views.admin_2fa_settings, name='admin_2fa_settings'),
    path('admin-auth-user/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-auth-user/logout/', views.admin_logout, name='admin_logout'),
    path('admin-auth-user/visitors/', views.visitor_list, name='admin_visitors'),
    path('admin-auth-user/cookies/', views.cookie_list, name='admin_cookies'),
    path('admin-auth-user/cookies/export/', views.export_cookie_preferences, name='admin_cookies_export'),
    path('admin-auth-user/cookies/manage/', views.manage_cookies_api, name='admin_cookies_manage'),
    path('admin-auth-user/export/', views.AdminExportView.as_view(), name='admin_export'),
    path('admin-auth-user/export/data/', views.export_data, name='admin_export_data'),
    path('admin-auth-user/download/<uuid:export_id>/', views.download_export, name='admin_download'),
    path('download-pdf/', views.download_pdf, name='download_pdf'),
    path('admin-auth-user/downloads/', views.admin_downloads_list, name='admin_downloads_list'),
]