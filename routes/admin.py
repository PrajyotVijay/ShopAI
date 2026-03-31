from flask import Blueprint, render_template, request, redirect, url_for, session, flash

admin_bp = Blueprint('admin', __name__)
mysql = None

def init_mysql(mysql_instance):
    global mysql
    mysql = mysql_instance

# Admin access decorator
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please login!', 'error')
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('Admin access required!', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated

# Admin Dashboard
@admin_bp.route('/admin')
@admin_required
def dashboard():
    cur = mysql.connection.cursor()

    # Get stats
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE fraud_risk_score > 0.5")
    high_risk_orders = cur.fetchone()[0]

    cur.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cur.fetchone()[0] or 0
    total_revenue = round(float(total_revenue), 2)
    # Recent orders
    cur.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5")
    recent = cur.fetchall()
    recent_orders = []
    for o in recent:
        recent_orders.append({
            'id': o[0],
            'user_id': o[1],
            'total_amount': o[2],
            'status': o[3],
            'fraud_risk_score': o[4],
            'created_at': o[5]
        })

    # Sales chart data (last 6 orders)
    cur.execute("SELECT created_at, total_amount FROM orders ORDER BY created_at DESC LIMIT 6")
    sales = cur.fetchall()
    chart_labels = [str(s[0])[:10] for s in sales]
    chart_data = [float(s[1]) for s in sales]
    cur.close()

    return render_template('admin/dashboard.html',
                       total_users=total_users,
                       total_products=total_products,
                       total_orders=total_orders,
                       high_risk_orders=high_risk_orders,
                       total_revenue=total_revenue,
                       recent_orders=recent_orders,
                       chart_labels=chart_labels,
                       chart_data=chart_data)

# Admin Products
@admin_bp.route('/admin/products')
@admin_required
def products():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    prods = cur.fetchall()
    cur.close()

    products_list = []
    for p in prods:
        products_list.append({
            'id': p[0],
            'name': p[1],
            'description': p[2],
            'price': p[3],
            'category': p[4],
            'image_url': p[5],
            'stock': p[6]
        })

    return render_template('admin/products.html', products=products_list)

# Add Product
@admin_bp.route('/admin/products/add', methods=['POST'])
@admin_required
def add_product():
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    category = request.form['category']
    image_url = request.form.get('image_url', '')
    stock = request.form['stock']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO products (name, description, price, category, image_url, stock)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, description, price, category, image_url, stock))
    mysql.connection.commit()
    cur.close()
    flash('Product added successfully!', 'success')
    return redirect(url_for('admin.products'))

# Edit Product
@admin_bp.route('/admin/products/edit', methods=['POST'])
@admin_required
def edit_product():
    product_id = request.form['product_id']
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    category = request.form['category']
    image_url = request.form.get('image_url', '')
    stock = request.form['stock']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE products
        SET name=%s, description=%s, price=%s, category=%s, image_url=%s, stock=%s
        WHERE id=%s
    """, (name, description, price, category, image_url, stock, product_id))
    mysql.connection.commit()
    cur.close()
    flash('Product updated successfully!', 'success')
    return redirect(url_for('admin.products'))

# Delete Product
@admin_bp.route('/admin/products/delete/<int:product_id>')
@admin_required
def delete_product(product_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    mysql.connection.commit()
    cur.close()
    flash('Product deleted!', 'success')
    return redirect(url_for('admin.products'))

# Admin Orders
# Admin Orders
@admin_bp.route('/admin/orders')
@admin_required
def orders():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT o.id, o.user_id, u.name, u.email, o.total_amount,
               o.status, o.fraud_risk_score, o.fraud_reasons, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    """)
    all_orders = cur.fetchall()
    cur.close()

    orders_list = []
    for o in all_orders:
        # Parse reasons from JSON
        import json
        try:
            reasons = json.loads(o[7]) if o[7] else []
        except:
            reasons = []

        # Determine risk level
        score = o[6]
        if score >= 0.6:
            risk_level = "HIGH RISK"
            risk_color = "danger"
        elif score >= 0.3:
            risk_level = "MEDIUM RISK"
            risk_color = "warning"
        else:
            risk_level = "LOW RISK"
            risk_color = "success"

        orders_list.append({
            'id': o[0],
            'user_id': o[1],
            'user_name': o[2],
            'user_email': o[3],
            'total_amount': o[4],
            'status': o[5],
            'fraud_risk_score': o[6],
            'fraud_reasons': reasons,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'created_at': o[8]
        })

    return render_template('admin/orders.html', orders=orders_list)

    # View Categories
@admin_bp.route('/admin/categories')
@admin_required
def categories():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    cats = cur.fetchall()
    cur.close()

    categories_list = []
    for c in cats:
        categories_list.append({
            'id': c[0],
            'name': c[1],
            'icon': c[2],
            'created_at': c[3]
        })

    return render_template('admin/categories.html', categories=categories_list)

# Add Category
@admin_bp.route('/admin/categories/add', methods=['POST'])
@admin_required
def add_category():
    name = request.form['name']
    icon = request.form.get('icon', 'bi-tag')

    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO categories (name, icon) VALUES (%s, %s)", (name, icon))
        mysql.connection.commit()
        cur.close()
        flash(f'Category "{name}" added successfully!', 'success')
    except:
        flash('Category already exists!', 'error')

    return redirect(url_for('admin.categories'))

# Delete Category
@admin_bp.route('/admin/categories/delete/<int:cat_id>')
@admin_required
def delete_category(cat_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
    mysql.connection.commit()
    cur.close()
    flash('Category deleted!', 'success')
    return redirect(url_for('admin.categories'))

# Update Order Status
@admin_bp.route('/admin/orders/update-status', methods=['POST'])
@admin_required
def update_order_status():
    order_id = request.form['order_id']
    status = request.form['status']

    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    mysql.connection.commit()
    cur.close()

    flash(f'Order #{order_id} status updated to {status}!', 'success')
    return redirect(url_for('admin.orders'))