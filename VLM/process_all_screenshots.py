from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import base64
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import json

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

class MonopolyHUD(BaseModel):
    popup_title: str = Field(..., description="Title of the popup if there is one.")
    popup_text: str = Field(..., description="Text of the popup if there is one.")
    action_buttons: List[str] = Field(..., description="List of available action buttons.")

# Function to crop image by removing 15% from each side
def crop_image(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        
        # Calculate crop boundaries (remove 15% from each side)
        left = int(width * 0.25)
        top = int(height * 0.25)
        right = int(width * 0.85)
        bottom = int(height * 0.85)
        
        # Crop the image
        cropped_img = img.crop((left, top, right, bottom))
        
        return cropped_img

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_image(image_path):
    """Analyze a single image with VLM and return the parsed data"""
    try:
        # Crop the image
        cropped_img = crop_image(image_path)
        
        # Save cropped image temporarily
        temp_path = "temp_cropped.png"
        cropped_img.save(temp_path)
        
        # Encode the image
        base64_image = encode_image(temp_path)
        
        # Call VLM
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
        
        # Clean up temp file
        os.remove(temp_path)
        
        hud_data = completion.choices[0].message
        
        if hud_data.refusal:
            return None, f"Model refused: {hud_data.refusal}"
        else:
            return hud_data.parsed, None
            
    except Exception as e:
        return None, str(e)

def add_text_to_image(image_path, parsed_data, output_path):
    """Add JSON results to the right side of the image with black background"""
    
    # Open the original image
    img = Image.open(image_path)
    width, height = img.size
    
    # Create JSON text
    json_text = json.dumps(parsed_data.model_dump(), indent=2, ensure_ascii=False)
    
    # Calculate new image size (add 40% width for text panel)
    text_panel_width = int(width * 0.4)
    new_width = width + text_panel_width
    
    # Create new image with black background
    new_img = Image.new('RGB', (new_width, height), color='black')
    
    # Paste original image on the left
    new_img.paste(img, (0, 0))
    
    # Draw text on the right panel
    draw = ImageDraw.Draw(new_img)
    
    # Try to use a monospace font, fallback to default if not available
    try:
        # Try different font sizes
        font = ImageFont.truetype("consolas.ttf", 14)
    except:
        try:
            font = ImageFont.truetype("courier.ttf", 14)
        except:
            # Use default font
            font = ImageFont.load_default()
    
    # Add title
    title_text = f"VLM Analysis - {Path(image_path).name}"
    draw.text((width + 10, 10), title_text, fill="white", font=font)
    
    # Add separator line
    draw.line([(width + 10, 35), (new_width - 10, 35)], fill="white", width=1)
    
    # Split JSON into lines and draw each line
    y_position = 50
    line_height = 20
    
    # Format the data nicely
    lines = [
        "═══════════════════════════════",
        f"📋 POPUP TITLE:",
        f"   {parsed_data.popup_title}",
        "",
        f"📝 POPUP TEXT:",
    ]
    
    # Wrap long text
    text_words = parsed_data.popup_text.split()
    current_line = "   "
    for word in text_words:
        if len(current_line + word) > 35:  # Approximate line width
            lines.append(current_line)
            current_line = "   " + word + " "
        else:
            current_line += word + " "
    if current_line.strip():
        lines.append(current_line)
    
    lines.extend([
        "",
        f"🔘 ACTION BUTTONS:",
    ])
    
    for button in parsed_data.action_buttons:
        lines.append(f"   • {button}")
    
    lines.append("═══════════════════════════════")
    
    # Draw all lines
    for line in lines:
        draw.text((width + 10, y_position), line, fill="white", font=font)
        y_position += line_height
    
    # Save the new image
    new_img.save(output_path)
    print(f"✅ Processed: {Path(image_path).name} -> {Path(output_path).name}")

def process_all_screenshots():
    """Process all screenshots in the screenshots directory"""
    
    # Set up directories
    screenshots_dir = Path("screenshots")
    processed_dir = Path("screenshots_processed")
    
    if not screenshots_dir.exists():
        print("❌ Screenshots directory not found!")
        return
    
    # Create processed directory
    processed_dir.mkdir(exist_ok=True)
    
    # Get all PNG files
    screenshot_files = list(screenshots_dir.glob("*.png"))
    
    if not screenshot_files:
        print("❌ No screenshots found in the directory!")
        return
    
    print(f"🔍 Found {len(screenshot_files)} screenshots to process\n")
    
    # Process each screenshot
    for i, image_path in enumerate(screenshot_files, 1):
        print(f"\n{'='*50}")
        print(f"📸 Processing {i}/{len(screenshot_files)}: {image_path.name}")
        print(f"{'='*50}")
        
        # Analyze the image
        parsed_data, error = analyze_image(str(image_path))
        
        if error:
            print(f"❌ Error analyzing image: {error}")
            continue
        
        # Print JSON result
        print("\n✅ VLM Response:")
        print(json.dumps(parsed_data.model_dump(), indent=2, ensure_ascii=False))
        
        # Create output filename
        output_filename = f"processed_{image_path.stem}.png"
        output_path = processed_dir / output_filename
        
        # Add text to image and save
        try:
            add_text_to_image(str(image_path), parsed_data, str(output_path))
        except Exception as e:
            print(f"❌ Error adding text to image: {e}")
    
    print(f"\n\n✅ Processing complete! {len(screenshot_files)} images processed.")
    print(f"📁 Results saved in: {processed_dir.absolute()}")

if __name__ == "__main__":
    process_all_screenshots()