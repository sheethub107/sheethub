import pandas as pd

def generate_ai_insights(df):
    insights = []

    insights.append(
        f"The dataset contains {len(df)} records and {df.shape[1]} columns."
    )

    if "department" in df.columns:
        top = df["department"].value_counts().idxmax()
        insights.append(f"The largest department is {top}.")

    if "salary" in df.columns:
        insights.append(f"The average salary is approximately {int(df['salary'].mean())}.")
        insights.append(f"The highest salary is {int(df['salary'].max())}.")

    if "hiredate" in df.columns:
        dates = pd.to_datetime(df["hiredate"], errors="coerce")
        if dates.notna().any():
            insights.append(
                f"The most common hiring year is {int(dates.dt.year.value_counts().idxmax())}."
            )

    missing = df.isna().sum().sum()
    if missing:
        insights.append(
            f"{missing} empty cells remain in optional (non-critical) fields."
        )

    return insights
