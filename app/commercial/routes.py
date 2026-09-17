"""Routes commerciales — Clients, Prospects, Produits, Commandes, Devis."""
from datetime import datetime, timezone
from decimal import Decimal
from flask import (
    render_template, redirect, url_for, request, flash, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.commercial import commercial
from app.core.models import Client, Product, Order, OrderItem


# ── Helpers ────────────────────────────────────────

def _format_currency(amount):
    try:
        return f"{float(amount):,.0f} FCFA".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 FCFA"


def _badge_html(status):
    badges = {
        'pending':    ('badge badge-warning',    '\U0001f7e0 En attente'),
        'paid':       ('badge badge-success',    '\u2705 Pay\u00e9e'),
        'delivering': ('badge badge-info',       '\U0001f69a En livraison'),
        'delivered':  ('badge badge-primary',    '\U0001f4e6 Livr\u00e9e'),
        'cancelled':  ('badge badge-destructive', '\u274c Annul\u00e9e'),
        'devis':      ('badge badge-default',    '\U0001f4c4 Devis'),
    }
    cls, label = badges.get(status, ('badge badge-default', status))
    return f'<span class="{cls}">{label}</span>'


def _gen_order_ref():
    today = datetime.now(timezone.utc)
    prefix = today.strftime('CMD-%Y%m%d-')
    last = Order.query.filter(
        Order.reference.like(f'{prefix}%')
    ).order_by(Order.id.desc()).first()
    num = 1
    if last and last.reference:
        try:
            num = int(last.reference.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    return f"{prefix}{num:03d}"


def _gen_devis_ref():
    today = datetime.now(timezone.utc)
    prefix = today.strftime('DEVIS-%Y%m%d-')
    last = Order.query.filter(
        Order.reference.like(f'{prefix}%')
    ).order_by(Order.id.desc()).first()
    num = 1
    if last and last.reference:
        try:
            num = int(last.reference.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    return f"{prefix}{num:03d}"


def _client_note_color(note):
    colors = {
        'A': 'var(--kavali-vert)',
        'B': 'var(--kavali-dore)',
        'C': '#F59E0B',
        'D': '#EF4444',
    }
    return colors.get(note.upper(), '#6B7280') if note else '#6B7280'


# ════════════════════════════════════════════════════
# CLIENTS CRUD
# ════════════════════════════════════════════════════

@commercial.route('/clients')
@login_required
def clients_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Client.query.filter(Client.is_prospect == False)
    if q:
        query = query.filter(
            or_(
                Client.name.ilike(f'%{q}%'),
                Client.contact.ilike(f'%{q}%'),
                Client.email.ilike(f'%{q}%'),
                Client.phone.ilike(f'%{q}%'),
                Client.zone.ilike(f'%{q}%'),
            )
        )
    query = query.order_by(Client.name.asc())
    clients = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'commercial/clients_list.html',
        clients=clients,
        q=q,
        note_color=_client_note_color,
    )


@commercial.route('/clients/new', methods=['GET'])
@login_required
def client_new():
    return render_template('commercial/client_form.html', client=None)


@commercial.route('/clients/new', methods=['POST'])
@login_required
def client_create():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Le nom du client est requis.', 'error')
        return redirect(url_for('commercial.client_new'))

    c = Client(
        name=name,
        contact=request.form.get('contact', '').strip(),
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        address=request.form.get('address', '').strip(),
        zone=request.form.get('zone', '').strip(),
        note=(request.form.get('note', 'C').strip().upper() or 'C'),
        is_prospect=False,
        assigned_to_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(c)
    db.session.commit()
    flash(f'Client "{c.name}" cr\u00e9\u00e9 avec succ\u00e8s.', 'success')
    return redirect(url_for('commercial.client_detail', id=c.id))


@commercial.route('/clients/<int:id>')
@login_required
def client_detail(id):
    c = Client.query.get_or_404(id)
    orders = Order.query.filter_by(client_id=id).order_by(Order.created_at.desc()).all()
    return render_template(
        'commercial/client_detail.html',
        client=c,
        orders=orders,
        note_color=_client_note_color,
        format_currency=_format_currency,
        badge=_badge_html,
    )


@commercial.route('/clients/<int:id>/edit', methods=['GET'])
@login_required
def client_edit(id):
    c = Client.query.get_or_404(id)
    return render_template('commercial/client_form.html', client=c)


@commercial.route('/clients/<int:id>/edit', methods=['POST'])
@login_required
def client_update(id):
    c = Client.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    if not name:
        flash('Le nom du client est requis.', 'error')
        return redirect(url_for('commercial.client_edit', id=id))

    c.name = name
    c.contact = request.form.get('contact', '').strip()
    c.phone = request.form.get('phone', '').strip()
    c.email = request.form.get('email', '').strip()
    c.address = request.form.get('address', '').strip()
    c.zone = request.form.get('zone', '').strip()
    c.note = (request.form.get('note', 'C').strip().upper() or 'C')
    db.session.commit()
    flash(f'Client "{c.name}" mis \u00e0 jour.', 'success')
    return redirect(url_for('commercial.client_detail', id=c.id))


@commercial.route('/clients/<int:id>/delete', methods=['POST'])
@login_required
def client_delete(id):
    c = Client.query.get_or_404(id)
    c.is_prospect = True  # Soft delete -> devient prospect
    db.session.commit()
    flash(f'Client "{c.name}" d\u00e9plac\u00e9 vers les prospects.', 'warning')
    return redirect(url_for('commercial.clients_list'))


# ════════════════════════════════════════════════════
# PROSPECTS
# ════════════════════════════════════════════════════

@commercial.route('/prospects')
@login_required
def prospects_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Client.query.filter(Client.is_prospect == True)
    if q:
        query = query.filter(
            or_(
                Client.name.ilike(f'%{q}%'),
                Client.contact.ilike(f'%{q}%'),
                Client.email.ilike(f'%{q}%'),
                Client.phone.ilike(f'%{q}%'),
            )
        )
    query = query.order_by(Client.created_at.desc())
    prospects = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('commercial/prospects_list.html', prospects=prospects, q=q)


@commercial.route('/prospects/<int:id>/convert', methods=['POST'])
@login_required
def prospect_convert(id):
    c = Client.query.get_or_404(id)
    if not c.is_prospect:
        flash('Ce client est d\u00e9j\u00e0 un client actif.', 'warning')
    else:
        c.is_prospect = False
        db.session.commit()
        flash(f'Prospect "{c.name}" converti en client.', 'success')
    return redirect(url_for('commercial.client_detail', id=c.id))


# ════════════════════════════════════════════════════
# PRODUCTS CRUD
# ════════════════════════════════════════════════════

@commercial.route('/products')
@login_required
def products_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Product.query
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

    return render_template('commercial/products_list.html', products=products, q=q)


@commercial.route('/products/new', methods=['GET'])
@login_required
def product_new():
    return render_template('commercial/product_form.html', product=None)


@commercial.route('/products/new', methods=['POST'])
@login_required
def product_create():
    ref = request.form.get('reference', '').strip()
    name = request.form.get('name', '').strip()
    if not ref or not name:
        flash('La r\u00e9f\u00e9rence et le nom sont requis.', 'error')
        return redirect(url_for('commercial.product_new'))

    existing = Product.query.filter_by(reference=ref).first()
    if existing:
        flash(f'La r\u00e9f\u00e9rence "{ref}" existe d\u00e9j\u00e0.', 'error')
        return redirect(url_for('commercial.product_new'))

    try:
        price = Decimal(request.form.get('price', '0'))
    except (ValueError, TypeError):
        price = Decimal('0')
    try:
        stock_qty = Decimal(request.form.get('stock_qty', '0'))
    except (ValueError, TypeError):
        stock_qty = Decimal('0')
    try:
        stock_min = Decimal(request.form.get('stock_min', '0'))
    except (ValueError, TypeError):
        stock_min = Decimal('0')

    p = Product(
        reference=ref,
        name=name,
        category=request.form.get('category', '').strip(),
        unit=request.form.get('unit', 'unit\u00e9').strip(),
        variant=request.form.get('variant', '').strip(),
        price=price,
        stock_qty=stock_qty,
        stock_min=stock_min,
        is_active=True,
    )
    db.session.add(p)
    db.session.commit()
    flash(f'Produit "{p.name}" cr\u00e9\u00e9.', 'success')
    return redirect(url_for('commercial.products_list'))


@commercial.route('/products/<int:id>/edit', methods=['GET'])
@login_required
def product_edit(id):
    p = Product.query.get_or_404(id)
    return render_template('commercial/product_form.html', product=p)


@commercial.route('/products/<int:id>/edit', methods=['POST'])
@login_required
def product_update(id):
    p = Product.query.get_or_404(id)
    ref = request.form.get('reference', '').strip()
    name = request.form.get('name', '').strip()
    if not ref or not name:
        flash('La r\u00e9f\u00e9rence et le nom sont requis.', 'error')
        return redirect(url_for('commercial.product_edit', id=id))

    existing = Product.query.filter(Product.reference == ref, Product.id != id).first()
    if existing:
        flash(f'La r\u00e9f\u00e9rence "{ref}" existe d\u00e9j\u00e0.', 'error')
        return redirect(url_for('commercial.product_edit', id=id))

    try:
        price = Decimal(request.form.get('price', '0'))
    except (ValueError, TypeError):
        price = Decimal('0')
    try:
        stock_qty = Decimal(request.form.get('stock_qty', '0'))
    except (ValueError, TypeError):
        stock_qty = Decimal('0')
    try:
        stock_min = Decimal(request.form.get('stock_min', '0'))
    except (ValueError, TypeError):
        stock_min = Decimal('0')

    p.reference = ref
    p.name = name
    p.category = request.form.get('category', '').strip()
    p.unit = request.form.get('unit', 'unit\u00e9').strip()
    p.variant = request.form.get('variant', '').strip()
    p.price = price
    p.stock_qty = stock_qty
    p.stock_min = stock_min
    db.session.commit()
    flash(f'Produit "{p.name}" mis \u00e0 jour.', 'success')
    return redirect(url_for('commercial.products_list'))


@commercial.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def product_delete(id):
    p = Product.query.get_or_404(id)
    p.is_active = False  # D\u00e9sactivation
    db.session.commit()
    flash(f'Produit "{p.name}" d\u00e9sactiv\u00e9.', 'warning')
    return redirect(url_for('commercial.products_list'))
# ════════════════════════════════════════════════════
# ORDERS CRUD
# ════════════════════════════════════════════════════

@commercial.route('/orders')
@login_required
def orders_list():
    status = request.args.get('status', '').strip()
    q = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)

    per_page = 20
    query = Order.query

    if status:
        query = query.filter(Order.status == status)
    if q:
        query = query.join(Client).filter(
            or_(
                Order.reference.ilike(f'%{q}%'),
                Client.name.ilike(f'%{q}%'),
            )
        )
    if date_from:
        try:
            dt_from = datetime.strptime(date_from + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
            query = query.filter(Order.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(Order.created_at <= dt_to)
        except ValueError:
            pass

    query = query.order_by(Order.created_at.desc())
    orders = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'commercial/orders_list.html',
        orders=orders,
        status=status,
        q=q,
        date_from=date_from,
        date_to=date_to,
        format_currency=_format_currency,
        badge=_badge_html,
    )


@commercial.route('/orders/new', methods=['GET'])
@login_required
def order_new():
    clients = Client.query.filter(Client.is_prospect == False).order_by(Client.name.asc()).all()
    products = Product.query.filter(Product.is_active == True).order_by(Product.name.asc()).all()
    return render_template(
        'commercial/order_form.html',
        order=None,
        clients=clients,
        products=products,
        format_currency=_format_currency,
    )


@commercial.route('/orders/new', methods=['POST'])
@login_required
def order_create():
    client_id = request.form.get('client_id', type=int)
    if not client_id:
        flash('Veuillez selectionner un client.', 'error')
        return redirect(url_for('commercial.order_new'))

    is_devis = request.form.get('is_devis', '0') == '1'
    status = 'devis' if is_devis else 'pending'
    ref = _gen_devis_ref() if is_devis else _gen_order_ref()

    try:
        discount_rate = Decimal(request.form.get('discount_rate', '0'))
    except (ValueError, TypeError):
        discount_rate = Decimal('0')

    order = Order(
        reference=ref,
        client_id=client_id,
        created_by_id=current_user.id,
        status=status,
        delivery_type=request.form.get('delivery_type', 'immediate').strip(),
        delivery_date=request.form.get('delivery_date') if request.form.get('delivery_date') else None,
        delivery_address=request.form.get('delivery_address', '').strip(),
        delivery_city=request.form.get('delivery_city', '').strip(),
        notes_client=request.form.get('notes_client', '').strip(),
        notes_internal=request.form.get('notes_internal', '').strip(),
        discount_rate=discount_rate,
        discount_motif=request.form.get('discount_motif', '').strip(),
    )
    db.session.add(order)
    db.session.flush()

    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    unit_prices = request.form.getlist('unit_price[]')

    total = Decimal('0')
    for i in range(len(product_ids)):
        pid = int(product_ids[i]) if product_ids[i] else 0
        if not pid:
            continue
        qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
        uprice = Decimal(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else Decimal('0')
        line_total = qty * uprice
        oi = OrderItem(
            order_id=order.id,
            product_id=pid,
            quantity=qty,
            unit_price=uprice,
            total=line_total,
        )
        db.session.add(oi)
        total += line_total

    if discount_rate > 0:
        total = total * (Decimal('1') - discount_rate / Decimal('100'))

    order.total = total
    db.session.commit()

    msg = 'Devis cree avec succes.' if is_devis else 'Commande creee avec succes.'
    flash(msg, 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))


@commercial.route('/orders/<int:id>')
@login_required
def order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template(
        'commercial/order_detail.html',
        order=order,
        format_currency=_format_currency,
        badge=_badge_html,
    )


@commercial.route('/orders/<int:id>/edit', methods=['GET'])
@login_required
def order_edit(id):
    order = Order.query.get_or_404(id)
    clients = Client.query.filter(Client.is_prospect == False).order_by(Client.name.asc()).all()
    products = Product.query.filter(Product.is_active == True).order_by(Product.name.asc()).all()
    return render_template(
        'commercial/order_form.html',
        order=order,
        clients=clients,
        products=products,
        format_currency=_format_currency,
    )


@commercial.route('/orders/<int:id>/edit', methods=['POST'])
@login_required
def order_update(id):
    order = Order.query.get_or_404(id)
    if order.status in ('paid', 'delivered', 'cancelled'):
        flash(f'Impossible de modifier une commande {order.status}.', 'error')
        return redirect(url_for('commercial.order_detail', id=id))

    client_id = request.form.get('client_id', type=int)
    if not client_id:
        flash('Veuillez selectionner un client.', 'error')
        return redirect(url_for('commercial.order_edit', id=id))

    try:
        discount_rate = Decimal(request.form.get('discount_rate', '0'))
    except (ValueError, TypeError):
        discount_rate = Decimal('0')

    order.client_id = client_id
    order.delivery_type = request.form.get('delivery_type', 'immediate').strip()
    order.delivery_date = request.form.get('delivery_date') if request.form.get('delivery_date') else None
    order.delivery_address = request.form.get('delivery_address', '').strip()
    order.delivery_city = request.form.get('delivery_city', '').strip()
    order.notes_client = request.form.get('notes_client', '').strip()
    order.notes_internal = request.form.get('notes_internal', '').strip()
    order.discount_rate = discount_rate
    order.discount_motif = request.form.get('discount_motif', '').strip()

    OrderItem.query.filter(OrderItem.order_id == order.id).delete()
    db.session.flush()

    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    unit_prices = request.form.getlist('unit_price[]')

    total = Decimal('0')
    for i in range(len(product_ids)):
        pid = int(product_ids[i]) if product_ids[i] else 0
        if not pid:
            continue
        qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
        uprice = Decimal(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else Decimal('0')
        line_total = qty * uprice
        oi = OrderItem(
            order_id=order.id,
            product_id=pid,
            quantity=qty,
            unit_price=uprice,
            total=line_total,
        )
        db.session.add(oi)
        total += line_total

    if discount_rate > 0:
        total = total * (Decimal('1') - discount_rate / Decimal('100'))

    order.total = total
    db.session.commit()
    flash('Commande mise a jour.', 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))


@commercial.route('/orders/<int:id>/validate', methods=['POST'])
@login_required
def order_validate(id):
    order = Order.query.get_or_404(id)
    if order.status == 'cancelled':
        flash('Impossible de valider une commande annulee.', 'error')
    elif order.status in ('paid', 'delivered'):
        flash('Cette commande est deja finalisee.', 'warning')
    else:
        if order.status == 'devis':
            order.reference = _gen_order_ref()
        order.status = 'pending'
        order.validated_by_id = current_user.id
        db.session.commit()
        flash(f'Commande {order.reference} validee.', 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))

@commercial.route('/orders/<int:id>/cancel', methods=['POST'])
@login_required
def order_cancel(id):
    order = Order.query.get_or_404(id)
    if order.status in ('delivered', 'cancelled'):
        flash('Impossible d\'annuler une commande {}.'.format(order.status), 'error')
    else:
        order.status = 'cancelled'
        db.session.commit()
        flash('Commande {} annulee.'.format(order.reference), 'warning')
    return redirect(url_for('commercial.order_detail', id=order.id))


@commercial.route('/orders/<int:id>/pay', methods=['POST'])
@login_required
def order_pay(id):
    order = Order.query.get_or_404(id)
    if order.status == 'cancelled':
        flash('Impossible de payer une commande annulee.', 'error')
    elif order.status == 'delivered':
        flash('Cette commande est deja livree.', 'warning')
    else:
        try:
            paid_amount = Decimal(request.form.get('paid_amount', '0'))
        except (ValueError, TypeError):
            paid_amount = Decimal('0')
        order.paid_amount = paid_amount if paid_amount > 0 else order.total
        order.paid_at = datetime.now(timezone.utc)
        order.paid_by_id = current_user.id
        order.payment_method = request.form.get('payment_method', '').strip()
        order.status = 'paid'
        db.session.commit()
        flash('Paiement de {} enregistre.'.format(_format_currency(order.paid_amount)), 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))


@commercial.route('/orders/<int:id>/deliver', methods=['POST'])
@login_required
def order_deliver(id):
    order = Order.query.get_or_404(id)
    if order.status in ('cancelled', 'delivered'):
        flash('Action impossible sur une commande {}.'.format(order.status), 'error')
    else:
        order.status = 'delivered'
        order.delivered_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('Commande {} marquee comme livree.'.format(order.reference), 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))


# ════════════════════════════════════════════════════
# DEVIS (Quotes)
# ════════════════════════════════════════════════════

@commercial.route('/devis')
@login_required
def devis_list():
    status = request.args.get('status', '').strip()
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    per_page = 20
    query = Order.query.filter(or_(Order.status == 'devis', Order.status == 'pending'))

    if status:
        query = query.filter(Order.status == status)
    if q:
        query = query.join(Client).filter(
            or_(
                Order.reference.ilike(f'%{q}%'),
                Client.name.ilike(f'%{q}%'),
            )
        )

    query = query.order_by(Order.created_at.desc())
    devis = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'commercial/devis_list.html',
        devis=devis,
        status=status,
        q=q,
        format_currency=_format_currency,
        badge=_badge_html,
    )


@commercial.route('/devis/<int:id>/convert-order', methods=['POST'])
@login_required
def devis_convert_order(id):
    order = Order.query.get_or_404(id)
    if order.status not in ('devis', 'pending'):
        flash('Seulement les devis ou commandes en attente peuvent etre convertis.', 'error')
    else:
        order.reference = _gen_order_ref()
        order.status = 'pending'
        order.validated_by_id = current_user.id
        db.session.commit()
        flash('Devis {} converti en commande.'.format(order.reference), 'success')
    return redirect(url_for('commercial.order_detail', id=order.id))


# ════════════════════════════════════════════════════
# HTMX Endpoints — Product line row for dynamic order forms
# ════════════════════════════════════════════════════

@commercial.route('/order/product-line')
@login_required
def order_product_line():
    """Returns an empty <tr> for a product line in the order form."""
    return '''<tr class="order-line">
    <td>
        <select name="product_id[]" class="form-input product-select" required>
            <option value="">-- Selectionner --</option>
        </select>
    </td>
    <td><input type="number" name="quantity[]" class="form-input" step="0.01" min="0.01" value="1"></td>
    <td><input type="number" name="unit_price[]" class="form-input unit-price" step="0.01" min="0"></td>
    <td class="line-total">0 FCFA</td>
    <td><button type="button" class="btn btn-danger btn-sm" onclick="this.closest('tr').remove(); recalcTotal();">X</button></td>
</tr>'''


@commercial.route('/order/products-json')
@login_required
def order_products_json():
    products = Product.query.filter(Product.is_active == True).order_by(Product.name.asc()).all()
    data = [{
        'id': p.id,
        'name': p.name,
        'reference': p.reference,
        'price': float(p.price) if p.price else 0,
        'stock': float(p.stock_qty) if p.stock_qty else 0,
        'unit': p.unit or 'unite',
    } for p in products]
    return jsonify(data)
