"""Customer authentication: register, login, logout, password reset."""
import secrets
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user, login_required

from .extensions import db
from .models import User, utcnow
from .utils import notify

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        elif User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            user = User(email=email, full_name=name, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            notify(user.id, "Welcome to " + "AD Security Camera Solution",
                   "Your account has been created successfully.", type_="account")
            db.session.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("auth.login"))

        for e in errors:
            flash(e, "error")
        return render_template("auth/register.html", name=name, email=email, phone=phone), 400

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("customer.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = "remember" in request.form
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Contact support.", "error")
            else:
                login_user(user, remember=remember)
                user.last_login_at = utcnow()
                db.session.commit()
                return redirect(url_for("customer.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = utcnow() + timedelta(hours=2)
            db.session.commit()
            flash("A password reset link has been generated.", "success")
            return redirect(url_for("auth.forgot_password", link=url_for("auth.reset_password", token=token)))
        flash("No account found for that email.", "error")
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not utcnow() < _expiry(user):
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            flash("Password updated. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", token=token)


def _expiry(user):
    expiry = user.reset_token_expires
    return expiry or utcnow()