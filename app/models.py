from app import db
import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Settings(db.Model):
    """
    Tabela para armazenar as configurações do admin (Menu Desenvolvedor).
    Vamos armazenar como pares chave-valor.
    """
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<Setting {self.key}>'

class Campaign(db.Model):
    """
    Tabela para o Histórico de Campanhas.
    """
    __tablename__ = 'campaign'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    theme = db.Column(db.String(500), nullable=False)
    # --- NOVA LINHA AQUI ---
    # nullable=False significa que é um campo obrigatório
    cta_url = db.Column(db.String(500), nullable=False, default='https://example.com')
    # --- FIM DA NOVA LINHA ---
    generated_html = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(100), nullable=False, default='Pendente') # Ex: Pendente, Gerando, Enviando, Concluído
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='campaigns')
    generated_html = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # --- NOVO: ID da tarefa no Redis (para poder cancelar depois) ---
    job_id = db.Column(db.String(100), nullable=True)

    # Guarda a data agendada (pode ser nula se for envio imediato)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamento: Uma campanha tem muitos destinatários
    recipients = db.relationship('Recipient', backref='campaign', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Campaign {self.subject}>'

class Recipient(db.Model):
    """
    Tabela para armazenar cada destinatário de uma campanha.
    """
    __tablename__ = 'recipient'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(100), nullable=False, default='Na Fila') # Ex: Na Fila, Enviado, Falhou

    def __repr__(self):
        return f'<Recipient {self.email} (Campaign {self.campaign_id})>'

class User(UserMixin, db.Model):
    """
    Tabela de Usuários com suporte a Login e Hash de Senha.
    """
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # Controle de Acesso (Role Based Access Control - RBAC)
    role = db.Column(db.String(20), default='editor') # 'admin' ou 'editor'
    is_active_user = db.Column(db.Boolean, default=True) # Para bloqueio

    def set_password(self, password):
        """Cria o hash da senha (criptografia)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha bate com o hash salvo."""
        return check_password_hash(self.password_hash, password)
    
    # O Flask-Login exige essa propriedade para saber se pode logar
    @property
    def is_active(self):
        return self.is_active_user

    def __repr__(self):
        return f'<User {self.username}>'