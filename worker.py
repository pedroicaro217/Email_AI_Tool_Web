import os
import redis
from rq import Queue
from rq.worker import SimpleWorker
from app import create_app, db
from app.models import Settings, Campaign, Recipient
from app import core_logic

# --- Configuração ---

# Garante que o worker possa encontrar os módulos 'app'
app = create_app()
app.app_context().push()

# Pega a URL do Redis (padrão é localhost)
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)

# A fila 'default' é onde o Flask colocará as tarefas
q = Queue(connection=conn)

# --- A Função da Tarefa (O "Trabalho Pesado") ---

def run_campaign_task(campaign_id):
    """
    Esta é a função que o worker executará.
    Ela busca a campanha, os leads e envia os e-mails, um por um.
    """
    print(f"--- [Worker] Tarefa recebida: Processando Campanha ID: {campaign_id} ---")
    
    try:
        # 1. Buscar a campanha no DB
        campaign = db.session.get(Campaign, campaign_id)
        if not campaign:
            print(f"[Worker] Erro: Campanha ID {campaign_id} não encontrada.")
            return

        # 2. Atualizar o status no DB
        campaign.status = 'Enviando'
        db.session.commit()

        # 3. Buscar as configurações de SMTP no DB
        settings_from_db = Settings.query.all()
        settings = {setting.key: setting.value for setting in settings_from_db}
        
        smtp_config = {
            'server': settings.get('SMTP_SERVER'),
            'port': settings.get('SMTP_PORT'),
            'user': settings.get('SMTP_USER'),
            'pass': settings.get('SMTP_PASS')
        }
        
        if not all(smtp_config.values()):
            print("[Worker] Erro: Configurações de SMTP incompletas.")
            campaign.status = 'Falhou (Config SMTP)'
            db.session.commit()
            return

        # 4. Buscar todos os destinatários desta campanha
        recipients = campaign.recipients
        total_leads = len(recipients)
        success_count = 0
        fail_count = 0
        
        print(f"[Worker] Encontrados {total_leads} destinatários. Iniciando disparos...")

        # 5. Loop de Envio (O trabalho pesado)
        for i, recipient in enumerate(recipients):
            print(f"[Worker] Enviando {i+1}/{total_leads} para: {recipient.email}")
            
            try:
                # Chama o motor de envio
                success = core_logic.send_email(
                    smtp_config,
                    recipient.nome,
                    recipient.email,
                    campaign.subject,
                    campaign.generated_html
                )
                
                if success:
                    recipient.status = 'Enviado'
                    success_count += 1
                else:
                    recipient.status = 'Falhou'
                    fail_count += 1
                    
            except Exception as e:
                print(f"[Worker] Erro inesperado ao enviar para {recipient.email}: {e}")
                recipient.status = f'Falhou (Exceção: {e})'
                fail_count += 1
            
            # Salva o status de *cada* destinatário no DB
            db.session.commit()

        # 6. Finalizar a campanha
        campaign.status = f'Concluído (Sucessos: {success_count}, Falhas: {fail_count})'
        db.session.commit()
        print(f"--- [Worker] Tarefa finalizada: Campanha ID: {campaign_id} ---")

    except Exception as e:
        # Se algo der errado ANTES do loop (ex: buscar campanha)
        print(f"[Worker] Erro CRÍTICO na tarefa: {e}")
        campaign = db.session.get(Campaign, campaign_id)
        if campaign:
            campaign.status = f'Falhou (Erro de Worker: {e})'
            db.session.commit()
        
# --- Ponto de Entrada do Worker ---

if __name__ == '__main__':
    print("--- [Worker] Iniciando 'ouvinte' na fila 'default' ---")
    # Passa a conexão 'conn' e a fila 'q' diretamente para o Worker
    worker = SimpleWorker([q], connection=conn)

    # Inicia o "ouvinLte"
    worker.work(with_scheduler=True)