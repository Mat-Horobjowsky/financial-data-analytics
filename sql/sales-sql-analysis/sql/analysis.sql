/* =========================================================
   Sales Performance & Customer Analysis
   ========================================================= */


/* 1. Total revenue, profit, and profit margin */
SELECT
    ROUND(SUM(sales), 2)  AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 2) AS profit_margin_pct
FROM orders;


/* 2. Monthly revenue and profit trend */
SELECT
    DATE_TRUNC('month', order_date) AS month,
    ROUND(SUM(sales), 2)  AS monthly_revenue,
    ROUND(SUM(profit), 2) AS monthly_profit
FROM orders
GROUP BY month
ORDER BY month;


/* 3. Revenue and profit by product category */
SELECT
    p.category,
    ROUND(SUM(o.sales), 2)  AS revenue,
    ROUND(SUM(o.profit), 2) AS profit
FROM orders o
JOIN products p
    ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;


/* 4. Top 10 products by total revenue */
SELECT
    p.product_name,
    ROUND(SUM(o.sales), 2) AS total_sales
FROM orders o
JOIN products p
    ON o.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_sales DESC
LIMIT 10;


/* 5. Top 10 customers by total revenue */
SELECT
    o.customer_id,
    ROUND(SUM(o.sales), 2) AS customer_revenue
FROM orders o
GROUP BY o.customer_id
ORDER BY customer_revenue DESC
LIMIT 10;


/* 6. Customer purchase behavior (order count & average order value) */
SELECT
    o.customer_id,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(o.sales), 2) AS total_spent,
    ROUND(SUM(o.sales) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o
GROUP BY o.customer_id
ORDER BY total_spent DESC;


/* 7. Regional performance analysis */
SELECT
    c.region,
    ROUND(SUM(o.sales), 2)  AS revenue,
    ROUND(SUM(o.profit), 2) AS profit
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY revenue DESC;


/* 8. Impact of discounts on profitability */
SELECT
    CASE
        WHEN discount = 0 THEN 'No Discount'
        WHEN discount <= 0.2 THEN 'Low Discount'
        WHEN discount <= 0.4 THEN 'Medium Discount'
        ELSE 'High Discount'
    END AS discount_bucket,
    COUNT(*) AS order_count,
    ROUND(AVG(profit), 2) AS avg_profit
FROM orders
GROUP BY discount_bucket
ORDER BY avg_profit DESC;


/* 9. Repeat vs one-time customers */
SELECT
    CASE
        WHEN order_count = 1 THEN 'One-time Customer'
        ELSE 'Repeat Customer'
    END AS customer_type,
    COUNT(*) AS number_of_customers
FROM (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS order_count
    FROM orders
    GROUP BY customer_id
) sub
GROUP BY customer_type;


/* 10. Ranking customers by total revenue (window function) */
SELECT
    customer_id,
    ROUND(SUM(sales), 2) AS total_revenue,
    RANK() OVER (ORDER BY SUM(sales) DESC) AS revenue_rank
FROM orders
GROUP BY customer_id
ORDER BY revenue_rank;
	

	



