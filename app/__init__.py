import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

# --- NOVO: Definir o caminho raiz do PROJETO ---
# __file__ aponta para /app/__init__.py
# os.path.dirname(__file__) aponta para /app
# O '..' sobe um nível para a raiz do projeto /email_marketer_web
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Carrega o .env ANTES de tudo
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# Inicializa os "plugins" (vazios por enquanto)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """
    Fábrica de Aplicação (Application Factory)
    Este é o padrão de arquitetura para criar o app Flask.
    """
    
    # --- ATUALIZADO: Apontar para o 'templates' na raiz ---
    app = Flask(__name__, 
                instance_relative_config=True,
                template_folder=os.path.join(BASE_DIR, 'templates')) # <--- ESTA É A CORREÇÃO

    # --- Configuração ---
    
    # 1. Chave Secreta (lendo do .env)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma-chave-secreta-padrao-mude-isso')
    
    # 2. Configuração do Banco de Dados SQLite
    # Ele criará o 'database.db' na pasta /instance/
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 3. Garante que a pasta 'instance' exista
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # A pasta já existe

    # --- Inicializa os Plugins com o App ---
    db.init_app(app)
    migrate.init_app(app, db)

    # --- Registra os "Blueprints" (Nossas páginas/rotas) ---
    with app.app_context():
        # Importa os modelos para que o 'migrate' os veja
        from . import models 
        
        # Importa e registra as rotas
        from . import routes
        app.register_blueprint(routes.main_bp)

        return app