from django.contrib import admin
from django.urls import path, include
from django.contrib import admin
from django.urls import path, include
from google_auth_app.views import home



urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('social_django.urls', namespace='social')),
    path('', include('google_auth_app.urls')),
    path("", home, name="home"),
    path("chat/", include("chat.urls")), 
]

