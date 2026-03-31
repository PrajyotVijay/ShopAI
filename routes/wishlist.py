from flask import Blueprint, render_template, redirect, url_for, session, flash, jsonify

wishlist_bp = Blueprint('wishlist', __name__)
mysql = None

def init_mysql(mysql_instance):
    global mysql
    mysql = mysql_instance

# View Wishlist
@wishlist_bp.route('/wishlist')
def view_wishlist():
    if not session.get('user_id'):
        flash('Please login to view wishlist!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT w.id, p.id, p.name, p.price, p.category, p.image_url, p.description, p.stock
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        WHERE w.user_id = %s
        ORDER BY w.created_at DESC
    """, (user_id,))
    items = cur.fetchall()
    cur.close()

    wishlist_items = []
    for item in items:
        wishlist_items.append({
            'wishlist_id': item[0],
            'product_id': item[1],
            'name': item[2],
            'price': item[3],
            'category': item[4],
            'image_url': item[5],
            'description': item[6],
            'stock': item[7]
        })

    return render_template('wishlist.html', wishlist_items=wishlist_items)

# Add to Wishlist
@wishlist_bp.route('/wishlist/add/<int:product_id>')
def add_to_wishlist(product_id):
    if not session.get('user_id'):
        flash('Please login to add to wishlist!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO wishlist (user_id, product_id) VALUES (%s, %s)",
                    (user_id, product_id))
        mysql.connection.commit()
        cur.close()
        flash('Added to wishlist!', 'success')
    except:
        flash('Already in wishlist!', 'error')

    return redirect(url_for('products.detail', product_id=product_id))

# Remove from Wishlist
@wishlist_bp.route('/wishlist/remove/<int:wishlist_id>')
def remove_from_wishlist(wishlist_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM wishlist WHERE id = %s AND user_id = %s",
                (wishlist_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash('Removed from wishlist!', 'success')
    return redirect(url_for('wishlist.view_wishlist'))

# Check if product is in wishlist (API)
@wishlist_bp.route('/wishlist/check/<int:product_id>')
def check_wishlist(product_id):
    if not session.get('user_id'):
        return jsonify({'in_wishlist': False})

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM wishlist WHERE user_id = %s AND product_id = %s",
                (session['user_id'], product_id))
    result = cur.fetchone()
    cur.close()
    return jsonify({'in_wishlist': bool(result), 'wishlist_id': result[0] if result else None})