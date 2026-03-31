from flask import Blueprint, render_template, request, redirect, url_for, session, flash

cart_bp = Blueprint('cart', __name__)
mysql = None

def init_mysql(mysql_instance):
    global mysql
    mysql = mysql_instance

# View Cart
@cart_bp.route('/cart')
def view_cart():
    if not session.get('user_id'):
        flash('Please login to view cart!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, p.id, p.name, p.price, p.category, p.image_url, c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cur.fetchall()
    cur.close()

    cart_items = []
    total = 0
    for item in items:
        cart_items.append({
            'cart_id': item[0],
            'product_id': item[1],
            'name': item[2],
            'price': item[3],
            'category': item[4],
            'image_url': item[5],
            'quantity': item[6]
        })
        total += item[3] * item[6]

    return render_template('cart.html', cart_items=cart_items, total=total)

# Add to Cart
@cart_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    if not session.get('user_id'):
        flash('Please login to add items to cart!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    product_id = request.form['product_id']
    quantity = int(request.form.get('quantity', 1))

    cur = mysql.connection.cursor()

    # Check if product already in cart
    cur.execute("SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s",
                (user_id, product_id))
    existing = cur.fetchone()

    if existing:
        # Update quantity
        new_qty = existing[1] + quantity
        cur.execute("UPDATE cart SET quantity = %s WHERE id = %s",
                    (new_qty, existing[0]))
    else:
        # Add new item
        cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                    (user_id, product_id, quantity))

    mysql.connection.commit()
    cur.close()
    flash('Product added to cart!', 'success')
    return redirect(url_for('cart.view_cart'))

# Update Cart Quantity
@cart_bp.route('/cart/update', methods=['POST'])
def update_cart():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    cart_id = request.form['cart_id']
    quantity = int(request.form['quantity'])

    if quantity < 1:
        quantity = 1

    cur = mysql.connection.cursor()
    cur.execute("UPDATE cart SET quantity = %s WHERE id = %s",
                (quantity, cart_id))
    mysql.connection.commit()
    cur.close()
    flash('Cart updated!', 'success')
    return redirect(url_for('cart.view_cart'))

# Remove from Cart
@cart_bp.route('/cart/remove/<int:cart_id>')
def remove_from_cart(cart_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cart WHERE id = %s AND user_id = %s",
                (cart_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash('Item removed from cart!', 'success')
    return redirect(url_for('cart.view_cart'))

# Cart Count API
@cart_bp.route('/cart/count')
def cart_count():
    from flask import jsonify
    if not session.get('user_id'):
        return jsonify({'count': 0})

    cur = mysql.connection.cursor()
    cur.execute("SELECT SUM(quantity) FROM cart WHERE user_id = %s",
                (session['user_id'],))
    result = cur.fetchone()
    cur.close()

    count = int(result[0]) if result[0] else 0
    return jsonify({'count': count})