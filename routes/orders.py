from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import json

orders_bp = Blueprint('orders', __name__)
mysql = None

def init_mysql(mysql_instance):
    global mysql
    mysql = mysql_instance

# Checkout Page
@orders_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('user_id'):
        flash('Please login to checkout!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # Get cart items
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, p.id, p.name, p.price, p.category, p.image_url, c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cur.fetchall()

    if not items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart.view_cart'))

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

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'card')

        # Calculate fraud risk score using AI module
        from ai.fraud_detector import calculate_fraud_score
        fraud_score, reasons, risk_level = calculate_fraud_score(mysql, total, user_id)

        # Store reasons as JSON string
        reasons_json = json.dumps(reasons)

        # Create order
        
        cur.execute("""
            INSERT INTO orders (user_id, total_amount, status, fraud_risk_score, fraud_reasons)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, total, 'confirmed', fraud_score, reasons_json))

        mysql.connection.commit()
        order_id = cur.lastrowid

        # Save order items and update stock
        for item in cart_items:
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['product_id'], item['quantity'], item['price']))

        # Update product stock
        cur.execute("""
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s AND stock >= %s
        """, (item['quantity'], item['product_id'], item['quantity']))

        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        mysql.connection.commit()
        cur.close()

        flash(f'Order #{order_id} placed successfully!', 'success')
        return redirect(url_for('orders.order_success', order_id=order_id))

    cur.close()
    return render_template('checkout.html', cart_items=cart_items, total=total)

# Order Success Page
@orders_bp.route('/order-success/<int:order_id>')
def order_success(order_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, session['user_id']))
    order = cur.fetchone()
    cur.close()

    if not order:
        return redirect(url_for('home'))

    order_dict = {
        'id': order[0],
        'total_amount': order[2],
        'status': order[3],
        'fraud_risk_score': order[4],
        'created_at': order[5]
    }

    return render_template('order_success.html', order=order_dict)

# My Orders Page
@orders_bp.route('/orders')
def my_orders():
    if not session.get('user_id'):
        flash('Please login to view orders!', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM orders WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))
    orders = cur.fetchall()
    cur.close()

    orders_list = []
    for o in orders:
        orders_list.append({
            'id': o[0],
            'total_amount': o[2],
            'status': o[3],
            'fraud_risk_score': o[4],
            'created_at': o[5]
        })

    return render_template('orders.html', orders=orders_list)