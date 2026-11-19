"""Örnek verileri yükler. Kullanım (backend klasöründe): python -m seed.seed_data

Tekrar çalıştırmak güvenlidir: zaten var olan kayıtlar atlanır, kopya oluşmaz.
"""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models import (
    PlanCode,
    Product,
    ProductCategory,
    Shop,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
    UserRole,
)

CUSTOMER_PHONE = "+905555555555"
SHOP_OWNER_PHONE = "+905444444444"
ADMIN_PHONE = "+905000000000"
OWNED_SHOP_NAME = "Meydan Kahve Kızılay"

USERS = [
    {
        "phone_number": CUSTOMER_PHONE,
        "full_name": "Test Kullanıcı",
        "email": "test@kahvecell.local",
        "role": UserRole.CUSTOMER,
        "preferences": {"coffee_types": ["Caffè Latte", "Türk Kahvesi"], "allergens": []},
    },
    {
        "phone_number": SHOP_OWNER_PHONE,
        "full_name": "Dükkân Sahibi",
        "email": "dukkan@kahvecell.local",
        "role": UserRole.SHOP_OWNER,
        "preferences": {},
    },
    {
        "phone_number": ADMIN_PHONE,
        "full_name": "Admin Kullanıcı",
        "email": "admin@kahvecell.local",
        "role": UserRole.ADMIN,
        "preferences": {},
    },
]

PLANS = [
    {
        "code": PlanCode.STARTER,
        "name": "Starter",
        "price_kurus": 8999,
        "monthly_credits": 10,
        "guest_passes": 0,
        "has_priority": False,
    },
    {
        "code": PlanCode.PREMIUM,
        "name": "Premium",
        "price_kurus": 14999,
        "monthly_credits": 20,
        "guest_passes": 2,
        "has_priority": False,
    },
    {
        "code": PlanCode.UNLIMITED,
        "name": "Unlimited",
        "price_kurus": 24999,
        "monthly_credits": None,
        "guest_passes": 5,
        "has_priority": True,
    },
]

ESPRESSO = ProductCategory.ESPRESSO_BASED
FILTER = ProductCategory.FILTER_COFFEE
COLD = ProductCategory.COLD_DRINK
OTHER = ProductCategory.OTHER

# Ürün adı -> (kategori, açıklama, orta segment Ankara fiyatı TL)
CATALOG = {
    "Espresso": (ESPRESSO, "Tek shot, yoğun gövdeli", 130),
    "Türk Kahvesi": (OTHER, "Közde pişirilir, lokumla servis edilir", 120),
    "Americano": (ESPRESSO, "Espresso ve sıcak su", 155),
    "Filtre Kahve": (FILTER, "Günün tek kökenli çekirdeğiyle demlenir", 150),
    "Cappuccino": (ESPRESSO, "Espresso, buharda ısıtılmış süt ve yoğun köpük", 175),
    "Caffè Latte": (ESPRESSO, "Espresso ve bol sütle yumuşak içim", 185),
    "Flat White": (ESPRESSO, "Çift shot ristretto ve ince süt köpüğü", 190),
    "Mocha": (ESPRESSO, "Espresso, sıcak çikolata ve süt", 200),
    "Iced Latte": (COLD, "Buz üzerine espresso ve soğuk süt", 200),
    "Cold Brew": (COLD, "18 saat soğuk demleme", 210),
    "Demleme Çay": (OTHER, "İnce belli bardakta Rize çayı", 45),
}

SHOPS = [
    {
        "name": "Meydan Kahve Kızılay",
        "description": "Kızılay Meydanı'na iki dakika; 7/24 açık, öğrenci dostu fiyatlar ve hızlı servis.",
        "address": "Sakarya Caddesi No:12, Kızılay",
        "latitude": 39.92060,
        "longitude": 32.85640,
        "phone": "+903125550101",
        # Açılış = kapanış: 7/24 açık.
        "opening_time": time(0, 0),
        "closing_time": time(0, 0),
        "rating": 4.5,
        "rating_count": 418,
        "price_factor": 0.95,
        "menu": ["Espresso", "Türk Kahvesi", "Americano", "Cappuccino", "Caffè Latte",
                 "Iced Latte", "Demleme Çay"],
    },
    {
        "name": "Tunalı Kahve Kavurma",
        "description": "Çekirdeklerini dükkânda kavuran, demleme odaklı üçüncü dalga kahveci.",
        "address": "Tunalı Hilmi Caddesi No:88, Kavaklıdere",
        "latitude": 39.90560,
        "longitude": 32.86010,
        "phone": "+903125550102",
        "opening_time": time(8, 0),
        "closing_time": time(23, 30),
        "rating": 4.7,
        "rating_count": 562,
        "price_factor": 1.10,
        "menu": ["Espresso", "Filtre Kahve", "Flat White", "Cappuccino", "Caffè Latte",
                 "Cold Brew", "Türk Kahvesi"],
    },
    {
        "name": "Yedinci Cadde Kahvecisi",
        "description": "Bahçelievler 7. Cadde'de geniş terasıyla mahalle kahvecisi.",
        "address": "7. Cadde No:45, Bahçelievler",
        "latitude": 39.92280,
        "longitude": 32.82390,
        "phone": "+903125550103",
        "opening_time": time(8, 30),
        "closing_time": time(23, 0),
        "rating": 4.4,
        "rating_count": 287,
        "price_factor": 1.00,
        "menu": ["Türk Kahvesi", "Espresso", "Americano", "Caffè Latte", "Mocha",
                 "Iced Latte", "Demleme Çay"],
    },
    {
        "name": "Arjantin Espresso Bar",
        "description": "Gaziosmanpaşa'da ayakta espresso kültürünü yaşatan küçük bar.",
        "address": "Arjantin Caddesi No:21, Gaziosmanpaşa",
        "latitude": 39.89870,
        "longitude": 32.86390,
        "phone": "+903125550104",
        "opening_time": time(9, 0),
        "closing_time": time(22, 0),
        "rating": 4.6,
        "rating_count": 198,
        "price_factor": 1.15,
        "menu": ["Espresso", "Americano", "Flat White", "Cappuccino", "Mocha", "Cold Brew"],
    },
    {
        "name": "Çayyolu Bahçe Kafe",
        "description": "Bahçeli, sakin, uzaktan çalışanlar için prizli masalar.",
        "address": "Prof. Dr. Ahmet Taner Kışlalı Caddesi No:5, Çayyolu",
        "latitude": 39.88510,
        "longitude": 32.69050,
        "phone": "+903125550105",
        "opening_time": time(8, 0),
        "closing_time": time(22, 0),
        "rating": 4.3,
        "rating_count": 154,
        "price_factor": 1.05,
        "menu": ["Türk Kahvesi", "Filtre Kahve", "Cappuccino", "Caffè Latte", "Iced Latte",
                 "Mocha", "Demleme Çay"],
    },
    {
        "name": "Konya Kahve Konağı",
        "description": "Alaaddin Tepesi ile Mevlâna Müzesi arasında, taş avlulu bir kahve konağı.",
        "address": "Mevlâna Caddesi No:24",
        "city": "Konya",
        "district": "Karatay",
        "latitude": 37.87160,
        "longitude": 32.49900,
        "phone": "+903325550201",
        "opening_time": time(7, 0),
        "closing_time": time(23, 0),
        "rating": 4.4,
        "rating_count": 213,
        "price_factor": 0.90,
        "menu": ["Türk Kahvesi", "Espresso", "Americano", "Cappuccino", "Caffè Latte",
                 "Iced Latte", "Demleme Çay"],
    },
    {
        "name": "Maas Koffiebar",
        "description": "Witte de Withstraat'ta, Hollanda'daki aboneler için ilk anlaşmalı kahveci.",
        "address": "Witte de Withstraat 42",
        "city": "Rotterdam",
        "district": "Centrum",
        "latitude": 51.91630,
        "longitude": 4.47760,
        "phone": "+31105550101",
        # Saatler Rotterdam yerel saatidir.
        "timezone": "Europe/Amsterdam",
        "opening_time": time(8, 0),
        "closing_time": time(18, 0),
        "rating": 4.5,
        "rating_count": 341,
        # Hollanda fiyatlarının yaklaşık TL karşılığı.
        "price_factor": 1.30,
        "menu": ["Espresso", "Americano", "Filtre Kahve", "Flat White", "Cappuccino",
                 "Caffè Latte", "Cold Brew"],
    },
]


def _price_kurus(base_tl: int, factor: float) -> int:
    # 5 TL'ye yuvarlanır: menülerde 167,50 TL gibi fiyatlar görünmesin.
    return round(base_tl * factor / 5) * 5 * 100


def seed_plans(db: Session) -> dict[PlanCode, SubscriptionPlan]:
    plans = {plan.code: plan for plan in db.scalars(select(SubscriptionPlan))}
    for data in PLANS:
        if data["code"] not in plans:
            plan = SubscriptionPlan(**data)
            db.add(plan)
            plans[plan.code] = plan
    return plans


def seed_shops(db: Session) -> int:
    existing_names = set(db.scalars(select(Shop.name)))
    added = 0
    for data in SHOPS:
        if data["name"] in existing_names:
            continue
        data = dict(data)
        menu = data.pop("menu")
        factor = data.pop("price_factor")
        shop = Shop(**{"city": "Ankara", "district": "Çankaya", **data})
        for product_name in menu:
            category, description, base_tl = CATALOG[product_name]
            shop.products.append(
                Product(
                    name=product_name,
                    category=category,
                    description=description,
                    price_kurus=_price_kurus(base_tl, factor),
                )
            )
        db.add(shop)
        added += 1
    return added


def seed_users(db: Session) -> dict[str, tuple[User, bool]]:
    result = {}
    for data in USERS:
        user = db.scalar(select(User).where(User.phone_number == data["phone_number"]))
        created = user is None
        if created:
            user = User(**data)
            db.add(user)
            db.flush()
        result[data["phone_number"]] = (user, created)
    return result


def assign_shop_owner(db: Session, owner: User) -> bool:
    shop = db.scalar(select(Shop).where(Shop.name == OWNED_SHOP_NAME))
    if shop is None or shop.owner_id is not None:
        return False
    shop.owner_id = owner.id
    return True


def seed_customer_subscription(db: Session, user: User, starter: SubscriptionPlan) -> bool:
    has_active = db.scalar(
        select(Subscription.id).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    if has_active is not None:
        return False
    now = datetime.now(timezone.utc)
    db.add(
        Subscription(
            user_id=user.id,
            plan_id=starter.id,
            remaining_credits=starter.monthly_credits,
            remaining_guest_passes=starter.guest_passes,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
    )
    return True


def main() -> None:
    init_db()
    with SessionLocal.begin() as db:
        plans = seed_plans(db)
        db.flush()
        shops_added = seed_shops(db)
        db.flush()
        users = seed_users(db)
        owner_assigned = assign_shop_owner(db, users[SHOP_OWNER_PHONE][0])
        subscription_created = seed_customer_subscription(
            db, users[CUSTOMER_PHONE][0], plans[PlanCode.STARTER]
        )

    with SessionLocal() as db:
        plan_count = len(db.scalars(select(SubscriptionPlan.id)).all())
        shop_count = len(db.scalars(select(Shop.id)).all())
        product_count = len(db.scalars(select(Product.id)).all())

    print("Örnek veri yükleme tamamlandı.")
    print(f"  Paketler : {plan_count}")
    print(f"  Dükkânlar: {shop_count} (bu çalıştırmada eklenen: {shops_added})")
    print(f"  Ürünler  : {product_count}")
    for phone, (user, created) in users.items():
        print(f"  {user.role.value:<10} {phone}: {'oluşturuldu' if created else 'zaten vardı'}")
    print(f"  Müşteri Starter aboneliği: {'tanımlandı' if subscription_created else 'zaten aktifti'}")
    print(f"  {OWNED_SHOP_NAME} sahibi: {'atandı' if owner_assigned else 'zaten atanmıştı'}")


if __name__ == "__main__":
    main()
