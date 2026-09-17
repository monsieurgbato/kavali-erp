from datetime import datetime, timezone
from app import db
from flask_login import UserMixin

# === PERMISSIONS ===
class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    ref = db.Column(db.String(10), unique=True, nullable=False)  # AUT001-116
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    
    def __repr__(self): return f'<Permission {self.ref}: {self.name}>'

# === ROLES ===
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # DG, Chef, Commercial, RH, Compta, Logistique, Admin
    description = db.Column(db.String(200), default='')
    is_default = db.Column(db.Boolean, default=False)
    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                   backref=db.backref('roles', lazy=True))
    def __repr__(self): return f'<Role {self.name}>'
    def has_permission(self, permission_ref):
        return any(p.ref == permission_ref for p in self.permissions)

# === COMPANY ===
class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    legal_form = db.Column(db.String(100), default='')      # Forme juridique
    activity = db.Column(db.String(200), default='')
    capital = db.Column(db.Numeric(15, 2), default=0)
    address = db.Column(db.Text, default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(120), default='')
    rccm = db.Column(db.String(50), default='')
    contribuable = db.Column(db.String(50), default='')
    cnps = db.Column(db.String(50), default='')
    bank_details = db.Column(db.Text, default='')
    logo_path = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

# === USERS ===
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), default='')
    phone = db.Column(db.String(50), default='')
    alias = db.Column(db.String(100), default='')  # Alias DG
    is_active = db.Column(db.Boolean, default=True)
    is_suspended = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    company = db.relationship('Company', backref=db.backref('users', lazy=True))
    service = db.Column(db.String(50), default='')  # Commercial, Communication, Admin, Tech-Logistique, Marketing, RH, Compta, DG
    position = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    def has_permission(self, perm_ref):
        return self.role and self.role.has_permission(perm_ref)
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_dg(self): return self.role and self.role.name == 'DG'
    
    @property
    def is_chef(self): return self.role and self.role.name == 'Chef' and self.service

# === CLIENT / PROSPECT ===
class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(50), default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(120), default='')
    address = db.Column(db.Text, default='')
    zone = db.Column(db.String(100), default='')
    is_prospect = db.Column(db.Boolean, default=True)  # prospect vs client
    note = db.Column(db.String(1), default='C')  # A, B, C, D
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_to = db.relationship('User', backref=db.backref('clients', lazy=True))
    service = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# === PRODUCT / ARTICLE ===
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default='')
    unit = db.Column(db.String(20), default='unité')  # unité de gestion
    variant = db.Column(db.String(100), default='')  # couleur, taille
    price = db.Column(db.Numeric(15, 2), nullable=False)
    stock_qty = db.Column(db.Numeric(15, 2), default=0)
    stock_min = db.Column(db.Numeric(15, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# === ORDER / COMMANDE ===
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False)  # auto-généré
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    client = db.relationship('Client', backref=db.backref('orders', lazy=True))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_orders')
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    validated_by = db.relationship('User', foreign_keys=[validated_by_id])
    status = db.Column(db.String(20), default='pending')  # pending, paid, delivering, delivered, cancelled
    payment_method = db.Column(db.String(50), default='')
    delivery_type = db.Column(db.String(20), default='immediate')  # immediate, scheduled
    delivery_date = db.Column(db.DateTime, nullable=True)
    delivery_address = db.Column(db.Text, default='')
    delivery_city = db.Column(db.String(100), default='')
    notes_client = db.Column(db.Text, default='')
    notes_internal = db.Column(db.Text, default='')
    discount_rate = db.Column(db.Numeric(5, 2), default=0)
    discount_motif = db.Column(db.String(200), default='')
    total = db.Column(db.Numeric(15, 2), default=0)
    paid_at = db.Column(db.DateTime, nullable=True)
    paid_amount = db.Column(db.Numeric(15, 2), default=0)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    paid_by = db.relationship('User', foreign_keys=[paid_by_id])
    delivered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    order = db.relationship('Order', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product')
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    total = db.Column(db.Numeric(15, 2), nullable=False)

# === SUPPLIER ===
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(50), default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(120), default='')
    address = db.Column(db.Text, default='')
    service_type = db.Column(db.String(100), default='')
    is_active = db.Column(db.Boolean, default=True)


# === EMPLOYEE ===
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), default='')
    phone = db.Column(db.String(50), default='')
    position = db.Column(db.String(100), default='')          # Poste occupé
    service = db.Column(db.String(50), default='')             # Service RH
    category = db.Column(db.String(50), default='')            # Catégorie professionnelle
    echelon = db.Column(db.String(20), default='')             # Échelon
    salary_base = db.Column(db.Numeric(15, 2), default=0)      # Salaire de base
    hire_date = db.Column(db.Date, nullable=True)               # Date d'embauche
    contract_type = db.Column(db.String(50), default='CDI')    # CDI, CDD, prestation
    contract_end = db.Column(db.Date, nullable=True)            # Fin de contrat
    status = db.Column(db.String(20), default='active')        # active, archived, suspended
    cnps_number = db.Column(db.String(50), default='')
    bank_account = db.Column(db.String(50), default='')
    birth_date = db.Column(db.Date, nullable=True)
    birth_place = db.Column(db.String(100), default='')
    address = db.Column(db.Text, default='')
    emergency_contact = db.Column(db.String(100), default='')
    emergency_phone = db.Column(db.String(50), default='')
    notes = db.Column(db.Text, default='')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('employee', uselist=False))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self): return f'<Employee {self.matricule}: {self.first_name} {self.last_name}>'

    @property
    def full_name(self): return f"{self.first_name} {self.last_name}"

    @property
    def contract_months(self):
        if self.hire_date:
            delta = datetime.now(timezone.utc).date() - self.hire_date
            return delta.days // 30
        return 0


# === VEHICLE ===
class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    immatriculation = db.Column(db.String(20), unique=True, nullable=False)
    brand = db.Column(db.String(50), default='')
    model = db.Column(db.String(50), default='')
    year = db.Column(db.Integer, default=0)
    type = db.Column(db.String(30), default='')              # utilitaire, berline, camion
    fuel_type = db.Column(db.String(20), default='essence')  # essence, diesel, électrique
    status = db.Column(db.String(20), default='available')   # available, in_use, maintenance, out_of_service
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    driver = db.relationship('Driver', backref=db.backref('vehicles', lazy=True))
    insurance_expiry = db.Column(db.Date, nullable=True)
    technical_visit = db.Column(db.Date, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_price = db.Column(db.Numeric(15, 2), default=0)
    notes = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self): return f'<Vehicle {self.immatriculation}>'


# === DRIVER ===
class Driver(db.Model):
    __tablename__ = 'drivers'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(120), default='')
    license_number = db.Column(db.String(50), default='')
    license_category = db.Column(db.String(10), default='B')  # A, B, C, D, E
    license_expiry = db.Column(db.Date, nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')       # active, suspended, archived
    address = db.Column(db.Text, default='')
    emergency_contact = db.Column(db.String(100), default='')
    emergency_phone = db.Column(db.String(50), default='')
    notes = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self): return f'<Driver {self.first_name} {self.last_name}>'

    @property
    def full_name(self): return f"{self.first_name} {self.last_name}"


# === FUEL RECORD ===
class FuelRecord(db.Model):
    __tablename__ = 'fuel_records'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    vehicle = db.relationship('Vehicle', backref=db.backref('fuel_records', lazy=True))
    date = db.Column(db.Date, nullable=False)
    liters = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    odometer = db.Column(db.Integer, default=0)
    station = db.Column(db.String(100), default='')
    notes = db.Column(db.Text, default='')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self): return f'<FuelRecord {self.vehicle_id} - {self.date}>'


# === MAINTENANCE ===
class Maintenance(db.Model):
    __tablename__ = 'maintenance'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    vehicle = db.relationship('Vehicle', backref=db.backref('maintenance_records', lazy=True))
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(50), default='')               # révision, réparation, pneu, vidange
    description = db.Column(db.Text, default='')
    cost = db.Column(db.Numeric(15, 2), default=0)
    provider = db.Column(db.String(100), default='')
    next_due_date = db.Column(db.Date, nullable=True)
    next_due_km = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='done')         # done, scheduled, pending
    notes = db.Column(db.Text, default='')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self): return f'<Maintenance {self.vehicle_id} - {self.type}>'