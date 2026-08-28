"""Admin dashboard: the central control system for the business."""
import json
import os
from datetime import datetime, timedelta

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, request,
    session, url_for,
)
from flask_login import current_user, login_user, login_required, logout_user
from sqlalchemy import func

from .extensions import db
from .models import (
    AdminUser,
    Announcement,
    AuditLog,
    Brand,
    CartItem,
    ContactMessage,
    FAQ,
    FooterLink,
    FooterSection,
    GalleryItem,
    HomepageSection,
    MediaItem,
    NavigationItem,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Page,
    Product,
    ProductCategory,
    ProductImage,
    Service,
    ServiceCategory,
    ServiceRequest,
    ServiceRequestFile,
    ServiceRequestStatusHistory,
    SocialLink,
    Testimonial,
    User,
    VersionHistory,
    WebsiteSetting,
    ORDER_STATUSES,
    utcnow,
)
from .utils import (
    allowed_file,
    audit,
    get_setting,
    notify,
    save_upload,
    set_setting,
)

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder="templates/admin",
    static_folder="static/admin",
)

ADMIN_ROLES = ("superadmin", "admin")


def admin_required(fn):
    """Protect admin routes. Enforces authorization server-side."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        admin = _current_admin()
        if admin is None:
            if request.path.startswith("/admin/login"):
                return fn(*args, **kwargs)
            return redirect(url_for("admin.login", next=request.path))
        if admin.role not in ADMIN_ROLES or not admin.is_active:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def _current_admin():
    admin_id = session.get("admin_id")
    if admin_id:
        return db.session.get(AdminUser, admin_id)
    return None


def _safe_next(target):
    """Allow only internal relative redirects to avoid open-redirect."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if _current_admin():
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = AdminUser.query.filter_by(email=email).first()
        if admin and admin.check_password(password) and admin.is_active:
            session["admin_id"] = admin.id
            admin.last_login_at = utcnow()
            audit(admin, "Admin login", "auth", admin.id, "Admin logged in", request.remote_addr)
            db.session.commit()
            return redirect(_safe_next(request.form.get("next")) or url_for("admin.dashboard"))
        flash("Invalid admin credentials.", "error")
    return render_template("admin/login.html", next=_safe_next(request.args.get("next")) or "")


@admin_bp.route("/logout")
@login_required
def logout():
    session.pop("admin_id", None)
    flash("Logged out of admin.", "success")
    return redirect(url_for("main.home"))


@admin_bp.route("/")
@admin_required
def dashboard():
    now = utcnow()
    today = now.date()
    start_week = today - timedelta(days=7)

    total_customers = User.query.filter_by(role="customer").count()
    new_customers = User.query.filter(
        User.role == "customer", func.date(User.created_at) >= today - timedelta(days=7)
    ).count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status="pending").count()
    completed_orders = Order.query.filter_by(status="completed").count()
    total_requests = ServiceRequest.query.count()
    pending_requests = ServiceRequest.query.filter_by(status="submitted").count()
    total_products = Product.query.count()
    low_stock = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).filter(Product.stock_quantity > 0).count()
    messages = ContactMessage.query.filter_by(is_read=False).count()
    revenue = db.session.query(func.sum(Order.total)).filter(
        Order.status != "cancelled"
    ).scalar() or 0

    # Orders over time (last 7 days)
    order_days = []
    sales_days = []
    for i in range(7, -1, -1):
        day = today - timedelta(days=i)
        nxt = day + timedelta(days=1)
        count = Order.query.filter(Order.placed_at >= day, Order.placed_at < nxt).count()
        day_rev = db.session.query(func.sum(Order.total)).filter(
            Order.placed_at >= day, Order.placed_at < nxt, Order.status != "cancelled"
        ).scalar() or 0
        order_days.append({"date": day.strftime("%b %d"), "count": count})
        sales_days.append({"date": day.strftime("%b %d"), "total": float(day_rev)})

    # Recent activity
    recent_orders = Order.query.order_by(Order.placed_at.desc()).limit(5).all()
    recent_requests = ServiceRequest.query.order_by(ServiceRequest.submitted_at.desc()).limit(5).all()
    recent_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        stats={
            "customers": total_customers, "new_customers": new_customers,
            "orders": total_orders, "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "requests": total_requests, "pending_requests": pending_requests,
            "products": total_products, "low_stock": low_stock,
            "messages": messages, "revenue": float(revenue),
        },
        order_days=order_days, sales_days=sales_days,
        recent_orders=recent_orders, recent_requests=recent_requests,
        recent_logs=recent_logs,
    )


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


@admin_bp.route("/customers")
@admin_required
def customers():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = User.query.filter_by(role="customer")
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(User.email.ilike(like), User.full_name.ilike(like), User.phone.ilike(like))
        )
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/customers.html", pagination=pagination, customers=pagination.items, q=q)


@admin_bp.route("/customers/<int:user_id>")
@admin_required
def customer_detail(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.placed_at.desc()).all()
    requests = ServiceRequest.query.filter_by(user_id=user.id).order_by(ServiceRequest.submitted_at.desc()).all()
    return render_template("admin/customer_detail.html", user=user, orders=orders, requests=requests)


@admin_bp.route("/customers/<int:user_id>/toggle", methods=["POST"])
@admin_required
def customer_toggle(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.is_active = not user.is_active
        audit(_current_admin(), "customer_toggle", "User", user.id,
              f"Set active={user.is_active}", request.remote_addr)
        db.session.commit()
        flash("Customer status updated.", "success")
    return redirect(url_for("admin.customer_detail", user_id=user_id))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@admin_bp.route("/orders")
@admin_required
def orders():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Order.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Order.order_number.ilike(like), Order.full_name.ilike(like), Order.phone.ilike(like)))
    if status:
        query = query.filter(Order.status == status)
    pagination = query.order_by(Order.placed_at.desc()).paginate(page=page, per_page=20, error_out=False)
    from .models import ORDER_STATUSES
    return render_template("admin/orders.html", pagination=pagination, orders=pagination.items, q=q, status=status, statuses=ORDER_STATUSES)


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    from .models import ORDER_STATUSES, PAYMENT_STATUSES
    return render_template("admin/order_detail.html", order=order, statuses=ORDER_STATUSES, payments=PAYMENT_STATUSES)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    new_status = request.form.get("status")
    note = request.form.get("note", "").strip()
    from .models import ORDER_STATUSES
    if new_status not in ORDER_STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    old = order.status
    order.status = new_status
    db.session.add(OrderStatusHistory(
        order_id=order.id, from_status=old, to_status=new_status, note=note,
        changed_by=_current_admin().full_name,
    ))
    # notify customer
    notify(order.user_id, f"Order {order.order_number} {new_status}",
           f"Your order status is now: {new_status.replace('_', ' ').title()}.", "order",
           url_for("customer.order_detail", order_id=order.id))
    audit(_current_admin(), "order_status", "Order", order.id,
          f"Changed status from {old} to {new_status}", request.remote_addr)
    db.session.commit()
    flash("Order status updated.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@admin_bp.route("/orders/<int:order_id>/notes", methods=["POST"])
@admin_required
def order_notes(order_id):
    order = db.session.get(Order, order_id)
    if order:
        order.internal_notes = request.form.get("internal_notes", "").strip()
        db.session.commit()
        flash("Notes saved.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


@admin_bp.route("/service-requests")
@admin_required
def service_requests():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    query = ServiceRequest.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(ServiceRequest.request_number.ilike(like),
                                    ServiceRequest.full_name.ilike(like),
                                    ServiceRequest.location.ilike(like)))
    if status:
        query = query.filter(ServiceRequest.status == status)
    pagination = query.order_by(ServiceRequest.submitted_at.desc()).paginate(page=page, per_page=20, error_out=False)
    from .models import SERVICE_REQUEST_STATUSES
    return render_template("admin/service_requests.html", pagination=pagination, requests=pagination.items, q=q, status=status, statuses=SERVICE_REQUEST_STATUSES)


@admin_bp.route("/service-requests/<int:request_id>")
@admin_required
def service_request_detail(request_id):
    req = db.session.get(ServiceRequest, request_id)
    if not req:
        abort(404)
    from .models import SERVICE_REQUEST_STATUSES
    return render_template("admin/service_request_detail.html", req=req, statuses=SERVICE_REQUEST_STATUSES)


@admin_bp.route("/service-requests/<int:request_id>/status", methods=["POST"])
@admin_required
def service_request_status(request_id):
    req = db.session.get(ServiceRequest, request_id)
    if not req:
        abort(404)
    new_status = request.form.get("status", "")
    note = request.form.get("note", "").strip()
    from .models import SERVICE_REQUEST_STATUSES
    if new_status not in SERVICE_REQUEST_STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.service_request_detail", request_id=req.id))
    old = req.status
    req.status = new_status
    req.assigned_technician = request.form.get("assigned_technician", "").strip() or req.assigned_technician
    if request.form.get("scheduled_date"):
        try:
            req.scheduled_at = datetime.strptime(request.form.get("scheduled_date"), "%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    db.session.add(ServiceRequestStatusHistory(
        request_id=req.id, from_status=old, to_status=new_status, note=note,
        changed_by=_current_admin().full_name,
    ))
    notify(req.user_id, f"Service request {req.request_number} {new_status}",
           f"Your service request status is now {new_status.replace('_', ' ').title()}.", "service",
           url_for("customer.request_detail", request_id=req.id))
    audit(_current_admin(), "service_request_status", "ServiceRequest", req.id,
          f"Changed status from {old} to {new_status}", request.remote_addr)
    db.session.commit()
    flash("Service request updated.", "success")
    return redirect(url_for("admin.service_request_detail", request_id=req.id))


@admin_bp.route("/service-requests/<int:request_id>/notes", methods=["POST"])
@admin_required
def service_request_notes(request_id):
    req = db.session.get(ServiceRequest, request_id)
    if req:
        req.internal_notes = request.form.get("internal_notes", "").strip()
        db.session.commit()
        flash("Notes saved.", "success")
    return redirect(url_for("admin.service_request_detail", request_id=request_id))


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@admin_bp.route("/messages")
@admin_required
def messages():
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=msgs)


@admin_bp.route("/messages/<int:message_id>", methods=["GET", "POST"])
@admin_required
def message_detail(message_id):
    msg = db.session.get(ContactMessage, message_id)
    if not msg:
        abort(404)
    if request.method == "POST":
        if "mark_read" in request.form:
            msg.is_read = True
        elif "mark_unread" in request.form:
            msg.is_read = False
        elif "mark_replied" in request.form:
            msg.is_replied = True
            msg.replied_at = utcnow()
        db.session.commit()
        flash("Message updated.", "success")
        return redirect(url_for("admin.message_detail", message_id=msg.id))
    return render_template("admin/message_detail.html", msg=msg)


# ---------------------------------------------------------------------------
# Products & categories
# ---------------------------------------------------------------------------


def _handle_product_form(product=None):
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip() or None
    sku = request.form.get("sku", "").strip()
    category_id = request.form.get("category_id", type=int)
    brand_id = request.form.get("brand_id", type=int)
    price = request.form.get("price", type=float)
    sale_price = request.form.get("sale_price", type=float)
    stock = request.form.get("stock_quantity", type=int)
    featured = "is_featured" in request.form
    published = "is_published" in request.form
    errors = []
    if not name:
        errors.append("Name is required.")
    if not sku:
        errors.append("SKU is required.")
    if price is None or price < 0:
        errors.append("Valid price is required.")
    if category_id is None:
        errors.append("Category is required.")
    if not slug:
        slug = _slugify(name)

    if not product:
        product = Product()
        db.session.add(product)
    product.name = name
    product.slug = slug
    product.sku = sku
    product.category_id = category_id
    product.brand_id = brand_id or None
    product.price = price
    product.sale_price = sale_price if sale_price is not None and sale_price >= 0 else None
    product.stock_quantity = stock or 0
    product.is_featured = featured
    product.is_published = published
    product.short_description = request.form.get("short_description", "").strip()
    product.description = request.form.get("description", "").strip()
    product.warranty = request.form.get("warranty", "").strip()
    product.features = request.form.get("features", "").strip()
    product.specifications = request.form.get("specifications", "").strip()
    return product, errors


@admin_bp.route("/products")
@admin_required
def products():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Product.name.ilike(like), Product.sku.ilike(like)))
    pagination = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    cats = ProductCategory.query.order_by(ProductCategory.sort_order).all()
    brands_all = Brand.query.order_by(Brand.name).all()
    return render_template("admin/products.html", pagination=pagination, products=pagination.items, q=q, cats=cats, brands=brands_all)


@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def product_add():
    cats = ProductCategory.query.all()
    brands_all = Brand.query.all()
    if request.method == "POST":
        product, errors = _handle_product_form()
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/product_form.html", product=product, cats=cats, brands=brands_all), 400
        image = request.files.get("image")
        if image and image.filename:
            url, filename, ext, size = save_upload(image, subfolder="products")
            if url:
                db.session.add(ProductImage(product_id=product.id, image_url=url, sort_order=0))
            else:
                flash("Invalid product image.", "error")
        db.session.commit()
        audit(_current_admin(), "product_created", "Product", product.id, f"Created product {product.name}", request.remote_addr)
        flash("Product created.", "success")
        return redirect(url_for("admin.product_edit", product_id=product.id))
    return render_template("admin/product_form.html", product=None, cats=cats, brands=brands_all)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)
    cats = ProductCategory.query.all()
    brands_all = Brand.query.all()
    if request.method == "POST":
        product, errors = _handle_product_form(product)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/product_form.html", product=product, cats=cats, brands=brands_all), 400
        if request.form.get("delete_image"):
            pi = db.session.get(ProductImage, int(request.form["delete_image"]))
            if pi:
                db.session.delete(pi)
        else:
            image = request.files.get("image")
            if image and image.filename:
                url, filename, ext, size = save_upload(image, subfolder="products")
                if url:
                    db.session.add(ProductImage(product_id=product.id, image_url=url, sort_order=len(product.images)))
        audit(_current_admin(), "product_updated", "Product", product.id, f"Updated product {product.name}", request.remote_addr)
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.product_edit", product_id=product.id))
    return render_template("admin/product_form.html", product=product, cats=cats, brands=brands_all)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    product = db.session.get(Product, product_id)
    if product:
        name = product.name
        db.session.delete(product)
        audit(_current_admin(), "product_deleted", "Product", product_id, f"Deleted product {name}", request.remote_addr)
        db.session.commit()
        flash("Product deleted.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/categories")
@admin_required
def categories():
    cats = ProductCategory.query.order_by(ProductCategory.sort_order).all()
    return render_template("admin/categories.html", cats=cats)


@admin_bp.route("/categories/add", methods=["POST"])
@admin_required
def category_add():
    name = request.form.get("name", "").strip()
    if name:
        db.session.add(ProductCategory(name=name, slug=_slugify(name)))
        db.session.commit()
        flash("Category added.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@admin_required
def category_edit(cat_id):
    cat = db.session.get(ProductCategory, cat_id)
    if cat:
        name = request.form.get("name", "").strip()
        if name:
            cat.name = name
            cat.slug = _slugify(name)
            db.session.commit()
            flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def category_delete(cat_id):
    cat = db.session.get(ProductCategory, cat_id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
        flash("Category deleted.", "success")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------------------
# Services management
# ---------------------------------------------------------------------------


@admin_bp.route("/services")
@admin_required
def services_list():
    services = Service.query.order_by(Service.sort_order).all()
    scats = ServiceCategory.query.all()
    return render_template("admin/services.html", services=services, scats=scats)


@admin_bp.route("/services/add", methods=["GET", "POST"])
@admin_required
def service_add():
    scats = ServiceCategory.query.all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Service name is required.", "error")
            return render_template("admin/service_form.html", service=None, scats=scats), 400
        svc = Service(
            name=name, slug=_slugify(name),
            category_id=request.form.get("category_id", type=int) or None,
            short_description=request.form.get("short_description", "").strip(),
            description=request.form.get("description", "").strip(),
            icon=request.form.get("icon", "shield").strip(),
            features=request.form.get("features", "").strip(),
            is_featured="is_featured" in request.form,
            is_published="is_published" in request.form,
        )
        price_from = request.form.get("price_from", type=float)
        svc.price_from = price_from if price_from is not None and price_from >= 0 else None
        db.session.add(svc)
        db.session.flush()
        image = request.files.get("image")
        if image and image.filename:
            url, filename, ext, size = save_upload(image, subfolder="services")
            if url:
                svc.image = url
        audit(_current_admin(), "service_created", "Service", svc.id, f"Created service {svc.name}", request.remote_addr)
        db.session.commit()
        flash("Service created.", "success")
        return redirect(url_for("admin.services_list"))
    return render_template("admin/service_form.html", service=None, scats=scats)


@admin_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@admin_required
def service_edit(service_id):
    svc = db.session.get(Service, service_id)
    if not svc:
        abort(404)
    scats = ServiceCategory.query.all()
    if request.method == "POST":
        svc.name = request.form.get("name", "").strip()
        svc.slug = _slugify(svc.name)
        svc.category_id = request.form.get("category_id", type=int) or None
        svc.short_description = request.form.get("short_description", "").strip()
        svc.description = request.form.get("description", "").strip()
        svc.icon = request.form.get("icon", "shield").strip()
        svc.features = request.form.get("features", "").strip()
        svc.is_featured = "is_featured" in request.form
        svc.is_published = "is_published" in request.form
        price_from = request.form.get("price_from", type=float)
        svc.price_from = price_from if price_from is not None and price_from >= 0 else None
        image = request.files.get("image")
        if image and image.filename:
            url, filename, ext, size = save_upload(image, subfolder="services")
            if url:
                svc.image = url
        audit(_current_admin(), "service_updated", "Service", svc.id, f"Updated service {svc.name}", request.remote_addr)
        db.session.commit()
        flash("Service updated.", "success")
        return redirect(url_for("admin.service_edit", service_id=svc.id))
    return render_template("admin/service_form.html", service=svc, scats=scats)


@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@admin_required
def service_delete(service_id):
    svc = db.session.get(Service, service_id)
    if svc:
        db.session.delete(svc)
        audit(_current_admin(), "service_deleted", "Service", service_id, f"Deleted service {svc.name}", request.remote_addr)
        db.session.commit()
        flash("Service deleted.", "success")
    return redirect(url_for("admin.services_list"))


@admin_bp.route("/service-categories/add", methods=["POST"])
@admin_required
def service_category_add():
    name = request.form.get("name", "").strip()
    if name:
        db.session.add(ServiceCategory(name=name, slug=_slugify(name)))
        db.session.commit()
        flash("Service category added.", "success")
    return redirect(url_for("admin.services_list"))


# ---------------------------------------------------------------------------
# Gallery / Testimonials / FAQs
# ---------------------------------------------------------------------------


@admin_bp.route("/gallery")
@admin_required
def gallery():
    items = GalleryItem.query.order_by(GalleryItem.sort_order).all()
    return render_template("admin/gallery.html", items=items)


@admin_bp.route("/gallery/add", methods=["POST"])
@admin_required
def gallery_add():
    image = request.files.get("image")
    url, filename, ext, size = (None, None, None, None)
    if image and image.filename:
        url, filename, ext, size = save_upload(image, subfolder="gallery")
    if url:
        item = GalleryItem(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            category=request.form.get("category", "").strip(),
            image_url=url,
            is_published="is_published" in request.form,
            is_featured="is_featured" in request.form,
        )
        db.session.add(item)
        db.session.commit()
        flash("Gallery item added.", "success")
    else:
        flash("Please upload a valid image.", "error")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/gallery/<int:item_id>/delete", methods=["POST"])
@admin_required
def gallery_delete(item_id):
    item = db.session.get(GalleryItem, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Gallery item deleted.", "success")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/testimonials")
@admin_required
def testimonials():
    items = Testimonial.query.order_by(Testimonial.sort_order).all()
    return render_template("admin/testimonials.html", items=items)


@admin_bp.route("/testimonials/add", methods=["GET", "POST"])
@admin_required
def testimonial_add():
    if request.method == "POST":
        first_name = request.form.get("customer_name", "").strip()
        if not first_name:
            flash("Customer name is required.", "error")
            return redirect(url_for("admin.testimonials"))
        t = Testimonial(
            customer_name=first_name,
            company=request.form.get("company", "").strip(),
            content=request.form.get("content", "").strip() or "Great service.",
            rating=request.form.get("rating", 5, type=int),
            is_published="is_published" in request.form,
        )
        db.session.add(t)
        db.session.flush()
        img = request.files.get("profile_image")
        if img and img.filename:
            url, filename, ext, size = save_upload(img, subfolder="testimonials")
            if url:
                t.profile_image = url
        db.session.commit()
        flash("Testimonial added.", "success")
        return redirect(url_for("admin.testimonials"))
    return render_template("admin/testimonial_form.html")


@admin_bp.route("/testimonials/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def testimonial_edit(item_id):
    t = db.session.get(Testimonial, item_id)
    if not t:
        abort(404)
    if request.method == "POST":
        t.customer_name = request.form.get("customer_name", "").strip()
        t.company = request.form.get("company", "").strip()
        t.content = request.form.get("content", "").strip()
        t.rating = request.form.get("rating", 5, type=int)
        t.is_published = "is_published" in request.form
        img = request.files.get("profile_image")
        if img and img.filename:
            url, filename, ext, size = save_upload(img, subfolder="testimonials")
            if url:
                t.profile_image = url
        db.session.commit()
        flash("Testimonial updated.", "success")
        return redirect(url_for("admin.testimonials"))
    return render_template("admin/testimonial_form.html", t=t)


@admin_bp.route("/testimonials/<int:item_id>/delete", methods=["POST"])
@admin_required
def testimonial_delete(item_id):
    t = db.session.get(Testimonial, item_id)
    if t:
        db.session.delete(t)
        db.session.commit()
        flash("Testimonial deleted.", "success")
    return redirect(url_for("admin.testimonials"))


@admin_bp.route("/faqs")
@admin_required
def faqs():
    items = FAQ.query.order_by(FAQ.sort_order).all()
    return render_template("admin/faqs.html", items=items)


@admin_bp.route("/faqs/add", methods=["POST"])
@admin_required
def faq_add():
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    if question and answer:
        db.session.add(FAQ(question=question, answer=answer, sort_order=FAQ.query.count()))
        db.session.commit()
        flash("FAQ added.", "success")
    return redirect(url_for("admin.faqs"))


@admin_bp.route("/faqs/<int:item_id>/edit", methods=["POST"])
@admin_required
def faq_edit(item_id):
    f = db.session.get(FAQ, item_id)
    if f:
        f.question = request.form.get("question", "").strip()
        f.answer = request.form.get("answer", "").strip()
        f.category = request.form.get("category", "").strip()
        f.is_published = "is_published" in request.form
        db.session.commit()
        flash("FAQ updated.", "success")
    return redirect(url_for("admin.faqs"))


@admin_bp.route("/faqs/<int:item_id>/delete", methods=["POST"])
@admin_required
def faq_delete(item_id):
    f = db.session.get(FAQ, item_id)
    if f:
        db.session.delete(f)
        db.session.commit()
        flash("FAQ deleted.", "success")
    return redirect(url_for("admin.faqs"))


# ---------------------------------------------------------------------------
# Media library
# ---------------------------------------------------------------------------


@admin_bp.route("/media")
@admin_required
def media():
    items = MediaItem.query.order_by(MediaItem.created_at.desc()).all()
    return render_template("admin/media.html", items=items)


@admin_bp.route("/media/upload", methods=["POST"])
@admin_required
def media_upload():
    file = request.files.get("file")
    url, filename, ext, size = save_upload(file, subfolder="media")
    if url:
        db.session.add(MediaItem(
            filename=filename, original_name=file.filename, file_type=ext,
            file_size=size, url=url, alt_text=request.form.get("alt_text", "").strip(),
        ))
        db.session.commit()
        flash("Media uploaded.", "success")
        return redirect(url_for("admin.media"))
    flash("Invalid media file.", "error")
    return redirect(url_for("admin.media"))


@admin_bp.route("/media/<int:item_id>/delete", methods=["POST"])
@admin_required
def media_delete(item_id):
    item = db.session.get(MediaItem, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Media deleted.", "success")
    return redirect(url_for("admin.media"))


# ---------------------------------------------------------------------------
# CMS: pages, navigation, footer, homepage, branding, SEO, appearance
# ---------------------------------------------------------------------------


@admin_bp.route("/pages")
@admin_required
def pages():
    pages = Page.query.order_by(Page.sort_order).all()
    return render_template("admin/pages.html", pages=pages)


@admin_bp.route("/pages/new", methods=["POST"])
@admin_required
def page_add_post():
    title = request.form.get("title", "").strip()
    slug = (request.form.get("slug", "").strip() or _slugify(title))
    if not title:
        flash("Page title is required.", "error")
        return redirect(url_for("admin.pages"))
    page = Page(
        title=title, slug=slug,
        subtitle=request.form.get("subtitle", "").strip() or None,
        content=request.form.get("content", "").strip() or "",
        is_published="is_published" in request.form,
    )
    db.session.add(page)
    db.session.flush()
    image = request.files.get("image")
    if image and image.filename:
        url, filename, ext, size = save_upload(image, subfolder="pages")
        if url:
            page.image = url
    audit(_current_admin(), "page_created", "Page", page.id, f"Created page {page.title}", request.remote_addr)
    db.session.commit()
    flash("Page created.", "success")
    return redirect(url_for("admin.page_edit", page_id=page.id))


@admin_bp.route("/pages/<int:page_id>/edit", methods=["GET", "POST"])
@admin_required
def page_edit(page_id):
    page = db.session.get(Page, page_id)
    if not page:
        abort(404)
    if request.method == "POST":
        page.title = request.form.get("title", "").strip()
        page.subtitle = request.form.get("subtitle", "").strip()
        page.content = request.form.get("content", "").strip()
        page.seo_title = request.form.get("seo_title", "").strip()
        page.seo_description = request.form.get("seo_description", "").strip()
        page.is_published = "is_published" in request.form
        image = request.files.get("image")
        if image and image.filename:
            url, filename, ext, size = save_upload(image, subfolder="pages")
            if url:
                page.image = url
        _record_version_change("Page", page.id, "edit", "Content page updated", request.remote_addr)
        audit(_current_admin(), "page_updated", "Page", page.id, f"Updated page {page.title}", request.remote_addr)
        db.session.commit()
        flash("Page updated.", "success")
        return redirect(url_for("admin.page_edit", page_id=page.id))
    return render_template("admin/page_form.html", page=page)


@admin_bp.route("/homepage", methods=["GET", "POST"])
@admin_required
def homepage():
    sections = HomepageSection.query.order_by(HomepageSection.sort_order).all()
    if request.method == "POST":
        s = HomepageSection.query.filter_by(section_key=request.form.get("key") or "hero").first()
        if s:
            if "visible" in request.form:
                s.is_visible = True
            else:
                s.is_visible = False
            db.session.commit()
            flash("Section visibility updated.", "success")
        return redirect(url_for("admin.homepage"))
    return render_template("admin/homepage.html", sections=sections)


@admin_bp.route("/homepage/<key>/edit", methods=["GET", "POST"])
@admin_required
def homepage_edit(key):
    s = HomepageSection.query.filter_by(section_key=key).first_or_404()
    if request.method == "POST":
        data = {}
        for field in ["heading", "subtitle", "title", "description", "cta1_label",
                      "cta1_url", "cta2_label", "cta2_url", "cta_label", "cta_url", "image_title"]:
            if request.form.get(field) is not None:
                data[field] = request.form.get(field)
        if request.form.get("section_title") is not None:
            s.title = request.form.get("section_title")
        if request.form.get("section_subtitle") is not None:
            s.subtitle = request.form.get("section_subtitle")
        image = request.files.get("background_image")
        if image and image.filename:
            url, filename, ext, size = save_upload(image, subfolder="homepage")
            if url:
                data["background_image"] = url
        s.content = json.dumps(data)
        _record_version_change("HomepageSection", s.id, "draft", f"Edited section {key}")
        audit(_current_admin(), "homepage_updated", "HomepageSection", s.id, f"Updated homepage section {key}", request.remote_addr)
        db.session.commit()
        flash("Homepage section updated.", "success")
        return redirect(url_for("admin.homepage"))
    section_data = {}
    if s.content:
        try:
            section_data = json.loads(s.content)
        except (ValueError, TypeError):
            section_data = {}
    return render_template("admin/homepage_section_form.html", s=s, data=section_data)


@admin_bp.route("/navigation")
@admin_required
def navigation():
    items = NavigationItem.query.order_by(NavigationItem.sort_order).all()
    return render_template("admin/navigation.html", items=items)


@admin_bp.route("/navigation/add", methods=["POST"])
@admin_required
def navigation_add():
    label = request.form.get("label", "").strip()
    url = request.form.get("url", "").strip()
    if label and url:
        db.session.add(NavigationItem(label=label, url=url, sort_order=NavigationItem.query.count()))
        db.session.commit()
        flash("Navigation item added.", "success")
    return redirect(url_for("admin.navigation"))


@admin_bp.route("/navigation/<int:item_id>/edit", methods=["POST"])
@admin_required
def navigation_edit(item_id):
    item = db.session.get(NavigationItem, item_id)
    if item:
        item.label = request.form.get("label", "").strip()
        item.url = request.form.get("url", "").strip()
        item.sort_order = request.form.get("sort_order", 0, type=int)
        item.is_visible = "is_visible" in request.form
        db.session.commit()
        flash("Navigation item updated.", "success")
    return redirect(url_for("admin.navigation"))


@admin_bp.route("/navigation/<int:item_id>/delete", methods=["POST"])
@admin_required
def navigation_delete(item_id):
    item = db.session.get(NavigationItem, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Navigation item deleted.", "success")
    return redirect(url_for("admin.navigation"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        group = request.form.get("settings_group", "general")
        for key, value in request.form.items():
            if key in ("csrf_token", "settings_group"):
                continue
            set_setting(key, value, group=group)
        # logo uploads
        for field in ("logo", "logo_light", "favicon"):
            f = request.files.get(field)
            if f and f.filename:
                url, filename, ext, size = save_upload(f, subfolder="branding")
                if url:
                    set_setting(field, url, group="branding", is_image=True)
        audit(_current_admin(), "settings_updated", "Settings", None, "Updated website settings", request.remote_addr)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    settings_map = {s.key: s.value for s in WebsiteSetting.query.all()}
    return render_template("admin/settings.html", s=settings_map)


@admin_bp.route("/social", methods=["GET", "POST"])
@admin_required
def social():
    if request.method == "POST":
        # update existing links by sort order handled in edit; simple add/removal
        pass
    links = SocialLink.query.order_by(SocialLink.sort_order).all()
    return render_template("admin/social.html", links=links)


@admin_bp.route("/social/add", methods=["POST"])
@admin_required
def social_add():
    platform = request.form.get("platform", "").strip()
    url = request.form.get("url", "").strip()
    if platform and url:
        db.session.add(SocialLink(platform=platform, username=request.form.get("username", "").strip(),
                                  url=url, icon=request.form.get("icon", platform.lower()), sort_order=SocialLink.query.count()))
        db.session.commit()
        flash("Social link added.", "success")
    return redirect(url_for("admin.social"))


@admin_bp.route("/social/<int:item_id>/edit", methods=["POST"])
@admin_required
def social_edit(item_id):
    link = db.session.get(SocialLink, item_id)
    if link:
        link.platform = request.form.get("platform", "").strip() or link.platform
        link.username = request.form.get("username", "").strip()
        link.url = request.form.get("url", "").strip()
        link.is_visible = "is_visible" in request.form
        db.session.commit()
        flash("Social link updated.", "success")
    return redirect(url_for("admin.social"))


@admin_bp.route("/social/<int:item_id>/delete", methods=["POST"])
@admin_required
def social_delete(item_id):
    link = db.session.get(SocialLink, item_id)
    if link:
        db.session.delete(link)
        db.session.commit()
        flash("Social link deleted.", "success")
    return redirect(url_for("admin.social"))


@admin_bp.route("/seo", methods=["GET", "POST"])
@admin_required
def seo():
    if request.method == "POST":
        for key in ("seo_title", "seo_description"):
            if request.form.get(key) is not None:
                set_setting(key, request.form.get(key), group="seo")
        db.session.commit()
        flash("SEO settings saved.", "success")
        return redirect(url_for("admin.seo"))
    s = {x.key: x.value for x in WebsiteSetting.query.filter_by(group="seo").all()}
    return render_template("admin/seo.html", s=s)


@admin_bp.route("/appearance", methods=["GET", "POST"])
@admin_required
def appearance():
    if request.method == "POST":
        for key in ("primary_color", "secondary_color", "accent_color"):
            if request.form.get(key) is not None:
                set_setting(key, request.form.get(key), group="appearance")
        db.session.commit()
        flash("Appearance saved.", "success")
        return redirect(url_for("admin.appearance"))
    s = {x.key: x.value for x in WebsiteSetting.query.all() if x.group == "appearance"}
    return render_template("admin/appearance.html", s=s)


@admin_bp.route("/audit-logs")
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/analytics")
@admin_required
def analytics():
    now = utcnow()
    since = now - timedelta(days=30)
    orders_30d = Order.query.filter(Order.placed_at >= since).all()
    revenue_30d = sum(float(o.total) for o in orders_30d if o.status != "cancelled")
    avg_order_value = revenue_30d / len(orders_30d) if orders_30d else 0
    new_customers_30d = User.query.filter(
        User.role == "customer", User.created_at >= since
    ).count()

    # top products by quantity sold
    top = db.session.query(
        OrderItem.product_name, func.sum(OrderItem.quantity).label("qty"),
        func.sum(OrderItem.line_total).label("rev"),
    ).group_by(OrderItem.product_name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    top_products = [
        {"name": name, "quantity": int(qty or 0), "revenue": float(rev or 0)}
        for name, qty, rev in top
    ]

    orders_by_status = {}
    for st in ORDER_STATUSES:
        orders_by_status[st] = Order.query.filter_by(status=st).count()

    total_visits = sum(p.view_count for p in Product.query.all())
    conversion_rate = round((len(orders_30d) / total_visits * 100), 1) if total_visits else 0

    data = {
        "revenue_30d": revenue_30d,
        "orders_30d": len(orders_30d),
        "avg_order_value": avg_order_value,
        "conversion_rate": conversion_rate,
        "new_customers_30d": new_customers_30d,
        "top_products": top_products,
        "orders_by_status": orders_by_status,
    }
    return render_template("admin/analytics.html", data=data)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _slugify(name):
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"


def _record_version_change(entity_type, entity_id, action, note, ip=""):
    db.session.add(VersionHistory(entity_type=entity_type, entity_id=entity_id,
                                  admin_name=(_current_admin().full_name if _current_admin() else "system"),
                                  action=action, note=note))