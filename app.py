import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import openai
import stripe
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, login_manager

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mysecretkey")  # for flash messages

# Set your OpenAI API key from an environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")

# Set your Stripe secret key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "your-stripe-secret-key")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User storage (for demonstration purposes, use a database in production)
users = {}

class User(UserMixin):
    def __init__(self, username):
        self.username = username

@login_manager.user_loader
def load_user(username):
    return User(username) if username in users else None

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users:
            flash("Username already exists.")
            return redirect(url_for("register"))
        users[username] = password  # Store password securely in production
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            session['paid'] = False  # Reset payment status on login
            return redirect(url_for("pay"))
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.before_request
def check_payment():
    if not current_user.is_authenticated or 'paid' not in session:
        session['paid'] = False

@app.route("/pay", methods=["GET", "POST"])
@login_required
def pay():
    if request.method == "POST":
        try:
            # Create a new Stripe Checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": "App Access",
                            },
                            "unit_amount": 1000,  # $10.00
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=url_for("success", _external=True),
                cancel_url=url_for("index", _external=True),
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            flash(f"Payment error: {e}")
            return redirect(url_for("pay"))

    return render_template("pay.html")

@app.route("/success")
@login_required
def success():
    session['paid'] = True
    flash("Payment successful! You now have access to the app.")
    return redirect(url_for("index"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not session.get('paid'):
        return redirect(url_for("pay"))

    if request.method == "POST":
        email_content = request.form.get("email_content")
        target_style = request.form.get("target_style")
        
        if not email_content or not target_style:
            flash("Please provide both email content and a target style.")
            return redirect(url_for("index"))
        
        try:
            result = transform_email_style(email_content, target_style)
            return render_template("index.html", result=result, email_content=email_content, target_style=target_style)
        except Exception as e:
            flash(f"An error occurred: {e}")
            return redirect(url_for("index"))
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)