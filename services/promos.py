# services/promos.py
import datetime, random
from mongoengine import Q
from models.promo import PromoCode, PromoRedemption
from models.transaction import Transaction
from models.user import User
from models.admin import Admin

LUCKY_TABLE = [
    # (weight, type, value) type: 'credit', 'percent', 'flat'
    (5, 'percent', 100),   # 5% chance: FREE (up to service price)
    (20, 'percent', 30),   # 20%: 30% off
    (25, 'percent', 20),   # 25%: 20% off
    (20, 'flat', 10),      # 20%: 10 💎 off
    (20, 'credit', 5),     # 20%: +5 💎 credit
    (10, 'credit', 0),     # 10%: sorry, no win (still recorded)
]

def _notify_admins(bot, text):
    for adm in Admin.objects():
        try:
            bot.send_message(adm.telegram_id, text)
        except Exception:
            pass

def _now():
    return datetime.datetime.utcnow()

def _within_window(p: PromoCode):
    if not p.start_at and not p.end_at:
        return True
    if p.start_at and _now() < p.start_at:
        return False
    if p.end_at and _now() > p.end_at:
        return False
    return True

def _user_redemption_count(promo, user):
    return PromoRedemption.objects(promo=promo, user=user, status__in=['granted','reserved','consumed']).count()

def _reserve_global_use(promo: PromoCode):
    if promo.max_uses and promo.uses >= promo.max_uses:
        return False
    # optimistic increment
    promo.update(inc__uses=1)
    promo.reload()
    return True

def _unreserve_global_use(promo: PromoCode):
    # best-effort: don’t go negative
    if promo.uses > 0:
        promo.update(dec__uses=1)
        promo.reload()

def redeem_code(bot, user: User, raw_code: str):
    """Main entry to redeem a code from chat."""
    code = (raw_code or "").strip().upper()
    promo = PromoCode.objects(code=code, active=True).first()
    if not promo or not _within_window(promo):
        return False, "❌ Invalid or inactive promo code."

    if promo.per_user_limit and _user_redemption_count(promo, user) >= promo.per_user_limit:
        return False, "❌ You have already used this promo the maximum allowed times."

    # For FCFS we must reserve a global use
    reserved = False
    if promo.type == "CREDIT_FCFS" and promo.max_uses:
        reserved = _reserve_global_use(promo)
        if not reserved:
            return False, "⌛ This promo has been fully claimed."

    try:
        if promo.type == "CREDIT_FCFS":
            amount = max(0.0, promo.amount or 0.0)
            user.balance += amount
            user.save()
            Transaction(user=user, type="credit", amount=amount,
                        closing_balance=user.balance, note=f"promo:{promo.code}").save()
            PromoRedemption(promo=promo, user=user, amount_credit=amount, status='granted').save()
            _notify_admins(bot,
                           f"🎟️ Promo used: {promo.code}\n👤 {user.username or user.telegram_id}\n💳 +{amount:.2f} 💎 (FCFS)\n🧮 uses: {promo.uses}/{promo.max_uses or '∞'}")
            return True, f"✅ {amount:.2f} 💎 credited to your balance."

        elif promo.type in ("PERCENT_SERVICE", "FLAT_SERVICE"):
            pr = PromoRedemption(promo=promo, user=user, status='reserved')
            if promo.type == "PERCENT_SERVICE":
                pr.percent = max(0.0, promo.percent or 0.0)
            else:
                pr.flat = max(0.0, promo.amount or 0.0)
            pr.save()
            return True, _reserved_msg(promo, pr)

        elif promo.type == "LUCKY":
            outcome = _lucky_roll()
            if outcome[0] == 'credit':
                amount = max(0.0, outcome[1])
                user.balance += amount
                user.save()
                Transaction(user=user, type="credit", amount=amount,
                            closing_balance=user.balance, note=f"promo:{promo.code}:lucky").save()
                PromoRedemption(promo=promo, user=user, amount_credit=amount, status='granted').save()
                return True, f"🍀 Lucky! {amount:.2f} 💎 added to your balance."
            elif outcome[0] == 'percent':
                pr = PromoRedemption(promo=promo, user=user, status='reserved', percent=float(outcome[1]))
                pr.save()
                return True, _reserved_msg(promo, pr, lucky=True)
            else:  # flat
                pr = PromoRedemption(promo=promo, user=user, status='reserved', flat=float(outcome[1]))
                pr.save()
                return True, _reserved_msg(promo, pr, lucky=True)

        else:
            return False, "❌ Unsupported promo type."
    except Exception as e:
        # roll back global use if we had reserved it
        if reserved:
            _unreserve_global_use(promo)
        return False, "⚠️ Something went wrong redeeming your promo."

def _reserved_msg(promo, pr: PromoRedemption, lucky=False):
    scope = "specific services" if promo.applicable_services else "any service"
    if pr.percent:
        base = f"🎟️ {'Lucky ' if lucky else ''}Promo applied: {pr.percent:.0f}% off"
    else:
        base = f"🎟️ {'Lucky ' if lucky else ''}Promo applied: {pr.flat:.2f} 💎 off"
    return f"{base} on your next purchase ({scope}). It will be auto-applied at checkout."

def _lucky_roll():
    total = sum(w for w, *_ in LUCKY_TABLE)
    r = random.randint(1, total)
    upto = 0
    for w, t, v in LUCKY_TABLE:
        upto += w
        if r <= upto:
            return (t, v)
    return ('credit', 0)

def find_applicable_reserved(user: User, service_id: str):
    """Return latest reserved redemption that matches service scope (or global)."""
    q = PromoRedemption.objects(user=user, status='reserved').order_by('-created_at')
    for pr in q:
        promo = pr.promo
        if not promo.active or not _within_window(promo):
            continue
        # service scope
        if promo.applicable_services and service_id not in (promo.applicable_services or []):
            continue
        return pr
    return None

def apply_discount_for_service(user: User, service, base_price: float):
    """
    Returns (final_price, redemption_or_None, discount_amount)
    If a reserved promo exists and matches service scope, apply it.
    """
    pr = find_applicable_reserved(user, getattr(service, 'service_id', None))
    if not pr:
        return base_price, None, 0.0

    discount = 0.0
    if pr.percent:
        discount = round(base_price * (pr.percent / 100.0), 2)
    elif pr.flat:
        discount = min(base_price, float(pr.flat))

    final_price = max(0.0, round(base_price - discount, 2))
    return final_price, pr, discount

def consume_reserved_promo(pr: PromoRedemption, service):
    """Mark reserved promo as consumed after successful purchase."""
    pr.update(status='consumed', service_id=getattr(service, 'service_id', None), consumed_at=_now())
