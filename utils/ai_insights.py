# utils/ai_insights.py
import pandas as pd

def generate_ai_insights(df: pd.DataFrame) -> list[str]:
    """
    Generate human-readable insights from a cleaned dataframe.
    Works without any AI API.
    """
    insights = []

    if df.empty:
        return ["Dataset is empty."]

    insights.append(f"The dataset contains {len(df)} records and {df.shape[1]} columns.")

    # Column insights
    if "department" in df.columns:
        dept_counts = df["department"].value_counts()
        top_dept = dept_counts.idxmax()
        insights.append(
            f"The largest department is {top_dept} with {dept_counts[top_dept]} employees."
        )

    # Salary insights
    if "salary" in df.columns:
        avg_salary = int(df["salary"].mean())
        max_salary = int(df["salary"].max())
        insights.append(f"The average salary is approximately {avg_salary}.")
        insights.append(f"The highest salary is {max_salary}.")

        # Outlier detection
        threshold = df["salary"].mean() + 2 * df["salary"].std()
        outliers = df[df["salary"] > threshold]
        if not outliers.empty:
            insights.append(
                f"{len(outliers)} employees have unusually high salaries."
            )

    # Date insights
    if "hiredate" in df.columns:
        try:
            df["hiredate"] = pd.to_datetime(df["hiredate"], errors="coerce")
            year_counts = df["hiredate"].dt.year.value_counts()
            top_year = year_counts.idxmax()
            insights.append(
                f"The most common hiring year is {int(top_year)}."
            )
        except Exception:
            pass

    # Missing data
    missing = df.isna().sum().sum()
    if missing > 0:
        insights.append(f"There are {missing} missing values remaining in the dataset.")
    else:
        insights.append("No missing values detected. Data quality is high.")

    return insights
