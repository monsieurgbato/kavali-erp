"""Routes Logistique — Stock, Fournisseurs, Ajustements."""
from datetime import datetime, timezone
from decimal import Decimal
from flask import (
    render_template, redirect, url_for, request, flash, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.logistique import logistique
from app.core.models import Product, Supplier


# ── Helpers ────────────────────────────────────────

def _format_currency(amount):
    try:
        return f"{float(amount):,.0f} FCFA".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 FCFA"


# ════════════════════════════════════════════════════
# REDIRECT
# ════════════════════════════════════════════════════

@logistique.route('/')
@login_required
def index():
    return redirect(url_for('logistique.stock_overview'))


# ════════════════════════════════════════════════════
# STOCK OVERVIEW
# ════════════════════════════════════════════════════

@logistique.route('/stock')
@login_required
def stock_overview():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Product.query.filter(Product.is_active == True)
    if q:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{q}%'),
                Product.reference.ilike(f'%{q}%'),
                Product.category.ilike(f'%{q}%'),
            )
        )
    query = query.order_by(Product.name.asc())
    products = query.paginate(page=page, per_page=per_page, error_out=False)

    # Low stock alerts
    low_stock = Product.query.filter(
        Product.is_active == True,
        Product.stock_qty < Product.stock_min
    ).order_by(Product.name.asc()).all()

    total_products = Product.query.filter(Product.is_active == True).count()
    low_stock_count = len(low_stock)
    total_stock_value = db.session.query(
        db.func.sum(Product.stock_qty * Product.price)
    ).filter(Product.is_active == True).scalar() or 0

    return render_template(
        'logistique/stock_overview.html',
        products=products,
        q=q,
        low_stock=low_stock,
        low_stock_count=low_stock_count,
        total_products=total_products,
        total_stock_value=total_stock_value,
        format_currency=_format_currency,
    )


@logistique.route('/stock/adjust', methods=['POST'])
@login_required
def stock_adjust():
    product_id = request.form.get('product_id', type=int)
    operation = request.form.get('operation', '').strip()  # 'add' or 'subtract'
    try:
        quantity = Decimal(request.form.get('quantity', '0'))
    except (ValueError, TypeError):
        quantity = Decimal('0')

    if not product_id or quantity <= 0:
        flash('Paramètres invalides.', 'error')
        return redirect(url_for('logistique.stock_overview'))

    product = Product.query.get_or_404(product_id)
    if not product.is_active:
        flash('Ce produit est désactivé.', 'error')
        return redirect(url_for('logistique.stock_overview'))

    if operation == 'add':
        product.stock_qty = (product.stock_qty or Decimal('0')) + quantity
        flash(f'Ajout de {quantity} au stock de "{product.name}".', 'success')
    elif operation == 'subtract':
        current = product.stock_qty or Decimal('0')
        if quantity > current:
            flash(f'Stock insuffisant pour "{product.name}" (stock actuel: {current}).', 'error')
            return redirect(url_for('logistique.stock_overview'))
        product.stock_qty = current - quantity
        flash(f'Retrait de {quantity} du stock de "{product.name}".', 'success')
    else:
        flash('Opération invalide.', 'error')

    db.session.commit()
    return redirect(url_for('logistique.stock_overview'))


# ════════════════════════════════════════════════════
# SUPPLIERS CRUD
# ════════════════════════════════════════════════════

@logistique.route('/suppliers')
@login_required
def suppliers_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Supplier.query.filter(Supplier.is_active == True)
    if q:
        query = query.filter(
            or_(
                Supplier.name.ilike(f'%{q}%'),
                Supplier.contact.ilike(f'%{q}%'),
                Supplier.email.ilike(f'%{q}%'),
                Supplier.phone.ilike(f'%{q}%'),
                Supplier.service_type.ilike(f'%{q}%'),
            )
        )
    query = query.order_by(Supplier.name.asc())
    suppliers = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'logistique/suppliers_list.html',
        suppliers=suppliers,
        q=q,
    )


@logistique.route('/suppliers/new', methods=['GET'])
@login_required
def supplier_new():
    return render_template('logistique/supplier_form.html', supplier=None)


@logistique.route('/suppliers/new', methods=['POST'])
@login_required
def supplier_create():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Le nom du fournisseur est requis.', 'error')
        return redirect(url_for('logistique.supplier_new'))

    supplier = Supplier(
        name=name,
        contact=request.form.get('contact', '').strip(),
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        address=request.form.get('address', '').strip(),
        service_type=request.form.get('service_type', '').strip(),
        is_active=True,
    )
    db.session.add(supplier)
    db.session.commit()
    flash(f'Fournisseur "{supplier.name}" créé avec succès.', 'success')
    return redirect(url_for('logistique.suppliers_list'))


@logistique.route('/suppliers/<int:id>/edit', methods=['GET'])
@login_required
def supplier_edit(id):
    supplier = Supplier.query.get_or_404(id)
    return render_template('logistique/supplier_form.html', supplier=supplier)


@logistique.route('/suppliers/<int:id>/edit', methods=['POST'])
@login_required
def supplier_update(id):
    supplier = Supplier.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Le nom du fournisseur est requis.', 'error')
        return redirect(url_for('logistique.supplier_edit', id=id))

    supplier.name = name
    supplier.contact = request.form.get('contact', '').strip()
    supplier.phone = request.form.get('phone', '').strip()
    supplier.email = request.form.get('email', '').strip()
    supplier.address = request.form.get('address', '').strip()
    supplier.service_type = request.form.get('service_type', '').strip()
    db.session.commit()
    flash(f'Fournisseur "{supplier.name}" mis à jour.', 'success')
    return redirect(url_for('logistique.suppliers_list'))


@logistique.route('/suppliers/<int:id>/delete', methods=['POST'])
@login_required
def supplier_delete(id):
    supplier = Supplier.query.get_or_404(id)
    supplier.is_active = False
    db.session.commit()
    flash(f'Fournisseur "{supplier.name}" désactivé.', 'warning')
    return redirect(url_for('logistique.suppliers_list'))