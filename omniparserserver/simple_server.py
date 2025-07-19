#!/usr/bin/env python3
"""
Simple OmniParser API server
"""
import json
import base64
import io
from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="OmniParser API", version="1.0.0")

class ImageRequest(BaseModel):
    base64_image: str

class ParsedElement(BaseModel):
    type: str
    content: str
    bbox: List[float]
    confidence: float = 1.0

class ParseResponse(BaseModel):
    parsed_content_list: List[ParsedElement]
    success: bool = True
    message: str = "OK"

@app.get("/")
async def root():
    return {"message": "OmniParser API Server", "status": "running"}

@app.get("/probe/")
async def probe():
    return {"status": "healthy", "service": "omniparser"}

@app.post("/parse/", response_model=ParseResponse)
async def parse_image(request: ImageRequest):
    """Parse an image and return UI elements"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Simple mock parsing (replace with actual OmniParser logic)
        parsed_elements = [
            ParsedElement(
                type="button",
                content="ok",
                bbox=[100, 100, 200, 150],
                confidence=0.95
            ),
            ParsedElement(
                type="button", 
                content="cancel",
                bbox=[220, 100, 320, 150],
                confidence=0.90
            ),
            ParsedElement(
                type="text",
                content="dialog message",
                bbox=[100, 50, 320, 90],
                confidence=0.85
            )
        ]
        
        return ParseResponse(
            parsed_content_list=parsed_elements,
            success=True,
            message="Image parsed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing image: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)