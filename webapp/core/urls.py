from django.urls import path

from . import views, api_views
from . import api

urlpatterns = [
    path("", views.index, name="index"),
    path("bet/", views.bets, name="bet"),
    path("bet/create/", views.create_bet, name="bet_create"),
    path("bet/remove/", views.remove_bet, name="bet_remove"),
    path("transaction_history/", views.transaction_history, name="transaction_history"),
    path("sell/", views.sell, name="sell"),
    path("profile/", views.profile, name="profile"),
    path("login/", views.login, name="login"),
    path("signup/", views.register, name="register"),
    path("logout/", views.logout, name="logout"),
    path("api/v1/get_time", api.get_time, name="get_time"),
    path(
        "api/v1/get_next_bet_sync_time",
        api.get_next_bet_sync_time,
        name="get_next_bet_sync_time",
    ),
    path("profile/private_key/", views.private_key, name="private_key"),
    path(
        "faq/",
        views.faq,
        name="faq",
    ),
    path("api/v1/login/", api_views.login, name="api_login"),
    path("api/v1/logout/", api_views.logout, name="api_logout"),
    path("api/v1/register/", api_views.register, name="api_register"),
    path("api/v1/bets/", api_views.bets, name="api_bets"),
    path("api/v1/bet/create/", api_views.create_bet, name="api_bet_create"),
    path("api/v1/bet/remove/", api_views.remove_bet, name="api_bet_remove"),
    path("api/v1/transaction_history/", api_views.transaction_history, name="api_transaction_history"),
    path("api/v1/sell/", api_views.sell, name="api_sell"),
    path("api/v1/profile/", api_views.profile, name="api_profile"),
    path("api/v1/profile/private_key/", api_views.private_key, name="api_private_key"),
]
