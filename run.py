from app import create_app

# Cria a instância do app usando nossa "fábrica"
app = create_app()

if __name__ == '__main__':
    # Roda o servidor em modo "debug"
    # (recarrega sozinho quando você salva um arquivo)
    # host='0.0.0.0' permite acesso pela sua rede local
    app.run(debug=True, host='0.0.0.0', port=5000)