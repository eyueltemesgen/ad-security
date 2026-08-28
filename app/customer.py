"""Customer portal: dashboard, cart, checkout, orders, service requests, profile."""
from datetime import datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from .extensions import db
from .models import (
    Address,
    CartItem,
    Notification,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    Service,
    ServiceRequest,
    ServiceRequestFile,
    ServiceRequestStatusHistory,
    User,
    utcnow,
)
from .utils import allowed_file, notify, save_upload

customer_bp = Blueprint("customer", __name__)


def _require_customer():
    if not current_user.is_authenticated or getattr(current_user, "role", "") != "customer":
        abort(403)
    if getattr(current_user, "role", "") == "admin":
        abort(403)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@customer_bp.route("/")
@login_required
def dashboard():
    if getattr(current_user, "role", "") == "admin":
        return redirect(url_for("admin.dashboard"))
    user = current_user
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.placed_at.desc()).all()
    requests = (ServiceRequest.query.filter_by(user_id=user.id)
                .order_by(ServiceRequest.submitted_at.desc()).all())
    notifications = Notification.query.filter_by(user_id=user.id).order_by(
        Notification.created_at.desc()).limit(8).all()
    stats = {
        "total_orders": len(orders),
        "active_orders": sum(1 for o in orders if o.status in ("pending", "confirmed", "processing")),
        "completed_orders": sum(1 for o in orders if o.status == "completed"),
        "total_requests": len(requests),
        "active_requests": sum(1 for r in requests if r.status in ("submitted", "under_review", "contacted", "scheduled", "in_progress")),
        "unread_notifications": Notification.query.filter_by(user_id=user.id, is_read=False).count(),
    }
    return render_template(
        "customer/dashboard.html", orders=orders, requests=requests,
        notifications=notifications, stats=stats,
    )


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


def _cart_items():
    return CartItem.query.filter_by(user_id=current_user.id).all()


def _cart_count():
    return sum(i.quantity for i in _cart_items())


@customer_bp.route("/cart")
@login_required
def cart():
    items = _cart_items()
    subtotal = sum(i.line_total for i in items)
    return render_template("customer/cart.html", items=items, subtotal=subtotal)


@customer_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    product_id = request.form.get("product_id", type=int)
    qty = request.form.get("quantity", 1, type=int)
    product = db.session.get(Product, product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("main.products"))
    if qty < 1:
        qty = 1
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if item:
        new_qty = item.quantity + qty
        item.quantity = min(new_qty, max(product.stock_quantity, 1))
    else:
        item = CartItem(user_id=current_user.id, product_id=product.id, quantity=min(qty, max(product.stock_quantity, 1)))
        db.session.add(item)
    db.session.commit()
    flash(f"Added {product.name} to cart.", "success")
    return redirect(request.referrer or url_for("main.products"))


@customer_bp.route("/cart/update", methods=["POST"])
@login_required
def update_cart():
    for key, value in request.form.items():
        if key.startswith("qty_"):
            try:
                item_id = int(key.split("_")[1])
                qty = int(value)
            except (ValueError, IndexError):
                continue
            item = db.session.get(CartItem, item_id)
            if item and item.user_id == current_user.id:
                if qty <= 0:
                    db.session.delete(item)
                else:
                    product = item.product
                    item.quantity = min(qty, max(product.stock_quantity, 1))
    db.session.commit()
    return redirect(url_for("customer.cart"))


@customer_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_cart_item(item_id):
    item = db.session.get(CartItem, item_id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("customer.cart"))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = _cart_items()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("customer.cart"))
    subtotal = sum(i.line_total for i in items)
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        postal = request.form.get("postal_code", "").strip()
        notes = request.form.get("delivery_notes", "").strip()
        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not phone:
            errors.append("Phone is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not address:
            errors.append("Address is required.")
        if not city:
            errors.append("City is required.")
        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("customer.checkout"))
        # Build order
        order = Order(
            order_number=_gen_order_number("ORD"),
            user_id=current_user.id,
            full_name=full_name, phone=phone, email=email,
            address_line=address, city=city, state=state, postal_code=postal,
            delivery_notes=notes,
            subtotal=subtotal, delivery_fee=0, discount=0, total=subtotal,
        )
        for item in items:
            p = item.product
            order.items.append(OrderItem(
                product_id=p.id, product_name=p.name, product_sku=p.sku,
                product_image=p.main_image, unit_price=p.display_price,
                quantity=item.quantity, line_total=p.display_price * item.quantity,
            ))
            # decrement stock
            p.stock_quantity = max(p.stock_quantity - item.quantity, 0)
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderStatusHistory(order_id=order.id, to_status="pending", note="Order placed by customer."))
        # save default address
        db.session.add(Address(
            user_id=current_user.id, full_name=full_name, phone=phone,
            address_line=address, city=city, state=state, postal_code=postal,
            label="Shipping",
        ))
        notify(current_user.id, f"Order {order.order_number} placed",
               f"Your order has been placed successfully.", "order", url_for("customer.order_detail", order_id=order.id))
        for item in items:
            db.session.delete(item)
        db.session.commit()
        return redirect(url_for("customer.order_confirmation", order_id=order.id))

    user = current_user
    default = Address.query.filter_by(user_id=user.id, is_default=True).first() or \
        Address.query.filter_by(user_id=user.id).first()
    return render_template("customer/checkout.html", items=items, subtotal=subtotal, default=default)


def _gen_order_number(prefix):
    import random
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    rand = random.randint(100, 999)
    return f"{prefix}-{timestamp}-{rand}"


@customer_bp.route("/order-confirmation/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    return render_template("customer/order_confirmation.html", order=order)


@customer_bp.route("/orders")
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.placed_at.desc()).all()
    return render_template("customer/orders.html", orders=orders)


@customer_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        abort(404)
    return render_template("customer/order_detail.html", order=order)


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


SERVICE_REQUEST_OPTIONS = [
    "CCTV Installation", "CCTV Maintenance", "CCTV Repair",
    "Network Installation", "Access Control Installation",
    "Time Attendance Installation", "Video Intercom Installation",
    "Web & IT Solutions", "Security Consultation", "System Inspection",
    "Security System Upgrade",
]


@customer_bp.route("/request-service", methods=["GET", "POST"])
def request_service():
    services = Service.query.filter_by(is_published=True).order_by(Service.sort_order).all()
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to request a service.", "warning")
            return redirect(url_for("auth.login"))
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        service_name = request.form.get("service_name", "").strip()
        location = request.form.get("location", "").strip()
        property_type = request.form.get("property_type", "").strip()
        pref_date = request.form.get("preferred_date", "").strip()
        pref_time = request.form.get("preferred_time", "").strip()
        device_count = request.form.get("device_count", type=int)
        current_system = request.form.get("current_system", "").strip()
        description = request.form.get("description", "").strip()
        notes = request.form.get("notes", "").strip()

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not phone:
            errors.append("Phone is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not service_name:
            errors.append("Service type is required.")
        if not location:
            errors.append("Location is required.")
        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("customer.request_service"))

        service = Service.query.filter_by(name=service_name).first()
        pref_date_obj = None
        if pref_date:
            try:
                pref_date_obj = datetime.strptime(pref_date, "%Y-%m-%d").date()
            except ValueError:
                pref_date_obj = None
        req = ServiceRequest(
            request_number=_gen_order_number("SRV"),
            user_id=current_user.id,
            service_id=service.id if service else None,
            service_name=service_name,
            full_name=full_name, phone=phone, email=email,
            location=location, property_type=property_type,
            preferred_date=pref_date_obj, preferred_time=pref_time,
            device_count=device_count, current_system=current_system,
            description=description, notes=notes,
        )
        db.session.add(req)
        db.session.flush()

        # file uploads
        import os
        from .utils import save_upload
        files = request.files.getlist("attachments")
        for f in files:
            if f and f.filename:
                allowed_types = db.get_app().config["SERVICE_FILE_TYPES"]
                url, filename, ext, size = save_upload(f, subfolder="service", allowed=allowed_types)
                if url:
                    is_image = ext in db.get_app().config["ALLOWED_IMAGE_TYPES"]
                    db.session.add(ServiceRequestFile(
                        request_id=req.id, filename=filename, original_name=f.filename,
                        file_type=ext, file_size=size, is_image=is_image,
                    ))

        db.session.add(ServiceRequestStatusHistory(request_id=req.id, to_status="submitted", note="Request submitted by customer."))
        notify(current_user.id, f"Service request {req.request_number} received",
               "We have received your service request and will contact you soon.")
        db.session.commit()
        flash("Your service request has been submitted.", "success")
        return redirect(url_for("customer.request_detail", request_id=req.id))
    return render_template("customer/request_service.html", services=services, options=SERVICE_REQUEST_OPTIONS)


@customer_bp.route("/service-requests")
@login_required
def service_requests():
    requests = (ServiceRequest.query.filter_by(user_id=current_user.id)
                .order_by(ServiceRequest.submitted_at.desc()).all())
    return render_template("customer/service_requests.html", requests=requests)


@customer_bp.route("/service-requests/<int:request_id>")
@login_required
def request_detail(request_id):
    req = db.session.get(ServiceRequest, request_id)
    if not req or req.user_id != current_user.id:
        abort(404)
    return render_template("customer/request_detail.html", req=req)


# ---------------------------------------------------------------------------
# Profile & notifications
# ---------------------------------------------------------------------------


@customer_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action", "profile")
        if action == "profile":
            name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip().lower()
            errors = []
            if not name:
                errors.append("Name is required.")
            if not email or "@" not in email:
                errors.append("A valid email is required.")
            elif User.query.filter(User.email == email, User.id != current_user.id).first():
                errors.append("That email is already in use.")
            if errors:
                for e in errors:
                    flash(e, "error")
            else:
                user = current_user
                user.full_name = name
                user.phone = phone
                user.email = email
                f = request.files.get("profile_image")
                if f and f.filename:
                    allowed = db.get_app().config["ALLOWED_IMAGE_TYPES"]
                    url, filename, ext, size = save_upload(f, subfolder="profiles", allowed=allowed)
                    if url:
                        user.profile_image = url
                    else:
                        flash("Invalid image file.", "error")
                db.session.commit()
                flash("Profile updated.", "success")
        elif action == "password":
            old = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not current_user.check_password(old):
                flash("Current password is incorrect.", "error")
            elif len(new) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new != confirm:
                flash("New passwords do not match.", "error")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("Password updated.", "success")
        return redirect(url_for("customer.profile"))
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template("customer/profile.html", addresses=addresses)


@customer_bp.route("/notifications")
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).all()
    return render_template("customer/notifications.html", notifications=notifs)


@customer_bp.route("/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("customer.notifications"))


@customer_bp.route("/addresses", methods=["POST"])
@login_required
def add_address():
    a = Address(
        user_id=current_user.id,
        full_name=request.form.get("full_name", "").strip() or current_user.full_name,
        phone=request.form.get("phone", "").strip(),
        address_line=request.form.get("address_line", "").strip(),
        city=request.form.get("city", "").strip(),
        state=request.form.get("state", "").strip(),
        postal_code=request.form.get("postal_code", "").strip(),
        label=request.form.get("label", "Home").strip() or "Home",
    )
    db.session.add(a)
    db.session.commit()
    flash("Address added.", "success")
    return redirect(url_for("customer.profile"))