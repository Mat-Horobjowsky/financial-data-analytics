📊 Sales Performance & Customer Analysis (SQL)
Overview

This project analyzes retail sales data using PostgreSQL to answer common business questions around sales performance, customer behavior, and product profitability.

The dataset comes from a Superstore-style retail dataset and was intentionally normalized into multiple tables to reflect how real-world analytical databases are structured.

The goal of this project is to demonstrate:

SQL querying skills

data modeling and normalization

handling messy real-world data

analytical thinking, not just syntax

Dataset

The original dataset was provided as a single flat CSV file (superstore_raw) containing order, customer, and product information.

Key characteristics:

anonymized customer data (no customer names)

mixed data types (dates stored as text)

business-oriented fields such as sales, profit, and discounts

Data Modeling & Normalization

Instead of querying the raw flat table directly, the data was split into three relational tables:

Tables Created

customers – customer-level attributes

products – product-level attributes

orders – transactional sales data

This design:

reduces redundancy

improves query clarity

enables realistic JOIN-based analysis

Schema Design

Primary keys were defined for each dimension table

Foreign keys were added to the orders table to enforce data integrity

Dates were converted from text to proper DATE types

This mirrors how data is structured in real analytics and BI environments.

ETL Process (Extract, Transform, Load)
1. Raw Data Import

The CSV file was first imported into PostgreSQL as a staging table:

superstore_raw

This table preserves the original column names and data types from the source file.

2. Data Transformation

During insertion into the final tables:

Columns with spaces and capitalization were mapped to clean snake_case names

Text-based date fields were converted using TO_DATE()

Numeric fields were cast to appropriate numeric types

Duplicate dimension records were removed using SELECT DISTINCT

3. Data Loading

Data was inserted in the following order to respect foreign key constraints:

customers

products

orders

This ensures referential integrity across tables.

Example Business Questions Answered

Some of the questions explored in this project include:

What is total revenue and profit by month?

Which product categories generate the most revenue?

Which regions are the most profitable?

Who are the highest-value customers?

How does discounting impact profitability?

(Queries can be found in the /sql folder.)

Tools Used

PostgreSQL – database engine

DBeaver – SQL client

SQL – data modeling and analysis

GitHub – version control and project documentation

Key Takeaways

Real-world datasets are rarely clean and require preprocessing

Proper schema design improves both performance and readability

SQL is not just about querying, but about structuring data for analysis

Next Steps

Planned enhancements for this project include:

advanced SQL queries using window functions

customer lifetime value analysis

year-over-year sales comparisons

integration with Power BI for visualization