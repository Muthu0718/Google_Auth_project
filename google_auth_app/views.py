from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
import os
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import google.oauth2.credentials
import google_auth_oauthlib.flow
from django.urls import reverse
from googleapiclient.http import MediaIoBaseDownload
import io
from django.http import HttpResponse, JsonResponse


def save_google_credentials(request, credentials):
    """Save OAuth credentials to session"""
    request.session['google_credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }

def google_auth_callback(request):
    """Handle Google OAuth callback after login"""
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json', 
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    flow.redirect_uri = "http://127.0.0.1:8000/google/callback/"
    
    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials  
    save_google_credentials(request, credentials) 

    return redirect('/drive/upload/')



def home(request):
    return HttpResponse("Hello, Google Auth Project is running!")


@login_required
def profile(request):
    user = request.user
    social = user.social_auth.get(provider='google-oauth2')
    user_data = social.extra_data  

    return render(request, "profile.html", {"user_data": user_data})
def logout_view(request):
    logout(request)
    return redirect('/')


def login_view(request):
    return redirect("/auth/login/google-oauth2/")

def google_drive_auth(request):
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/drive.file'],
        redirect_uri="http://127.0.0.1:8000/auth/drive/callback/"  
    )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return redirect(auth_url)

def google_drive_callback(request):
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=settings.GOOGLE_DRIVE_SCOPES,
        redirect_uri='http://127.0.0.1:8000/auth/drive/callback/'
    )
    flow.fetch_token(code=request.GET.get('code'))

    credentials = flow.credentials
    request.session['google_drive_credentials'] = credentials_to_dict(credentials)

    return redirect('drive_files')

import google.oauth2.credentials

def get_google_credentials(request):
    creds_data = request.session.get('google_drive_credentials') 

    if not creds_data:
        return None 

    credentials = google.oauth2.credentials.Credentials(**creds_data)

    if credentials and credentials.valid:
        print("✅ Credentials found and valid")
        return credentials
    else:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(google.auth.transport.requests.Request())
                request.session['google_drive_credentials'] = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
                return credentials
            except Exception as e:
                print("❌ Token refresh failed:", str(e))
                return None

    return None



def list_drive_files(request):
    credentials = get_google_credentials(request)
    if not credentials or not credentials.valid:
        return redirect('/login/')

    drive_service = build('drive', 'v3', credentials=credentials)
    results = drive_service.files().list().execute()
    files = results.get('files', [])

    for file in files:
        file['download_url'] = reverse('drive_download', args=[file['id']])

    return render(request, 'drive_files.html', {'files': files})

def upload_file_to_drive(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        credentials = get_google_credentials(request)
        if not credentials or not credentials.valid:
            return redirect('/login/')  

        file_path = default_storage.save(uploaded_file.name, ContentFile(uploaded_file.read()))
        abs_file_path = os.path.join(default_storage.location, file_path)

        try:
            drive_service = build('drive', 'v3', credentials=credentials)
            file_metadata = {'name': uploaded_file.name}
            media = MediaFileUpload(abs_file_path, mimetype=uploaded_file.content_type, resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        finally:
            if os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except PermissionError:
                    print("❌ Unable to delete file. File might still be in use.")

        return render(request, 'upload_file.html', {'message': 'File uploaded successfully!'})

    return render(request, 'upload_file.html')

def download_file_from_drive(request, file_id):
    credentials = get_google_credentials(request)
    if not credentials or not credentials.valid:
        return redirect('/login/') 

    try:
        drive_service = build('drive', 'v3', credentials=credentials)

        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get("name", "downloaded_file")

        request = drive_service.files().get_media(fileId=file_id)
        
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_stream.seek(0)

        response = HttpResponse(file_stream.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def delete_file_from_drive(request, file_id):
    credentials = get_google_credentials(request)
    if not credentials or not credentials.valid:
        return redirect('/login/') 

    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        drive_service.files().delete(fileId=file_id).execute()
        return redirect('/drive/files/')  
    except Exception as e:
        return render(request, 'file_list.html', {'error': f'Error deleting file: {str(e)}'})

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }