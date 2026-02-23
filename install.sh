#!/bin/bash

echo "🚀 Instalando LinkedIn Scraper..."

# Atualizar sistema
echo "📦 Atualizando pacotes do sistema..."
sudo apt update

# Instalar Python e pip
echo "🐍 Instalando Python e pip..."
sudo apt install -y python3 python3-pip python3-venv

# Instalar Google Chrome
echo "🌐 Instalando Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install -y google-chrome-stable

# Criar ambiente virtual
echo "📁 Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependências Python
echo "📚 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Configurar arquivo .env
echo "⚙️ Configurando ambiente..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado. Edite-o com suas credenciais do LinkedIn."
fi

# Criar diretórios necessários
mkdir -p exports

echo "🎉 Instalação concluída!"
echo ""
echo "📋 Próximos passos:"
echo "1. Edite o arquivo .env com suas credenciais do LinkedIn"
echo "2. Ative o ambiente virtual: source venv/bin/activate"
echo "3. Inicie a aplicação: python3 app.py"
echo "4. Acesse: http://localhost:5000"
echo ""
echo "⚠️  Importante: Use com responsabilidade e respeite os termos de uso do LinkedIn!"
