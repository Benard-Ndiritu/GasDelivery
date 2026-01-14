from django.urls import path
from . import views
from .views import RegisterUser, LoginUser

urlpatterns = [
    path('register/', views.RegisterUser.as_view()),
    path('login/', views.LoginUser.as_view()),
]


urlpatterns = [
    path('register/', RegisterUser.as_view()),
    path('login/', LoginUser.as_view()),
]
