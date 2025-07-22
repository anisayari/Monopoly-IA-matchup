from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import base64
from PIL import Image
import os
from pathlib import Path

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

class MonopolyHUD(BaseModel):
    popup_title: str = Field(..., description="Title of the popup if there is one.")
    popup_text: str = Field(..., description="Text of the popup if there is one.")
    action_buttons: List[str] = Field(..., description="List of available action buttons.")

# Function to crop image by removing 15% from each side
def crop_image(image_path, output_path):
    with Image.open(image_path) as img:
        width, height = img.size
        
        # Calculate crop boundaries (remove 15% from each side)
        left = int(width * 0.25)
        top = int(height * 0.25)
        right = int(width * 0.85)
        bottom = int(height * 0.85)
        
        # Crop the image
        cropped_img = img.crop((left, top, right, bottom))
        
        # Save the cropped image
        cropped_img.save(output_path)
        
        return output_path

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Get the first image from screenshots directory
screenshots_dir = Path("screenshots")
if not screenshots_dir.exists():
    print("❌ Screenshots directory not found!")
    exit(1)

# Get all PNG files in the directory
screenshot_files = list(screenshots_dir.glob("*.png"))
if not screenshot_files:
    print("❌ No screenshots found in the directory!")
    exit(1)

# Sort by modification time and get the most recent
screenshot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
image_path = str(screenshot_files[0])
print(f"📸 Using screenshot: {image_path}")

# Crop the image and save as debug_resized.png
cropped_image_path = crop_image(image_path, "debug_resized.png")

# Getting the Base64 string from the cropped image
base64_image = encode_image(cropped_image_path)

completion = client.chat.completions.parse(
    model="gemma3:4b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that can parse the HUD of a Monopoly game."},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What's in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ],
        }
    ],
    response_format=MonopolyHUD,
)

import json

hud_data = completion.choices[0].message

# If the model refuses to respond, you will get a refusal message
if (hud_data.refusal):
    print("❌ Model refusal:", hud_data.refusal)
else:
    # Convert the parsed Pydantic model to dict and print as JSON
    parsed_data = hud_data.parsed
    print("\n✅ VLM Response (MonopolyHUD):")
    print(json.dumps(parsed_data.model_dump(), indent=2, ensure_ascii=False))
    
    # Also print individual fields for clarity
    print("\n📋 Parsed fields:")
    print(f"  - Popup Title: {parsed_data.popup_title}")
    print(f"  - Popup Text: {parsed_data.popup_text}")
    print(f"  - Action Buttons: {parsed_data.action_buttons}")