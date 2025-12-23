from flask import Flask, request, redirect, render_template
import mysql.connector
from datetime import date, timedelta

app = Flask(__name__)

# ---- DATABASE CONNECTION ----
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="task_manager"
)
cursor = db.cursor()

@app.route("/")
def home():
    return render_template("home.html", title="Home")

@app.route("/tasks")
def view_tasks():
    cursor.execute("""
        SELECT task_id, title, created_at
        FROM tasks
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """)
    raw_tasks = cursor.fetchall()

    tasks = []
    today = date.today()

    for task in raw_tasks:
        task_id, title, created_at = task
        age_days = (today - created_at.date()).days

        if age_days <= 2:
            age_class = "fresh"
        elif age_days <= 5:
            age_class = "aging"
        else:
            age_class = "stale"

        tasks.append({
            "id": task_id,
            "title": title,
            "age_days": age_days,
            "age_class": age_class
        })

    return render_template(
        "tasks.html",
        title="Pending Tasks",
        tasks=tasks
    )

@app.route("/completed")
def view_completed():
    cursor.execute("""
        SELECT task_id, title, completed_at
        FROM tasks
        WHERE status = 'completed'
        ORDER BY completed_at DESC
    """)
    tasks = cursor.fetchall()

    return render_template(
        "completed.html",
        title="Completed Tasks",
        tasks=tasks
    )
@app.route("/archived")
def view_archived():
    cursor.execute("""
        SELECT task_id, title, created_at
        FROM tasks
        WHERE status = 'archived'
        ORDER BY created_at DESC
    """)
    tasks = cursor.fetchall()

    return render_template(
        "archived.html",
        title="Archived Tasks",
        tasks=tasks
    )

@app.route("/insights")
def insights():
    cursor.execute("""
        SELECT DISTINCT DATE(completed_at)
        FROM tasks
        WHERE completed_at IS NOT NULL
        ORDER BY DATE(completed_at)
    """)
    rows = cursor.fetchall()

    completed_dates = [row[0] for row in rows]

    # ---- CURRENT STREAK ----
    today = date.today()
    current_streak = 0

    day_pointer = today
    while day_pointer in completed_dates:
        current_streak += 1
        day_pointer -= timedelta(days=1)

    # ---- LONGEST STREAK ----
    longest_streak = 0
    streak = 0
    prev_day = None

    for d in completed_dates:
        if prev_day and d == prev_day + timedelta(days=1):
            streak += 1
        else:
            streak = 1
        longest_streak = max(longest_streak, streak)
        prev_day = d

    # ---- HEATMAP DATA (last 28 days) ----
    days = []
    for i in range(27, -1, -1):
        day = today - timedelta(days=i)
        days.append({
            "date": day,
            "active": day in completed_dates
        })

    return render_template(
        "insights.html",
        title="Insights",
        days=days,
        current_streak=current_streak,
        longest_streak=longest_streak
    )


@app.route("/add", methods=["GET", "POST"])
def add_task():
    error = None

    if request.method == "POST":
        title = request.form["title"]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'")
        pending_count = cursor.fetchone()[0]

        if pending_count >= 5:
            error = (
                "You already have 5 pending tasks. "
                "Complete an existing task before adding a new one."
            )
        else:
            cursor.execute(
                "INSERT INTO tasks (user_id, title, status) VALUES (1, %s, %s)",
                (title, "pending")
            )
            db.commit()
            return redirect("/tasks")

    return render_template(
        "add.html",
        title="Add Task",
        error=error
    )


@app.route("/complete/<int:task_id>")
def complete_task(task_id):
    cursor.execute(
    "UPDATE tasks SET status='completed', completed_at=NOW() WHERE task_id=%s",
    (task_id,)
    )
    db.commit()
    return redirect("/tasks")

@app.route("/archive/<int:task_id>")
def archive_task(task_id):
    cursor.execute(
        "UPDATE tasks SET status='archived' WHERE task_id=%s",
        (task_id,)
    )
    db.commit()
    return redirect("/tasks")


app.run()
