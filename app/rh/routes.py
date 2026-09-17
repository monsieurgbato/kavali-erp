"""Routes RH — Employés, Contrats, Pointage, Paie."""
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from flask import (
    render_template, redirect, url_for, request, flash, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.rh import rh
from app.core.models import Employee


# ── Helpers ────────────────────────────────────────

SERVICES = [
    'Commercial', 'Communication', 'Admin', 'Tech-Logistique',
    'Marketing', 'RH', 'Compta', 'DG', 'Production', 'Achats'
]

CONTRACT_TYPES = ['CDI', 'CDD', 'prestation']

STATUSES = ['active', 'archived', 'suspended']


def _format_currency(amount):
    try:
        return f"{float(amount):,.0f} FCFA".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 FCFA"


def _gen_matricule():
    last = Employee.query.order_by(Employee.id.desc()).first()
    num = 1
    if last and last.matricule:
        try:
            num = int(last.matricule.replace('EMP', '')) + 1
        except (ValueError, AttributeError):
            num = 1
    return f"EMP{num:03d}"


def _parse_date(val):
    if val:
        try:
            return datetime.strptime(val.strip(), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    return None


# ════════════════════════════════════════════════════
# DASHBOARD / REDIRECT
# ════════════════════════════════════════════════════

@rh.route('/')
@login_required
def index():
    return redirect(url_for('rh.employees_list'))


# ════════════════════════════════════════════════════
# EMPLOYEES CRUD
# ════════════════════════════════════════════════════

@rh.route('/employees')
@login_required
def employees_list():
    q = request.args.get('q', '').strip()
    service = request.args.get('service', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Employee.query

    if q:
        query = query.filter(
            or_(
                Employee.first_name.ilike(f'%{q}%'),
                Employee.last_name.ilike(f'%{q}%'),
                Employee.matricule.ilike(f'%{q}%'),
                Employee.email.ilike(f'%{q}%'),
                Employee.phone.ilike(f'%{q}%'),
                Employee.position.ilike(f'%{q}%'),
            )
        )
    if service:
        query = query.filter(Employee.service == service)
    if status:
        query = query.filter(Employee.status == status)

    query = query.order_by(Employee.last_name.asc(), Employee.first_name.asc())
    employees = query.paginate(page=page, per_page=per_page, error_out=False)

    # Stats
    total_active = Employee.query.filter_by(status='active').count()
    total_archived = Employee.query.filter_by(status='archived').count()
    total_suspended = Employee.query.filter_by(status='suspended').count()

    return render_template(
        'rh/employees_list.html',
        employees=employees,
        q=q,
        service=service,
        status=status,
        services=SERVICES,
        total_active=total_active,
        total_archived=total_archived,
        total_suspended=total_suspended,
        format_currency=_format_currency,
    )


@rh.route('/employees/new', methods=['GET'])
@login_required
def employee_new():
    return render_template(
        'rh/employee_form.html',
        employee=None,
        services=SERVICES,
        contract_types=CONTRACT_TYPES,
        statuses=STATUSES,
    )


@rh.route('/employees/new', methods=['POST'])
@login_required
def employee_create():
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    if not first_name or not last_name:
        flash('Le prenom et le nom sont requis.', 'error')
        return redirect(url_for('rh.employee_new'))

    email = request.form.get('email', '').strip()
    if email:
        existing = Employee.query.filter_by(email=email).first()
        if existing:
            flash(f'L email "{email}" est deja utilise par {existing.full_name}.', 'error')
            return redirect(url_for('rh.employee_new'))

    try:
        salary = Decimal(request.form.get('salary_base', '0'))
    except (ValueError, TypeError):
        salary = Decimal('0')

    emp = Employee(
        matricule=_gen_matricule(),
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=request.form.get('phone', '').strip(),
        position=request.form.get('position', '').strip(),
        service=request.form.get('service', '').strip(),
        category=request.form.get('category', '').strip(),
        echelon=request.form.get('echelon', '').strip(),
        salary_base=salary,
        hire_date=_parse_date(request.form.get('hire_date')),
        contract_type=request.form.get('contract_type', 'CDI'),
        contract_end=_parse_date(request.form.get('contract_end')),
        status=request.form.get('status', 'active'),
        cnps_number=request.form.get('cnps_number', '').strip(),
        bank_account=request.form.get('bank_account', '').strip(),
        birth_date=_parse_date(request.form.get('birth_date')),
        birth_place=request.form.get('birth_place', '').strip(),
        address=request.form.get('address', '').strip(),
        emergency_contact=request.form.get('emergency_contact', '').strip(),
        emergency_phone=request.form.get('emergency_phone', '').strip(),
        notes=request.form.get('notes', '').strip(),
    )
    db.session.add(emp)
    db.session.commit()
    flash(f'Employe {emp.full_name} cree avec succes (Matricule: {emp.matricule}).', 'success')
    return redirect(url_for('rh.employee_detail', id=emp.id))


@rh.route('/employees/<int:id>')
@login_required
def employee_detail(id):
    emp = Employee.query.get_or_404(id)
    return render_template(
        'rh/employee_detail.html',
        employee=emp,
        format_currency=_format_currency,
    )


@rh.route('/employees/<int:id>/edit', methods=['GET'])
@login_required
def employee_edit(id):
    emp = Employee.query.get_or_404(id)
    return render_template(
        'rh/employee_form.html',
        employee=emp,
        services=SERVICES,
        contract_types=CONTRACT_TYPES,
        statuses=STATUSES,
    )


@rh.route('/employees/<int:id>/edit', methods=['POST'])
@login_required
def employee_update(id):
    emp = Employee.query.get_or_404(id)
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    if not first_name or not last_name:
        flash('Le prenom et le nom sont requis.', 'error')
        return redirect(url_for('rh.employee_edit', id=id))

    email = request.form.get('email', '').strip()
    if email and email != emp.email:
        existing = Employee.query.filter(Employee.email == email, Employee.id != id).first()
        if existing:
            flash(f'L email "{email}" est deja utilise.', 'error')
            return redirect(url_for('rh.employee_edit', id=id))

    try:
        salary = Decimal(request.form.get('salary_base', '0'))
    except (ValueError, TypeError):
        salary = Decimal('0')

    emp.first_name = first_name
    emp.last_name = last_name
    emp.email = email
    emp.phone = request.form.get('phone', '').strip()
    emp.position = request.form.get('position', '').strip()
    emp.service = request.form.get('service', '').strip()
    emp.category = request.form.get('category', '').strip()
    emp.echelon = request.form.get('echelon', '').strip()
    emp.salary_base = salary
    emp.hire_date = _parse_date(request.form.get('hire_date'))
    emp.contract_type = request.form.get('contract_type', 'CDI')
    emp.contract_end = _parse_date(request.form.get('contract_end'))
    emp.status = request.form.get('status', 'active')
    emp.cnps_number = request.form.get('cnps_number', '').strip()
    emp.bank_account = request.form.get('bank_account', '').strip()
    emp.birth_date = _parse_date(request.form.get('birth_date'))
    emp.birth_place = request.form.get('birth_place', '').strip()
    emp.address = request.form.get('address', '').strip()
    emp.emergency_contact = request.form.get('emergency_contact', '').strip()
    emp.emergency_phone = request.form.get('emergency_phone', '').strip()
    emp.notes = request.form.get('notes', '').strip()
    db.session.commit()
    flash(f'Employe {emp.full_name} mis a jour.', 'success')
    return redirect(url_for('rh.employee_detail', id=emp.id))


@rh.route('/employees/<int:id>/archive', methods=['POST'])
@login_required
def employee_archive(id):
    emp = Employee.query.get_or_404(id)
    emp.status = 'archived'
    db.session.commit()
    flash(f'Employe {emp.full_name} archive.', 'warning')
    return redirect(url_for('rh.employee_detail', id=emp.id))


@rh.route('/employees/<int:id>/activate', methods=['POST'])
@login_required
def employee_activate(id):
    emp = Employee.query.get_or_404(id)
    emp.status = 'active'
    db.session.commit()
    flash(f'Employe {emp.full_name} reactive.', 'success')
    return redirect(url_for('rh.employee_detail', id=emp.id))


# ════════════════════════════════════════════════════
# CONTRACTS
# ════════════════════════════════════════════════════

@rh.route('/contracts')
@login_required
def contracts_list():
    query = Employee.query.filter(
        Employee.status != 'archived',
        Employee.contract_type.in_(['CDI', 'CDD'])
    ).order_by(Employee.contract_end.asc().nullslast())

    q = request.args.get('q', '').strip()
    if q:
        query = query.filter(
            or_(
                Employee.first_name.ilike(f'%{ q}%'),
                Employee.last_name.ilike(f'%{ q}%'),
                Employee.matricule.ilike(f'%{ q}%'),
            )
        )

    employees = query.all()
    today = date.today()
    expiring = []
    near_expiry = []
    ok = []

    for emp in employees:
        if emp.contract_end:
            days_left = (emp.contract_end - today).days
            setattr(emp, '_days_left', days_left)
            if days_left <= 30:
                setattr(emp, '_expiry_class', 'danger')
                near_expiry.append(emp)
            elif days_left <= 60:
                setattr(emp, '_expiry_class', 'warning')
                expiring.append(emp)
            else:
                setattr(emp, '_expiry_class', 'ok')
                ok.append(emp)
        else:
            setattr(emp, '_days_left', None)
            setattr(emp, '_expiry_class', 'ok')
            ok.append(emp)

    return render_template(
        'rh/contracts_list.html',
        employees=employees,
        q=q,
        format_currency=_format_currency,
        near_expiry=near_expiry,
        expiring=expiring,
    )


@rh.route('/contracts/expiring')
@login_required
def contracts_expiring():
    today = date.today()
    limit = today + timedelta(days=60)
    employees = Employee.query.filter(
        Employee.status != 'archived',
        Employee.contract_type.in_(['CDI', 'CDD']),
        Employee.contract_end.is_not(None),
        Employee.contract_end <= limit,
    ).order_by(Employee.contract_end.asc()).all()

    for emp in employees:
        if emp.contract_end:
            emp._days_left = (emp.contract_end - today).days
            emp._expiry_class = 'danger' if emp._days_left <= 30 else 'warning'

    return render_template(
        'rh/contracts_list.html',
        employees=employees,
        q='',
        format_currency=_format_currency,
        expiring_filter=True,
    )


# ════════════════════════════════════════════════════
# ATTENDANCE / POINTAGE
# ════════════════════════════════════════════════════

@rh.route('/attendance')
@login_required
def attendance():
    return render_template('rh/attendance.html')


# ════════════════════════════════════════════════════
# PAYROLL / PAIE
# ════════════════════════════════════

@rh.route('/payroll')
@login_required
def payroll():
    return render_template('rh/payroll.html')


@rh.route('/payroll/prepare')
@login_required
def payroll_prepare():
    flash('Module de preparation de la paie en cours de developpement.', 'info')
    return redirect(url_for('rh.payroll'))