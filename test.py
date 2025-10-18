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

cloudinary.uploader.upload(file='https://i.pinimg.com/736x/40/ca/92/40ca92ad3db301e2e7e659d99837fe0c.jpg', asset_folder='emilio/level1/task1')