from app import db
import datetime

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