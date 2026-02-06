# Sales SQL Analysis

This project demonstrates **SQL-based data modeling and analysis** using a realistic sales dataset.  
The goal is to showcase practical SQL skills, including schema design, relational thinking, and analytical querying to answer business-focused questions.

---

## 📌 Project Overview

In this project, an analysis-ready sales dataset is loaded into a relational database and analyzed using SQL.

The work focuses on:
- Designing a normalized database schema
- Writing clean, readable SQL queries
- Translating business questions into analytical insights

This project reflects real-world scenarios where analysts work with structured data provided by upstream systems.

---

## 🗂️ Dataset Description

The dataset represents historical sales transactions and includes information such as:
- Orders and order dates
- Products and product categories
- Customers
- Sales revenue, costs, and profit

The data is assumed to be **pre-cleaned** and suitable for direct database ingestion.

---

## 🏗️ Database Schema

The database is structured using a relational model with fact and dimension tables.

### Key tables include:
- **customers** – customer identifiers and attributes  
- **products** – product details and categories  
- **orders** – order-level transaction data  
- **sales** – fact table containing revenue, cost, and profit metrics  

Primary and foreign keys are used to enforce relationships and ensure data integrity.

📄 See `schema.sql` for full table definitions.

---

## 🧪 SQL Files

| File | Description |
|-----|-------------|
| `schema.sql` | Creates database tables and relationships |
| `inserts.sql` | Inserts data into tables |
| `analysis.sql` | Contains analytical SQL queries |

---

## 📊 Analysis & Business Questions

The SQL queries explore questions such as:
- What are the overall revenue and profit trends?
- Which products and categories perform best?
- Who are the top customers by revenue?
- How does performance vary across time periods?

The focus is on writing **clear, maintainable SQL** rather than overly complex queries.

---

## 🧠 Skills Demonstrated

- SQL querying and joins
- Aggregations and filtering
- Relational schema design
- Business-oriented data analysis
- Query organization and documentation

---

## 🚀 Purpose

This project is part of a broader **data analytics portfolio**, intended to demonstrate readiness for entry-level data analyst and analytics-focused roles.

---