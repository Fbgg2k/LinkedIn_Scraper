from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
from datetime import datetime
from linkedin_scraper_clean import LinkedInScraper
import threading
import uuid
import json
import csv

app = Flask(__name__)
CORS(app)

# Armazenamento temporário de tarefas
scraping_tasks = {}

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_profiles():
    """API para iniciar scraping (versão limpa e organizada)"""
    try:
        data = request.get_json()
        profile_urls = data.get('urls', [])
        
        if not profile_urls:
            return jsonify({"error": "Nenhuma URL fornecida"}), 400
        
        # Validar URLs
        valid_urls = []
        for url in profile_urls:
            if 'linkedin.com/in/' in url:
                valid_urls.append(url)
            else:
                print(f"URL inválida ignorada: {url}")
        
        if not valid_urls:
            return jsonify({"error": "Nenhuma URL válida do LinkedIn fornecida"}), 400
        
        # Criar ID único para a tarefa
        task_id = str(uuid.uuid4())
        
        # Iniciar scraping em thread separada
        def run_scraping():
            try:
                scraper = LinkedInScraper()
                results = scraper.scrape_multiple_profiles(valid_urls)
                scraper.close()
                
                # Calcular estatísticas
                total = len(results)
                success = len([r for r in results if r.get('nome') != 'ERRO'])
                errors = total - success
                
                # Salvar resultados
                scraping_tasks[task_id] = {
                    'status': 'completed',
                    'results': results,
                    'timestamp': datetime.now().isoformat(),
                    'total': total,
                    'success': success,
                    'errors': errors,
                    'mode': 'clean'
                }
                
                print(f"Tarefa {task_id} concluída: {success} sucessos, {errors} erros")
                
            except Exception as e:
                print(f"Erro na tarefa {task_id}: {e}")
                scraping_tasks[task_id] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        # Marcar tarefa como em andamento
        scraping_tasks[task_id] = {
            'status': 'running',
            'started': datetime.now().isoformat(),
            'total_urls': len(valid_urls),
            'mode': 'clean'
        }
        
        thread = threading.Thread(target=run_scraping)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "message": "Scraping iniciado (modo limpo e organizado)",
            "total_urls": len(valid_urls),
            "mode": "clean"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Verificar status da tarefa"""
    if task_id not in scraping_tasks:
        return jsonify({"error": "Tarefa não encontrada"}), 404
    
    return jsonify(scraping_tasks[task_id])

@app.route('/api/download/<task_id>')
def download_results(task_id):
    """Baixar resultados em CSV (versão limpa e organizada)"""
    if task_id not in scraping_tasks:
        return jsonify({"error": "Tarefa não encontrada"}), 404
    
    task = scraping_tasks[task_id]
    
    if task['status'] != 'completed':
        return jsonify({"error": "Tarefa não concluída"}), 400
    
    try:
        # Gerar arquivo CSV
        filename = f'linkedin_clean_results_{task_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        filepath = os.path.join('exports', filename)
        
        # Criar diretório se não existir
        os.makedirs('exports', exist_ok=True)
        
        # Salvar CSV com dados limpos e organizados
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Nome', 
                'Cargo Atual', 
                'Último Cargo', 
                'Empresa', 
                'Localização', 
                'Telefone', 
                'Email', 
                'URL', 
                'Status', 
                'Método Extração', 
                'Download PDF'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in task['results']:
                # Limpar e organizar dados antes de salvar
                row_data = {
                    'Nome': result.get('nome', 'Não encontrado'),
                    'Cargo Atual': result.get('cargo_atual', 'Não encontrado'),
                    'Último Cargo': result.get('ultimo_cargo', 'Não encontrado'),
                    'Empresa': result.get('empresa', 'Não encontrado'),
                    'Localização': result.get('localizacao', 'Não encontrado'),
                    'Telefone': result.get('telefone', 'Não encontrado'),
                    'Email': result.get('email', 'Não encontrado'),
                    'URL': result.get('url', ''),
                    'Status': result.get('status', ''),
                    'Método Extração': result.get('metodo_extração', ''),
                    'Download PDF': result.get('pdf_download', '')
                }
                
                # Validações finais
                if row_data['Nome'] == 'ERRO':
                    row_data['Status'] = f"ERRO: {result.get('status', 'Erro desconhecido')}"
                
                writer.writerow(row_data)
        
        print(f"Arquivo CSV limpo gerado: {filepath}")
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"Erro ao gerar download: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks')
def list_tasks():
    """Listar todas as tarefas"""
    return jsonify(scraping_tasks)

@app.route('/api/validate-url', methods=['POST'])
def validate_url():
    """Validar URL do LinkedIn"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if 'linkedin.com/in/' in url:
            return jsonify({"valid": True, "message": "URL válida do LinkedIn"})
        else:
            return jsonify({"valid": False, "message": "URL inválida. Use URLs do tipo: linkedin.com/in/nome-do-perfil"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-download')
def test_download():
    """Teste de download com dados de exemplo limpos"""
    try:
        # Gerar arquivo CSV de teste
        filename = f'test_clean_download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        filepath = os.path.join('exports', filename)
        
        # Criar diretório se não existir
        os.makedirs('exports', exist_ok=True)
        
        # Salvar CSV de teste com dados limpos
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Nome', 'Cargo', 'Empresa', 'Localização', 'Telefone', 'Email', 'URL', 'Status', 'Método Extração', 'Download PDF']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerow({
                'Nome': 'João Silva',
                'Cargo': 'Desenvolvedor Full Stack',
                'Empresa': 'Tech Solutions Ltda',
                'Localização': 'São Paulo, SP',
                'Telefone': '(11) 99999-9999',
                'Email': 'joao.silva@techsolutions.com',
                'URL': 'https://linkedin.com/in/joao-silva',
                'Status': 'Dados extraídos com sucesso',
                'Método Extração': 'HTML Completo',
                'Download PDF': 'Não disponível'
            })
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Iniciando LinkedIn Scraper - VERSÃO LIMPA E ORGANIZADA")
    print("📋 Dados extraídos de forma específica por campo")
    print("🧹 Validação e limpeza automática dos dados")
    print("📊 CSV organizado e sem confusão")
    print("🌐 Acesse: http://localhost:5003")
    app.run(debug=True, host='0.0.0.0', port=5003)
