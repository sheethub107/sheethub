import matplotlib.pyplot as plt

def bar_chart(df, x_col, y_col):
    fig, ax = plt.subplots()
    df.groupby(x_col)[y_col].sum().plot(kind="bar", ax=ax)
    return fig

def line_chart(df, x_col, y_col):
    fig, ax = plt.subplots()
    df.sort_values(x_col).plot(x=x_col, y=y_col, ax=ax)
    return fig

def histogram(df, col):
    fig, ax = plt.subplots()
    df[col].plot(kind="hist", bins=20, ax=ax)
    return fig

def pie_chart(df, col):
    fig, ax = plt.subplots()
    df[col].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax)
    ax.set_ylabel("")
    return fig
