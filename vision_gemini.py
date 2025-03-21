from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

import PIL.Image

# Load environment variables from .env file
load_dotenv()

image = PIL.Image.open('104-10006-10247-1.png')

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["What is this image?", image])

print(response.text)