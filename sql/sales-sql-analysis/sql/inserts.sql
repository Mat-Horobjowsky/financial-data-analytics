INSERT INTO customers (
    customer_id, segment, region, country, state, city
)
SELECT DISTINCT 
    "Customer ID", "Segment", "Region", "Country", "State", "City"
FROM superstore_raw
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO products (
    product_id,
    product_name,
    category,
    sub_category
)
SELECT DISTINCT 
    "Product ID", 
    "Product Name", 
    "Category", 
    "Sub-Category"
FROM superstore_raw
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO orders (
    order_id, order_date, ship_date, ship_mode, 
    customer_id, product_id, quantity, sales, discount, profit
)
SELECT 
    "Order ID", 
    TO_DATE("Order Date", 'MM/DD/YYYY'), 
    TO_DATE("Ship Date", 'MM/DD/YYYY'), 
    "Ship Mode", 
    "Customer ID", 
    "Product ID", 
    "Quantity", 
    "Sales"::NUMERIC(10,2), 
    "Discount"::NUMERIC(5,2), 
    "Profit"::NUMERIC(10,2)
FROM superstore_raw
ON CONFLICT (order_id, product_id) DO NOTHING;