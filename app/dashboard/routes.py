from datetime import datetime, timezone
from flask import render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.dashboard import dashboard
from app.core.models import Order, OrderItem, Client


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _stats_data():
    """Calcule les 4 indicateurs du dashboard : CA engagé, encaissé, commandes, alertes."""
    now = datetime.now(timezone.utc)

    ca_engage = db.session.query(
        func.coalesce(func.sum(Order.total), 0)
    ).filter(Order.status != 'cancelled').scalar()

    ca_encaisse = db.session.query(
        func.coalesce(func.sum(Order.paid_amount), 0)
    ).filter(Order.status.in_(['paid', 'delivered'])).scalar()

    total_orders = Order.query.filter(Order.status != 'cancelled').count()
    pending_orders = Order.query.filter(Order.status == 'pending').count()

    overdue_deliveries = Order.query.filter(
        Order.delivery_type == 'scheduled',
        Order.delivery_date < now,
        Order.status != 'delivered',
        Order.status != 'cancelled'
    ).count()

    return {
        'ca_engage': ca_engage,
        'ca_encaisse': ca_encaisse,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'overdue_deliveries': overdue_deliveries,
    }


def _recent_orders(limit=5):
    return Order.query.filter(
        Order.status != 'cancelled'
    ).order_by(Order.created_at.desc()).limit(limit).all()


def _recent_orders_all():
    """Toutes les commandes récentes (hors annulées), pour activité."""
    return Order.query.filter(
        Order.status != 'cancelled'
    ).order_by(Order.created_at.desc()).limit(10).all()


def _format_currency(amount):
    try:
        return f"{amount:,.0f} FCFA".replace(',', ' ')
    except (TypeError, ValueError):
        return "0 FCFA"


def _badge_html(status):
    """Retourne le badge Shadcn/ui selon le statut."""
    badges = {
        'pending': ('badge badge-warning', '🟠 En attente'),
        'paid': ('badge badge-success', '✅ Payée'),
        'delivering': ('badge badge-info', '🚚 En livraison'),
        'delivered': ('badge badge-primary', '📦 Livrée'),
        'cancelled': ('badge badge-destructive', '❌ Annulée'),
    }
    cls, label = badges.get(status, ('badge badge-default', status))
    return f'<span class="{cls}">{label}</span>'


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@dashboard.route('/')
@login_required
def index():
    """Page principale du tableau de bord."""
    stats = _stats_data()
    recent = _recent_orders()

    return render_template(
        'dashboard.html',
        current_user=current_user,
        stats=stats,
        recent_orders=recent,
        format_currency=_format_currency,
        today=datetime.now,
    )


@dashboard.route('/dashboard/stats')
@login_required
def stats():
    """Endpoint HTMX — retourne les 4 cartes de statistiques (Shadcn/ui style)."""
    s = _stats_data()

    cards = f"""
    <div class="stat-card">
        <div class="stat-accent-bar" style="background:#2D6A2E;"></div>
        <div class="stat-header">
            <span class="stat-label">CA Engagé</span>
            <span class="stat-icon-wrapper primary">💰</span>
        </div>
        <div class="stat-value" style="color:#2D6A2E;">{_format_currency(s['ca_engage'])}</div>
        <div class="stat-footer">
            <span>Chiffre d'affaires total engagé</span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-accent-bar" style="background:#22C55E;"></div>
        <div class="stat-header">
            <span class="stat-label">CA Encaissé</span>
            <span class="stat-icon-wrapper success">💳</span>
        </div>
        <div class="stat-value" style="color:#15803D;">{_format_currency(s['ca_encaisse'])}</div>
        <div class="stat-footer">
            <span>{'0' if s['ca_engage'] == 0 else f"{s['ca_encaisse'] / s['ca_engage'] * 100:.1f}%"}</span>
            <span class="stat-trend-up">du CA engagé</span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-accent-bar" style="background:#937C33;"></div>
        <div class="stat-header">
            <span class="stat-label">Commandes</span>
            <span class="stat-icon-wrapper dore">📋</span>
        </div>
        <div class="stat-value" style="color:#937C33;">{s['total_orders']}</div>
        <div class="stat-footer">
            <span>{s['pending_orders']} en attente</span>
            { '<span class="stat-trend-up">•</span>' if s['pending_orders'] > 0 else '' }
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-accent-bar" style="background:#F59E0B;"></div>
        <div class="stat-header">
            <span class="stat-label">Alertes</span>
            <span class="stat-icon-wrapper warning">🚨</span>
        </div>
        <div class="stat-value" style="color:#B45309;">{s['overdue_deliveries']}</div>
        <div class="stat-footer">
            <span>{s['overdue_deliveries']} livraison(s) en retard</span>
            { '<span class="stat-trend-up">⚠️</span>' if s['overdue_deliveries'] > 0 else '' }
        </div>
    </div>
    """
    return cards


@dashboard.route('/dashboard/recent')
@login_required
def recent_orders():
    """Endpoint HTMX — retourne les lignes <tr> des 5 dernières commandes."""
    recent = _recent_orders()

    rows = ''
    for order in recent:
        client_name = order.client.name if order.client else '—'
        badge = _badge_html(order.status)
        rows += f"""<tr>
            <td><a href="#" class="cell-link">{order.reference}</a></td>
            <td>{client_name}</td>
            <td style="font-weight:500;">{_format_currency(order.total)}</td>
            <td>{badge}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--muted-foreground);">Aucune commande récente.</td></tr>'

    return rows


@dashboard.route('/dashboard/activity')
@login_required
def recent_activity():
    """Endpoint HTMX — retourne la liste des activités récentes."""
    recent = _recent_orders_all()

    items = ''
    colors = {
        'pending': '#937C33',
        'paid': '#22C55E',
        'delivering': '#3B82F6',
        'delivered': '#2D6A2E',
        'cancelled': '#EF4444',
    }
    icons = {
        'pending': '🆕',
        'paid': '💳',
        'delivering': '🚚',
        'delivered': '📦',
        'cancelled': '❌',
    }

    for order in recent:
        color = colors.get(order.status, '#6B7280')
        icon = icons.get(order.status, '📋')
        client_name = order.client.name if order.client else 'N/C'
        created = order.created_at.strftime('%d/%m/%Y %H:%M') if order.created_at else ''
        items += f"""<li class="activity-item">
            <span class="activity-dot" style="background:{color};"></span>
            <span class="activity-content">
                <strong>{icon} {order.reference}</strong> — {client_name}
                <span style="display:block;font-size:0.75rem;color:var(--muted-foreground);margin-top:0.15rem;">
                    {_format_currency(order.total)}
                </span>
            </span>
            <span class="activity-time">{created}</span>
        </li>"""

    if not items:
        items = '<li class="activity-item" style="justify-content:center;padding:2rem;color:var(--muted-foreground);">Aucune activité récente.</li>'

    return items