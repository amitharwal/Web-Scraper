"""
Authentication Routes.
Defines the /login, /signup, and /logout endpoints.
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from auditor_pro import db, bcrypt
from auditor_pro.models import User


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Handles user registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('That email is already taken. Please log in.', 'danger')
            return redirect(url_for('auth.login'))

        # Create new user
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        # Log them in immediately
        login_user(new_user)
        flash('Account created successfully! Welcome.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember'))
            flash('Logged in successfully.', 'success')

            # Redirect to the page they were trying to access, or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handles user logout.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))