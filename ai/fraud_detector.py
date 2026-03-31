from datetime import datetime, timedelta

def calculate_fraud_score(mysql, total, user_id):
    score = 0.0
    reasons = []

    cur = mysql.connection.cursor()

    # Factor 1: High order amount
    if total > 10000:
        score += 0.2
        reasons.append("High order amount")

    # Factor 2: Very high order amount
    if total > 50000:
        score += 0.4
        reasons.append("Very high order amount")

    # Factor 3: Check if new account (created less than 1 day ago)
    cur.execute("SELECT created_at FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if user:
        account_age = datetime.now() - user[0]
        if account_age < timedelta(days=1):
            score += 0.2
            reasons.append("New account")

    # Factor 4: Multiple orders in last 1 hour
    cur.execute("""
        SELECT COUNT(*) FROM orders
        WHERE user_id = %s
        AND created_at >= %s
    """, (user_id, datetime.now() - timedelta(hours=1)))
    recent_orders = cur.fetchone()[0]
    if recent_orders >= 2:
        score += 0.3
        reasons.append("Multiple orders in short time")

    # Factor 5: First large order
    cur.execute("SELECT COUNT(*) FROM orders WHERE user_id = %s", (user_id,))
    total_orders = cur.fetchone()[0]
    if total_orders == 0 and total > 5000:
        score += 0.2
        reasons.append("Large first order")

    cur.close()

    # Cap score at 1.0
    score = min(round(score, 2), 1.0)

    # Determine risk level
    if score >= 0.6:
        risk_level = "HIGH RISK ⚠️"
    elif score >= 0.3:
        risk_level = "MEDIUM RISK ⚡"
    else:
        risk_level = "LOW RISK ✅"

    return score, reasons, risk_level