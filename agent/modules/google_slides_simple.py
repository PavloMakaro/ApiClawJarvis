import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import webbrowser

SCOPES = ['https://www.googleapis.com/auth/presentations']

def authenticate_google_slides():
    """Simple authentication for Google Slides."""
    creds = None
    token_path = 'data/google_token.pickle'
    creds_path = 'data/google_credentials.json'

    # Check if credentials file exists
    if not os.path.exists(creds_path):
        return "❌ Файл учетных данных не найден. Сохраните его как data/google_credentials.json"

    # Load existing token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create flow with console-only authorization
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)

            # Get authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent')

            print(f"🔗 Перейдите по ссылке для авторизации:")
            print(auth_url)
            print("\nПосле авторизации скопируйте код и введите его здесь.")

            # Try to open browser
            try:
                webbrowser.open(auth_url)
            except:
                pass

            # Get authorization code from user
            code = input("Введите код авторизации: ").strip()

            # Exchange code for credentials
            flow.fetch_token(code=code)
            creds = flow.credentials

        # Save credentials
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return "✅ Авторизация успешна!"

def create_simple_presentation(title="Моя презентация"):
    """Create a simple presentation."""
    # First authenticate
    auth_result = authenticate_google_slides()
    if "❌" in auth_result:
        return auth_result

    # Load credentials
    token_path = 'data/google_token.pickle'
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)

    # Create service
    service = build('slides', 'v1', credentials=creds)

    # Create presentation
    presentation = service.presentations().create(
        body={'title': title}
    ).execute()

    presentation_id = presentation['presentationId']
    url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    return f"✅ Презентация создана!\nСсылка: {url}"

if __name__ == '__main__':
    print(create_simple_presentation())