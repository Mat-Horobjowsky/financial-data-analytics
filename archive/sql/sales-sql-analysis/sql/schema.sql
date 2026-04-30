CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    segment VARCHAR(50),
    region VARCHAR(50),
    country VARCHAR(50),
    state VARCHAR(50),
    city VARCHAR(50)
);


CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(128),
    category VARCHAR(50),
    sub_category VARCHAR(50)
);

CREATE TABLE orders (
    order_id VARCHAR(50),
    order_date DATE,
    ship_date DATE,
    ship_mode VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    quantity INT,
    sales NUMERIC(10,2),
    discount NUMERIC(5,2),
    profit NUMERIC(10,2),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);










