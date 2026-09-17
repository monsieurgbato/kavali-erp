from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config
from app.utils.email import init_mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    init_mail(app)
    
    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.commercial import commercial as commercial_bp
    app.register_blueprint(commercial_bp, url_prefix='/commercial')
    
    from app.dashboard import dashboard as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    from app.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.rh import rh as rh_bp
    app.register_blueprint(rh_bp, url_prefix='/rh')
    
    from app.logistique import logistique as logistique_bp
    app.register_blueprint(logistique_bp, url_prefix='/logistique')
    
    from app.fleet import fleet as fleet_bp
    app.register_blueprint(fleet_bp, url_prefix='/fleet')
    
    from app.documents import documents as documents_bp
    app.register_blueprint(documents_bp, url_prefix='/documents')
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html', error=e), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', error=e), 403
    
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server error: {e}")
        return render_template('errors/500.html'), 500
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.core.models import User
    return User.query.get(int(user_id))