import os
import base64
from fastapi import APIRouter, File, UploadFile, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import List

from app.core.config import settings

router = APIRouter(prefix="/vision", tags=["Vision AI"])

class VisionResponse(BaseModel):
    detected_ingredients: List[str]
    prompt_summary: str

@router.post("/analyze", response_model=VisionResponse)
async def analyze_fridge_photo(file: UploadFile = File(...)):
    """
    Analyzes an uploaded fridge/pantry photo using OpenRouter Vision Models.
    Returns detected ingredients as a list and clean prompt summary.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File uploaded must be a valid image (JPG, PNG, WEBP).")

    try:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode("utf-8")
        data_uri = f"data:{file.content_type};base64,{base64_image}"

        # Initialize Vision Model
        vision_llm = ChatOpenAI(
            model=os.environ.get("VISION_MODEL", "google/gemini-2.0-flash-exp:free"),
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=300,
        )

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Analyze this fridge/pantry image carefully. List all visible food items and ingredients you can identify. "
                        "Return ONLY a clean, comma-separated list of items (e.g. '3 eggs, 1 onion, cheddar cheese, bell pepper'). "
                        "Do not include conversational filler."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri}
                }
            ]
        )

        response = vision_llm.invoke([message])
        raw_text = response.content.strip()

        # Parse detected items
        items = [item.strip() for item in raw_text.split(",") if item.strip()]

        return VisionResponse(
            detected_ingredients=items,
            prompt_summary=raw_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision AI Analysis Error: {str(e)}")
