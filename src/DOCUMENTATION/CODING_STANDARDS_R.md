# R Coding Standards & Guidelines

## Overview
This document outlines the coding standards and best practices used in this project. These guidelines ensure consistency, readability, and maintainability across all R and R Markdown files.

---

## 1. File Organization

### R Markdown Structure
- **YAML Front Matter**: Include title, output format, and generation date
- **Setup Chunk**: First code chunk should contain `knitr::opts_chunk$set()` with appropriate options
- **Logical Sections**: Organize code into distinct chunks with clear headers
- **Sequential Flow**: Arrange code in logical order (load → clean → transform → analyze → export)

**Example:**
```
---
title: "Project Name"
output: html_document
date: "YYYY-MM-DD"
---

```{r setup, include=FALSE}
knitr::opts_chunk$set(echo = TRUE)
```
```

---

## 2. Naming Conventions

### Variables and Objects
- **Style**: `snake_case`
- **Descriptive**: Names should clearly indicate content/purpose

### Columns and Features
- **Style**: `snake_case` or `descriptive_name`

---

## 3. Required Packages & Dependencies

### Standard Packages (Tidyverse Ecosystem)
- `dplyr` - Data manipulation
- `tidyr` - Data tidying and reshaping
- `ggplot2` - Data visualization
- `ggthemes` - Additional ggplot2 themes

### Additional Packages Used
- `openxlsx` - Excel file I/O
- `knitr` - R Markdown rendering

### Import Pattern
```r
library(dplyr)
library(tidyr)
library(openxlsx)
library(ggplot2)
library(ggthemes)
```

---

## 4. Data Manipulation

### Preferred Syntax
- **Pipe Operator**: Use `|>` for method chaining
- **dplyr Verbs**: 
  - `filter()` - Subset rows by conditions
  - `select()` - Choose or create columns
  - `mutate()` - Create/modify columns
  - `left_join()` - Merge dataframes (preserve left)
  - `distinct()` - Remove duplicate rows
  - `pivot_wider()` - Wide format transformation
  - `summarise()` - Aggregate data

### Example Pattern
```r
df_enhanced <- df |>
  filter(condition) |>
  mutate(new_col = calculation) |>
  select(-unwanted_col)
```

### Data Cleaning Practices
- Remove duplicates using `distinct()` with `.keep_all` parameter
- Use `left_join()` with `by` parameter for explicit join keys
- Handle missing values with `na.omit()` and `is.finite()`
- Filter edge cases (e.g., values outside reasonable ranges)
- Use `coalesce()` to fill missing values with alternatives

**Example:**
```r
df <- df |>
  distinct(key_col1, key_col2, .keep_all = TRUE)

df_clean <- df |>
  filter(abs(column) < threshold) |>
  mutate(new_col = coalesce(option1, option2))
```

---

## 5. Data Visualization

### ggplot2 Standards
- **Base Layer**: Start with `ggplot(data, aes(...))`
- **Geoms**: Use `geom_line()`, `geom_point()`, etc. based on visualization type
- **Aesthetics**: Leverage color, fill, size for meaningful distinctions
- **Labels**: Always include informative title, axis labels, and legend labels
- **Theme**: Use `theme_minimal()` for clean, professional appearance
- **Colors**: Use `scale_color_colorblind()` for accessibility

### Example Pattern
```r
ggplot(df, aes(x = x_var, y = y_var, color = factor(group_var))) +
  geom_line() +
  labs(
    title = "Descriptive Title",
    x = "X Axis Label with Units",
    y = "Y Axis Label with Units",
    color = "Legend Title"
  ) +
  scale_x_continuous(breaks = seq(0, max, by = interval)) +
  scale_color_colorblind() +
  expand_limits(y = 0) +
  theme_minimal()
```

### Best Practices
- Always set axis breaks for clarity
- Use `expand_limits()` to ensure y-axis starts at 0 when appropriate
- Include units in axis labels
- Use factor conversion for discrete color mapping
- Label legend items descriptively

---

## 6. Comments & Documentation

### Chunk Headers
- Add descriptive headers before each code chunk explaining its purpose
- Use section breaks with `#` symbols to delineate major sections

### Inline Comments
- Comment non-obvious operations and calculations
- Explain the "why" when the code isn't self-explanatory
- Use `#` for single-line comments

---

## 7. Data Transformation Patterns

### Feature Engineering
When creating derived columns from existing data:
1. Define the transformation logic clearly
2. Use `mutate()` to add calculated columns
3. Chain join operations for multi-step lags or lookups
4. Document the business logic in comments

---

## 8. Output & Export

### File Output Standards
- **Format Preference**: Excel (`.xlsx`) for tabular data
- **Method**: Use `write.xlsx()` from `openxlsx`
- **Multiple Sheets**: Create list of dataframes for export

**Example:**
```r
list_of_datasets <- list(
  "sheet_name_1" = df_pivot_1,
  "sheet_name_2" = df_pivot_2
)
write.xlsx(list_of_datasets, file = "output.xlsx")
```

---

## 9. Code Quality Checklist

Before finalizing code:
- [ ] All variables use `snake_case` naming
- [ ] Each code chunk has a descriptive comment
- [ ] All calculations are documented
- [ ] Missing value handling is explicit
- [ ] Visualizations include all necessary labels
- [ ] Colors are colorblind-friendly
- [ ] Code is readable (proper spacing, indentation)
- [ ] Pipes (`|>`) are line-broken for readability
- [ ] Temporary columns are cleaned up after use
- [ ] Edge cases are handled (filtering, NAs, infinite values)

---

## 10. Workflow Process

### Typical Analysis Workflow:
1. **Load Data** - Use `load()` or `read.xlsx()`
2. **Explore** - Check structure with `str()`, `summary()`, `glimpse()`
3. **Clean** - Remove duplicates, handle missing values
4. **Engineer** - Create new features via `mutate()`
5. **Transform** - Reshape with `pivot_wider()`, `pivot_longer()`
6. **Analyze** - Filter, summarize, calculate statistics
7. **Visualize** - Create publication-quality plots
8. **Export** - Write results to Excel/files

---

## 11. Notes for AI Agents

When working with this codebase:
- Preserve the `snake_case` naming convention
- Always use tidyverse/dplyr patterns over base R when possible
- Include meaningful comments for non-obvious operations
- Chain operations with `|>` rather than intermediate assignments (when appropriate)
- Ensure visualizations follow the ggplot2 patterns outlined above
- Handle edge cases explicitly (NAs, infinite values, outliers)
- Document transformations clearly so the logic is reproducible
