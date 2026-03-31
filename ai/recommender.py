import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def track_activity(mysql, user_id, product_id, activity_type):
    """Track user activity (view, click, purchase)"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO user_activity (user_id, product_id, activity_type)
            VALUES (%s, %s, %s)
        """, (user_id, product_id, activity_type))
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Activity tracking error: {e}")


def get_collaborative_recommendations(mysql, user_id, current_product_id=None):
    """
    Collaborative Filtering using Cosine Similarity
    Finds users similar to current user and recommends
    what they bought/viewed
    """
    try:
        cur = mysql.connection.cursor()

        # Get all user-product interactions
        cur.execute("""
            SELECT user_id, product_id, COUNT(*) as interaction_count
            FROM user_activity
            GROUP BY user_id, product_id
        """)
        interactions = cur.fetchall()

        if not interactions or len(interactions) < 2:
            cur.close()
            return []

        # Build user-product matrix using pandas
        df = pd.DataFrame(interactions, columns=['user_id', 'product_id', 'score'])
        user_product_matrix = df.pivot_table(
            index='user_id',
            columns='product_id',
            values='score',
            fill_value=0
        )

        # Check if current user is in matrix
        if user_id not in user_product_matrix.index:
            cur.close()
            return []

        # Calculate cosine similarity between users
        similarity_matrix = cosine_similarity(user_product_matrix)
        similarity_df = pd.DataFrame(
            similarity_matrix,
            index=user_product_matrix.index,
            columns=user_product_matrix.index
        )

        # Get similar users (excluding current user)
        similar_users = similarity_df[user_id].drop(user_id).sort_values(ascending=False)

        if similar_users.empty:
            cur.close()
            return []

        # Get top similar user
        top_similar_user = similar_users.index[0]

        # Get products bought by similar user
        cur.execute("""
            SELECT DISTINCT product_id FROM user_activity
            WHERE user_id = %s
        """, (int(top_similar_user),))
        similar_user_products = [row[0] for row in cur.fetchall()]

        # Get products current user already interacted with
        cur.execute("""
            SELECT DISTINCT product_id FROM user_activity
            WHERE user_id = %s
        """, (user_id,))
        current_user_products = [row[0] for row in cur.fetchall()]

        # Recommend products similar user bought but current user hasn't
        recommend_ids = [
            pid for pid in similar_user_products
            if pid not in current_user_products
            and pid != current_product_id
        ]

        recommendations = []
        for pid in recommend_ids[:4]:
            cur.execute("""
                SELECT id, name, price, category, image_url, description
                FROM products WHERE id = %s
            """, (pid,))
            p = cur.fetchone()
            if p:
                recommendations.append({
                    'id': p[0],
                    'name': p[1],
                    'price': p[2],
                    'category': p[3],
                    'image_url': p[4],
                    'description': p[5],
                    'reason': '👥 Users like you bought this'
                })

        cur.close()
        return recommendations

    except Exception as e:
        print(f"Collaborative filtering error: {e}")
        return []


def get_content_recommendations(mysql, user_id, current_product_id=None, category=None):
    """
    Content Based Filtering
    Recommends products from same category
    """
    try:
        cur = mysql.connection.cursor()
        recommendations = []
        seen_ids = set()

        if current_product_id:
            seen_ids.add(current_product_id)

        # Get category from current product
        if not category and current_product_id:
            cur.execute("SELECT category FROM products WHERE id = %s",
                       (current_product_id,))
            cat = cur.fetchone()
            if cat:
                category = cat[0]

        # Get category from last order
        if not category and user_id:
            cur.execute("""
                SELECT p.category FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = %s
                ORDER BY o.created_at DESC LIMIT 1
            """, (user_id,))
            last = cur.fetchone()
            if last:
                category = last[0]

        if category:
            exclude = tuple(seen_ids) if seen_ids else (0,)
            cur.execute("""
                SELECT id, name, price, category, image_url, description
                FROM products
                WHERE category = %s AND id NOT IN %s
                LIMIT 4
            """, (category, exclude))
            products = cur.fetchall()

            for p in products:
                if p[0] not in seen_ids:
                    recommendations.append({
                        'id': p[0],
                        'name': p[1],
                        'price': p[2],
                        'category': p[3],
                        'image_url': p[4],
                        'description': p[5],
                        'reason': '🏷️ Similar to what you like'
                    })
                    seen_ids.add(p[0])

        cur.close()
        return recommendations

    except Exception as e:
        print(f"Content filtering error: {e}")
        return []


def get_recommendations(mysql, user_id, current_product_id=None, category=None):
    """
    Main recommendation function
    Combines Collaborative + Content Based + Fallback
    """
    recommendations = []
    seen_ids = set()

    if current_product_id:
        seen_ids.add(current_product_id)

    # Step 1: Try Collaborative Filtering first
    if user_id:
        collab = get_collaborative_recommendations(mysql, user_id, current_product_id)
        for r in collab:
            if r['id'] not in seen_ids:
                recommendations.append(r)
                seen_ids.add(r['id'])

    # Step 2: Fill with Content Based if needed
    if len(recommendations) < 4:
        content = get_content_recommendations(mysql, user_id, current_product_id, category)
        for r in content:
            if r['id'] not in seen_ids:
                recommendations.append(r)
                seen_ids.add(r['id'])

    # Step 3: Fallback to popular products
    if len(recommendations) < 4:
        try:
            cur = mysql.connection.cursor()
            needed = 4 - len(recommendations)
            exclude = tuple(seen_ids) if seen_ids else (0,)
            cur.execute("""
                SELECT id, name, price, category, image_url, description
                FROM products WHERE id NOT IN %s
                LIMIT %s
            """, (exclude, needed))
            products = cur.fetchall()
            cur.close()

            for p in products:
                if p[0] not in seen_ids:
                    recommendations.append({
                        'id': p[0],
                        'name': p[1],
                        'price': p[2],
                        'category': p[3],
                        'image_url': p[4],
                        'description': p[5],
                        'reason': '🔥 Popular product'
                    })
                    seen_ids.add(p[0])
        except Exception as e:
            print(f"Fallback error: {e}")

    return recommendations[:4]