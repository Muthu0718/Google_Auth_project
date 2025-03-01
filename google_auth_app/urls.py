from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import google_drive_auth, google_drive_callback, list_drive_files, upload_file_to_drive,download_file_from_drive,delete_file_from_drive



urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("profile/", views.profile, name="profile"),
     path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path('auth/drive/', google_drive_auth, name='google_drive_auth'),
    path('auth/drive/callback/', google_drive_callback, name='google_drive_callback'),
    path('drive/files/', list_drive_files, name='drive_files'),
    path('drive/upload/', upload_file_to_drive, name='drive_upload'),
    path('drive/download/<str:file_id>/', download_file_from_drive, name='drive_download'),  
    path('drive/delete/<str:file_id>/', delete_file_from_drive, name='drive_delete'),
    

]



