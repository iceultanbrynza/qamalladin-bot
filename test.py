import cloudinary
import cloudinary.uploader
import cloudinary.api

# Import the CloudinaryImage and CloudinaryVideo methods for the simplified syntax used in this guide
from cloudinary import CloudinaryImage
from cloudinary import CloudinaryVideo

from dotenv import load_dotenv
import os
load_dotenv(dotenv_path='config/.env')

cloudinary.config(
  cloud_name = os.getenv('CLOUD_NAME'),
  api_key = os.getenv('API_KEY'),
  api_secret = os.getenv('API_SECRET')
)

# info = cloudinary.api.resource("25IT777B1SN120251019_011017")
# print(info['secure_url'])
# url = cloudinary.utils.cloudinary_url("25IT777B1SN120251019_011914", resource_type='raw')[0]
# l = url.split('/')
# print(url.split('/'))
# public_id = l[-1]
# print(l[-1])
# l[-1] = f'fl_attachment:{public_id}.pdf'
# l.append(public_id)
# new_url = '/'.join(l)
# print(new_url)

# print(url+'.pdf')
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
# from google.auth.transport.requests import Request
# from google.oauth2 import service_account
# from google.auth.transport.requests import Request
import base64, json, requests, datetime
# fb_decoded_key = base64.b64decode(os.getenv("FIREBASE_KEY")).decode('utf-8')
# fb_private_key = json.loads(fb_decoded_key)
# cred = credentials.Certificate(fb_private_key)
# SERVICE_ACCOUNT_FILE = "service_account.json"
# SCOPES = ["https://www.googleapis.com/auth/monitoring.read"]
# cred = service_account.Credentials.from_service_account_file(
#     SERVICE_ACCOUNT_FILE,
#     scopes=SCOPES
# )
# cred.refresh(Request())
# token = cred.token
# print(cred.token)
from utilities.database import get_log
fb_decoded_key = base64.b64decode(os.getenv("FIREBASE_KEY")).decode('utf-8')
fb_private_key = json.loads(fb_decoded_key)

cred = credentials.Certificate(fb_private_key)

app = firebase_admin.initialize_app(cred)

db = firestore.client()
reponse = get_log(db)
print(reponse)