from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

INGREDIENT_TO_PRODUCT_MAP = {
    # --- WHISKEY / SPIRIT PRODUCTS ---
    "bourbon": "KOVAL Bourbon",
    # Four Grain is listed simply as "Four Grain" and "Oat" is listed as "Oat" in recipes
    "four grain": "KOVAL Four Grain Whiskey",
    "oat": "KOVAL Oat Whiskey", 
    "rye": "KOVAL Rye Whiskey",
    "white rye": "KOVAL White Rye Whiskey",
    "amburana rye": "KOVAL Amburana Rye Whiskey",
    "maple rye": "KOVAL Maple Rye Whiskey",
    "base spirit": "ANY_KOVAL_SPIRIT", # Used for MULES/CALL DRINKS where base spirit is flexible
    
    # --- GIN PRODUCTS ---
    "dry gin": "KOVAL Dry Gin",
    "barrel aged gin": "KOVAL Barreled Gin",
    "cranberry gin": "KOVAL Cranberry Gin Liqueur", 
    
    # --- LIQUEUR PRODUCTS ---
    "coffee liqueur": "KOVAL Coffee Liqueur",
    "rosehip liqueur": "KOVAL Rose Hip Liqueur",
    "honey & chrysanthemum liqueur": "KOVAL Chrysanthemum & Honey Liqueur",
    "ginger liqueur": "KOVAL Ginger Liqueur",
    "caraway liqueur": "KOVAL Caraway Liqueur",
    
    # --- OTHER SPECIFIC/INFUSED SPIRITS ---
    "chili infused vodka": "KOVAL Infused Vodka", # Assumes base is a KOVAL spirit
    "vodka": "KOVAL Vodka", # Assumes base is a KOVAL spirit
}

def get_recipes_by_multiple_ingredients(recipes_data, ingredient_names, match_logic="OR"):
    """
    Filters recipes based on selected products, handling both 'AND'/'OR' logic
    and the special 'ANY_KOVAL_SPIRIT' placeholder.
    """
    if not ingredient_names:
        return []

    selected_products_set = {name.strip() for name in ingredient_names}
    found_recipes = []
    
    # Flag to quickly check if the user has *any* product selected (excluding the VIEW_ALL flag)
    user_has_product_selected = any(p != 'VIEW_ALL_RECIPES_FLAG' for p in selected_products_set)

    # This prevents 'rye' from matching ingredients that are actually 'white rye'
    sorted_map_keys = sorted(
        INGREDIENT_TO_PRODUCT_MAP.keys(),
        key=len,
        reverse=True
    )

    for recipe in recipes_data['cocktail_recipes']:
        required_products = set()

        for item in recipe['ingredients']:
            recipe_item_lower = item['item'].strip().lower()
            
            # --- Use the SORTED map keys for prioritized matching ---
            mapped_product_name = None
            
            # 2. Iterate through the keys, checking longest first
            for map_key in sorted_map_keys:
                if map_key in recipe_item_lower:
                    # Found the longest, most specific match!
                    mapped_product_name = INGREDIENT_TO_PRODUCT_MAP[map_key]
                    break 
            
            if mapped_product_name:
                required_products.add(mapped_product_name)
        
        # --- LOGIC APPLICATION ---
        
        # 1. Check for the generic base spirit requirement
        requires_any_koval = "ANY_KOVAL_SPIRIT" in required_products
        
        # Remove the placeholder so it doesn't interfere with the AND/OR math
        required_products.discard("ANY_KOVAL_SPIRIT") 
        
        # 2. Check overlap for specific products
        specific_overlap = required_products.intersection(selected_products_set)
        
        
        is_match = False

        if match_logic == "OR":
            # Match if: (1) specific products overlap, OR (2) recipe requires 'Any Spirit' AND user selected any product
            if specific_overlap or (requires_any_koval and user_has_product_selected):
                is_match = True
        
        elif match_logic == "AND":
            # AND logic is complex here:
            
            # Scenario A: Recipe requires only specific products.
            if not requires_any_koval:
                # Standard AND: All selected products must be a subset of required specific products.
                if selected_products_set.issubset(required_products):
                    is_match = True
            
            # Scenario B: Recipe requires 'Any Spirit' PLUS other specific products (e.g., 'Base Spirit' + 'Coffee Liqueur')
            else: 
                # Match if: ALL specific selected products (excluding the "Any Spirit" requirement) are met.
                # Since 'Any Spirit' can be fulfilled by ANY selection, we only need to ensure
                # the *other* selected products are met.
                if specific_overlap:
                    is_match = True
                
                if not required_products and user_has_product_selected:
                    is_match = True

        if is_match:
            found_recipes.append(recipe)

    return found_recipes

# Load products
with open("data/products.json", "r") as f:
    products = json.load(f)

# Load recipes
with open("data/recipes.json", "r") as f:
    recipes = json.load(f)


@app.route("/")
def index():
    return render_template("index.html", products=products)

@app.route("/recommend", methods=["POST"])
def recommend():
    global recipes
    data = request.get_json()
    selected_products = data.get("selected", [])
    # 1. Read the new logic parameter
    match_logic = data.get("logic", "OR") 
    
    # Check for the "View All" flag first
    if 'VIEW_ALL_RECIPES_FLAG' in selected_products:
        recommendations = recipes['cocktail_recipes']
    else:
        if isinstance(selected_products, list):
            selected_ingredients = [item.strip() for item in selected_products if item.strip()]
        else:
            selected_ingredients = []

        # 2. Pass the match_logic parameter to the filtering function
        recommendations = get_recipes_by_multiple_ingredients(
            recipes, 
            selected_ingredients, 
            match_logic
        )

    return jsonify({"recommendations": recommendations})


if __name__ == "__main__":
    app.run(debug=True)
