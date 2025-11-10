import asyncio
from datetime import datetime
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import pytz

import cloudinary
import cloudinary.uploader
import cloudinary.api

# Import the CloudinaryImage and CloudinaryVideo methods for the simplified syntax used in this guide
from cloudinary import CloudinaryImage
from cloudinary import CloudinaryVideo

def upload_file(file:BytesIO, username, task, public_id, format):
    tz = pytz.timezone("Asia/Almaty")
    month = datetime.now(tz).strftime("%B")
    folder_path = f'{username}/{month}/{task}'
    response = cloudinary.uploader.upload(file,
                                          asset_folder=folder_path,
                                          resource_type='auto',
                                          public_id=public_id)
    return response

def upload_good_file(file:BytesIO, public_id):
    folder_path = 'shop'
    response = cloudinary.uploader.upload(file,
                                          asset_folder=folder_path,
                                          resource_type='auto',
                                          public_id=public_id)
    return response

def get_url(public_id:str):
    try:
        info = cloudinary.api.resource(public_id)
        url = info.get('secure_url', '')
        format = info.get('format')
    except:
        info = cloudinary.api.resource(public_id, resource_type="video")
        url = info.get('secure_url', '')
        format = info.get('format')
    return (url, format)

pool = ThreadPoolExecutor(max_workers=5)

async def upload_many_async(files: dict, username: str, task: str):
    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(pool, upload_file, f, username, task, public_id)
        for public_id, f in files.items()
    ]
    return await asyncio.gather(*tasks)