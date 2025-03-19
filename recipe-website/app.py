from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import re
import os

# Initialize the Flask application
app = Flask(__name__)
app.config['DATABASE'] = 'recipes.db'

# Database helper functions
def get_db():
    """Connect to the database and return the connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row  # This enables column access by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection when the application context ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database schema and add sample data"""
    with app.app_context():
        db = get_db()
        # Create tables
        db.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                ingredient TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        
        # Add sample data if the recipes table is empty
        if db.execute('SELECT COUNT(*) FROM recipes').fetchone()[0] == 0:
            # Insert sample recipe
            db.execute('''
                INSERT INTO recipes (id, name, instructions) 
                VALUES (?, ?, ?)
            ''', ('midnight-ramen', 'Midnight Ramen', '1. Boil water\n2. Cook noodles\n3. Add toppings'))
            
            # Insert ingredients for the sample recipe
            ingredients = ["instant ramen", "egg", "green onions", "hot sauce"]
            for ingredient in ingredients:
                db.execute('''
                    INSERT INTO ingredients (recipe_id, ingredient)
                    VALUES (?, ?)
                ''', ('midnight-ramen', ingredient))
        
        db.commit()

# Routes
@app.route('/')
def index():
    """Display the home page with a list of all recipes"""
    db = get_db()
    recipes = db.execute('SELECT id, name FROM recipes').fetchall()
    return render_template('index.html', recipes=recipes)

@app.route('/recipe/<recipe_id>')
def recipe(recipe_id):
    """Display details for a specific recipe"""
    db = get_db()
    
    # Get recipe details
    recipe = db.execute('SELECT id, name, instructions FROM recipes WHERE id = ?', 
                         (recipe_id,)).fetchone()
    
    if recipe is None:
        return "Recipe not found", 404
    
    # Get ingredients for this recipe
    ingredients = db.execute('SELECT ingredient FROM ingredients WHERE recipe_id = ?', 
                              (recipe_id,)).fetchall()
    
    return render_template('recipe.html', recipe=recipe, ingredients=ingredients)

@app.route('/add', methods=['GET', 'POST'])
def add_recipe():
    """Handle adding a new recipe"""
    if request.method == 'POST':
        # Extract form data
        name = request.form['name']
        ingredients = request.form['ingredients'].split('\n')
        instructions = request.form['instructions']
        
        # Create a URL-friendly ID from the recipe name
        recipe_id = re.sub(r'[^\w\s]', '', name.lower()).replace(' ', '-')
        
        # Insert data into database
        db = get_db()
        
        # Insert recipe
        db.execute('INSERT INTO recipes (id, name, instructions) VALUES (?, ?, ?)',
                   (recipe_id, name, instructions))
        
        # Insert ingredients
        for ingredient in ingredients:
            if ingredient.strip():  # Skip empty lines
                db.execute('INSERT INTO ingredients (recipe_id, ingredient) VALUES (?, ?)',
                          (recipe_id, ingredient.strip()))
        
        db.commit()
        
        return redirect(url_for('recipe', recipe_id=recipe_id))
    
    return render_template('add_recipe.html')

# Custom template filter for new lines to <br>
@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to HTML line breaks"""
    return value.replace('\n', '<br>')

if __name__ == '__main__':
    # Create database and tables if they don't exist
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    else:
        # Make sure tables are created
        with app.app_context():
            db = get_db()
            db.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    instructions TEXT NOT NULL
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id TEXT NOT NULL,
                    ingredient TEXT NOT NULL,
                    FOREIGN KEY (recipe_id) REFERENCES recipes (id)
                )
            ''')
            db.commit()
    
    # Run the Flask development server
    app.run(debug=True)