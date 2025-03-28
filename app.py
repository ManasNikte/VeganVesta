import os
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Load CSV data
try:
    csv_path = os.path.join(os.path.dirname(__file__), 'tripadvisor.csv')
    print(f"Loading restaurant data from: {csv_path}")
    restaurants_df = pd.read_csv(csv_path)
    print(f"Successfully loaded {len(restaurants_df)} restaurants")
except Exception as e:
    print(f"Error loading restaurant data: {str(e)}")
    restaurants_df = pd.DataFrame()

# Load CSV data
df = pd.read_csv("vegan_recipes.csv")

# Define categories
CATEGORIES = {
    "Breakfast": ["oats", "pancake", "smoothie", "toast", "cereal", "muffin", "porridge"],
    "Lunch": ["sandwich", "salad", "wrap", "rice", "curry", "bowl"],
    "Dinner": ["pasta", "soup", "stir-fry", "burger", "casserole", "stew", "pizza"]
}

def classify_recipe(title, ingredients):
    """Classify recipes into Breakfast, Lunch, or Dinner."""
    title = title.lower()
    ingredients = str(ingredients).lower()
    
    for category, keywords in CATEGORIES.items():
        if any(keyword in title or keyword in ingredients for keyword in keywords):
            return category
    return "Uncategorized"

def find_recipe(query):
    """Find matching recipes and classify them."""
    query = query.lower()
    matches = df[df["title"].str.lower().str.contains(query, na=False)]
    
    if matches.empty:
        return [{"title": "No Recipe Found", "category": "N/A", "ingredients": "Try another keyword!", "preparation": "", "href": "#"}]
    
    results = []
    for _, row in matches.iterrows():
        category = classify_recipe(row["title"], row["ingredients"])
        results.append({
            "title": row["title"],
            "category": category,
            "ingredients": row["ingredients"],
            "preparation": row["preparation"],
            "href": row["href"]
        })
    return results[:3]  # Limit to top 3 results

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_recipe", methods=["POST"])
def get_recipe():
    user_input = request.form["user_input"]
    recipes = find_recipe(user_input)
    return jsonify(recipes)

@app.route('/get_restaurants', methods=['POST'])
def get_restaurants():
    try:
        if restaurants_df is None or restaurants_df.empty:
            print("Error: No restaurant data available")
            return jsonify([])

        location = request.form.get('location', '').lower().strip()
        print(f"Searching for location: {location}")

        # Create location pattern for exact matching
        location_pattern = fr'\b{location}\b'
        
        # First try to find restaurants in the exact location
        filtered_restaurants = restaurants_df[
            restaurants_df['address'].str.lower().str.contains(location_pattern, na=False, case=False, regex=True)
        ]

        print(f"Found {len(filtered_restaurants)} matching restaurants")

        if filtered_restaurants.empty:
            return jsonify([])

        # Clean and format results - Replace NaN with None for JSON serialization
        filtered_restaurants = filtered_restaurants.fillna({
            'cuisines': 'Various Cuisines',
            'Phone': 'N/A',
            'rating': 0.0,
            'review_count': 0,
            'price_range_from': 0,
            'price_range_to': 0,
            'average_count': 0,
            'excellent_count': 0,
            'poor_count': 0,
            'terrible_count': 0,
            'very_good_count': 0
        })

        # Group by area
        def extract_area(address):
            parts = str(address).lower().split(',')
            for part in parts:
                if location in part.lower():
                    return part.strip()
            return parts[0].strip()

        filtered_restaurants['area'] = filtered_restaurants['address'].apply(extract_area)
        current_area = filtered_restaurants['area'].iloc[0] if not filtered_restaurants.empty else None
        
        # Filter only restaurants from current area
        filtered_restaurants = filtered_restaurants[filtered_restaurants['area'] == current_area]

        # Get top restaurants and convert to dictionary
        top_restaurants = filtered_restaurants.sort_values(
            ['rating', 'review_count'], 
            ascending=[False, False]
        ).head(12)

        # Convert DataFrame to dict and clean up NaN values
        results = []
        for _, row in top_restaurants.iterrows():
            restaurant_dict = row.to_dict()
            # Convert any remaining NaN to appropriate values
            for key, value in restaurant_dict.items():
                if pd.isna(value):
                    if isinstance(value, (int, float)):
                        restaurant_dict[key] = 0
                    else:
                        restaurant_dict[key] = ''
            results.append(restaurant_dict)

        print(f"Returning {len(results)} restaurants in {current_area}")
        return jsonify(results)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify([])

# if __name__ == "__main__":
#     app.run(debug=True)
