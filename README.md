# Financial Data Analytics Portfolio

This repository showcases an end-to-end **data analytics workflow**, from raw data cleaning in Excel to structured SQL analysis and (optionally) business intelligence visualization.

The goal of this project is to demonstrate practical, job-ready analytics skills using realistic business data and professional tooling.

---

## 📂 Project Structure
financial-data-analytics/
├── excel/
│ └── excel-data-cleaning-analysis/
├── sql/
│ └── sales-sql-analysis/
├── powerbi/
└── README.md

Each folder represents a key stage of the analytics pipeline.

---

## 🧹 Excel: Data Cleaning & Preparation

**Location:** `excel/excel-data-cleaning-analysis/`

This stage focuses on preparing raw sales data for analysis.

Key tasks include:
- Cleaning inconsistent or missing values
- Standardizing column formats
- Validating data types and ranges
- Preparing a clean dataset suitable for database ingestion

This step simulates the real-world scenario where analysts must work with imperfect data before analysis can begin.

📁 See the folder-level README for detailed cleaning steps and assumptions.

---

## 🗄️ SQL: Data Modeling & Analysis

**Location:** `sql/sales-sql-analysis/`

In this stage, the cleaned data is loaded into a PostgreSQL database and normalized into a relational schema.

### Highlights:
- Schema design with fact and dimension tables
- Primary and foreign key relationships
- SQL insert scripts to populate tables
- Analytical queries answering business questions such as:
  - Revenue and profit trends
  - Top customers and products
  - Performance by category and region

**Key files:**
- `schema.sql` – database schema and constraints
- `inserts.sql` – data loading logic
- `analysis.sql` – business-focused SQL queries

This section demonstrates strong SQL fundamentals, problem-solving, and analytical thinking.

---

## 📊 Power BI (Optional / In Progress)

**Location:** `powerbi/`

This section is reserved for visualizing insights derived from the SQL analysis using Power BI dashboards.

Planned outputs include:
- Sales and profit dashboards
- Trend analysis
- Category and regional performance summaries

---

## 🧠 Skills Demonstrated

- Data cleaning and validation (Excel)
- Relational database design
- SQL querying and analysis
- Business-oriented data interpretation
- Git & GitHub project organization

---

## 🚀 Purpose

This repository is part of a broader effort to build a **professional data analytics portfolio** and demonstrate readiness for entry-level data analyst or analytics-focused roles.

---
