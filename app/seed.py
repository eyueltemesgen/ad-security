"""Seed data for demonstration.

All content seeded here is stored in the database and can be edited/deleted
by an Admin from the dashboard - it is not hardcoded in templates.
"""
import json
import re

from .extensions import db
from .models import (
    AdminUser,
    Announcement,
    Brand,
    FAQ,
    FooterLink,
    FooterSection,
    GalleryItem,
    HomepageSection,
    NavigationItem,
    Page,
    Product,
    ProductCategory,
    ProductImage,
    Service,
    ServiceCategory,
    SocialLink,
    Testimonial,
    User,
)
from .utils import set_setting


def _slug(name):
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"


def _img(name):
    return f"/static/img/demo/{name}"


def seed_admin_users():
    if AdminUser.query.filter_by(email="admin@adsecurity.example").first():
        return
    admin = AdminUser(
        email="admin@adsecurity.example", full_name="System Administrator", role="superadmin"
    )
    admin.set_password("Admin@12345")
    db.session.add(admin)
    print("   * admin: admin@adsecurity.example / Admin@12345")


def seed_demo_customer():
    if User.query.filter_by(email="customer@example.com").first():
        return
    u = User(email="customer@example.com", full_name="Demo Customer", phone="0911 000 000")
    u.set_password("Customer@123")
    db.session.add(u)
    print("   * customer: customer@example.com / Customer@123")


def seed_settings():
    settings = [
        ("company_name", "AD Security Camera Solution", "branding"),
        ("company_slogan", "Complete Security Solutions for Your Home & Business", "branding"),
        ("company_description", "Professional security and technology company providing CCTV, networking, access control, time attendance, video intercom, and IT/web solutions.", "branding"),
        ("site_title", "AD Security Camera Solution", "branding"),
        ("logo", "/static/img/logo.png", "branding", True),
        ("logo_light", "/static/img/logo.png", "branding", True),
        ("favicon", "/static/img/favicon.png", "branding", True),
        ("contact_email", "adsecuritycamerasolution@gmail.com", "contact"),
        ("contact_phone", "+251 900 000 000", "contact"),
        ("contact_address", "Addis Ababa, Ethiopia", "contact"),
        ("working_hours", "Mon - Sat: 8:30 AM - 6:00 PM", "contact"),
        ("seo_title", "AD Security Camera Solution | CCTV, Networking & Security Systems", "seo"),
        ("seo_description", "Professional security camera installation, CCTV systems, networking, access control, time attendance and IT solutions for home and business.", "seo"),
        ("footer_copyright", "© %s AD Security Camera Solution. All rights reserved.", "general"),
        ("primary_color", "#0b1f3a", "appearance"),
        ("secondary_color", "#0e7a5a", "appearance"),
        ("accent_color", "#d9a521", "appearance"),
    ]
    for item in settings:
        key, value, group = item[0], item[1], item[2]
        is_image = len(item) > 3 and item[3]
        set_setting(key, value, group=group, is_image=is_image)
    print("  * website settings")


def seed_navigation():
    if NavigationItem.query.first():
        return
    items = [
        ("Home", "/", 1),
        ("Products", "/products", 2),
        ("Services", "/services", 3),
        ("About", "/about", 4),
        ("Gallery", "/gallery", 5),
        ("FAQ", "/faq", 6),
        ("Contact", "/contact", 7),
    ]
    for label, url, order in items:
        db.session.add(NavigationItem(label=label, url=url, sort_order=order))
    print("  * navigation")


def seed_footer():
    if FooterSection.query.first():
        return
    quick = FooterSection(title="Quick Links", sort_order=1)
    prod = FooterSection(title="Products", sort_order=2)
    serv = FooterSection(title="Services", sort_order=3)
    db.session.add_all([quick, prod, serv])
    db.session.flush()
    db.session.add_all([
        FooterLink(section=quick, label="Home", url="/", sort_order=1),
        FooterLink(section=quick, label="Products", url="/products", sort_order=2),
        FooterLink(section=quick, label="Services", url="/services", sort_order=3),
        FooterLink(section=quick, label="About Us", url="/about", sort_order=4),
        FooterLink(section=quick, label="Gallery", url="/gallery", sort_order=5),
        FooterLink(section=quick, label="Contact", url="/contact", sort_order=6),
        FooterLink(section=prod, label="CCTV Cameras", url="/products?category=cctv-cameras", sort_order=1),
        FooterLink(section=prod, label="DVR / NVR", url="/products", sort_order=2),
        FooterLink(section=prod, label="Access Control", url="/products", sort_order=3),
        FooterLink(section=serv, label="CCTV Installation", url="/services", sort_order=1),
        FooterLink(section=serv, label="Network Solutions", url="/services", sort_order=2),
        FooterLink(section=serv, label="Time Attendance", url="/services", sort_order=3),
    ])
    print("  * footer")


def seed_social():
    if SocialLink.query.first():
        return
    db.session.add_all([
        SocialLink(platform="Instagram", username="@adsecuritycamera", url="https://instagram.com/adsecuritycamera", icon="instagram", sort_order=1),
        SocialLink(platform="Telegram", username="@adsecuritycamera", url="https://t.me/adsecuritycamera", icon="telegram", sort_order=2),
        SocialLink(platform="TikTok", username="@adsecuritycamera", url="https://tiktok.com/@adsecuritycamera", icon="tiktok", sort_order=3),
    ])
    print("  * social links")


def seed_catalog():
    if ProductCategory.query.first():
        return
    cat_names = [
        "CCTV Cameras", "IP Cameras", "Analog Cameras", "DVR", "NVR",
        "Hard Drives", "Network Equipment", "Access Control",
        "Time Attendance", "Video Intercom", "Cables & Accessories",
        "Power Supplies", "Security Accessories",
    ]
    for i, name in enumerate(cat_names):
        db.session.add(ProductCategory(name=name, slug=_slug(name), sort_order=i))
    for name in ["Hikvision", "Dahua", "Honeywell", "ZKTeco", "Generic"]:
        db.session.add(Brand(name=name, slug=_slug(name)))
    print("  * categories & brands")


def seed_products():
    if Product.query.first():
        return
    rows = [
        ("4MP IP Bullet Camera", "IP Cameras", "Hikvision", 149.00, 129.00, 25, True, "IP-BULBUL-4MP",
         "4MP IP bullet camera with smart motion detection and long-range IR night vision.",
         ["4MP resolution", "IP67 weatherproof", "Smart motion detection", "Built-in microSD slot", "H.265+ compression"], "2-year warranty", _img("cam1.jpg")),
        ("8MP IP Dome Camera", "IP Cameras", "Hikvision", 189.00, None, 18, True, "IP-DOME-8MP",
         "8MP ultra high-definition IP dome camera ideal for retail and office environments.",
         ["8MP ultra HD", "Smart detection", "PoE support", "Wide dynamic range"], "2-year warranty", _img("cam2.jpg")),
        ("1080p Analog Bullet Camera", "Analog Cameras", "Dahua", 79.00, 69.00, 40, True, "AN-BULB-1080",
         "Full HD 1080p analog bullet camera with long-range IR for reliable outdoor coverage.",
         ["1080p resolution", "30m IR range", "Weatherproof housing", "Easy DVR pairing"], "1-year warranty", _img("cctv1.jpg")),
        ("16-Channel DVR", "DVR", "Hikvision", 249.00, None, 12, True, "DVR-16CH-1080",
         "16-channel 1080p TurboHD DVR with HDMI output and mobile remote viewing.",
         ["16 channels", "1080p recording", "4TB HDD support", "Remote viewing app"], "2-year warranty", _img("dvr1.jpg")),
        ("32-Channel NVR", "NVR", "Hikvision", 389.00, 359.00, 8, True, "NVR-32CH-4K",
         "Network video recorder supporting 4K cameras with smart search and multi-display modes.",
         ["32 channels", "4K recording", "HDMI/VGA output", "PoE switch support"], "3-year warranty", _img("nvr1.jpg")),
        ("4TB Surveillance Hard Drive", "Hard Drives", "Hikvision", 119.00, None, 30, True, "HDD-4TB-SUR",
         "Purpose-built surveillance hard drive engineered for continuous recording.",
         ["4TB capacity", "Surveillance optimized", "Low power", "Reliable writes"], "3-year warranty", _img("hdd1.jpg")),
        ("16-Port PoE Switch", "Network Equipment", "Generic", 99.00, 89.00, 15, True, "NET-POE-16",
         "16-port PoE+ network switch for powering and connecting IP camera systems.",
         ["16 PoE+ ports", "250W budget", "Smart management", "Metal housing"], "2-year warranty", _img("net1.jpg")),
        ("IP Video Intercom Kit", "Video Intercom", "Honeywell", 159.00, None, 10, True, "INT-KIT-103",
         "Indoor monitor and outdoor doorbell kit with two-way audio, video and remote unlock.",
         ["7\" color monitor", "Night vision", "Remote unlock", "Video calling"], "1-year warranty", _img("intercom1.jpg")),
    ]
    for (name, cat_name, brand_name, price, sale, stock, featured, sku, short, feats, warranty, image) in rows:
        p = Product(
            name=name, slug=_slug(name), sku=sku,
            category_id=cat_obj(cat_name) or 1, brand_id=brand_obj(brand_name),
            short_description=short, description=short,
            price=price, sale_price=sale, stock_quantity=stock,
            is_featured=featured, is_published=True,
            features="\n".join(feats), warranty=warranty,
        )
        db.session.add(p)
        db.session.flush()
        db.session.add(ProductImage(product_id=p.id, image_url=image, sort_order=0))
        db.session.add(ProductImage(product_id=p.id, image_url=_img("cctv2.jpg"), sort_order=1))
    print("  * products")


def cat_obj(name):
    c = ProductCategory.query.filter_by(name=name).first()
    return c.id if c else None


def brand_obj(name):
    b = Brand.query.filter_by(name=name).first()
    return b.id if b else None


def seed_services():
    if ServiceCategory.query.first():
        return
    cats = ["Security & Maintenance", "Network & IT", "Access Control & Attendance", "Inspection & Consulting"]
    for name in cats:
        db.session.add(ServiceCategory(name=name, slug=_slug(name)))
    db.session.flush()
    services = [
        ("CCTV Installation", "Security & Maintenance", "shield",
         "Professional surveillance systems for homes, offices, shops and businesses. Site assessment, system design, installation, configuration, testing and user training.", "install1.jpg"),
        ("CCTV Maintenance", "Security & Maintenance", "clipboard",
         "Scheduled maintenance to keep your cameras recording and your footage secure.", "maintenance1.jpg"),
        ("CCTV Repair", "Security & Maintenance", "tools",
         "Fast, reliable repair for faulty cameras, recorders and connectivity issues.", "cctv3.jpg"),
        ("Network Solutions", "Network & IT", "network",
         "Complete networking infrastructure, structured cabling and reliable Wi-Fi for business and home.", "net2.jpg"),
        ("Web & IT Solutions", "Network & IT", "laptop",
         "Professional websites, IT services and technology solutions for modern businesses.", "web1.jpg"),
        ("Time Attendance", "Access Control & Attendance", "clock",
         "Digital and biometric attendance systems to manage your team efficiently.", "attendance.jpg"),
        ("Video Intercom", "Access Control & Attendance", "monitor",
         "Video communication and entrance monitoring systems for secure access.", "intercom1.jpg"),
        ("Access Control", "Access Control & Attendance", "lock",
         "Door access, biometric access and secure entry systems for any facility.", "access1.jpg"),
        ("System Inspection", "Inspection & Consulting", "search",
         "Detailed inspection of your current security setup with professional recommendations.", "inspect1.jpg"),
        ("Security Consultation", "Inspection & Consulting", "message",
         "Expert advice to design the right security strategy for your property.", "consult1.jpg"),
    ]
    for i, (name, cname, icon, short, img) in enumerate(services):
        sc = ServiceCategory.query.filter_by(name=cname).first()
        db.session.add(Service(
            name=name, slug=_slug(name), category_id=sc.id if sc else None,
            short_description=short, description=short, icon=icon,
            image=_img(img), is_featured=True, is_published=True, sort_order=i,
        ))
    print("  * services")


def seed_pages():
    if Page.query.first():
        return
    db.session.add_all([
        Page(slug="about", title="About Us",
             subtitle="Discover our story, mission and values.",
             content="<p>AD Security Camera Solution is a professional security and technology company providing CCTV, networking, access control, time attendance, video intercom, and web &amp; IT solutions to homes and businesses.</p>")
    ])
    print("  * pages")


def seed_homepage_sections():
    if HomepageSection.query.first():
        return
    hero = {
        "heading": "Complete Security Solutions for Your Home & Business",
        "subtitle": "AD Security Camera Solution provides security systems, professional installation and technology solutions to protect what matters most.",
        "cta1_label": "Explore Products", "cta1_url": "/products",
        "cta2_label": "Request a Service", "cta2_url": "/request-service",
        "background_image": _img("hero.jpg"),
    }
    trust = {
        "title": "Why trust us",
        "points": [
            {"icon": "shield", "title": "Professional Installation", "text": "Certified technicians install every system to the highest standard."},
            {"icon": "box", "title": "Quality Equipment", "text": "Trusted brands and genuine security equipment."},
            {"icon": "headset", "title": "Technical Support", "text": "Responsive support whenever you need us."},
            {"icon": "clock", "title": "Reliable Service", "text": "On-time installation, maintenance and repair."},
            {"icon": "users", "title": "Security Expertise", "text": "Years of experience protecting homes and businesses."},
        ],
    }
    installation = {
        "heading": "Professional CCTV Installation & Service",
        "description": "From site inspection and system design to installation, configuration, testing and ongoing support - we handle it all.",
        "points": ["Site Inspection", "System Design", "Installation", "Configuration", "Testing", "Maintenance", "Support"],
        "cta_label": "Book Installation", "cta_url": "/request-service", "image": _img("install1.jpg"),
    }
    why = {
        "title": "Why Choose Us",
        "benefits": [
            {"icon": "shield", "title": "Professional Installation", "text": "Factory-trained technicians for every project."},
            {"icon": "box", "title": "Quality Security Equipment", "text": "Genuine equipment from trusted brands."},
            {"icon": "headset", "title": "Experienced Technical Support", "text": "Knowledgeable support from our team."},
            {"icon": "tools", "title": "Reliable Maintenance", "text": "Planned maintenance keeps systems running."},
            {"icon": "settings", "title": "Customized Security Solutions", "text": "Solutions tailored to your property."},
            {"icon": "heart", "title": "Customer-focused Service", "text": "We put your safety and satisfaction first."},
        ],
    }
    process = {
        "title": "How It Works",
        "steps": [
            {"title": "Contact Us", "text": "Reach out by phone, email or the contact form."},
            {"title": "Discuss Your Needs", "text": "We discuss your security requirements."},
            {"title": "Site Assessment", "text": "We inspect your site for the best solution."},
            {"title": "Solution & Quote", "text": "Receive a tailored solution and clear quote."},
            {"title": "Installation", "text": "Professional installation by our team."},
            {"title": "Support & Maintenance", "text": "Ongoing support to keep you protected."},
        ],
    }
    final_cta = {
        "heading": "Protect What Matters Most",
        "description": "Request a professional security service today or browse our catalogue of quality products.",
        "cta1_label": "Request Service", "cta1_url": "/request-service",
        "cta2_label": "Shop Products", "cta2_url": "/products",
        "background_image": _img("hero.jpg"),
    }
    sections = [
        ("hero", "Hero", hero["heading"], hero["subtitle"], json.dumps(hero), True, 1),
        ("trust", "Trust Section", "Why Trust Us", None, json.dumps(trust), True, 2),
        ("services", "Services Section", "Our Services", "Professional security services for home and business.", None, True, 3),
        ("featured_products", "Featured Products", "Featured Products", "Handpicked security equipment.", None, True, 4),
        ("installation", "Installation Section", installation["heading"], installation["description"], json.dumps(installation), True, 5),
        ("why_choose_us", "Why Choose Us", why["title"], None, json.dumps(why), True, 6),
        ("how_it_works", "How It Works", process["title"], None, json.dumps(process), True, 7),
        ("testimonials", "Testimonials", "What Customers Say", "Real feedback from our clients.", None, True, 8),
        ("gallery", "Gallery Preview", "Recent Projects", "Some of our recent installation work.", None, True, 9),
        ("faq", "FAQ Preview", "Frequently Asked Questions", None, None, True, 10),
        ("final_cta", "Final Call to Action", final_cta["heading"], final_cta["description"], json.dumps(final_cta), True, 11),
    ]
    for key, title, st, sub, content, vis, order in sections:
        db.session.add(HomepageSection(section_key=key, title=title, subtitle=sub, content=content, is_visible=vis, sort_order=order))
    print("  * homepage sections")


def seed_testimonials():
    if Testimonial.query.first():
        return
    db.session.add_all([
        Testimonial(customer_name="Million Ayele", company="Grand Hotel", rating=5,
                    content="AD Security installed our complete CCTV system across the hotel. Professional installation and great support afterwards.",
                    profile_image=_img("profile1.jpg"), sort_order=1),
        Testimonial(customer_name="Selam Bekele", company="Retail Mart", rating=5,
                    content="Excellent networking and access control work. Our stores are now monitored securely and the system is easy to manage.",
                    profile_image=_img("profile2.jpg"), sort_order=2),
        Testimonial(customer_name="Dawit Girma", company="Homeowner", rating=4,
                    content="Fast installation and affordable pricing. The team was clean, polite and very professional. Highly recommend.",
                    profile_image=_img("profile3.jpg"), sort_order=3),
    ])
    print("  * testimonials")


def seed_faqs():
    if FAQ.query.first():
        return
    pairs = [
        ("What CCTV system should I choose?", "It depends on your property and needs. We carry out a site assessment and recommend the right cameras - IP for high resolution, analog for reliable cost-effective coverage."),
        ("Do you provide installation?", "Yes. We provide professional installation, configuration and testing for every system we sell."),
        ("Do you provide maintenance?", "Yes, we offer scheduled maintenance plans to keep cameras, recorders and networks running reliably."),
        ("Can you install systems for businesses?", "Absolutely. We specialise in business, retail, warehouse and multi-property installations."),
        ("Do you provide access control?", "Yes, including card readers, biometric and intercom access control systems."),
        ("Do you provide networking services?", "Yes. We design and install complete networking, cabling and Wi-Fi infrastructure."),
    ]
    for i, (q, a) in enumerate(pairs):
        db.session.add(FAQ(question=q, answer=a, sort_order=i))
    print("  * FAQs")


def seed_gallery():
    if GalleryItem.query.first():
        return
    items = [
        ("Hotel Reception CCTV", "gallery1.jpg", "CCTV Installation", 1),
        ("Warehouse Camera Setup", "gallery2.jpg", "CCTV Installation", 2),
        ("Office Access Control", "gallery3.jpg", "Access Control", 3),
        ("Office Attendance", "gallery4.jpg", "Time Attendance", 4),
        ("Networking Rack", "gallery5.jpg", "Networking", 5),
        ("Video Intercom Entry", "gallery6.jpg", "Video Intercom", 6),
    ]
    for title, img, cat, order in items:
        db.session.add(GalleryItem(title=title, image_url=_img(img), category=cat, is_published=True, sort_order=order))
    print("  * gallery")


def seed_announcements():
    if Announcement.query.first():
        return
    db.session.add(Announcement(
        title="Free Site Assessment",
        message="Book a consultation before the end of the month and enjoy a free site assessment on your first CCTV installation.",
        cta_label="Request Service", cta_url="/request-service", is_active=True,
    ))
    print("  * announcement")


def run():
    print("Seeding database...")
    seed_admin_users()
    seed_demo_customer()
    seed_settings()
    seed_navigation()
    seed_footer()
    seed_social()
    seed_catalog()
    seed_products()
    seed_services()
    seed_pages()
    seed_homepage_sections()
    seed_testimonials()
    seed_faqs()
    seed_gallery()
    seed_announcements()
    db.session.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    run()