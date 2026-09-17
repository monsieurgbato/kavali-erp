from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.auth import auth
from app.core.models import User
from app.utils.email import generate_reset_token, verify_reset_token, send_reset_email


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion — GET affiche le formulaire, POST authentifie."""
    # Si déjà connecté, rediriger vers le dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    error = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Recherche de l'utilisateur par email
        user = User.query.filter_by(email=email).first()

        if user is None:
            error = "Email ou mot de passe incorrect."
        elif not user.is_active:
            error = "Ce compte est désactivé. Contactez l'administrateur."
        elif user.is_suspended:
            error = "Ce compte est suspendu. Contactez l'administrateur."
        elif not check_password_hash(user.password_hash, password):
            error = "Email ou mot de passe incorrect."
        else:
            # Connexion réussie
            login_user(user)
            user.last_login = db.func.now()
            db.session.commit()
            flash("Connexion réussie. Bienvenue !", 'success')
            return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html', error=error)


@auth.route('/logout')
@login_required
def logout():
    """Déconnexion."""
    logout_user()
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('auth.login'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Page de réinitialisation de mot de passe — envoie un email avec lien."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    sent = False
    error = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        # Toujours dire "envoyé" même si l'email n'existe pas (sécurité)
        sent = True

        if user:
            if not user.is_active or user.is_suspended:
                # Ne pas informer que le compte est inactif (sécurité)
                pass
            else:
                try:
                    token = generate_reset_token(email)
                    send_reset_email(email, token)
                    print(f"[EMAIL SENT] Reset password link sent to {email}")
                except Exception as e:
                    error = "Erreur technique lors de l'envoi. Veuillez réessayer plus tard."
                    print(f"[EMAIL ERROR] Failed to send to {email}: {e}")
                    sent = False

    return render_template('auth/forgot_password.html', sent=sent, error=error)


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Page de réinitialisation avec token — permet de définir un nouveau mot de passe."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    # Vérifier le token
    email = verify_reset_token(token)
    if email is None:
        return render_template('auth/reset_password.html', invalid=True, expired=False)

    error = None
    success = False

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if len(password) < 8:
            error = "Le mot de passe doit contenir au moins 8 caractères."
        elif password != confirm:
            error = "Les mots de passe ne correspondent pas."
        else:
            user = User.query.filter_by(email=email).first()
            if user is None:
                error = "Ce compte n'existe plus."
            elif not user.is_active or user.is_suspended:
                error = "Ce compte n'est pas actif. Contactez l'administrateur."
            else:
                user.password_hash = generate_password_hash(password)
                db.session.commit()
                flash("✅ Mot de passe réinitialisé avec succès ! Connectez-vous.", 'success')
                return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', invalid=False, expired=False,
                           error=error, token=token)


@auth.route('/me')
@login_required
def me():
    """Retourne les informations de l'utilisateur courant au format JSON."""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'phone': current_user.phone,
        'role': current_user.role.name if current_user.role else None,
        'service': current_user.service,
        'position': current_user.position,
        'company': current_user.company.name if current_user.company else None,
        'is_active': current_user.is_active,
    })