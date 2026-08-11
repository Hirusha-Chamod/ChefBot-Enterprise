import os
import json
import urllib.request
import urllib.parse
from langchain_core.tools import tool
from tavily import TavilyClient
from app.core.config import settings

CULINARY_MATRIX = {
    "butter": "Olive oil, vegetable oil, coconut oil, or margarine (1:1 ratio).",
    "milk": "Unsweetened almond milk, oat milk, soy milk, or water with a splash of oil.",
    "eggs": "1/4 cup unsweetened applesauce, 1/2 mashed banana, or 1 tbsp flaxseed + 3 tbsp water (per egg).",
    "egg": "1/4 cup unsweetened applesauce, 1/2 mashed banana, or 1 tbsp flaxseed + 3 tbsp water.",
    "soy sauce": "Tamari, Worcestershire sauce, coconut aminos, or 1/4 tsp salt + pinch of sugar.",
    "heavy cream": "Full-fat coconut milk, or 3/4 cup milk + 1/3 cup melted butter/oil.",
    "garlic": "1/8 tsp garlic powder, or minced shallots/chives (per clove).",
    "onion": "Shallots, leeks, green onions (scallions), or 1 tbsp onion powder.",
    "flour": "Gluten-free 1:1 baking flour, oat flour, almond flour, or cornstarch (use half amount).",
    "sugar": "Honey, maple syrup, agave nectar, or stevia/erythritol.",
}

@tool
def web_search(query: str) -> str:
    """PRIMARY SEARCH TOOL: Searches live web via Tavily for recipes, culinary techniques, or food info matching ingredients."""
    api_key = settings.TAVILY_API_KEY
    if not api_key or api_key.startswith("your_"):
        return "[CONFIG ERROR]: TAVILY_API_KEY is not configured."

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        if not results:
            return f"No web search results found for query: '{query}'."

        formatted = []
        for r in results:
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            snippet = r.get("content", "")[:250]
            formatted.append(f"- **{title}**\n  URL: {url}\n  Snippet: {snippet}...")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"[WEB SEARCH ERROR]: {e}"

@tool
def search_recipes_api(ingredients: str) -> str:
    """FALLBACK SEARCH TOOL: Searches TheMealDB database for recipes containing a main ingredient. Use when web_search is disabled or empty."""
    main_ing = ingredients.split(",")[0].strip()
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={urllib.parse.quote(main_ing)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        meals = data.get("meals")
        if not meals:
            return f"No direct API matches found in TheMealDB for '{main_ing}'."
        results = [{"id": m["idMeal"], "title": m["strMeal"]} for m in meals[:3]]
        return json.dumps(results)
    except Exception as e:
        return f"[THEMEALDB ERROR]: {e}"

@tool
def get_recipe_details(recipe_id: str) -> str:
    """Fetches full recipe instructions from TheMealDB by numeric recipe ID."""
    url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={urllib.parse.quote(recipe_id.strip())}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        meals = data.get("meals")
        if not meals:
            return f"No recipe details found for ID '{recipe_id}'."
        meal = meals[0]
        instructions = meal.get("strInstructions", "No instructions available.")
        return f"Recipe: {meal.get('strMeal')}\nCategory: {meal.get('strCategory')}\nInstructions:\n{instructions[:800]}..."
    except Exception as e:
        return f"[RECIPE DETAILS ERROR]: {e}"

@tool
def substitute_ingredient(missing_item: str) -> str:
    """Suggests culinary substitutes for missing ingredients using fast matrix lookup."""
    item_clean = missing_item.strip().lower()
    match = CULINARY_MATRIX.get(item_clean)
    if match:
        return f"Substitute for '{missing_item}': {match}"
    return f"No exact match in matrix for '{missing_item}'. Try using a neutral oil, standard salt/pepper, or similar texture item."

@tool
def calculate_nutrition(ingredients_summary: str) -> str:
    """MANDATORY TOOL: Calculates estimated total calories and macros (Protein, Carbs, Fats) for recipe ingredients using USDA precision."""
    api_key = settings.USDA_API_KEY
    items = [i.strip() for i in ingredients_summary.split(",") if i.strip()]
    if not items:
        return "No ingredients provided for nutrition calculation."

    total_kcal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    processed_items = []

    for item in items[:5]:
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}&query={urllib.parse.quote(item)}&pageSize=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            foods = data.get("foods", [])
            if foods:
                nutrients = foods[0].get("foodNutrients", [])
                item_kcal = item_protein = item_carbs = item_fat = 0.0
                for n in nutrients:
                    name = n.get("nutrientName", "").lower()
                    val = float(n.get("value", 0.0))
                    if "energy" in name and val > item_kcal:
                        item_kcal = val
                    elif "protein" in name:
                        item_protein = val
                    elif "carbohydrate" in name:
                        item_carbs = val
                    elif "total lipid" in name or "fat" in name:
                        item_fat = val
                total_kcal += item_kcal
                total_protein += item_protein
                total_carbs += item_carbs
                total_fat += item_fat
                processed_items.append(item)
            else:
                total_kcal += 120.0
                total_protein += 4.0
                total_carbs += 15.0
                total_fat += 3.0
                processed_items.append(f"{item} (estimated)")
        except Exception:
            total_kcal += 100.0
            total_protein += 3.0
            total_carbs += 12.0
            total_fat += 2.0
            processed_items.append(f"{item} (est fallback)")

    return (
        f"Live USDA Nutrition Breakdown for ({', '.join(processed_items)}):\n"
        f"~{total_kcal:.0f} kcal | Protein: {total_protein:.1f}g | Carbs: {total_carbs:.1f}g | Fats: {total_fat:.1f}g"
    )

# Registered LangChain tools list
ALL_TOOLS = [web_search, search_recipes_api, get_recipe_details, substitute_ingredient, calculate_nutrition]
