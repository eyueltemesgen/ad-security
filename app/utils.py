"""Shared helpers: settings access, file uploads, notifications, audit."""
import json
import os
import secrets
import uuid
from datetime import datetime, timezone

from flask import current_app
from werkzeug.utils import secure_filename

from .extensions import db
from .models import AuditLog, Notification, WebsiteSetting, utcnow

# ---------------------------------------------------------------------------
# Settings helper (single source of truth for all website content)
# ---------------------------------------------------------------------------


def get_setting(key, default=None):
    row = WebsiteSetting.query.filter_by(key=key).first()
    if row is None:
        return default
    return row.value if row.value is not None else default


def set_setting(key, value, group="general", is_image=False):
    row = WebsiteSetting.query.filter_by(key=key).first()
    if row is None:
        row = WebsiteSetting(key=key, value=str(value), group=group, is_image=is_image)
        db.session.add(row)
    else:
        row.value = value
        row.group = group
        row.is_image = is_image
    return row


def get_settings_map():
    """Return all settings as a dict, keyed for easy template access."""
    rows = WebsiteSetting.query.all()
    result = {}
    for r in rows:
        result[r.key] = r.value
    return result


# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------


def allowed_file(filename, allowed=()):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed


def safe_filename(original):
    ext = original.rsplit(".", 1)[1].lower() if "." in original else ""
    name = uuid.uuid4().hex
    return f"{name}.{ext}" if ext else f"{name}.bin"


def save_upload(file_storage, subfolder="", allowed=None):
    """Save an uploaded file, returning relative URL and metadata dict.

    Returns (url, filename, extension, size) or (None, None, None, None).
    """
    if file_storage is None or file_storage.filename == "":
        return None, None, None, None
    ext = file_storage.filename.rsplit(".", 1)[1].lower() if "." in file_storage.filename else ""
    if allowed is None:
        allowed = current_app.config["ALLOWED_IMAGE_TYPES"]
    if ext not in allowed:
        return None, None, None, None
    filename = safe_upload(file_storage.filename)
    subdir = current_app.config["UPLOAD_FOLDER"]
    if subfolder:
        subdir = os.path.join(subdir, subfolder)
        os.makedirs(subdir, exist_ok=True)
    size = 0
    file_storage.save(os.path.join(subdir, filename))
    size = os.path.getsize(os.path.join(subdir, filename))
    url = f"/static/img/uploads/{subfolder}/{filename}" if subfolder else f"/static/img/uploads/{filename}"
    url = url.replace("//", "/")
    return url, filename, ext, size


# ---------------------------------------------------------------------------
# Notifications / audit
# ---------------------------------------------------------------------------


def notify(user_id, title, message="", type_="general", link=""):
    n = Notification(user_id=user_id, title=title, message=message, type=type_, link=link)
    db.session.add(n)
    return n


def audit(admin, action, target_type="", target_id=None, description="", ip=""):
    entry = AuditLog(
        admin_id=admin.id if admin else None,
        admin_name=admin.full_name if admin else "system",
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=description,
        ip_address=ip,
    )
    db.session.add(entry)
    return entry


def now_iso():
    return datetime.now(timezone.utc)