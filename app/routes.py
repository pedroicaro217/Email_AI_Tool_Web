from flask import (
    Blueprint, render_template, request, flash, 
    redirect, url_for, current_app, abort
)
from app import db
from app.models import Settings, Campaign, Recipient, User
from app import core_logic # <-- Importa nosso motor
from flask_login import login_required, current_user
import os
import secrets # <-- Para gerar nomes de arquivo seguros
import redis
from rq import Queue

main_bp = Blueprint('main', __name__)

def get_settings_dict():
    """Função utilitária para pegar as configurações do DB."""
    settings_from_db = Settings.query.all()
    return {setting.key: setting.value for setting in settings_from_db}

@main_bp.route('/')
@login_required
def index():
    """
    Rota principal (Homepage).
    Redireciona para o Histórico.
    """
    return redirect(url_for('main.history'))

@main_bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    """Rota do Menu do Desenvolvedor (Fase 3)."""
    if request.method == 'POST':
        keys = ['API_KEY', 'COMPANY_NAME', 'LOGO_URL', 'SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS']
        for key in keys:
            value_from_form = request.form.get(key)
            setting_obj = db.session.query(Settings).filter_by(key=key).first()
            if setting_obj:
                setting_obj.value = value_from_form
            else:
                setting_obj = Settings(key=key, value=value_from_form)
                db.session.add(setting_obj)
        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('main.admin'))

    settings_dict = get_settings_dict()
    return render_template('admin.html', settings=settings_dict)

@main_bp.route('/history')
@login_required
def history():
    """
    Página principal (Dashboard) - Mostra todas as campanhas.
    """
    # Busca campanhas do DB, da mais nova para a mais antiga
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('history.html', campaigns=campaigns)

@main_bp.route('/campaign/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """
    Mostra os detalhes de uma campanha específica (status de cada e-mail).
    """
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign:
        flash('Campanha não encontrada.', 'error')
        return redirect(url_for('main.history'))

    return render_template('campaign_detail.html', campaign=campaign)


# --- ROTAS DA FASE 4 ---

@main_bp.route('/campaign/new')
@login_required
def new_campaign():
    """
    Mostra o formulário inicial para criar uma nova campanha.
    (ATUALIZADO: Agora também passa o 'csv_filename')
    """
    # Pega os dados da URL (se existirem)
    subject_val = request.args.get('subject', '')
    theme_val = request.args.get('theme', '')
    csv_filename_val = request.args.get('csv_filename', '') 
    cta_url_val = request.args.get('cta_url', '') # <-- NOVO

    # Passa os valores para o template
    return render_template('new_campaign.html',
                           subject=subject_val,
                           theme=theme_val,
                           csv_filename=csv_filename_val, 
                           cta_url=cta_url_val) # <-- NOVO


@main_bp.route('/campaign/generate_preview', methods=['POST'])
@login_required
def generate_preview():
    """
    Recebe o formulário (Assunto, Tema, CSV).
    (ATUALIZADO: Lógica inteligente de arquivo + Coleta de Configurações)
    """
    try:
        # 1. Pega os dados do formulário
        subject = request.form.get('subject')
        theme = request.form.get('theme')
        cta_url = request.form.get('cta_url') # <-- Pega o CTA do form
        new_csv_file = request.files.get('leads_csv')
        existing_csv_filename = request.form.get('existing_csv_filename')

        if not all([subject, theme, cta_url]): # <-- Valida o CTA
            flash('Assunto, Tema e URL do CTA são obrigatórios.', 'error')
            return redirect(url_for('main.new_campaign'))

        # --- Lógica de Arquitetura do CSV ---
        csv_path = None
        csv_filename_to_use = None
        upload_folder = os.path.join(current_app.instance_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        if new_csv_file and new_csv_file.filename != '':
            print("[Roteador] Novo CSV detectado. Salvando...")
            random_hex = secrets.token_hex(8)
            _, f_ext = os.path.splitext(new_csv_file.filename)
            csv_filename_to_use = random_hex + f_ext
            csv_path = os.path.join(upload_folder, csv_filename_to_use)
            new_csv_file.save(csv_path)
        
        elif existing_csv_filename:
            print(f"[Roteador] Reutilizando CSV existente: {existing_csv_filename}")
            csv_filename_to_use = existing_csv_filename
            csv_path = os.path.join(upload_folder, csv_filename_to_use)
            
            if not os.path.exists(csv_path):
                flash(f'Erro: O arquivo CSV salvo ({existing_csv_filename}) não foi encontrado. Por favor, envie-o novamente.', 'error')
                return redirect(url_for('main.new_campaign', subject=subject, theme=theme, cta_url=cta_url))
        else:
            flash('Você deve enviar um arquivo de leads (.csv).', 'error')
            return redirect(url_for('main.new_campaign', subject=subject, theme=theme, cta_url=cta_url))
        
        # --- Fim da Lógica do CSV ---

        # 3. Carrega TODAS as configurações do DB
        settings = get_settings_dict()
        api_key = settings.get('API_KEY')
        company_name = settings.get('COMPANY_NAME') # <-- Pega o Nome do DB
        logo_url = settings.get('LOGO_URL')     # <-- Pega a Logo do DB
        
        if not api_key or not company_name: # <-- Valida o Nome
            flash('Chave da API e Nome da Empresa não configurados no Menu Admin.', 'error')
            return redirect(url_for('main.new_campaign'))

        # 4. Chama nosso "motor" (core_logic) para gerar o HTML
        #    (ESTA É A LINHA QUE CORRIGE O ERRO)
        html_content = core_logic.generate_ai_html(
            api_key=api_key,
            email_theme=theme,
            cta_url=cta_url,
            company_name=company_name,
            logo_url=logo_url
        )
        
        if not html_content:
            flash('Erro ao gerar HTML pela API (Timeout ou Erro 504). Tente novamente.', 'error')
            return redirect(url_for('main.new_campaign'))
        
        # 5. Sucesso! Renderiza a página novamente, passando os dados
        return render_template('new_campaign.html',
                               html_preview=html_content,
                               subject=subject,
                               theme=theme,
                               cta_url=cta_url, # <-- Passa o CTA de volta
                               csv_filename=csv_filename_to_use)

    except Exception as e:
        # O erro que você viu foi pego aqui
        print(f"Erro inesperado em generate_preview: {e}") # Adiciona um log no console
        flash(f'Ocorreu um erro inesperado: {e}', 'error')
        return redirect(url_for('main.new_campaign'))

@main_bp.route('/campaign/send', methods=['POST'])
@login_required
def send_campaign():
    """
    Recebe o formulário "APROVAR E ENVIAR".
    (ATUALIZADO: Agora salva no DB e adiciona a tarefa na fila do RQ)
    """
    try:
        # 1. Pega os dados do formulário oculto
        subject = request.form.get('subject')
        theme = request.form.get('theme')
        cta_url = request.form.get('cta_url') # <-- NOVO
        csv_filename = request.form.get('csv_filename')
        html_content = request.form.get('html_content')

        # 2. Salva a nova campanha no Banco de Dados
        new_camp = Campaign(
            subject=subject,
            theme=theme,
            cta_url=cta_url, # <-- NOVO
            generated_html=html_content,
            status='Na Fila', # O Worker mudará isso
            user=current_user
        )
        db.session.add(new_camp)
        
        # 3. Lê o CSV (que já está salvo) e cria os Recipientes
        upload_folder = os.path.join(current_app.instance_path, 'uploads')
        csv_path = os.path.join(upload_folder, csv_filename)
        
        leads_df = core_logic.get_leads(csv_path)
        
        if leads_df is None or leads_df.empty:
            flash('Erro ao ler o arquivo CSV salvo ou arquivo vazio.', 'error')
            return redirect(url_for('main.new_campaign'))

        for index, row in leads_df.iterrows():
            recipient = Recipient(
                nome=row['nome'],
                email=row['email'],
                campaign=new_camp # Vincula o destinatário à campanha
            )
            db.session.add(recipient)

        # 4. Confirma tudo no DB (para que a campanha e os leads tenham IDs)
        db.session.commit()

        # --- NOVA ARQUITETURA DE FILA (RQ) ---
        # 5. Conecta ao Redis e coloca a tarefa na fila
        try:
            redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
            conn = redis.from_url(redis_url)
            q = Queue(connection=conn)
            
            # Adiciona a tarefa na fila
            # Passa apenas o ID da campanha. A tarefa buscará os detalhes no DB.
            q.enqueue('worker.run_campaign_task', new_camp.id)
            
            print(f"[Flask] Campanha ID {new_camp.id} adicionada à fila.")

        except Exception as e:
            # Se o Redis estiver offline
            # --- CORREÇÃO DE ARQUITETURA (Zumbi) ---
            print(f"[Flask] Erro Crítico no Redis: {e}")
            
            new_camp.status = 'Erro de Sistema (Fila)'
            for r in new_camp.recipients:
                r.status = 'Não Enviado (Erro Fila)'
            
            db.session.commit() # Salva o status de erro
            
            flash(f'Campanha salva, mas NÃO enviada. Erro na fila: {e}', 'error')
            return redirect(url_for('main.history'))
        # --- FIM DA LÓGICA DE FILA ---

        flash(f'Campanha aprovada e adicionada à fila! ({len(leads_df)} e-mails)', 'success')
        # (Na Fase 6, vamos redirecionar para a página de /historico)
        return redirect(url_for('main.history')) # Redireciona para o Histórico

    except Exception as e:
        db.session.rollback() # Desfaz qualquer mudança no DB em caso de erro geral
        print(f"[Flask] Erro Geral: {e}")
        flash(f'Erro ao criar campanha: {e}', 'error')
        return redirect(url_for('main.new_campaign'))

# --- ROTAS DE GESTÃO DE USUÁRIOS (Fase 6) ---

@main_bp.route('/users')
@login_required
def manage_users():
    # Segurança: Só admin pode ver
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.history'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@main_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    if current_user.role != 'admin':
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.history'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Validação simples
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Usuário ou E-mail já cadastrado.', 'error')
            return redirect(url_for('main.new_user'))
        
        try:
            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'Usuário {username} criado com sucesso!', 'success')
            return redirect(url_for('main.manage_users'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {e}', 'error')

    return render_template('new_user.html')

@main_bp.route('/users/<int:user_id>/toggle')
@login_required
def toggle_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('main.history'))
    if user_id == current_user.id: return redirect(url_for('main.manage_users')) # Não pode se bloquear

    user = db.session.get(User, user_id)
    if user:
        user.is_active_user = not user.is_active_user # Inverte o status
        db.session.commit()
        status = "Ativado" if user.is_active_user else "Bloqueado"
        flash(f'Usuário {user.username} foi {status}.', 'success')
    
    return redirect(url_for('main.manage_users'))

@main_bp.route('/users/<int:user_id>/delete')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('main.history'))
    if user_id == current_user.id: return redirect(url_for('main.manage_users'))

    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {user.username} excluído.', 'success')
    
    return redirect(url_for('main.manage_users'))