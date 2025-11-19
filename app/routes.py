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
from datetime import datetime
import pytz
from rq.job import Job
from rq.exceptions import NoSuchJobError


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
    Lida com envio imediato OU agendado.
    """
    try:
        # 1. Pega os dados
        subject = request.form.get('subject')
        theme = request.form.get('theme')
        cta_url = request.form.get('cta_url')
        csv_filename = request.form.get('csv_filename')
        html_content = request.form.get('html_content')
        
        schedule_time_str = request.form.get('schedule_time')
        
        scheduled_datetime_utc = None
        status_inicial = 'Na Fila'

        # --- LÓGICA DE TIMEZONE ---
        if schedule_time_str:
            local_dt = datetime.strptime(schedule_time_str, '%Y-%m-%dT%H:%M')
            local_tz = pytz.timezone('America/Sao_Paulo')
            local_dt = local_tz.localize(local_dt)
            scheduled_datetime_utc = local_dt.astimezone(pytz.utc)
            status_inicial = 'Agendado'
            print(f"[Flask] Agendamento detectado: {local_dt} (Local) -> {scheduled_datetime_utc} (UTC)")

        # 2. Salva no DB
        new_camp = Campaign(
            subject=subject,
            theme=theme,
            cta_url=cta_url,
            generated_html=html_content,
            status=status_inicial,
            user=current_user,
            scheduled_at=scheduled_datetime_utc
        )
        db.session.add(new_camp)
        
        # 3. Processa o CSV
        upload_folder = os.path.join(current_app.instance_path, 'uploads')
        csv_path = os.path.join(upload_folder, csv_filename)
        leads_df = core_logic.get_leads(csv_path)
        
        if leads_df is None or leads_df.empty:
            flash('Erro no CSV.', 'error')
            return redirect(url_for('main.new_campaign'))

        for index, row in leads_df.iterrows():
            recipient = Recipient(
                nome=row['nome'], email=row['email'], 
                campaign=new_camp, status='Aguardando'
            )
            db.session.add(recipient)

        db.session.commit()

        # --- FILA REDIS ---
        try:
            redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
            conn = redis.from_url(redis_url)
            q = Queue(connection=conn)
            
            if scheduled_datetime_utc:
                # AGENDAR
                # Atribui à variável 'job' (CORREÇÃO DO ERRO DE REFERÊNCIA)
                job = q.enqueue_at(scheduled_datetime_utc, 'worker.run_campaign_task', new_camp.id)
                
                new_camp.job_id = job.id
                db.session.commit()
                flash(f'Campanha AGENDADA para {local_dt.strftime("%d/%m/%Y %H:%M")}!', 'success')
            else:
                # IMEDIATO
                job = q.enqueue('worker.run_campaign_task', new_camp.id)
                
                new_camp.job_id = job.id
                db.session.commit()
                flash(f'Campanha enviada para a fila de processamento!', 'success')

        except Exception as e:
            print(f"[Flask] Erro Redis: {e}")
            new_camp.status = 'Erro de Sistema (Fila)'
            db.session.commit()
            flash(f'Erro na fila: {e}', 'error')
            return redirect(url_for('main.history'))

        return redirect(url_for('main.history'))

    except Exception as e:
        db.session.rollback()
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

@main_bp.route('/campaign/<int:campaign_id>/cancel')
@login_required
def cancel_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or campaign.status != 'Agendado' or not campaign.job_id:
        flash('Campanha não pode ser cancelada.', 'error')
        return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))

    try:
        # Conecta ao Redis
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
        conn = redis.from_url(redis_url)
        
        # Busca a tarefa e cancela
        job = Job.fetch(campaign.job_id, connection=conn)
        job.cancel()
        
        # Atualiza o DB
        campaign.status = 'Cancelado'
        campaign.job_id = None # Remove o vínculo
        db.session.commit()
        
        flash('Agendamento cancelado com sucesso.', 'success')
    except NoSuchJobError:
        # Se a tarefa já sumiu do Redis
        campaign.status = 'Cancelado (Erro: Tarefa não encontrada)'
        db.session.commit()
        flash('A tarefa não foi encontrada no Redis, mas a campanha foi marcada como cancelada.', 'warning')
    except Exception as e:
        flash(f'Erro ao cancelar: {e}', 'error')

    return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))


@main_bp.route('/campaign/<int:campaign_id>/send_now')
@login_required
def send_now_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or campaign.status != 'Agendado':
        flash('Ação inválida.', 'error')
        return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))

    # 1. Cancela o agendamento antigo primeiro
    if campaign.job_id:
        try:
            redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
            conn = redis.from_url(redis_url)
            job = Job.fetch(campaign.job_id, connection=conn)
            job.cancel()
        except:
            pass # Ignora erro se não achar, o importante é enviar agora

    # 2. Envia imediatamente (cria nova tarefa)
    try:
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
        conn = redis.from_url(redis_url)
        q = Queue(connection=conn)
        q.enqueue('worker.run_campaign_task', campaign.id)
        
        campaign.status = 'Na Fila (Forçado)'
        campaign.scheduled_at = None # Limpa a data pois foi forçado
        db.session.commit()
        
        flash('Campanha enviada para a fila agora!', 'success')
    except Exception as e:
        flash(f'Erro ao enviar: {e}', 'error')

    return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))