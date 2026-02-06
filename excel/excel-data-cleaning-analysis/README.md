# Excel Data Cleaning & Analysis (Power BI–Ready)

## Project Overview

This project demonstrates my ability to clean, transform, and analyze messy business data using **Excel** and **Power Query**, following real-world data analyst workflows. The final dataset is fully standardized and ready for downstream analysis in **Power BI**.

The focus of this project is not just analysis, but **data preparation**, which is a critical (and often overlooked) part of analytics work.

---

## Tools Used

* Microsoft Excel
* Power Query (Excel)
* PivotTables & PivotCharts

---

## Dataset Description

The dataset simulates a real-world sales export containing common data quality issues:

* Inconsistent date formats (US, EU, text-based)
* Duplicate records
* Mixed data types (numbers stored as text, currency symbols)
* Inconsistent text casing and spacing
* Missing values

---

## Data Cleaning Process

### 1. Text Standardization

* Removed leading/trailing spaces using TRIM
* Standardized text casing for categories and IDs
* Normalized Product IDs to prevent failed joins

### 2. Date Normalization

* Identified mixed date formats within a single column
* Used conditional parsing and helper logic to convert all values into a single, consistent date format
* Validated dates to ensure Excel recognized them as true date values

### 3. Numeric Data Cleanup

* Removed currency symbols from revenue values
* Converted text-based numbers into numeric data types
* Replaced invalid values (e.g., N/A) with nulls where appropriate

### 4. Duplicate Handling

* Identified exact duplicate records
* Removed duplicates safely without affecting legitimate transactions

### 5. Power Query Transformation

* Loaded cleaned data into Power Query
* Explicitly set correct data types for all columns
* Removed unnecessary columns
* Automated all transformation steps for repeatable refreshes
* Loaded the final table into the Excel Data Model (Power BI–ready)

---

## Analysis & Insights

Using PivotTables and PivotCharts, I analyzed:

* Revenue by product category
* Order volume by category
* Revenue trends over time (monthly)

These analyses allowed quick identification of high-performing categories and seasonal patterns.

---

## Key Skills Demonstrated

* Data cleaning and preparation
* Handling inconsistent date formats
* Conditional logic in Excel
* Power Query (ETL-style transformations)
* PivotTable-based analysis
* Preparing datasets for Power BI

---

## Outcome

The final output is a clean, structured dataset that can be refreshed automatically and loaded directly into Power BI for further modeling and visualization.

This project reflects real analyst work, where data quality, repeatability, and clarity are as important as the final insights.
