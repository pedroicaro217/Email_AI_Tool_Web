import click
from . import db
from .models import User

def register(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.argument("password")
    def create_admin(username, email, password):
        """
        Comando para criar um novo usuário Admin via terminal.
        Uso: flask create-admin [username] [email] [senha]
        """
        # Verifica se já existe
        if db.session.query(User).filter_by(email=email).first():
            print(f"Erro: O e-mail {email} já está cadastrado.")
            return
        
        if db.session.query(User).filter_by(username=username).first():
            print(f"Erro: O usuário {username} já existe.")
            return

        # Cria o usuário
        try:
            user = User(username=username, email=email, role='admin')
            user.set_password(password) # Criptografa a senha
            db.session.add(user)
            db.session.commit()
            print(f"✅ Sucesso! Usuário Admin '{username}' criado.")
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")