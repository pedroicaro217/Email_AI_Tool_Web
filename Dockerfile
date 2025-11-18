# 1. Define a imagem base (Python 3.10 leve rodando em Linux Debian)
FROM python:3.10-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Define variáveis de ambiente para otimizar o Python no Docker
# PYTHONDONTWRITEBYTECODE: Previne o Python de criar arquivos .pyc desnecessários
# PYTHONUNBUFFERED: Garante que os logs (print) apareçam instantaneamente no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Instala dependências do sistema operacional
# (Necessário para compilar algumas bibliotecas Python)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Copia o arquivo de requisitos e instala as bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia todo o restante do código do projeto para a pasta /app
COPY . .

# 7. Expõe a porta 5000 (apenas para documentação, o compose é quem libera)
EXPOSE 5000

# 8. Comando padrão (será sobrescrito pelo docker-compose para o worker)
CMD ["python", "run.py"]