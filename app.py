from flask import Flask, render_template, session, jsonify
from flask_mysqldb import MySQL
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MySQL
mysql = MySQL(app)

# Register blueprints
from routes.auth import auth_bp, init_mysql as auth_mysql
from routes.products import products_bp, init_mysql as products_mysql
from routes.cart import cart_bp, init_mysql as cart_mysql
from routes.orders import orders_bp, init_mysql as orders_mysql
from routes.admin import admin_bp, init_mysql as admin_mysql
from routes.wishlist import wishlist_bp, init_mysql as wishlist_mysql

auth_mysql(mysql)
products_mysql(mysql)
cart_mysql(mysql)
orders_mysql(mysql)
admin_mysql(mysql)
wishlist_mysql(mysql)

app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(wishlist_bp)

# Make categories available to ALL templates globally
@app.context_processor
def inject_categories():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, icon FROM categories")
        cats = cur.fetchall()
        cur.close()
        categories = [{'id': c[0], 'name': c[1], 'icon': c[2]} for c in cats]
    except:
        categories = []
    return dict(categories=categories)

# Home route
@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products LIMIT 8")
    products = cur.fetchall()
    cur.close()

    products_list = []
    for p in products:
        products_list.append({
            'id': p[0],
            'name': p[1],
            'description': p[2],
            'price': p[3],
            'category': p[4],
            'image_url': p[5],
            'stock': p[6]
        })

    # Get recommendations for logged in user
    recommendations = []
    if session.get('user_id'):
        from ai.recommender import get_recommendations
        recommendations = get_recommendations(mysql, session['user_id'])

    return render_template('index.html',
                           products=products_list,
                           recommendations=recommendations)

# Recommendation API endpoint
@app.route('/recommend/<int:user_id>')
def recommend(user_id):
    from ai.recommender import get_recommendations
    recommendations = get_recommendations(mysql, user_id)
    return jsonify(recommendations)

# Custom 404 page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Run the app
if __name__ == '__main__':
    app.run(debug=True)