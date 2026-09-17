"""Utilitaires email pour KAVALI ERP."""
from flask import current_app, render_template
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

mail = Mail()

def init_mail(app):
    """Initialise Flask-Mail avec l'app Flask."""
    mail.init_app(app)

def get_token_serializer():
    """Crée un serializer de token avec la secret key de l'app."""
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='password-reset-salt'
    )

def generate_reset_token(email):
    """Génère un token de réinitialisation valide 1 heure."""
    s = get_token_serializer()
    return s.dumps(email)

def verify_reset_token(token, max_age=3600):
    """Vérifie un token et retourne l'email s'il est valide, None sinon."""
    s = get_token_serializer()
    try:
        email = s.loads(token, max_age=max_age)
        return email
    except Exception:
        return None

def send_reset_email(email, token):
    """Envoie l'email de réinitialisation de mot de passe."""
    # Détection de l'hôte pour le lien de reset
    app = current_app._get_current_object()
    host = app.config.get('RESET_HOST', 'http://192.168.100.219:5050')
    reset_url = f"{host}/auth/reset-password/{token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; background: #F5F2ED; padding: 2rem; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .header {{ background: linear-gradient(135deg, #0A3809, #1a5f19); padding: 2rem; text-align: center; }}
            .header img {{ height: 44px; filter: brightness(0) invert(1); }}
            .body {{ padding: 2rem; }}
            .body h2 {{ color: #0A3809; font-size: 1.3rem; margin-bottom: 0.5rem; }}
            .body p {{ color: #6b7280; line-height: 1.6; font-size: 0.9rem; }}
            .btn {{ display: inline-block; background: linear-gradient(135deg, #0A3809, #1a5f19); color: #fff; text-decoration: none; padding: 0.8rem 2rem; border-radius: 10px; font-weight: 600; margin: 1.5rem 0; }}
            .footer {{ padding: 1.5rem 2rem; border-top: 1px solid #e5e7eb; text-align: center; font-size: 0.75rem; color: #9ca3af; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://img.icons8.com/ios-filled/50/ffffff/lock.png" alt="🔒">
            </div>
            <div class="body">
                <h2>🔑 Réinitialisation de mot de passe</h2>
                <p>Vous avez demandé la réinitialisation de votre mot de passe KAVALI ERP.</p>
                <p>Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe :</p>
                <div style="text-align: center;">
                    <a href="{reset_url}" class="btn">Réinitialiser mon mot de passe</a>
                </div>
                <p style="margin-top:1rem;">Ce lien expire dans <strong>1 heure</strong>.</p>
                <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
            </div>
            <div class="footer">
                KAVALI ERP — Abidjan, Côte d'Ivoire
            </div>
        </div>
    </body>
    </html>
    """

    msg = Message(
        subject="🔑 KAVALI ERP — Réinitialisation de votre mot de passe",
        recipients=[email],
        html=html
    )
    mail.send(msg)