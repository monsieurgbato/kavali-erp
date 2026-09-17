"""Routes Admin — Utilisateurs, Rôles, Paramètres société."""
from decimal import Decimal
from flask import (
    render_template, redirect, url_for, request, flash
)
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from app import db
from app.admin import admin
from app.core.models import User, Role, Company, Permission


# ── Helpers ────────────────────────────────────────

SERVICES = [
    'Commercial', 'Communication', 'Admin', 'Tech-Logistique',
    'Marketing', 'RH', 'Compta', 'DG', 'Production', 'Achats'
]

POSITIONS = [
    'Directeur Général', 'Directeur Commercial', 'Directeur RH',
    'Comptable', 'Commercial', 'Chef de Service', 'Assistant',
    'Technicien', 'Magasinier', 'Chauffeur', 'Autre'
]

DEFAULT_PASSWORD = '***'


# ════════════════════════════════════════════════════
# DASHBOARD / REDIRECT
# ════════════════════════════════════════════════════

@admin.route('/')
@login_required
def index():
    return redirect(url_for('admin.users_list'))


# ════════════════════════════════════════════════════
# USERS CRUD
# ════════════════════════════════════════════════════

@admin.route('/users')
@login_required
def users_list():
    q = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = User.query

    if q:
        query = query.filter(
            or_(
                User.username.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%'),
                User.full_name.ilike(f'%{q}%'),
                User.phone.ilike(f'%{q}%'),
            )
        )
    if role_filter:
        query = query.filter(User.role_id == int(role_filter))

    query = query.order_by(User.created_at.desc())
    users = query.paginate(page=page, per_page=per_page, error_out=False)

    roles = Role.query.order_by(Role.name).all()

    # Stats
    total_active = User.query.filter_by(is_active=True, is_suspended=False).count()
    total_suspended = User.query.filter_by(is_suspended=True).count()
    total_inactive = User.query.filter_by(is_active=False).count()

    return render_template(
        'admin/users_list.html',
        users=users,
        roles=roles,
        q=q,
        role_filter=role_filter,
        total_active=total_active,
        total_suspended=total_suspended,
        total_inactive=total_inactive,
    )


@admin.route('/users/new', methods=['GET'])
@login_required
def user_new():
    roles = Role.query.order_by(Role.name).all()
    return render_template(
        'admin/user_form.html',
        user=None,
        roles=roles,
        services=SERVICES,
        positions=POSITIONS,
    )


@admin.route('/users/new', methods=['POST'])
@login_required
def user_create():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    role_id = request.form.get('role_id', '').strip()
    service = request.form.get('service', '').strip()
    position = request.form.get('position', '').strip()

    if not username or not email or not password:
        flash('Le nom d\'utilisateur, l\'email et le mot de passe sont requis.', 'error')
        return redirect(url_for('admin.user_new'))

    # Vérifier unicité
    if User.query.filter_by(username=username).first():
        flash(f'Le nom d\'utilisateur "{username}" est déjà utilisé.', 'error')
        return redirect(url_for('admin.user_new'))

    if User.query.filter_by(email=email).first():
        flash(f'L\'email "{email}" est déjà utilisé.', 'error')
        return redirect(url_for('admin.user_new'))

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        full_name=full_name,
        phone=phone,
        role_id=int(role_id) if role_id and role_id.isdigit() else None,
        service=service,
        position=position,
        company_id=1,  # Société par défaut
    )
    db.session.add(user)
    db.session.commit()
    flash(f'Utilisateur {full_name or username} créé avec succès.', 'success')
    return redirect(url_for('admin.users_list'))


@admin.route('/users/<int:id>/edit', methods=['GET'])
@login_required
def user_edit(id):
    user = User.query.get_or_404(id)
    roles = Role.query.order_by(Role.name).all()
    return render_template(
        'admin/user_form.html',
        user=user,
        roles=roles,
        services=SERVICES,
        positions=POSITIONS,
    )


@admin.route('/users/<int:id>/edit', methods=['POST'])
@login_required
def user_update(id):
    user = User.query.get_or_404(id)

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    role_id = request.form.get('role_id', '').strip()
    service = request.form.get('service', '').strip()
    position = request.form.get('position', '').strip()

    if not username or not email:
        flash('Le nom d\'utilisateur et l\'email sont requis.', 'error')
        return redirect(url_for('admin.user_edit', id=id))

    # Vérifier unicité username
    existing = User.query.filter(User.username == username, User.id != id).first()
    if existing:
        flash(f'Le nom d\'utilisateur "{username}" est déjà utilisé.', 'error')
        return redirect(url_for('admin.user_edit', id=id))

    # Vérifier unicité email
    existing = User.query.filter(User.email == email, User.id != id).first()
    if existing:
        flash(f'L\'email "{email}" est déjà utilisé.', 'error')
        return redirect(url_for('admin.user_edit', id=id))

    user.username = username
    user.email = email
    user.full_name = full_name
    user.phone = phone
    user.role_id = int(role_id) if role_id and role_id.isdigit() else None
    user.service = service
    user.position = position
    db.session.commit()
    flash(f'Utilisateur {full_name or username} mis à jour.', 'success')
    return redirect(url_for('admin.users_list'))


@admin.route('/users/<int:id>/toggle-suspend', methods=['POST'])
@login_required
def user_toggle_suspend(id):
    user = User.query.get_or_404(id)
    if user.is_suspended:
        user.is_suspended = False
        flash(f'Utilisateur {user.full_name or user.username} réactivé.', 'success')
    else:
        user.is_suspended = True
        flash(f'Utilisateur {user.full_name or user.username} suspendu.', 'warning')
    db.session.commit()
    return redirect(url_for('admin.users_list'))


@admin.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
def user_reset_password(id):
    user = User.query.get_or_404(id)
    user.password_hash = generate_password_hash(DEFAULT_PASSWORD)
    db.session.commit()
    flash(f'Mot de passe réinitialisé à "{DEFAULT_PASSWORD}" pour {user.full_name or user.username}.', 'success')
    return redirect(url_for('admin.users_list'))


@admin.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def user_delete(id):
    user = User.query.get_or_404(id)
    user.is_active = False
    user.is_suspended = True
    db.session.commit()
    flash(f'Utilisateur {user.full_name or user.username} désactivé.', 'warning')
    return redirect(url_for('admin.users_list'))


# ════════════════════════════════════════════════════
# COMPANY SETTINGS
# ════════════════════════════════════════════════════

LEGAL_FORMS = [
    'SARL', 'SA', 'SAS', 'SASU', 'EURL', 'SNC',
    'GIE', 'Association', 'Auto-entrepreneur', 'Autre'
]


@admin.route('/settings', methods=['GET'])
@login_required
def settings():
    company = Company.query.get(1) or Company()
    return render_template(
        'admin/settings.html',
        company=company,
        legal_forms=LEGAL_FORMS,
    )


@admin.route('/settings', methods=['POST'])
@login_required
def settings_update():
    company = Company.query.get(1) or Company()
    is_new = company.id is None

    company.name = request.form.get('name', '').strip()
    company.legal_form = request.form.get('legal_form', '').strip()
    company.activity = request.form.get('activity', '').strip()
    try:
        company.capital = Decimal(request.form.get('capital', '0'))
    except (ValueError, TypeError):
        company.capital = Decimal('0')

    company.address = request.form.get('address', '').strip()
    company.phone = request.form.get('phone', '').strip()
    company.email = request.form.get('email', '').strip()
    company.rccm = request.form.get('rccm', '').strip()
    company.contribuable = request.form.get('contribuable', '').strip()
    company.cnps = request.form.get('cnps', '').strip()
    company.bank_details = request.form.get('bank_details', '').strip()

    if is_new:
        db.session.add(company)
    db.session.commit()
    flash('Paramètres de la société mis à jour.', 'success')
    return redirect(url_for('admin.settings'))


# ════════════════════════════════════════════════════
# ROLES
# ════════════════════════════════════════════════════

@admin.route('/roles')
@login_required
def roles_list():
    roles = Role.query.order_by(Role.name).all()
    return render_template('admin/roles_list.html', roles=roles)


@admin.route('/roles/<int:id>')
@login_required
def roles_detail(id):
    role = Role.query.get_or_404(id)
    permissions = Permission.query.order_by(Permission.ref).all()
    return render_template(
        'admin/roles_detail.html',
        role=role,
        permissions=permissions,
    )