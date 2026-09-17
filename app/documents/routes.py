"""Routes for PDF document generation using WeasyPrint."""

from datetime import datetime, timezone
from flask import render_template, send_file, abort
from flask_login import login_required
from weasyprint import HTML
import io

from app import db
from app.documents import documents
from app.core.models import Order, Company, OrderItem


def _generate_pdf(template_name, order_id, doc_type_label):
    """Helper: load order + company, render template, return PDF."""
    order = Order.query.options(
        db.joinedload(Order.client),
        db.joinedload(Order.items).joinedload(OrderItem.product),
        db.joinedload(Order.created_by),
        db.joinedload(Order.validated_by),
    ).get(order_id)

    if not order:
        abort(404, description=f"Commande #{order_id} introuvable.")

    company = Company.query.first()

    html_string = render_template(
        template_name,
        order=order,
        company=company,
        doc_type=doc_type_label,
        now=datetime.now(timezone.utc),
    )

    pdf_bytes = HTML(string=html_string).write_pdf()

    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)

    filename = f"{order.reference or 'document'}_{doc_type_label.replace(' ', '_')}.pdf"

    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=filename,
    )


@documents.route('/devis/<int:order_id>')
@login_required
def devis_pdf(order_id):
    """Generate PDF for a devis / proforma invoice."""
    return _generate_pdf('documents/invoice.html', order_id, 'DEVIS')


@documents.route('/facture/<int:order_id>')
@login_required
def facture_pdf(order_id):
    """Generate PDF for an invoice (facture)."""
    return _generate_pdf('documents/invoice.html', order_id, 'FACTURE')


@documents.route('/bon-livraison/<int:order_id>')
@login_required
def bon_livraison_pdf(order_id):
    """Generate PDF for a delivery note (bon de livraison)."""
    return _generate_pdf('documents/delivery_note.html', order_id, 'BON DE LIVRAISON')


@documents.route('/bon-commande/<int:order_id>')
@login_required
def bon_commande_pdf(order_id):
    """Generate PDF for a purchase order (bon de commande)."""
    return _generate_pdf('documents/purchase_order.html', order_id, 'BON DE COMMANDE')


@documents.route('/avoir/<int:order_id>')
@login_required
def avoir_pdf(order_id):
    """Generate PDF for a credit note (note d'avoir)."""
    return _generate_pdf('documents/credit_note.html', order_id, 'NOTE D\'AVOIR')