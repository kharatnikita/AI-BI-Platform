import os
import re
import uuid

import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_file
)

from werkzeug.utils import secure_filename

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from config import get_db_connection


# =====================================
# Flask App Configuration
# =====================================

app = Flask(__name__)
app.secret_key = "nikita123"


# =====================================
# Upload Folder Configuration
# =====================================

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# =====================================
# Home Page
# =====================================

@app.route("/")
def home():
    return render_template("login.html")


# =====================================
# Register Page
# =====================================

@app.route("/register")
def register():
    return render_template("register.html")


# =====================================
# Register User
# =====================================

@app.route("/register_user", methods=["POST"])
def register_user():

    name = request.form["name"].strip()
    email = request.form["email"].strip()
    password = request.form["password"]

    # Email Validation
    email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if not re.match(email_pattern, email):
        return "Invalid Email Address"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users(name, email, password)
        VALUES (%s, %s, %s)
        """,
        (name, email, password)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/")


# =====================================
# Settings Page
# =====================================

@app.route("/settings")
def settings():
    return render_template("settings.html")

## =====================================
# Login User
# =====================================

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"].strip()
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:

        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["email"] = user["email"]

        return redirect("/dashboard")

    return "Invalid Email or Password"


# =====================================
# Dashboard
# =====================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "dashboard.html",
        name=session.get("name")
    )


# =====================================
# Upload Page
# =====================================

@app.route("/upload")
def upload():

    if "user_id" not in session:
        return redirect("/")

    return render_template("upload.html")


# =====================================
# Upload Dataset
# =====================================

@app.route("/upload_file", methods=["POST"])
def upload_file():

    if "file" not in request.files:
        return "No file selected."

    file = request.files["file"]

    if file.filename == "":
        return "Please select a file."

    filename = secure_filename(file.filename)
    

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    session["filepath"] = filepath
    session["uploaded_file"] = filepath

    dataset_name = filename

    file_size = round(
        os.path.getsize(filepath) / 1024,
        2
    )

    file_type = filename.split(".")[-1].upper()
    file_name = filename

    # =====================================
    # Read Dataset
    # =====================================
    if filename.endswith(".csv"):

        df = pd.read_csv(filepath)

    elif filename.endswith((".xlsx", ".xls")):

        df = pd.read_excel(filepath)

    else:
        return "Unsupported File Format"

    # =====================================
    # Dataset Information
    # =====================================
    df = df.dropna(how="all")
    rows = df.shape[0]
    cols = df.shape[1]

    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()

    clean_rows = rows - duplicates

    completion = (
        round(((rows - missing) / rows) * 100, 2)
        if rows > 0 else 0
    )

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    numeric_count = len(numeric_columns)

    categorical_count = len(
        df.select_dtypes(
            exclude="number"
        ).columns
    )

    selected_column = None
    min_value = None
    max_value = None

    # =====================================
    # Dataset Preview
    # =====================================

    table = df.head(10).to_html(
        classes="table table-bordered table-striped",
        index=False
    )

    # =====================================
    # AI Insights
    # =====================================
    numeric_columns = df.select_dtypes(include="number").columns
    recommendation = []

    highest = None
    lowest = None
    average = None

    mean = None
    median = None
    std = None
    variance = None

    if len(numeric_columns) > 0:

        selected_column = numeric_columns[0]

        highest = df[selected_column].max()
        lowest = df[selected_column].min()

        average = round(df[selected_column].mean(), 2)

        mean = round(df[selected_column].mean(), 2)
        median = round(df[selected_column].median(), 2)

        std = round(df[selected_column].std(), 2)
        variance = round(df[selected_column].var(), 2)

        min_value = df[selected_column].min()
        max_value = df[selected_column].max()

    # =====================================
    # AI Recommendations
    # =====================================

    if missing > 0:
        recommendation.append(
            f"The dataset contains {missing} missing values."
        )

    if duplicates > 0:
        recommendation.append(
            f"{duplicates} duplicate rows were detected."
        )

    if std is not None:

        if std > 15:

            recommendation.append(
                "The dataset shows high variation."
            )

        else:

            recommendation.append(
                "The dataset shows low variation."
            )
    if mean is not None:
        if mean < 0:

            recommendation.append(
                "Most numeric values are below zero."
            )

        else:

            recommendation.append(
                "Most numeric values are positive."
            )

    recommendation.append(
        "Dataset is suitable for visualization and business analysis."
    )

    if missing == 0 and duplicates == 0:

        recommendation.append(
            "Dataset is clean and ready for advanced analytics."
        )

    # =====================================
    # Clean Dataset
    # =====================================

    if len(numeric_columns) > 0:

        df = df[
            (df[selected_column] >= min_value) &
            (df[selected_column] <= max_value)
        ]

    # =====================================
    # AI Dataset Summary
    # =====================================

    ai_summary = f"""
This dataset contains {rows} rows and {cols} columns.

There are {numeric_count} numeric columns and
{categorical_count} categorical columns.

The dataset contains {missing} missing values
and {duplicates} duplicate rows.

The overall data quality is {completion}%.

This dataset is suitable for business analytics,
data visualization and machine learning.
"""

    # =====================================
    # Charts
    # =====================================

    histogram = None
    bar_chart = None
    pie_chart = None
    line_chart = None
    box_chart = None
    scatter_chart = None
    heatmap = None

    if len(numeric_columns) > 0:

        # Histogram
        fig1 = px.histogram(
            df,
            x=selected_column,
            title=f"Histogram of {selected_column}"
        )

        histogram = fig1.to_html(full_html=False)

        # Bar Chart
        fig2 = px.bar(
            df,
            x=df.columns[0],
            y=selected_column,
            title=f"{selected_column} by {df.columns[0]}"
        )

        bar_chart = fig2.to_html(full_html=False)

        # Pie Chart
        fig3 = px.pie(
            df,
            names=df.columns[0],
            values=selected_column,
            title=f"{selected_column} Distribution"
        )

        pie_chart = fig3.to_html(full_html=False)

        # Line Chart
        fig4 = px.line(
            df,
            x=df.columns[0],
            y=selected_column,
            title=f"{selected_column} Trend"
        )

        line_chart = fig4.to_html(full_html=False)

        # Box Plot
        fig5 = px.box(
            df,
            y=selected_column,
            title=f"Box Plot of {selected_column}"
        )

        box_chart = fig5.to_html(full_html=False)

        # Scatter Plot
        if len(numeric_columns) >= 2:

            fig_scatter = px.scatter(
                df,
                x=numeric_columns[0],
                y=numeric_columns[1],
                title=f"{numeric_columns[0]} vs {numeric_columns[1]}"
            )

            scatter_chart = fig_scatter.to_html(full_html=False)

            # Correlation Heatmap
            corr = df[numeric_columns].corr()

            fig6 = ff.create_annotated_heatmap(
                z=corr.values,
                x=list(corr.columns),
                y=list(corr.index),
                annotation_text=round(corr, 2).values,
                colorscale="Viridis",
                showscale=True
            )

            fig6.update_layout(
                title="Correlation Heatmap"
            )

            heatmap = fig6.to_html(full_html=False)

    # =====================================
    # Box Plot (Outlier Detection)
    # =====================================

    box_plot = None

    if len(numeric_columns) > 0:

        fig7 = px.box(
            df,
            y=numeric_columns[0],
            title=f"Outlier Detection - {numeric_columns[0]}"
        )

        box_plot = fig7.to_html(full_html=False)

    # =====================================
    # Store Values in Session
    # =====================================

    session["rows"] = int(rows)
    session["cols"] = int(cols)
    session["missing"] = int(missing)
    session["duplicates"] = int(duplicates)

    session["highest"] = float(highest) if highest is not None else None
    session["lowest"] = float(lowest) if lowest is not None else None
    session["average"] = float(average) if average is not None else None

    session["mean"] = float(mean) if mean is not None else None
    session["median"] = float(median) if median is not None else None
    session["std"] = float(std) if std is not None else None
    session["variance"] = float(variance) if variance is not None else None

    session["recommendation"] = recommendation

    dataset_name_value = locals().get("dataset_name")
    if dataset_name_value:
        session["dataset_name"] = dataset_name_value
    else:
        session["dataset_name"] = os.path.basename(session.get("uploaded_file", ""))
    session["file_type"] = file_type
    session["file_size"] = file_size

    session["numeric_count"] = numeric_count
    session["categorical_count"] = categorical_count

    session["filepath"] = filepath

    # =====================================
    # Save Clean Dataset
    # =====================================

    cleaned_file = os.path.join(
        app.config["UPLOAD_FOLDER"],
        "cleaned_dataset.csv"
    )

    df.to_csv(cleaned_file, index=False)

    # =====================================
    # Render Analytics Page
    # =====================================
    return render_template(

        "analytics.html",

        table=table,

        rows=rows,
        cols=cols,

        missing=missing,
        duplicates=duplicates,

        highest=highest,
        lowest=lowest,
        average=average,

        mean=mean,
        median=median,

        std=std,
        variance=variance,

        max_value=max_value,
        min_value=min_value,

        recommendation=recommendation,
    ai_summary=ai_summary,

    dataset_name=dataset_name,
    file_name=file_name,
    file_size=file_size,
    file_type=file_type,

    histogram=histogram,
    bar_chart=bar_chart,
    pie_chart=pie_chart,
    line_chart=line_chart,
    box_chart=box_chart,
    scatter_chart=scatter_chart,
    heatmap=heatmap,
    box_plot=box_plot,

    numeric_column=selected_column,

    clean_rows=clean_rows,
    completion=completion,

    numeric_count=numeric_count,
    categorical_count=categorical_count
)
    return render_template("analytics.html")

# =====================================
# Download PDF Report
# =====================================

@app.route("/download_report")
def download_report():

    pdf = "AI_Report.pdf"

    doc = SimpleDocTemplate(pdf)
    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph("<b>AI Powered Data Analytics Report</b>", styles["Title"])
    )
    story.append(Paragraph("<br/>", styles["Normal"]))

    story.append(
        Paragraph(f"Total Rows : {session.get('rows')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Total Columns : {session.get('cols')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Missing Values : {session.get('missing')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Duplicate Rows : {session.get('duplicates')}", styles["Normal"])
    )

    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(
        Paragraph("<b>Statistical Analysis</b>", styles["Heading2"])
    )

    story.append(
        Paragraph(f"Highest Value : {session.get('highest')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Lowest Value : {session.get('lowest')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Average : {session.get('average')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Mean : {session.get('mean')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Median : {session.get('median')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Standard Deviation : {session.get('std')}", styles["Normal"])
    )
    story.append(
        Paragraph(f"Variance : {session.get('variance')}", styles["Normal"])
    )

    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(
        Paragraph("<b>AI Recommendations</b>", styles["Heading2"])
    )

    for item in session.get("recommendation", []):
        story.append(
            Paragraph("• " + item, styles["Normal"])
        )

    doc.build(story)

    return send_file(pdf, as_attachment=True)


# =====================================
# Download CSV
# =====================================

@app.route("/download_csv")
def download_csv():

    filepath = session.get("uploaded_file")

    if not filepath:
        return "No dataset uploaded."

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    output = f"Analysis_{uuid.uuid4().hex[:6]}.csv"

    df.to_csv(output, index=False)

    return send_file(output, as_attachment=True)


# =====================================
# Download Excel
# =====================================

@app.route("/download_excel")
def download_excel():

    filepath = session.get("uploaded_file")

    if not filepath:
        return "No dataset uploaded."

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    output = f"Analysis_{uuid.uuid4().hex[:6]}.xlsx"

    df.to_excel(output, index=False)

    return send_file(output, as_attachment=True)


# =====================================
# Search Dataset
# =====================================

@app.route("/search")
def search():

    keyword = request.args.get("keyword", "").strip()

    filepath = session.get("filepath")

    if not filepath:
        return "Upload dataset first."

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    result = df[
        df.astype(str)
        .apply(lambda x: x.str.contains(keyword, case=False, na=False))
        .any(axis=1)
    ]

    table = result.to_html(
        classes="table table-bordered table-striped",
        index=False
    )

    return render_template(
        "search.html",
        table=table,
        keyword=keyword
    )


# =====================================
# Download Cleaned Dataset
# =====================================

@app.route("/download_cleaned")
def download_cleaned():

    cleaned_file = os.path.join(
        app.config["UPLOAD_FOLDER"],
        "cleaned_dataset.csv"
    )

    if not os.path.exists(cleaned_file):
        return "Cleaned dataset not found."

    return send_file(
        cleaned_file,
        as_attachment=True
    )


# =====================================
# Clean Dataset
# =====================================

@app.route("/clean_dataset")
def clean_dataset():

    filepath = session.get("filepath")

    if not filepath:
        return "No dataset uploaded."

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    # Remove Missing Values
    df = df.dropna()

    # Remove Duplicate Rows
    df = df.drop_duplicates()

    cleaned_file = os.path.join(
        app.config["UPLOAD_FOLDER"],
        "cleaned_dataset.csv"
    )

    df.to_csv(cleaned_file, index=False)

    return send_file(
        cleaned_file,
        as_attachment=True
    )


# =====================================
# Run Application
# =====================================

if __name__ == "__main__":
    app.run(debug=True)