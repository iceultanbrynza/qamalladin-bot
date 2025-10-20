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

info = cloudinary.api.resource("25IT777B1SN120251019_011017")
print(info['secure_url'])
url = cloudinary.utils.cloudinary_url("25IT777B1SN120251019_011914", resource_type='raw')[0]
l = url.split('/')
print(url.split('/'))
public_id = l[-1]
print(l[-1])
l[-1] = f'fl_attachment:{public_id}.pdf'
l.append(public_id)
new_url = '/'.join(l)
print(new_url)

print(url+'.pdf')