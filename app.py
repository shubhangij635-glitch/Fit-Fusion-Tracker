from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness.db'

# Edamam API Keys
APP_ID = "e7ec9349"
APP_KEY = "eeb4d01941ce71ccdd837bef0d0593fc"

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# -------------------- USER MODEL --------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(120), default="default.png")

    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    gender = db.Column(db.String(10))

    steps = db.Column(db.Integer, default=0)
    calories = db.Column(db.Integer, default=0)
    workouts_completed = db.Column(db.Integer, default=0)
    distance = db.Column(db.Float, default=0.0)
    step_goal = db.Column(db.Integer, default=10000)
    distance_goal = db.Column(db.Float, default=5)
    workout_goal = db.Column(db.Integer, default=1)
    calories_goal = db.Column(db.Integer, default=2500)
    workouts = db.relationship('Workout', backref='user', lazy=True)
# -------------------- WORKOUT MODEL --------------------
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(150), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)

    date = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# -------------------- NUTRITION MODEL --------------------
class Nutrition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal = db.Column(db.String(100), nullable=False)
    food = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Integer, nullable=False)
    carbs = db.Column(db.Integer, nullable=False)
    fats = db.Column(db.Integer, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
# -------------------- LOGIN MANAGER --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- HOME --------------------
@app.route('/')
def home():
    return render_template("index.html")

# -------------------- DASHBOARD --------------------
@app.route('/dashboard')
@login_required
def dashboard():

    step_percent = int((current_user.steps / current_user.step_goal) * 100) if current_user.step_goal else 0

    calories_percent = int((current_user.calories / current_user.calories_goal) * 100) if current_user.calories_goal else 0

    workout_percent = int((current_user.workouts_completed / current_user.workout_goal) * 100) if current_user.workout_goal else 0

    distance_percent = int((current_user.distance / current_user.distance_goal) * 100) if current_user.distance_goal else 0

    return render_template(
        'dashboard.html',
        step_percent=step_percent,
        calorie_percent=calories_percent,
        workout_percent=workout_percent,
        distance_percent=distance_percent,
        user=current_user
    )

# -------------------- OVERVIEW --------------------
@app.route('/overview')
@login_required
def overview():
    return render_template("overview.html")

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")

    return render_template('login.html')

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Password match check
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        # Check if user exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# -------------------- LOGOUT --------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# -------------------- PROFILE --------------------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.age = request.form['age']
        current_user.weight = request.form['weight']
        current_user.height = request.form['height']
        current_user.gender = request.form.get("gender")
        current_user.calories_goal = request.form.get('calories_goal')
        current_user.step_goal = request.form['step_goal']
        current_user.distance_goal = request.form['distance_goal']
        current_user.workout_goal = request.form['workout_goal']
        
        db.session.commit()

        flash("Profile updated successfully!", "success")

    return render_template('profile.html', user=current_user)

# -------------------- SETTINGS PAGE --------------------
@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")

        current_user.username = username
        current_user.email = email

        file = request.files.get("profile_pic")

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            current_user.profile_pic = filename

        db.session.commit()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html")

# -------------------- ACTIVITY UPDATE --------------------
@app.route('/update_activity', methods=['POST'])
@login_required
def update_activity():

    current_user.steps += int(request.form['steps'])
    current_user.calories += int(request.form['calories'])
    current_user.distance += float(request.form['distance'])
    current_user.workouts_completed += int(request.form['workouts'])
    db.session.commit()

    flash("Activity updated!", "success")

    return redirect(url_for('dashboard'))
# -------------------- COMPLETE WORKOUT --------------------
@app.route('/complete_workout')
@login_required
def complete_workout():

    current_user.workouts_completed += 1
    current_user.calories += 150

    db.session.commit()

    flash("Workout completed 💪", "success")

    return redirect(url_for('dashboard'))

# -------------------- save WORKOUT --------------------

@app.route("/log_workout", methods=["POST"])
@login_required
def log_workout():

    exercise = request.form["exercise"]
    sets = int(request.form["sets"])
    reps = int(request.form["reps"])

    workout = Workout(
        exercise_name=exercise,
        sets=sets,
        reps=reps,
        user_id=current_user.id
    )

    db.session.add(workout)
    db.session.commit()

    flash("Workout logged successfully!", "success")

    return redirect(url_for("workouts"))

# -------------------- WORKOUT PAGE --------------------
@app.route('/workouts')
@login_required
def workouts():
    exercises = [
        {'name': 'Push-ups', 'reps': '15 reps', 'image': 'push_ups.gif'},
        {'name': 'Squats', 'reps': '20 reps', 'image': 'squat.gif'},
        {'name': 'Lunges', 'reps': '12 reps', 'image': 'lunges.gif'},
        {'name': 'Deadlifts', 'reps': '10 reps', 'image': 'deadlift.gif'}
    ]
    workouts = Workout.query.filter_by(
        user_id=current_user.id
    ).order_by(Workout.date.desc()).all()
    return render_template('workout.html', exercises=exercises,workouts=workouts)

# -------------------- NUTRITION PAGE --------------------
@app.route('/nutrition', methods=['GET', 'POST'])
@login_required
def nutrition():

    if request.method == 'POST':
        meal = request.form['meal']
        food = request.form['food']
        calories = int(request.form['calories'])
        protein = int(request.form['protein'])
        carbs = int(request.form['carbs'])
        fats = int(request.form['fats'])

        new_entry = Nutrition(
            meal=meal,
            food=food,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fats=fats,
            user_id=current_user.id
        )

        db.session.add(new_entry)
        db.session.commit()

        flash("Meal added successfully!", "success")
        return redirect(url_for('nutrition'))

    # GET REQUEST SECTION
    meals = Nutrition.query.filter_by(user_id=current_user.id).all()

    total_calories = sum(m.calories for m in meals)
    total_protein = sum(m.protein for m in meals)
    total_carbs = sum(m.carbs for m in meals)
    total_fats = sum(m.fats for m in meals)

    calorie_goal = current_user.calories_goal or 1
    progress_percentage = min((total_calories / calorie_goal) * 100, 100)

    return render_template(
        'nutrition.html',
        meals=meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        calorie_goal=calorie_goal,
        progress_percentage=progress_percentage
    )

# -------------------- DELETE MEAL --------------------
@app.route('/delete_meal/<int:meal_id>')
@login_required
def delete_meal(meal_id):
    meal = Nutrition.query.get_or_404(meal_id)

    if meal.user_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('nutrition'))

    db.session.delete(meal)
    db.session.commit()

    flash("Meal deleted!", "success")
    return redirect(url_for('nutrition'))


# -------------------- PROGRESS PAGE --------------------
@app.route('/progress')
@login_required
def progress():

    goal_type = session.get('goal_type')
    goal_target = session.get('goal_target')

    progress_percent = 0
    current_value = 0

    if goal_target:
        try:
            goal_target = float(goal_target)

            if goal_target > 0:

                if goal_type == "Calories Burn":
                    current_value = current_user.calories or 0

                elif goal_type == "Step Goal":
                    current_value = current_user.steps or 0

                elif goal_type == "Distance Goal":
                    current_value = current_user.distance or 0

                elif goal_type == "Workout Goal":
                    current_value = current_user.workouts_completed or 0

                progress_percent = min(int((current_value / goal_target) * 100), 100)

        except ValueError:
            progress_percent = 0
            current_value = 0

    # ✅ 👉 ADD THIS PART (Overall Fitness Score)
    step_p = (current_user.steps / current_user.step_goal) * 100 if current_user.step_goal else 0
    cal_p = (current_user.calories / current_user.calories_goal) * 100 if current_user.calories_goal else 0
    dist_p = (current_user.distance / current_user.distance_goal) * 100 if current_user.distance_goal else 0
    work_p = (current_user.workouts_completed / current_user.workout_goal) * 100 if current_user.workout_goal else 0

    overall_score = int((step_p + cal_p + dist_p + work_p) / 4)

    # ✅ 👉 MODIFY THIS (pass overall_score)
    return render_template(
        "progress.html",
        goal_type=goal_type,
        goal_target=goal_target,
        progress_percent=progress_percent,
        current_value=current_value,
        overall_score=overall_score   # 🔥 IMPORTANT
    )
# -------------------- SET GOAL --------------------
@app.route('/set_goal', methods=['POST'])
@login_required
def set_goal():
    goal_type = request.form.get('goal_type')
    goal_target = request.form.get('goal_target')

    if not goal_target:
        flash("Please enter a valid goal!", "danger")
        return redirect(url_for('progress'))

    session['goal_type'] = goal_type
    session['goal_target'] = goal_target

    flash("Goal set successfully!", "success")
    return redirect(url_for('progress'))

# -------------------- EDAMAM FOOD API --------------------
@app.route("/search_food")
@login_required
def search_food():

    query = request.args.get("q")

    url = "https://api.edamam.com/api/food-database/v2/parser"

    params = {
        "ingr": query,
        "app_id": APP_ID,
        "app_key": APP_KEY
    }

    response = requests.get(url, params=params)

    print("STATUS:", response.status_code)
    print("RESPONSE TEXT:", response.text)

    if response.status_code != 200:
        return jsonify({"error": "API request failed"}), 500

    try:
        data = response.json()
    except:
        return jsonify({"error": "Invalid API response"}), 500

    if not data["parsed"]:
        return jsonify({"error": "Food not found"}), 404

    food = data["parsed"][0]["food"]
    nutrients = food["nutrients"]

    result = {
        "food": food["label"],
        "calories": nutrients.get("ENERC_KCAL", 0),
        "protein": nutrients.get("PROCNT", 0),
        "carbs": nutrients.get("CHOCDF", 0),
        "fats": nutrients.get("FAT", 0)
    }

    return jsonify(result)

# -------------------- RUN APP --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
