from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from urllib.parse import urlsplit
from app import db

# Definimos um novo "grupo" de rotas chamado 'auth'
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, manda para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.history'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Busca o usuário no banco
        # (Aqui permitimos logar com username OU email, para ser flexível)
        user = User.query.filter((User.username == username) | (User.email == username)).first()

        # Verifica se o usuário existe e se a senha bate
        if user is None or not user.check_password(password):
            flash('Usuário ou senha inválidos.', 'error')
            return redirect(url_for('auth.login'))
        
        # Verifica se está ativo (Bloqueio)
        if not user.is_active:
            flash('Esta conta foi desativada pelo administrador.', 'error')
            return redirect(url_for('auth.login'))

        # TUDO CERTO: Loga o usuário!
        login_user(user)
        
        # Redirecionamento inteligente:
        # Se o usuário tentou acessar /admin sem estar logado, o Flask guardou
        # essa intenção em 'next'. Mandamos ele para lá agora.
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.history')
            
        return redirect(next_page)

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')

        # 1. Verifica se a senha atual está correta
        if not current_user.check_password(current_pw):
            flash('A senha atual está incorreta.', 'error')
            return redirect(url_for('auth.change_password'))

        # 2. Verifica se a nova senha bate com a confirmação
        if new_pw != confirm_pw:
            flash('As novas senhas não conferem.', 'error')
            return redirect(url_for('auth.change_password'))
        
        # 3. Verifica se a nova senha não é vazia
        if not new_pw or len(new_pw) < 6:
             flash('A nova senha deve ter pelo menos 6 caracteres.', 'error')
             return redirect(url_for('auth.change_password'))

        # 4. Salva a nova senha (Criptografada)
        try:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Sua senha foi alterada com sucesso!', 'success')
            return redirect(url_for('main.history'))
        except Exception as e:
            flash(f'Erro ao salvar senha: {e}', 'error')

    return render_template('change_password.html')