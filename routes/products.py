from flask import Blueprint, render_template, request, session
from flask_mysqldb import MySQL

products_bp = Blueprint('products', __name__)
mysql = None

def init_mysql(mysql_instance):
    global mysql
    mysql = mysql_instance

# Products Listing Route
@products_bp.route('/products')
def listing():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    max_price = request.args.get('max_price', '')
    page = int(request.args.get('page', 1))
    per_page = 8

    query = "SELECT * FROM products WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE %s"
        count_query += " AND name LIKE %s"
        params.append(f'%{search}%')

    if category:
        query += " AND category = %s"
        count_query += " AND category = %s"
        params.append(category)

    if max_price:
        query += " AND price <= %s"
        count_query += " AND price <= %s"
        params.append(max_price)

    # Get total count
    cur = mysql.connection.cursor()
    cur.execute(count_query, params)
    total_products = cur.fetchone()[0]
    total_pages = (total_products + per_page - 1) // per_page

    # Get paginated products
    query += " LIMIT %s OFFSET %s"
    params.append(per_page)
    params.append((page - 1) * per_page)

    cur.execute(query, params)
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

    return render_template('products/listing.html',
                           products=products_list,
                           page=page,
                           total_pages=total_pages,
                           total_products=total_products)
# Product Detail Route
@products_bp.route('/products/<int:product_id>')
def detail(product_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()

    if not product:
        return "Product not found!", 404

    product_dict = {
        'id': product[0],
        'name': product[1],
        'description': product[2],
        'price': product[3],
        'category': product[4],
        'image_url': product[5],
        'stock': product[6]
    }

    # Track user activity
    if session.get('user_id'):
        from ai.recommender import track_activity
        track_activity(mysql, session['user_id'], product_id, 'view')

    # Get recommendations
    from ai.recommender import get_recommendations
    recommendations = get_recommendations(
        mysql,
        session.get('user_id'),
        current_product_id=product_id,
        category=product_dict['category']
    )

    # Get reviews
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.rating, r.review_text, r.created_at, u.name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.product_id = %s
        ORDER BY r.created_at DESC
    """, (product_id,))
    reviews = cur.fetchall()
    cur.close()

    reviews_list = []
    for r in reviews:
        reviews_list.append({   
            'rating': r[0],
            'review_text': r[1],
            'created_at': r[2],
            'user_name': r[3]
        })

    # Calculate average rating
    avg_rating = 0
    if reviews_list:
        avg_rating = round(sum(r['rating'] for r in reviews_list) / len(reviews_list), 1)

    return render_template('products/detail.html',
                        product=product_dict,
                        recommendations=recommendations,
                        reviews=reviews_list,
                        avg_rating=avg_rating)

# Add Review
@products_bp.route('/products/<int:product_id>/review', methods=['POST'])
def add_review(product_id):
    from flask import redirect, url_for, flash
    if not session.get('user_id'):
        flash('Please login to add a review!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    rating = request.form.get('rating')
    review_text = request.form.get('review_text')

    # Check if user already reviewed
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM reviews WHERE product_id = %s AND user_id = %s",
                (product_id, user_id))
    existing = cur.fetchone()

    if existing:
        flash('You have already reviewed this product!', 'error')
        return redirect(url_for('products.detail', product_id=product_id))

    # Add review
    cur.execute("""
        INSERT INTO reviews (product_id, user_id, rating, review_text)
        VALUES (%s, %s, %s, %s)
    """, (product_id, user_id, rating, review_text))
    mysql.connection.commit()
    cur.close()

    flash('Review added successfully!', 'success')
    return redirect(url_for('products.detail', product_id=product_id))