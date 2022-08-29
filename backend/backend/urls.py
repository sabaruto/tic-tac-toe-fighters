"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework import routers
from aiTicTacToe import views

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', views.LoginView.as_view(), name="login"),
    path('api/fighters/', views.FighterList.as_view(), name="fighterList"),
    path('api/fighters/<str:pk>', views.FighterDetails.as_view(), name='fighterDetails'),
    path('api/plays/<str:game_pk>/', views.PlayList.as_view(), name="play"),
    path('api/game/new/', views.NewGame.as_view(), name="newGame"),
    path('api/game/<str:pk>/', views.PlayGame.as_view(), name="playGame"),
    path('api/game/<str:pk>/details/', views.GameDetails.as_view(), name="gameDetails"),
    path('api/game/<str:game_pk>/cells/', views.CellDetails.as_view(), name="cellDetails"),
    path('api/node/new/', views.NewNode.as_view(), name="newNode"),
    path('api/pool/', views.PoolList.as_view(), name="poolList"),
    path('api/pool/<str:pk>/', views.PoolDetails.as_view(), name="poolDetails"),
    path('api/pool/<str:pk>/fighters', views.PoolFightersList.as_view(), name="poolFighters"),
    path('api/pool/<str:pk>/games', views.PoolGameList.as_view(), name="poolGames"),
]
