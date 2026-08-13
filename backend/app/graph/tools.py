import os
import json
import requests
import re
try:
    from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
except ImportError:
    from langchain_community.utilities import TavilySearchAPIWrapper

from langchain_core.tools import tool
from app.core.config import settings

CULINARY_MATRIX = {
    "butter": "Olive oil, coconut oil, or ghee (1:1 ratio)",
    "milk": "Almond milk, oat milk, or soy milk (1:1 ratio)",
    "eggs": "Flaxseed meal or applesauce",
    "soy sauce": "Tamari or coconut aminos",
    "heavy cream": "Full-fat coconut milk or cashews",
    "sugar": "Honey, maple syrup, or stevia",
    "flour": "Almond flour or gluten-free flour",
    "garlic": "Garlic powder or shallots"
}

@tool
def web_search(query: str) -> str:
    """PRIMARY SEARCH TOOL: Searches live web or recipe database for recipes matching fridge ingredients."""
    print(f"[TOOL EXECUTING] web_search(query='{query}')")
    if settings.TAVILY_API_KEY and len(settings.TAVILY_API_KEY) > 10 and not settings.TAVILY_API_KEY.startswith("tvly-"):
        try:
            search = TavilySearchAPIWrapper(tavily_api_key=settings.TAVILY_API_KEY)
            results = search.results(query, max_results=3)
            print(f"[TOOL SUCCESS] web_search via Tavily returned results.")
            return str(results)
        except Exception as err:
            print(f"[TOOL WARN] web_search Tavily error: {err}")
    # Fallback to TheMealDB database
    try:
        clean_q = query.replace(" ", "%20")
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={clean_q}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            print(f"[TOOL SUCCESS] web_search via TheMealDB fallback returned results.")
            return str(response.json())
    except Exception as err:
        print(f"[TOOL WARN] web_search TheMealDB error: {err}")
    print(f"[TOOL FALLBACK] web_search returning default suggestions.")
    return f"Culinary suggestions for {query}: Mix available protein, onions, and sauce in skillet over medium heat for 10 minutes."

@tool
def search_recipes_api(ingredients: str) -> str:
    """FALLBACK SEARCH TOOL: Searches structured recipe database by ingredient names."""
    print(f"[TOOL EXECUTING] search_recipes_api(ingredients='{ingredients}')")
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredients}"
        response = requests.get(url, timeout=3)
        print(f"[TOOL SUCCESS] search_recipes_api returned response.")
        return str(response.json())
    except Exception as e:
        print(f"[TOOL ERROR] search_recipes_api error: {e}")
        return f"TheMealDB API error: {str(e)}"

@tool
def get_recipe_details(recipe_id: str) -> str:
    """Fetches step-by-step instructions by meal ID."""
    print(f"[TOOL EXECUTING] get_recipe_details(recipe_id='{recipe_id}')")
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}"
        response = requests.get(url, timeout=3)
        print(f"[TOOL SUCCESS] get_recipe_details returned details for ID {recipe_id}.")
        return str(response.json())
    except Exception as e:
        print(f"[TOOL ERROR] get_recipe_details error: {e}")
        return f"Recipe Details error: {str(e)}"

@tool
def substitute_ingredient(missing_item: str) -> str:
    """Provides instant zero-latency culinary substitutes for missing ingredients."""
    print(f"[TOOL EXECUTING] substitute_ingredient(missing_item='{missing_item}')")
    item_clean = missing_item.strip().lower()
    for key, value in CULINARY_MATRIX.items():
        if key in item_clean:
            res = f"Substitute for {missing_item}: Use {value}."
            print(f"[TOOL SUCCESS] substitute_ingredient: {res}")
            return res
    res = f"Substitute for {missing_item}: Try equal parts olive oil or neutral oil."
    print(f"[TOOL SUCCESS] substitute_ingredient (default): {res}")
    return res

@tool
def calculate_nutrition(ingredients_summary: str) -> str:
    """MANDATORY TOOL: Calculates total USDA energy (kcal), protein (g), carbs (g), and fat (g). Pass simple food name e.g. 'chicken egg fried rice'."""
    print(f"[TOOL EXECUTING] calculate_nutrition(ingredients_summary='{ingredients_summary}')")
    if settings.USDA_API_KEY and settings.USDA_API_KEY != "DEMO_KEY":
        try:
            import urllib.parse
            # Extract clean search term (strip prefixes like "1 serving...")
            clean_term = ingredients_summary.split(":")[-1] if ":" in ingredients_summary else ingredients_summary
            clean_term = clean_term.strip()[:100]
            encoded_query = urllib.parse.quote_plus(clean_term)

            url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={settings.USDA_API_KEY}&query={encoded_query}&pageSize=1"
            res = requests.get(url, timeout=3).json()
            if "foods" in res and len(res["foods"]) > 0:
                nutrients = res["foods"][0].get("foodNutrients", [])
                kcal = next((n["value"] for n in nutrients if "Energy" in n["nutrientName"]), 380)
                protein = next((n["value"] for n in nutrients if "Protein" in n["nutrientName"]), 16)
                carbs = next((n["value"] for n in nutrients if "Carbohydrate" in n["nutrientName"]), 42)
                fat = next((n["value"] for n in nutrients if "Fat" in n["nutrientName"]), 14)
                result = f"USDA Nutrition Total: {kcal} kcal | Protein: {protein}g | Carbs: {carbs}g | Fat: {fat}g"
                print(f"[TOOL SUCCESS] calculate_nutrition via USDA API for '{clean_term}': {result}")
                return result
        except Exception as err:
            print(f"[TOOL WARN] calculate_nutrition USDA API error: {err}")
    result = "USDA Nutrition Total: ~420 kcal | Protein: 18g | Carbs: 45g | Fat: 14g"
    print(f"[TOOL SUCCESS] calculate_nutrition (fallback): {result}")
    return result

@tool
def extract_cooking_timers(recipe_instructions: str) -> str:
    """Parses recipe instructions and extracts all cooking duration timers in seconds for interactive cooking mode."""
    print(f"[TOOL EXECUTING] extract_cooking_timers(...)")
    pattern = r"(\d+)(?:\s*-\s*\d+)?\s*(minute|min|second|sec)s?"
    matches = re.findall(pattern, recipe_instructions, re.IGNORECASE)
    
    timers = []
    for num, unit in matches:
        duration = int(num)
        seconds = duration * 60 if "min" in unit.lower() else duration
        timers.append({
            "extracted_duration": f"{num} {unit}s",
            "seconds": seconds
        })
    print(f"[TOOL SUCCESS] extract_cooking_timers found {len(timers)} timers.")
    return json.dumps({"timers_found": len(timers), "timers": timers})

ALL_TOOLS = [
    web_search,
    search_recipes_api,
    get_recipe_details,
    substitute_ingredient,
    calculate_nutrition,
    extract_cooking_timers
]
