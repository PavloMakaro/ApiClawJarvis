import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/presentations']

def get_google_slides_service():
    """Get authenticated Google Slides service."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    token_path = 'data/google_token.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'data/google_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('slides', 'v1', credentials=creds)
    return service

def create_presentation(title):
    """Create a new presentation."""
    service = get_google_slides_service()

    # Create presentation
    presentation = {
        'title': title
    }

    presentation = service.presentations().create(body=presentation).execute()
    presentation_id = presentation.get('presentationId')

    print(f'Created presentation with ID: {presentation_id}')
    print(f'View it at: https://docs.google.com/presentation/d/{presentation_id}/edit')

    return presentation_id

def add_slide(presentation_id, title, content=None):
    """Add a slide to presentation."""
    service = get_google_slides_service()

    # Create requests for adding a slide
    requests = [
        {
            'createSlide': {
                'slideLayoutReference': {
                    'predefinedLayout': 'TITLE_AND_BODY'
                }
            }
        }
    ]

    # Execute the request
    response = service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={'requests': requests}
    ).execute()

    slide_id = response['replies'][0]['createSlide']['objectId']

    # Add title and content
    if title:
        requests = [
            {
                'insertText': {
                    'objectId': slide_id,
                    'text': title,
                    'insertionIndex': 0
                }
            }
        ]

        if content:
            requests.append({
                'insertText': {
                    'objectId': slide_id,
                    'text': content,
                    'insertionIndex': 1
                }
            })

        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

    return slide_id

if __name__ == '__main__':
    # Test the functions
    presentation_id = create_presentation("Test Presentation")
    add_slide(presentation_id, "Test Slide", "This is test content")