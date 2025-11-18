import pandas as pd
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

# --- Lógica de IA ---

def _clean_html_response(raw_text):
    """Limpa a resposta da IA, removendo os marcadores de Markdown (```html)."""
    if '```html' in raw_text:
        start_index = raw_text.find('```html') + len('```html')
    elif '```' in raw_text:
        start_index = raw_text.find('```') + len('```')
    else:
        return raw_text.strip()

    if '```' in raw_text[start_index:]:
        end_index = raw_text.rfind('```')
    else:
        return raw_text[start_index:].strip()

    cleaned_html = raw_text[start_index:end_index].strip()
    
    if cleaned_html.startswith("<") or cleaned_html.startswith("<!DOCTYPE"):
        return cleaned_html
    else:
        return raw_text.replace("```html", "").replace("```", "").strip()


def generate_ai_html(api_key, email_theme, cta_url, company_name, logo_url, model_name='gemini-2.5-flash-lite'):
    """
    Conecta na API do Gemini e solicita o HTML para o tema.
    (ATUALIZADO com Engenharia de Prompt Condicional)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # --- LÓGICA CONDICIONAL DA LOGO (Seu pedido) ---
        # Começa com uma instrução vazia
        logo_instruction = ""
        if logo_url and logo_url.strip(): # Verifica se a string não é vazia
            # Se uma URL foi fornecida, adiciona a instrução
            logo_instruction = f"2. O e-mail DEVE incluir uma logo. Use esta URL: {logo_url}"
        else:
            # Se a URL estiver vazia, instrui a IA a NÃO usar uma.
            logo_instruction = "2. O e-mail NÃO DEVE incluir uma logo nem espaço para ela."
        # --- FIM DA LÓGICA CONDICIONAL ---

        # --- LÓGICA DO ANO VIGENTE ---
        ano_vigente = datetime.datetime.now().year

        # --- PROMPT INTELIGENTE FINAL ---
        prompt = (
            f"Crie um e-mail marketing em HTML completo (inline CSS) sobre o tema: '{email_theme}'.\n"
            f"O e-mail deve ser profissional e amigável.\n"
            
            # --- INSTRUÇÕES OBRIGATÓRIAS (Suas features) ---
            f"1. O botão principal de Call-to-Action (CTA) DEVE apontar para esta URL: {cta_url}\n"
            f"{logo_instruction}\n"
            f"3. O nome da empresa é: '{company_name}'. Use-o no rodapé.\n"
            f"4. O ano de copyright no rodapé DEVE ser o ano vigente: {ano_vigente}.\n"
            
            # --- PLACEHOLDERS PADRÃO ---
            f"Use o placeholder [NOME] onde o nome do cliente deve ir.\n"
            f"Coloque o código HTML final dentro de um bloco de código Markdown (```html ... ```)."
        )
        
        print(f"[Core_Logic] Enviando prompt para Gemini API...")
        # print(prompt) # Descomente esta linha se quiser ver o prompt final no console
        
        request_options = {'timeout': 30}
        response = model.generate_content(prompt, request_options=request_options)
        
        print(f"[Core_Logic] Resposta recebida. Limpando HTML...")
        cleaned_html = _clean_html_response(response.text)
             
        return cleaned_html
    
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini (pode ser TIMEOUT): {e}")
        return None

# --- Lógica de Leads ---

def get_leads(csv_file_path):
    """
    Lê o arquivo CSV (salvo temporariamente) e retorna um DataFrame limpo.
    """
    try:
        df = pd.read_csv(csv_file_path)
        if "email" not in df.columns or "nome" not in df.columns:
            print(f"Erro: O arquivo CSV deve conter as colunas 'nome' e 'email'.")
            return None
        
        original_count = len(df)
        df = df.dropna(subset=['nome', 'email'])
        
        cleaned_count = len(df)
        if cleaned_count < original_count:
            print(f"[Core_Logic] Aviso: {original_count - cleaned_count} linhas removidas do CSV por dados faltantes ('nan').")

        if not df.empty:
            df['nome'] = df['nome'].astype(str)
            df['email'] = df['email'].astype(str)
            
        return df
    
    except Exception as e:
        print(f"Erro ao ler o CSV: {e}")
        return None

# --- Lógica de Envio ---

def send_email(smtp_config, to_name, to_email, subject, html_body):
    """
    Envia um único e-mail.
    Recebe 'smtp_config' (um dict com server, port, user, pass) como argumento.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['user']
        msg['To'] = to_email
        msg['Subject'] = subject

        personalized_body = html_body.replace("[NOME]", to_name.split(" ")[0]) 
        msg.attach(MIMEText(personalized_body, 'html'))

        print(f"[Core_Logic] Conectando ao SMTP {smtp_config['server']}...")
        server = smtplib.SMTP(smtp_config['server'], int(smtp_config['port']))
        server.starttls()
        server.login(smtp_config['user'], smtp_config['pass'])
        
        print(f"[Core_Logic] Enviando e-mail para {to_email}...")
        server.sendmail(smtp_config['user'], to_email, msg.as_string())
        server.quit()
        
        print(f"[Core_Logic] E-mail enviado com sucesso para {to_email}.")
        return True
    
    except Exception as e:
        print(f"Erro ao enviar e-mail (SMTP) para {to_email}: {e}")
        return False