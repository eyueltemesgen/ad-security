"""Public website routes."""
import json
import re

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import or_

from .extensions import db
from .models import (
    Brand,
    FAQ,
    GalleryItem,
    HomepageSection,
    Page,
    Product,
    ProductCategory,
    Service,
    ServiceCategory,
    Testimonial,
)
from .utils import allowed_file, save_upload

main_bp = Blueprint("main", __name__)


def _home_section(key):
    return HomepageSection.query.filter_by(section_key=key).first()


def _section_json(key):
    s = _home_section(key)
    if not s or not s.content:
        return {}
    try:
        return json.loads(s.content)
    except (ValueError, TypeError):
        return {}


@main_bp.context_processor
def main_ctx():
    return {}


@main_bp.route("/")
def home():
    hero = _section_json("hero")
    trust = _section_json("trust")
    installation = _section_json("installation")
    why = _section_json("why_choose_us")
    process = _section_json("how_it_works")
    final_cta = _section_json("final_cta")

    services = Service.query.filter_by(is_published=True).order_by(Service.sort_order).all()
    products = Product.query.filter_by(is_published=True, is_featured=True).limit(8).all()
    testimonials = Testimonial.query.filter_by(is_published=True).order_by(Testimonial.sort_order).all()
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.sort_order).limit(6).all()
    gallery = (GalleryItem.query.filter_by(is_published=True)
               .order_by(GalleryItem.sort_order).limit(6).all())

    return render_template(
        "home.html",
        hero=hero,
        trust=trust,
        installation=installation,
        why=why,
        process=process,
        final_cta=final_cta,
        services=services,
        featured_products=products,
        testimonials=testimonials,
        faqs=faqs,
        gallery=gallery,
        services_visible=_home_section("services").is_visible if _home_section("services") else True,
        featured_visible=_home_section("featured_products").is_visible if _home_section("featured_products") else True,
        testimonials_visible=_home_section("testimonials").is_visible if _home_section("testimonials") else True,
        gallery_visible=_home_section("gallery").is_visible if _home_section("gallery") else True,
        faq_visible=_home_section("faq").is_visible if _home_section("faq") else True,
        catalog_visible=_home_section("featured_products").is_visible if _home_section("featured_products") else True,
    )


@main_bp.route("/products")
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    brand = request.args.get("brand", "").strip()
    availability = request.args.get("availability", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort = request.args.get("sort", "newest")

    query = Product.query.filter_by(is_published=True)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Product.name.ilike(like),
            Product.sku.ilike(like),
            Product.short_description.ilike(like),
        ))
    if category:
        cat = ProductCategory.query.filter_by(slug=category).first()
        if cat:
            query = query.filter(Product.category_id == cat.id)
    if brand:
        br = Brand.query.filter_by(slug=brand).first()
        if br:
            query = query.filter(Product.brand_id == br.id)
    if availability == "in":
        query = query.filter(Product.stock_quantity > 0)
    if availability == "out":
        query = query.filter(Product.stock_quantity <= 0)
    if min_price:
        try:
            query = query.filter(Product.price >= float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            query = query.filter(Product.price <= float(max_price))
        except ValueError:
            pass

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name":
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    page = request.args.get("page", 1, type=int)
    per_page = 12
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    categories = ProductCategory.query.filter_by(is_published=True).order_by(ProductCategory.sort_order).all()
    brands = Brand.query.order_by(Brand.name).all()

    return render_template(
        "products.html",
        products=products,
        pagination=pagination,
        categories=categories,
        brands=brands,
        q=q, category=category, brand=brand, availability=availability,
        min_price=min_price, max_price=max_price, sort=sort,
    )


@main_bp.route("/products/<slug>")
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, is_published=True).first_or_404()
    product.view_count = (product.view_count or 0) + 1
    db.session.commit()
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_published == True,  # noqa: E712
    ).limit(4).all()
    return render_template("product_detail.html", product=product, related=related)


@main_bp.route("/services")
def services():
    cats = ServiceCategory.query.order_by(ServiceCategory.sort_order).all()
    return render_template("services.html", cats=cats)


@main_bp.route("/services/<slug>")
def service_detail(slug):
    service = Service.query.filter_by(slug=slug, is_published=True).first_or_404()
    related = Service.query.filter(Service.id != service.id).limit(4).all()
    return render_template("service_detail.html", service=service, related=related)


@main_bp.route("/about")
def about():
    page = Page.query.filter_by(slug="about", is_published=True).first()
    return render_template("about.html", page=page)


@main_bp.route("/gallery")
def gallery():
    items = GalleryItem.query.filter_by(is_published=True).order_by(GalleryItem.sort_order).all()
    categories = db.session.query(GalleryItem.category).distinct().all()
    return render_template("gallery.html", items=items, categories=[c[0] for c in categories])


@main_bp.route("/faq")
def faq():
    faqs = FAQ.query.filter_by(is_published=True).order_by(FAQ.sort_order).all()
    return render_template("faq.html", faqs=faqs)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        errors = []
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not subject:
            errors.append("Subject is required.")
        if not message:
            errors.append("Message is required.")
        if len(message) > 5000:
            errors.append("Message is too long.")
        if not errors:
            from .models import ContactMessage
            msg = ContactMessage(name=name, email=email, phone=phone, subject=subject, message=message)
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for("main.contact", sent=1))
        return render_template("contact.html", errors=errors, **request.form), 400
    return render_template("contact.html", sent=request.args.get("sent"))