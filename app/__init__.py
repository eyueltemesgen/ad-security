"""Application factory."""
import logging
import os

from flask import Flask, redirect, render_template, request, url_for

from .config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "warning"

    # Admin support: separate loader registry handled in admin blueprint via
    # a request-local context. Flask-Login's user_loader covers customer.

    from .auth import auth_bp
    from .customer import customer_bp
    from .main import main_bp
    from .admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Context processors
    @app.context_processor
    def inject_globals():
        from .utils import get_setting
        from .models import NavigationItem, SocialLink, FooterSection, Announcement, WebsiteSetting
        from datetime import datetime

        ann = Announcement.query.filter_by(is_active=True).first() \
            if db.session.is_active else None

        cart_count = 0
        from flask_login import current_user
        try:
            if current_user.is_authenticated and getattr(current_user, "role", "") == "customer":
                from sqlalchemy import func as _func
                from .models import CartItem
                cart_count = db.session.query(
                    _func.sum(CartItem.quantity)
                ).filter(CartItem.user_id == current_user.id).scalar() or 0
        except Exception:
            cart_count = 0

        return {
            "cart_count": cart_count,
            "site": {
                "name": get_setting("company_name", "AD Security Camera Solution"),
                "slogan": get_setting("company_slogan"),
                "email": get_setting("contact_email"),
                "phone": get_setting("contact_phone"),
                "address": get_setting("contact_address"),
                "hours": get_setting("working_hours"),
                "logo": get_setting("logo", "/static/img/logo.png"),
                "favicon": get_setting("favicon", "/static/img/favicon.png"),
                "description": get_setting("company_description"),
                "seo_title": get_setting("seo_title", "AD Security Camera Solution"),
                "seo_description": get_setting("seo_description"),
            },
            "nav_items": NavigationItem.query.filter_by(is_visible=True)
                          .order_by(NavigationItem.sort_order).all(),
            "footer_sections": FooterSection.query.filter_by(is_visible=True)
                               .order_by(FooterSection.sort_order).all(),
            "social_links": SocialLink.query.filter_by(is_visible=True)
                            .order_by(SocialLink.sort_order).all(),
            "active_announcement": ann,
            "primary_color": get_setting("primary_color", "#0b1f3a"),
            "secondary_color": get_setting("secondary_color", "#0e7a5a"),
            "accent_color": get_setting("accent_color", "#d9a521"),
            "current_year": datetime.now().year,
        }

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.cli.command("init-db")
    def init_db():
        """Create database tables."""
        from .models import (  # noqa - register all models
            User, AdminUser, Address, ProductCategory, Brand, Product,
            ProductImage, ServiceCategory, Service, CartItem, Order,
            OrderItem, OrderStatusHistory, ServiceRequest,
            ServiceRequestFile, ServiceRequestStatusHistory, ContactMessage,
            Notification, GalleryItem, Testimonial, FAQ, WebsiteSetting,
            HomepageSection, Page, NavigationItem, FooterSection, FooterLink,
            SocialLink, MediaItem, Announcement, AuditLog, VersionHistory,
        )
        db.create_all()
        print("Database created.")

    @app.cli.command("seed")
    def seed_cmd():
        from .seed import run
        run()

    return app