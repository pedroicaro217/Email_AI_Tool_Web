import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import pytz
from datetime import datetime
from flask_login import LoginManager # <-- NOVO

# --- Caminho raiz do PROJETO ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Carrega o .env ANTES de tudo
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# Inicializa os "plugins"
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager() # <-- NOVO
login.login_view = 'auth.login' # <-- Define qual é a rota de login
login.login_message = 'Por favor, faça login para acessar esta página.'

def create_app():
    """Fábrica de Aplicação"""
    
    app = Flask(__name__, 
                instance_relative_config=True,
                template_folder=os.path.join(BASE_DIR, 'templates'))

    # --- Configuração ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma-chave-secreta-padrao-mude-isso')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379')

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass 

    # --- Inicializa Plugins ---
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app) # <-- NOVO

    # --- Filtro de Data (DEFINIDO DENTRO DA FACTORY) ---
    def format_datetime(value):
        if value is None:
            return ""
        local_tz = pytz.timezone('America/Sao_Paulo')
        utc_dt = value.replace(tzinfo=pytz.utc)
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime('%d/%m/%Y %H:%M')

    # Registra o filtro
    app.jinja_env.filters['datetimeformat'] = format_datetime

    # --- Registra Blueprints ---
    with app.app_context():
        from . import models 
        from . import routes
        from . import auth
        
        # (Futuro: Aqui registraremos o blueprint de auth)
        app.register_blueprint(routes.main_bp)
        app.register_blueprint(auth.auth_bp)

        from . import cli
        cli.register(app)

        return app

# --- NOVO: User Loader (FORA DA FACTORY) ---
@login.user_loader
def load_user(id):
    from .models import User
    return db.session.get(User, int(id))