"""Database models for the AD Security Camera Solution platform.

Every table uses foreign keys, timestamps, indexes and constraints where
appropriate.  All business content that the Admin should control lives in
the database (single source of truth).
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utcnow():
    return datetime.now(timezone.utc)


def slugify(text):
    import re

    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "item"


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


# ---------------------------------------------------------------------------
# Users / roles
# ---------------------------------------------------------------------------


class User(UserMixin, TimestampMixin, db.Model):
    """Customer account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), default="customer", nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    profile_image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    last_login_ip = db.Column(db.String(64))
    reset_token = db.Column(db.String(255), index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True))

    addresses = db.relationship(
        "Address", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    orders = db.relationship(
        "Order", backref="customer", lazy=True, cascade="all, delete-orphan"
    )
    service_requests = db.relationship(
        "ServiceRequest", backref="customer", lazy=True, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    cart_items = db.relationship(
        "CartItem", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class AdminUser(UserMixin, TimestampMixin, db.Model):
    """Admin / staff accounts."""

    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default="admin", nullable=False)  # superadmin/admin
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    reset_token = db.Column(db.String(255), index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == "superadmin"


class Address(TimestampMixin, db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    label = db.Column(db.String(50), default="Home")
    full_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(30))
    country = db.Column(db.String(100), default="Ethiopia")
    is_default = db.Column(db.Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class ProductCategory(TimestampMixin, db.Model):
    __tablename__ = "product_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    products = db.relationship("Product", backref="category", lazy=True)


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)

    products = db.relationship("Product", backref="brand", lazy=True)


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("product_categories.id"), nullable=False, index=True
    )
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), index=True)
    short_description = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    sale_price = db.Column(db.Numeric(12, 2))
    cost_price = db.Column(db.Numeric(12, 2))
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=5, nullable=False)
    specifications = db.Column(db.Text)  # JSON string of key/value pairs
    features = db.Column(db.Text)  # newline separated
    warranty = db.Column(db.String(255))
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_published = db.Column(db.Boolean, default=True, nullable=False, index=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)

    images = db.relationship(
        "ProductImage", backref="product", lazy=True, cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    order_items = db.relationship("OrderItem", backref="product", lazy=True)

    @property
    def display_price(self):
        if self.sale_price is not None and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def has_sale(self):
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def stock_status(self):
        if self.stock_quantity <= 0:
            return "out"
        if self.stock_quantity <= self.low_stock_threshold:
            return "low"
        return "in"

    @property
    def main_image(self):
        if self.images:
            return self.images[0].image_url
        return None


class ProductImage(TimestampMixin, db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False, index=True
    )
    image_url = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0, nullable=False)


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


class ServiceCategory(TimestampMixin, db.Model):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)

    services = db.relationship("Service", backref="category", lazy=True)


class Service(TimestampMixin, db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("service_categories.id"), index=True
    )
    short_description = db.Column(db.String(500))
    description = db.Column(db.Text)
    icon = db.Column(db.String(80), default="shield")
    image = db.Column(db.String(255))
    features = db.Column(db.Text)  # newline separated
    price_from = db.Column(db.Numeric(12, 2))
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    requests = db.relationship("ServiceRequest", backref="service", lazy=True)


# ---------------------------------------------------------------------------
# E-commerce
# ---------------------------------------------------------------------------


class CartItem(TimestampMixin, db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, default=1, nullable=False)

    product = db.relationship("Product", lazy=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

    @property
    def line_total(self):
        return self.product.display_price * self.quantity


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(
        db.String(30),
        default="pending",
        nullable=False,
        index=True,
    )
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(30))
    country = db.Column(db.String(100), default="Ethiopia")
    delivery_notes = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    discount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), default="cash_on_delivery")
    payment_status = db.Column(db.String(30), default="unpaid", nullable=False)
    internal_notes = db.Column(db.Text)
    placed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    items = db.relationship(
        "OrderItem", backref="order", lazy=True, cascade="all, delete-orphan"
    )
    status_history = db.relationship(
        "OrderStatusHistory", backref="order", lazy=True, cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items)

    @property
    def status_label(self):
        return ORDER_STATUS_LABELS.get(self.status, self.status.title())


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), index=True)
    product_name = db.Column(db.String(200), nullable=False)
    product_sku = db.Column(db.String(80))
    product_image = db.Column(db.String(255))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)


class OrderStatusHistory(TimestampMixin, db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(500))
    changed_by = db.Column(db.String(100))


# ---------------------------------------------------------------------------
# Service requests
# ---------------------------------------------------------------------------


class ServiceRequest(TimestampMixin, db.Model):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), index=True)
    service_name = db.Column(db.String(200), nullable=False)
    status = db.Column(
        db.String(30), default="submitted", nullable=False, index=True
    )
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(100))
    preferred_date = db.Column(db.Date)
    preferred_time = db.Column(db.String(50))
    device_count = db.Column(db.Integer)
    current_system = db.Column(db.Text)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    assigned_technician = db.Column(db.String(150))
    scheduled_at = db.Column(db.DateTime(timezone=True))
    submitted_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    files = db.relationship(
        "ServiceRequestFile", backref="request", lazy=True, cascade="all, delete-orphan"
    )
    status_history = db.relationship(
        "ServiceRequestStatusHistory", backref="request", lazy=True,
        cascade="all, delete-orphan", order_by="ServiceRequestStatusHistory.created_at",
    )

    @property
    def status_label(self):
        return SERVICE_REQUEST_STATUS_LABELS.get(self.status, self.status.title())


class ServiceRequestFile(TimestampMixin, db.Model):
    __tablename__ = "service_request_files"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer, db.ForeignKey("service_requests.id"), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    file_type = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    is_image = db.Column(db.Boolean, default=False, nullable=False)


class ServiceRequestStatusHistory(TimestampMixin, db.Model):
    __tablename__ = "service_request_status_history"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer, db.ForeignKey("service_requests.id"), nullable=False, index=True
    )
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(500))
    changed_by = db.Column(db.String(100))


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------


class ContactMessage(TimestampMixin, db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_replied = db.Column(db.Boolean, default=False, nullable=False)
    replied_at = db.Column(db.DateTime(timezone=True))


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    type = db.Column(db.String(50), default="general")
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# CMS content
# ---------------------------------------------------------------------------


class GalleryItem(TimestampMixin, db.Model):
    __tablename__ = "gallery"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(100), index=True)
    image_url = db.Column(db.String(255), nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class Testimonial(TimestampMixin, db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150))
    profile_image = db.Column(db.String(255))
    rating = db.Column(db.Integer, default=5, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class FAQ(TimestampMixin, db.Model):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class WebsiteSetting(db.Model):
    """Key/value store for branding, contact, social, SEO, appearance."""

    __tablename__ = "website_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    group = db.Column(db.String(50), default="general", index=True)
    is_image = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class HomepageSection(TimestampMixin, db.Model):
    """Configurable sections of the homepage (hero, trust, services, etc.)."""

    __tablename__ = "homepage_sections"

    id = db.Column(db.Integer, primary_key=True)
    section_key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255))
    subtitle = db.Column(db.Text)
    content = db.Column(db.Text)  # JSON blob for section-specific fields
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class Page(TimestampMixin, db.Model):
    """CMS pages (about, services, products, gallery, faq, contact, custom)."""

    __tablename__ = "pages"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(500))
    content = db.Column(db.Text)  # HTML content
    image = db.Column(db.String(255))
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class NavigationItem(TimestampMixin, db.Model):
    __tablename__ = "navigation_items"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    is_external = db.Column(db.Boolean, default=False, nullable=False)


class FooterSection(TimestampMixin, db.Model):
    __tablename__ = "footer_sections"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)

    links = db.relationship(
        "FooterLink", backref="section", lazy=True, cascade="all, delete-orphan",
        order_by="FooterLink.sort_order",
    )


class FooterLink(TimestampMixin, db.Model):
    __tablename__ = "footer_links"

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(
        db.Integer, db.ForeignKey("footer_sections.id"), nullable=False, index=True
    )
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class SocialLink(TimestampMixin, db.Model):
    __tablename__ = "social_links"

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(100))
    url = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50))
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class MediaItem(TimestampMixin, db.Model):
    __tablename__ = "media"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    file_type = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    url = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255))
    usage = db.Column(db.String(100))


class Announcement(TimestampMixin, db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    image = db.Column(db.String(255))
    cta_label = db.Column(db.String(100))
    cta_url = db.Column(db.String(255))
    start_date = db.Column(db.DateTime(timezone=True))
    end_date = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class AuditLog(TimestampMixin, db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), index=True)
    admin_name = db.Column(db.String(150))
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(64))

    admin = db.relationship("AdminUser", lazy=True)


class VersionHistory(TimestampMixin, db.Model):
    """History for important website changes (draft/publish)."""

    __tablename__ = "version_history"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    admin_name = db.Column(db.String(150))
    action = db.Column(db.String(50), nullable=False)  # draft/publish/update/restore
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    note = db.Column(db.String(500))


# ---------------------------------------------------------------------------
# Status lookup tables
# ---------------------------------------------------------------------------

ORDER_STATUSES = [
    "pending",
    "confirmed",
    "processing",
    "ready",
    "out_for_delivery",
    "completed",
    "cancelled",
]

ORDER_STATUS_LABELS = {
    "pending": "Pending",
    "confirmed": "Confirmed",
    "processing": "Processing",
    "ready": "Ready",
    "out_for_delivery": "Out for Delivery",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

SERVICE_REQUEST_STATUSES = [
    "submitted",
    "under_review",
    "contacted",
    "scheduled",
    "in_progress",
    "completed",
    "cancelled",
]

SERVICE_REQUEST_STATUS_LABELS = {
    "submitted": "Submitted",
    "under_review": "Under Review",
    "contacted": "Contacted",
    "scheduled": "Scheduled",
    "in_progress": "In Progress",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

PAYMENT_STATUSES = ["unpaid", "paid", "refunded"]

GALLERY_CATEGORIES = [
    "CCTV Installation",
    "Access Control",
    "Networking",
    "Time Attendance",
    "Video Intercom",
    "Security Projects",
]

# ---------------------------------------------------------------------------
# Login manager
# ---------------------------------------------------------------------------


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
