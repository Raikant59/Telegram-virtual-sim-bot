from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.user import User
from models.order import Order
from models.transaction import Transaction
from models.otp import OtpMessage


users_bp = Blueprint('users', __name__, template_folder='../templates')

@users_bp.route('/', methods=['GET'])
def users_list():
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip().lower()

    query = User.objects
    if search:
        query = query.filter(__raw__={
            "$or": [
                {"username": {"$regex": search, "$options": "i"}},
                {"telegram_id": {"$regex": search}}
            ]
        })
    if status == 'blocked':
        query = query.filter(blocked=True)
    elif status == 'active':
        query = query.filter(blocked__ne=True)

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page

    users = query.order_by('-created_at').skip((page-1)*per_page).limit(per_page)

    for i, u in enumerate(users):
        u.index = (page-1)*per_page + i + 1

    return render_template(
        'users_list.html',
        users=users,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status
    )


@users_bp.route('/<user_id>', methods=['GET', 'POST'])
def user_profile(user_id):
    user = User.objects(id=user_id).first()
    if not user:
        abort(404)

    # derived stats
    total_numbers = Order.objects(user=user).count()
    used_numbers = Order.objects(user=user, status='completed').count()
    user_refers_count = getattr(user, 'refers', 0)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_balance':
            try:
                amount = float(request.form.get('amount') or 0)
            except ValueError:
                flash('Invalid amount', 'danger')
                return redirect(url_for('users.user_profile', user_id=user_id))
            user.balance = (user.balance or 0) + amount
            user.save()
            Transaction(user=user, type='credit', amount=amount,
                        closing_balance=user.balance, note='by admin').save()
            flash('Balance added', 'success')
            return redirect(url_for('users.user_profile', user_id=user_id))

        if action == 'cut_balance':
            try:
                amount = float(request.form.get('amount') or 0)
            except ValueError:
                flash('Invalid amount', 'danger')
                return redirect(url_for('users.user_profile', user_id=user_id))
            if (user.balance or 0) < amount:
                flash('User does not have enough balance', 'danger')
            else:
                user.balance = user.balance - amount
                user.save()
                Transaction(user=user, type='debit', amount=amount,
                        closing_balance=user.balance, note='by admin').save()
                flash('Balance cut', 'success')
                return redirect(url_for('users.user_profile', user_id=user_id))

        if action == 'block_toggle':
            # Requires `blocked` boolean on User model (see migration note)
            user.blocked = not getattr(user, 'blocked', False)
            user.save()
            flash('User status updated', 'success')
            return redirect(url_for('users.user_profile', user_id=user_id))

    # add other actions (special_discount etc.) as needed

    return render_template('user_profile.html', user=user, total_numbers=total_numbers, used_numbers=used_numbers, user_refers_count=user_refers_count)


@users_bp.route('/<user_id>/numbers')
def view_numbers(user_id):
    user = User.objects(id=user_id).first() or abort(404)

    # Pagination params
    page = int(request.args.get('page', 1))
    per_page = 15
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip().lower()

    query = Order.objects(user=user)
    if search:
        query = query.filter(number__icontains=search)
    if status in ['pending', 'completed', 'cancelled', 'active']:
        query = query.filter(status=status)

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page

    orders = query.order_by('-created_at').skip((page-1)*per_page).limit(per_page)

    for i, o in enumerate(orders):
        o.index = (page-1)*per_page + i + 1
        # Attach OTP if status is completed
        if o.status == "completed":
            otp = OtpMessage.objects(order=o).order_by("-created_at").first()
            o.otp_code = otp.otp if otp else None

    return render_template(
        'user_numbers.html',
        user=user,
        orders=orders,
        page=page,
        total_pages=total_pages,
        search=search,
        status=status
    )

@users_bp.route('/<user_id>/transactions')
def view_transactions(user_id):
    user = User.objects(id=user_id).first() or abort(404)
    
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 15
    total_count = Transaction.objects(user=user).count()
    total_pages = (total_count + per_page - 1) // per_page
    
    transactions = Transaction.objects(user=user)\
        .order_by('-created_at')\
        .skip((page-1)*per_page)\
        .limit(per_page)

    # add loop.index for template numbering
    for i, t in enumerate(transactions):
        t.index = (page-1)*per_page + i + 1

    return render_template(
        'user_transactions.html',
        user=user,
        trnx=transactions,
        page=page,
        total_pages=total_pages
    )
