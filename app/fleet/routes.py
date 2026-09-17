"""Routes Fleet — Véhicules, Chauffeurs, Carburant, Maintenance."""
from datetime import datetime, timezone, date
from decimal import Decimal
from flask import (
    render_template, redirect, url_for, request, flash, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.fleet import fleet
from app.core.models import Vehicle, Driver, FuelRecord, Maintenance


# ── Helpers ────────────────────────────────────────

VEHICLE_TYPES = ['utilitaire', 'berline', 'camion', '4x4', 'minibus', 'bus']
FUEL_TYPES = ['essence', 'diesel', 'électrique', 'hybride', 'GPL']
VEHICLE_STATUSES = ['available', 'in_use', 'maintenance', 'out_of_service']
DRIVER_STATUSES = ['active', 'suspended', 'archived']
LICENSE_CATEGORIES = ['A', 'B', 'C', 'D', 'E']
MAINTENANCE_TYPES = ['révision', 'réparation', 'pneu', 'vidange', 'freins', 'climatisation', 'carrosserie', 'électricité']
MAINTENANCE_STATUSES = ['done', 'scheduled', 'pending']


def _format_currency(amount):
    try:
        return f"{float(amount):,.0f} FCFA".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 FCFA"


def _vehicle_badge(status):
    badges = {
        'available':      ('badge badge-success',    'Disponible'),
        'in_use':         ('badge badge-info',        'En service'),
        'maintenance':    ('badge badge-warning',     'En maintenance'),
        'out_of_service': ('badge badge-destructive', 'HS'),
    }
    cls, label = badges.get(status, ('badge badge-default', status))
    return f'<span class="{cls}">{label}</span>'


def _driver_badge(status):
    badges = {
        'active':    ('badge badge-success', 'Actif'),
        'suspended': ('badge badge-warning', 'Suspendu'),
        'archived':  ('badge badge-destructive', 'Archivé'),
    }
    cls, label = badges.get(status, ('badge badge-default', status))
    return f'<span class="{cls}">{label}</span>'


def _maintenance_badge(status):
    badges = {
        'done':      ('badge badge-success', 'Effectuée'),
        'scheduled': ('badge badge-info',    'Planifiée'),
        'pending':   ('badge badge-warning', 'En attente'),
    }
    cls, label = badges.get(status, ('badge badge-default', status))
    return f'<span class="{cls}">{label}</span>'


def _parse_date(val):
    if val:
        try:
            return datetime.strptime(val.strip(), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    return None


# ════════════════════════════════════════════════════
# REDIRECT
# ════════════════════════════════════════════════════

@fleet.route('/')
@login_required
def index():
    return redirect(url_for('fleet.vehicles_list'))


# ════════════════════════════════════════════════════
# VEHICLES CRUD
# ════════════════════════════════════════════════════

@fleet.route('/vehicles')
@login_required
def vehicles_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Vehicle.query.filter(Vehicle.is_active == True)
    if q:
        query = query.filter(
            or_(
                Vehicle.immatriculation.ilike(f'%{q}%'),
                Vehicle.brand.ilike(f'%{q}%'),
                Vehicle.model.ilike(f'%{q}%'),
            )
        )
    if status:
        query = query.filter(Vehicle.status == status)

    query = query.order_by(Vehicle.brand.asc(), Vehicle.model.asc())
    vehicles = query.paginate(page=page, per_page=per_page, error_out=False)

    today = date.today()
    expiring_insurance = Vehicle.query.filter(
        Vehicle.is_active == True,
        Vehicle.insurance_expiry.is_not(None),
        Vehicle.insurance_expiry <= today
    ).count()

    return render_template(
        'fleet/vehicles_list.html',
        vehicles=vehicles,
        q=q,
        status=status,
        vehicle_statuses=VEHICLE_STATUSES,
        badge=_vehicle_badge,
        format_currency=_format_currency,
        today=today,
        expiring_insurance=expiring_insurance,
    )


@fleet.route('/vehicles/new', methods=['GET'])
@login_required
def vehicle_new():
    drivers = Driver.query.filter(Driver.status == 'active', Driver.is_active == True).order_by(Driver.first_name.asc()).all()
    return render_template(
        'fleet/vehicle_form.html',
        vehicle=None,
        drivers=drivers,
        vehicle_types=VEHICLE_TYPES,
        fuel_types=FUEL_TYPES,
        statuses=VEHICLE_STATUSES,
    )


@fleet.route('/vehicles/new', methods=['POST'])
@login_required
def vehicle_create():
    immatriculation = request.form.get('immatriculation', '').strip().upper()
    if not immatriculation:
        flash("L'immatriculation est requise.", 'error')
        return redirect(url_for('fleet.vehicle_new'))

    existing = Vehicle.query.filter_by(immatriculation=immatriculation).first()
    if existing:
        flash(f'Le véhicule avec l\'immatriculation "{immatriculation}" existe déjà.', 'error')
        return redirect(url_for('fleet.vehicle_new'))

    try:
        year = int(request.form.get('year', '0'))
    except (ValueError, TypeError):
        year = 0
    try:
        purchase_price = Decimal(request.form.get('purchase_price', '0'))
    except (ValueError, TypeError):
        purchase_price = Decimal('0')

    driver_id = request.form.get('driver_id', type=int)
    if driver_id == 0:
        driver_id = None

    v = Vehicle(
        immatriculation=immatriculation,
        brand=request.form.get('brand', '').strip(),
        model=request.form.get('model', '').strip(),
        year=year,
        type=request.form.get('type', '').strip(),
        fuel_type=request.form.get('fuel_type', 'essence').strip(),
        status=request.form.get('status', 'available').strip(),
        driver_id=driver_id,
        insurance_expiry=_parse_date(request.form.get('insurance_expiry')),
        technical_visit=_parse_date(request.form.get('technical_visit')),
        purchase_date=_parse_date(request.form.get('purchase_date')),
        purchase_price=purchase_price,
        notes=request.form.get('notes', '').strip(),
        is_active=True,
    )
    db.session.add(v)
    db.session.commit()
    flash(f'Véhicule "{v.immatriculation}" ({v.brand} {v.model}) créé avec succès.', 'success')
    return redirect(url_for('fleet.vehicle_detail', id=v.id))


@fleet.route('/vehicles/<int:id>')
@login_required
def vehicle_detail(id):
    v = Vehicle.query.get_or_404(id)
    fuel_records = FuelRecord.query.filter_by(vehicle_id=id).order_by(FuelRecord.date.desc()).limit(20).all()
    maintenance_records = Maintenance.query.filter_by(vehicle_id=id).order_by(Maintenance.date.desc()).all()
    return render_template(
        'fleet/vehicle_detail.html',
        vehicle=v,
        fuel_records=fuel_records,
        maintenance_records=maintenance_records,
        format_currency=_format_currency,
        badge=_vehicle_badge,
        maint_badge=_maintenance_badge,
    )


@fleet.route('/vehicles/<int:id>/edit', methods=['GET'])
@login_required
def vehicle_edit(id):
    v = Vehicle.query.get_or_404(id)
    drivers = Driver.query.filter(Driver.status == 'active', Driver.is_active == True).order_by(Driver.first_name.asc()).all()
    return render_template(
        'fleet/vehicle_form.html',
        vehicle=v,
        drivers=drivers,
        vehicle_types=VEHICLE_TYPES,
        fuel_types=FUEL_TYPES,
        statuses=VEHICLE_STATUSES,
    )


@fleet.route('/vehicles/<int:id>/edit', methods=['POST'])
@login_required
def vehicle_update(id):
    v = Vehicle.query.get_or_404(id)
    immatriculation = request.form.get('immatriculation', '').strip().upper()
    if not immatriculation:
        flash("L'immatriculation est requise.", 'error')
        return redirect(url_for('fleet.vehicle_edit', id=id))

    existing = Vehicle.query.filter(Vehicle.immatriculation == immatriculation, Vehicle.id != id).first()
    if existing:
        flash(f'L\'immatriculation "{immatriculation}" est déjà utilisée.', 'error')
        return redirect(url_for('fleet.vehicle_edit', id=id))

    try:
        year = int(request.form.get('year', '0'))
    except (ValueError, TypeError):
        year = 0
    try:
        purchase_price = Decimal(request.form.get('purchase_price', '0'))
    except (ValueError, TypeError):
        purchase_price = Decimal('0')

    driver_id = request.form.get('driver_id', type=int)
    if driver_id == 0:
        driver_id = None

    v.immatriculation = immatriculation
    v.brand = request.form.get('brand', '').strip()
    v.model = request.form.get('model', '').strip()
    v.year = year
    v.type = request.form.get('type', '').strip()
    v.fuel_type = request.form.get('fuel_type', 'essence').strip()
    v.status = request.form.get('status', 'available').strip()
    v.driver_id = driver_id
    v.insurance_expiry = _parse_date(request.form.get('insurance_expiry'))
    v.technical_visit = _parse_date(request.form.get('technical_visit'))
    v.purchase_date = _parse_date(request.form.get('purchase_date'))
    v.purchase_price = purchase_price
    v.notes = request.form.get('notes', '').strip()
    db.session.commit()
    flash(f'Véhicule "{v.immatriculation}" mis à jour.', 'success')
    return redirect(url_for('fleet.vehicle_detail', id=v.id))


@fleet.route('/vehicles/<int:id>/delete', methods=['POST'])
@login_required
def vehicle_delete(id):
    v = Vehicle.query.get_or_404(id)
    v.is_active = False
    db.session.commit()
    flash(f'Véhicule "{v.immatriculation}" désactivé.', 'warning')
    return redirect(url_for('fleet.vehicles_list'))


# ════════════════════════════════════════════════════
# DRIVERS CRUD
# ════════════════════════════════════════════════════

@fleet.route('/drivers')
@login_required
def drivers_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Driver.query.filter(Driver.is_active == True)
    if q:
        query = query.filter(
            or_(
                Driver.first_name.ilike(f'%{q}%'),
                Driver.last_name.ilike(f'%{q}%'),
                Driver.phone.ilike(f'%{q}%'),
                Driver.license_number.ilike(f'%{q}%'),
            )
        )
    if status:
        query = query.filter(Driver.status == status)

    query = query.order_by(Driver.last_name.asc(), Driver.first_name.asc())
    drivers = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'fleet/drivers_list.html',
        drivers=drivers,
        q=q,
        status=status,
        driver_statuses=DRIVER_STATUSES,
        badge=_driver_badge,
    )


@fleet.route('/drivers/new', methods=['GET'])
@login_required
def driver_new():
    return render_template(
        'fleet/driver_form.html',
        driver=None,
        statuses=DRIVER_STATUSES,
        license_categories=LICENSE_CATEGORIES,
    )


@fleet.route('/drivers/new', methods=['POST'])
@login_required
def driver_create():
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    if not first_name or not last_name:
        flash('Le prénom et le nom sont requis.', 'error')
        return redirect(url_for('fleet.driver_new'))

    d = Driver(
        first_name=first_name,
        last_name=last_name,
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        license_number=request.form.get('license_number', '').strip(),
        license_category=request.form.get('license_category', 'B').strip(),
        license_expiry=_parse_date(request.form.get('license_expiry')),
        hire_date=_parse_date(request.form.get('hire_date')),
        status=request.form.get('status', 'active').strip(),
        address=request.form.get('address', '').strip(),
        emergency_contact=request.form.get('emergency_contact', '').strip(),
        emergency_phone=request.form.get('emergency_phone', '').strip(),
        notes=request.form.get('notes', '').strip(),
        is_active=True,
    )
    db.session.add(d)
    db.session.commit()
    flash(f'Chauffeur {d.full_name} créé avec succès.', 'success')
    return redirect(url_for('fleet.drivers_list'))


@fleet.route('/drivers/<int:id>/edit', methods=['GET'])
@login_required
def driver_edit(id):
    d = Driver.query.get_or_404(id)
    return render_template(
        'fleet/driver_form.html',
        driver=d,
        statuses=DRIVER_STATUSES,
        license_categories=LICENSE_CATEGORIES,
    )


@fleet.route('/drivers/<int:id>/edit', methods=['POST'])
@login_required
def driver_update(id):
    d = Driver.query.get_or_404(id)
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    if not first_name or not last_name:
        flash('Le prénom et le nom sont requis.', 'error')
        return redirect(url_for('fleet.driver_edit', id=id))

    d.first_name = first_name
    d.last_name = last_name
    d.phone = request.form.get('phone', '').strip()
    d.email = request.form.get('email', '').strip()
    d.license_number = request.form.get('license_number', '').strip()
    d.license_category = request.form.get('license_category', 'B').strip()
    d.license_expiry = _parse_date(request.form.get('license_expiry'))
    d.hire_date = _parse_date(request.form.get('hire_date'))
    d.status = request.form.get('status', 'active').strip()
    d.address = request.form.get('address', '').strip()
    d.emergency_contact = request.form.get('emergency_contact', '').strip()
    d.emergency_phone = request.form.get('emergency_phone', '').strip()
    d.notes = request.form.get('notes', '').strip()
    db.session.commit()
    flash(f'Chauffeur {d.full_name} mis à jour.', 'success')
    return redirect(url_for('fleet.drivers_list'))


# ════════════════════════════════════════════════════
# FUEL RECORDS
# ════════════════════════════════════════════════════

@fleet.route('/fuel')
@login_required
def fuel_list():
    q = request.args.get('q', '').strip()
    vehicle_id = request.args.get('vehicle_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = FuelRecord.query
    if vehicle_id:
        query = query.filter(FuelRecord.vehicle_id == vehicle_id)
    if q:
        query = query.join(Vehicle).filter(
            Vehicle.immatriculation.ilike(f'%{q}%')
        )

    query = query.order_by(FuelRecord.date.desc(), FuelRecord.created_at.desc())
    fuel_records = query.paginate(page=page, per_page=per_page, error_out=False)

    vehicles = Vehicle.query.filter(Vehicle.is_active == True).order_by(Vehicle.immatriculation.asc()).all()

    return render_template(
        'fleet/fuel_list.html',
        fuel_records=fuel_records,
        q=q,
        vehicle_id=vehicle_id,
        vehicles=vehicles,
        format_currency=_format_currency,
    )


@fleet.route('/fuel/new', methods=['GET'])
@login_required
def fuel_new():
    vehicles = Vehicle.query.filter(Vehicle.is_active == True).order_by(Vehicle.immatriculation.asc()).all()
    return render_template(
        'fleet/fuel_form.html',
        fuel_record=None,
        vehicles=vehicles,
    )


@fleet.route('/fuel/new', methods=['POST'])
@login_required
def fuel_create():
    vehicle_id = request.form.get('vehicle_id', type=int)
    if not vehicle_id:
        flash('Veuillez sélectionner un véhicule.', 'error')
        return redirect(url_for('fleet.fuel_new'))

    try:
        liters = Decimal(request.form.get('liters', '0'))
    except (ValueError, TypeError):
        liters = Decimal('0')
    try:
        unit_price = Decimal(request.form.get('unit_price', '0'))
    except (ValueError, TypeError):
        unit_price = Decimal('0')
    try:
        odometer = int(request.form.get('odometer', '0'))
    except (ValueError, TypeError):
        odometer = 0

    if liters <= 0 or unit_price <= 0:
        flash('Les litres et le prix unitaire doivent être positifs.', 'error')
        return redirect(url_for('fleet.fuel_new'))

    total_amount = liters * unit_price

    record = FuelRecord(
        vehicle_id=vehicle_id,
        date=_parse_date(request.form.get('date')) or date.today(),
        liters=liters,
        unit_price=unit_price,
        total_amount=total_amount,
        odometer=odometer,
        station=request.form.get('station', '').strip(),
        notes=request.form.get('notes', '').strip(),
        created_by_id=current_user.id,
    )
    db.session.add(record)
    db.session.commit()
    flash('Relevé de carburant ajouté avec succès.', 'success')
    return redirect(url_for('fleet.fuel_list'))


# ════════════════════════════════════════════════════
# MAINTENANCE RECORDS
# ════════════════════════════════════════════════════

@fleet.route('/maintenance')
@login_required
def maintenance_list():
    q = request.args.get('q', '').strip()
    vehicle_id = request.args.get('vehicle_id', type=int)
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Maintenance.query
    if vehicle_id:
        query = query.filter(Maintenance.vehicle_id == vehicle_id)
    if status:
        query = query.filter(Maintenance.status == status)
    if q:
        query = query.join(Vehicle).filter(
            Vehicle.immatriculation.ilike(f'%{q}%')
        )

    query = query.order_by(Maintenance.date.desc(), Maintenance.created_at.desc())
    maintenance_records = query.paginate(page=page, per_page=per_page, error_out=False)

    vehicles = Vehicle.query.filter(Vehicle.is_active == True).order_by(Vehicle.immatriculation.asc()).all()

    return render_template(
        'fleet/maintenance_list.html',
        maintenance_records=maintenance_records,
        q=q,
        vehicle_id=vehicle_id,
        status=status,
        vehicles=vehicles,
        maintenance_statuses=MAINTENANCE_STATUSES,
        format_currency=_format_currency,
        badge=_maintenance_badge,
    )


@fleet.route('/maintenance/new', methods=['GET'])
@login_required
def maintenance_new():
    vehicles = Vehicle.query.filter(Vehicle.is_active == True).order_by(Vehicle.immatriculation.asc()).all()
    return render_template(
        'fleet/maintenance_form.html',
        maintenance=None,
        vehicles=vehicles,
        maintenance_types=MAINTENANCE_TYPES,
        statuses=MAINTENANCE_STATUSES,
    )


@fleet.route('/maintenance/new', methods=['POST'])
@login_required
def maintenance_create():
    vehicle_id = request.form.get('vehicle_id', type=int)
    if not vehicle_id:
        flash('Veuillez sélectionner un véhicule.', 'error')
        return redirect(url_for('fleet.maintenance_new'))

    try:
        cost = Decimal(request.form.get('cost', '0'))
    except (ValueError, TypeError):
        cost = Decimal('0')
    try:
        next_due_km = int(request.form.get('next_due_km', '0'))
    except (ValueError, TypeError):  
        next_due_km = 0

    record = Maintenance(
        vehicle_id=vehicle_id,
        date=_parse_date(request.form.get('date')) or date.today(),
        type=request.form.get('type', '').strip(),
        description=request.form.get('description', '').strip(),
        cost=cost,
        provider=request.form.get('provider', '').strip(),
        next_due_date=_parse_date(request.form.get('next_due_date')),
        next_due_km=next_due_km,
        status=request.form.get('status', 'done').strip(),
        notes=request.form.get('notes', '').strip(),
        created_by_id=current_user.id,
    )
    db.session.add(record)
    db.session.commit()
    flash('Enregistrement de maintenance ajouté avec succès.', 'success')
    return redirect(url_for('fleet.maintenance_list'))