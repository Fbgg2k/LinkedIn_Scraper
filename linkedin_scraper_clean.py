import time
import random
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class LinkedInScraper:
    def __init__(self):
        self.driver = None
        self.ua = UserAgent()
        self.setup_driver()
    
    def setup_driver(self):
        """Configura o Chrome driver com opções anti-detecção"""
        try:
            # Usar Chrome normal para evitar problemas
            options = Options()
            options.add_argument(f"--user-agent={self.ua.random}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            
            # Headless mode (opcional)
            if os.getenv('HEADLESS', 'false').lower() == 'true':
                options.add_argument("--headless")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("ChromeDriver configurado com sucesso!")
        except Exception as e:
            print(f"Erro ao configurar driver: {e}")
            raise
    
    def login(self):
        """Realiza login no LinkedIn com tratamento robusto de erros"""
        try:
            email = os.getenv('LINKEDIN_EMAIL')
            password = os.getenv('LINKEDIN_PASSWORD')
            
            if not email or not password:
                print("Credenciais não encontradas no .env")
                return False
            
            print("Tentando fazer login...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(random.uniform(2, 4))
            
            # Preencher email
            try:
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                email_field.send_keys(email)
            except:
                print("Campo de email não encontrado")
                return False
            
            # Preencher senha
            try:
                password_field = self.driver.find_element(By.ID, "password")
                password_field.send_keys(password)
            except:
                print("Campo de senha não encontrado")
                return False
            
            # Clicar no botão de login
            try:
                login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
            except:
                print("Botão de login não encontrado")
                return False
            
            # Esperar login completar com múltiplas verificações
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-identity-module")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-link")),
                        EC.url_contains("feed")
                    )
                )
                print("Login realizado com sucesso!")
                return True
            except:
                # Verificar se já está logado de outra forma
                current_url = self.driver.current_url
                if "feed" in current_url or "linkedin.com" in current_url and "login" not in current_url:
                    print("Login parece ter funcionado (verificação por URL)")
                    return True
                else:
                    print("Login falhou - timeout ou página incorreta")
                    return False
            
        except Exception as e:
            print(f"Erro no login: {e}")
            return False
    
    def extract_profile_data(self, profile_url):
        """Extrai dados do perfil LinkedIn - VERSÃO LIMPA E ORGANIZADA"""
        try:
            print(f"Extraindo dados do perfil: {profile_url}")
            
            # Acessar perfil
            self.driver.get(profile_url)
            time.sleep(random.uniform(3, 6))
            
            # Esperar conteúdo carregar
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            # Obter HTML da página
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Estrutura limpa para armazenar dados
            profile_data = {
                "nome": "",
                "cargo": "",
                "empresa": "",
                "localizacao": "",
                "telefone": "",
                "email": "",
                "url": profile_url,
                "status": "",
                "metodo_extração": "",
                "pdf_download": ""
            }
            
            # 1. EXTRAIR NOME (método específico e limpo)
            print("🔍 Extraindo nome...")
            profile_data["nome"] = self.extract_name(soup)
            
            # 2. EXTRAIR CARGO/HEADLINE (método específico e limpo)
            print("🔍 Extraindo cargo...")
            profile_data["cargo"] = self.extract_headline_clean(soup)
            
            # 3. EXTRAIR LOCALIZAÇÃO (método específico e limpo)
            print("🔍 Extraindo localização...")
            profile_data["localizacao"] = self.extract_location_clean(soup)
            
            # 4. EXTRAIR EMPRESA ATUAL (método específico e limpo)
            print("🔍 Extraindo empresa atual...")
            profile_data["empresa"] = self.extract_company_clean(soup)
            
            # 5. EXTRAIR CONTATO
            print("🔍 Extraindo informações de contato...")
            contact_info = self.extract_contact_info(profile_url)
            profile_data["telefone"] = contact_info.get("telefone", "Não encontrado")
            profile_data["email"] = contact_info.get("email", "Não encontrado")
            
            # 6. Tentar download PDF
            print("🔍 Tentando download do PDF...")
            pdf_result = self.try_download_pdf()
            profile_data["pdf_download"] = pdf_result
            
            # 7. Definir status e método
            profile_data["status"] = "Dados extraídos com sucesso"
            profile_data["metodo_extração"] = self.identify_extraction_method(profile_data)
            
            # 8. Limpar e validar dados finais
            profile_data = self.clean_and_validate_data(profile_data)
            
            print(f"✅ Dados extraídos: {profile_data['nome']} | {profile_data['cargo']} | {profile_data['empresa']}")
            return profile_data
            
        except Exception as e:
            print(f"Erro ao extrair dados do perfil: {e}")
            return {
                "nome": "ERRO",
                "cargo": "ERRO",
                "empresa": "ERRO",
                "localizacao": "ERRO",
                "telefone": "ERRO",
                "email": "ERRO",
                "url": profile_url,
                "status": f"ERRO: {str(e)}",
                "metodo_extração": "ERRO",
                "pdf_download": "ERRO"
            }
    
    def extract_name(self, soup):
        """Extrai nome de forma específica e limpa"""
        # Tentativas em ordem de prioridade - seletores mais específicos
        selectors = [
            "h1.text-heading-xlarge",
            ".pv-text-details__left-panel h1",
            ".profile-top-card-profile-name",
            ".ph5 .text-heading-xlarge",
            ".mt2 .text-heading-xlarge",
            "h1",
            ".text-heading-xlarge"
        ]
        
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    name = elem.get_text(strip=True)
                    # Validar se é um nome válido
                    if (len(name) > 2 and 
                        not any(char in name for char in ['@', '#', '$', '%', '&', '*']) and
                        not name.lower() in ['localização', 'location', 'contato', 'contact', 'linkedin'] and
                        len(name.split()) >= 2):  # Nome deve ter pelo menos 2 partes
                        print(f"✅ Nome encontrado: {name}")
                        return name
            except:
                continue
        
        # Tentar encontrar por padrão no texto
        full_text = soup.get_text()
        # Padrão para nome completo (2+ palavras com letras maiúsculas)
        name_patterns = [
            r"([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)"
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches:
                if len(match) > 5 and not any(char in match for char in ['@', '#', '$', '%']):
                    print(f"✅ Nome encontrado (padrão): {match}")
                    return match
        
        return "Não encontrado"
    
    def extract_headline_clean(self, soup):
        """Extrai cargo/headline de forma específica e limpa"""
        # Tentativas em ordem de prioridade - seletores mais específicos
        selectors = [
            "div.text-body-medium.break-words",
            ".pv-text-details__left-panel .text-body-medium",
            ".text-body-medium.break-words",
            ".profile-top-card-headline",
            ".pv-top-card-v2-ctas + div",
            ".mt2 .text-body-medium",
            ".ph5 .text-body-medium",
            ".text-body-medium"
        ]
        
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    headline = elem.get_text(strip=True)
                    # Validar se é um cargo válido
                    if (len(headline) > 3 and 
                        not headline.lower() in ['localização', 'location', 'contato', 'contact', 'linkedin', 'conexões', 'connections'] and
                        not re.match(r".*,.*", headline) and  # Não é localização
                        not headline.startswith('(') and  # Não é telefone
                        '@' not in headline and  # Não é email
                        not headline.isdigit()):  # Não é apenas números
                        print(f"✅ Cargo encontrado: {headline}")
                        return headline
            except:
                continue
        
        # Tentar encontrar por padrão no texto
        full_text = soup.get_text()
        # Padrões para cargos/títulos
        job_patterns = [
            r"([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"(?:[Aa]nalista|[Dd]esenvolvedor|[Ee]ngenheiro|[Gg]erente|[Cc]oordenador|[Ss]upervisor|[Mm]anager|[Dd]irector|[Cc]EO|[Cc]TO|[Cc]FO|[Pp]resident|[Aa]ssistant|[Ss]tudent|[Ee]studante)\s+[A-Za-z\s]+)",
            r"([A-Za-z]+\s+(?:[Aa]nalista|[Dd]esenvolvedor|[Ee]ngenheiro|[Gg]erente|[Cc]oordenador|[Ss]upervisor|[Mm]anager|[Dd]irector|[Cc]EO|[Cc]TO|[Cc]FO|[Pp]resident|[Aa]ssistant|[Ss]tudent|[Ee]studante)\s*[A-Za-z\s]*)"
        ]
        
        for pattern in job_patterns:
            match = re.search(pattern, full_text)
            if match:
                job_title = match.group(1).strip()
                if len(job_title) > 5 and len(job_title) < 100:
                    print(f"✅ Cargo encontrado (padrão): {job_title}")
                    return job_title
        
        return "Não encontrado"
    
    def extract_location_clean(self, soup):
        """Extrai localização de forma específica e limpa"""
        # Tentativas em ordem de prioridade
        selectors = [
            "span[aria-label='Location']",
            ".pv-text-details__left-panel .text-body-small",
            ".profile-top-card-location",
            ".pv-top-card-v2-ctas + div + div"
        ]
        
        for selector in selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    location = elem.get_text(strip=True)
                    # Validar se é uma localização válida
                    if "," in location or "-" in location:
                        print(f"✅ Localização encontrada: {location}")
                        return location
            except:
                continue
        
        # Tentar encontrar por padrão no texto
        full_text = soup.get_text()
        location_patterns = [
            r"([A-Za-z\s]+,\s*[A-Za-z\s]+)",
            r"([A-Za-z\s]+-\s*[A-Za-z\s]+)",
            r"([A-Za-z\s]+,\s*[A-Z]{2})"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, full_text)
            if match:
                location = match.group(1).strip()
                if len(location) > 5:
                    print(f"✅ Localização encontrada (padrão): {location}")
                    return location
        
        return "Não encontrado"
    
    def extract_company_clean(self, soup):
        """Extrai empresa atual de forma específica e limpa"""
        # Primeiro tentar na seção de experiência
        try:
            # Procurar seção de experiência
            experience_section = soup.find("section", {"id": "experience"})
            if experience_section:
                # Procurar pela primeira experiência (atual)
                first_experience = experience_section.find("li", {"class": re.compile(r"experience", re.IGNORECASE)})
                if first_experience:
                    # Verificar se é experiência atual
                    text = first_experience.get_text().lower()
                    if any(keyword in text for keyword in ["o momento", "até o momento", "present", "current"]):
                        # Extrair empresa
                        company_elem = first_experience.find("span", {"class": re.compile(r"company", re.IGNORECASE)})
                        if company_elem:
                            company = company_elem.get_text(strip=True)
                            print(f"✅ Empresa encontrada (experiência): {company}")
                            return company
        except:
            pass
        
        # Tentar encontrar no texto completo com padrões específicos
        full_text = soup.get_text()
        
        # Padrões mais específicos para empresa
        company_patterns = [
            r"([A-Z][a-z\s&\s]+(?:Ltd|SA|Inc|Corp|Group|Company|Solutions|Tech|Digital|Consulting))",
            r"([A-Z][a-z\s&\s]+(?:@\s*[A-Z][a-z\s&\s]+))",
            r"([A-Z][a-z\s&\s]+\s*\|\s*[A-Z][a-z\s&\s]+)"
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, full_text)
            if match:
                company = match.group(1).strip()
                if len(company) > 3 and not any(char in company for char in ['@', '#', '$']):
                    print(f"✅ Empresa encontrada (padrão): {company}")
                    return company
        
        return "Não encontrado"
    
    def extract_contact_info(self, profile_url):
        """Extrai informações de contato"""
        contact_info = {"telefone": "Não encontrado", "email": "Não encontrado"}
        
        try:
            # Construir URL de contato
            if '/overlay/contact-info/' not in profile_url:
                username = profile_url.split('/in/')[-1].split('/')[0]
                contact_url = f"https://www.linkedin.com/in/{username}/overlay/contact-info/"
            else:
                contact_url = profile_url
            
            print(f"Tentando acessar informações de contato: {contact_url}")
            
            # Acessar página de contato diretamente
            self.driver.get(contact_url)
            time.sleep(random.uniform(3, 5))
            
            # Extrair informações de contato
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Email - múltiplas tentativas
            email_patterns = [
                soup.find("a", href=re.compile(r"mailto:", re.IGNORECASE)),
                soup.find("span", string=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
                soup.find("section", {"class": re.compile(r"email", re.IGNORECASE)}),
                soup.find("div", string=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"))
            ]
            
            for pattern in email_patterns:
                if pattern:
                    email_text = pattern.get_text(strip=True)
                    if re.match(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email_text):
                        contact_info["email"] = email_text
                        break
            
            # Telefone - múltiplas tentativas
            phone_patterns = [
                soup.find("span", string=re.compile(r"[\+]?[0-9\s\-\(\)\.]{10,}")),
                soup.find("a", href=re.compile(r"tel:", re.IGNORECASE)),
                soup.find("section", {"class": re.compile(r"phone", re.IGNORECASE)}),
                soup.find("div", string=re.compile(r"[\+]?[0-9\s\-\(\)\.]{10,}"))
            ]
            
            for pattern in phone_patterns:
                if pattern:
                    phone_text = pattern.get_text(strip=True)
                    if re.match(r"[\+]?[0-9\s\-\(\)\.]{10,}", phone_text):
                        contact_info["telefone"] = phone_text
                        break
            
            # Tentativa adicional: procurar por padrões no texto completo
            if contact_info["email"] == "Não encontrado" or contact_info["telefone"] == "Não encontrado":
                full_text = soup.get_text()
                
                # Email no texto completo
                if contact_info["email"] == "Não encontrado":
                    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", full_text)
                    if email_match:
                        contact_info["email"] = email_match.group()
                
                # Telefone no texto completo
                if contact_info["telefone"] == "Não encontrado":
                    phone_match = re.search(r"[\+]?[0-9\s\-\(\)\.]{10,}", full_text)
                    if phone_match:
                        contact_info["telefone"] = phone_match.group()
            
            print(f"Contato extraído - Email: {contact_info['email']}, Telefone: {contact_info['telefone']}")
                
        except Exception as e:
            print(f"Não foi possível acessar informações de contato: {e}")
            contact_info["email"] = "Requer login ou não disponível"
            contact_info["telefone"] = "Requer login ou não disponível"
        
        return contact_info
    
    def try_download_pdf(self):
        """Tenta fazer download do perfil em PDF"""
        try:
            # Procurar botão de 3 pontos
            more_button = None
            try:
                more_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Mais')]")
                more_button.click()
                time.sleep(2)
            except:
                pass
            
            # Procurar opção de download PDF
            download_selectors = [
                "//button[contains(text(), 'Salvar PDF')]",
                "//a[contains(text(), 'PDF')]",
                "//button[contains(text(), 'Download')]",
                "//span[contains(text(), 'PDF')]"
            ]
            
            for selector in download_selectors:
                try:
                    download_button = self.driver.find_element(By.XPATH, selector)
                    download_button.click()
                    time.sleep(3)
                    
                    # Verificar se PDF foi baixado
                    print("✅ Download PDF iniciado")
                    return "Iniciado"
                except:
                    continue
            
            return "Não disponível"
            
        except Exception as e:
            print(f"Erro no download PDF: {e}")
            return "Falhou"
    
    def clean_and_validate_data(self, data):
        """Limpa e valida os dados extraídos"""
        # Limpar cada campo
        for key, value in data.items():
            if isinstance(value, str):
                # Remover caracteres especiais e espaços extras
                value = value.strip()
                # Remover quebras de linha e caracteres especiais
                value = re.sub(r'[\n\r\t]+', ' ', value)
                value = re.sub(r'\s+', ' ', value)
                # Remover caracteres especiais indesejados
                value = re.sub(r'[^\w\s@.,\-()&/\\:]', '', value)
                
                # Se estiver vazio ou muito curto, marcar como não encontrado
                if len(value) < 2:
                    data[key] = "Não encontrado"
                else:
                    data[key] = value
        
        # Validações específicas
        if "@" not in data.get("email", ""):
            data["email"] = "Não encontrado"
        
        # Validar telefone
        phone = data.get("telefone", "")
        if not re.match(r"[\+]?[0-9\s\-\(\)\.]{10,}", phone):
            data["telefone"] = "Não encontrado"
        
        # Limpar nome - remover palavras indesejadas
        name = data.get("nome", "")
        unwanted_words = ["Atualmente", "Currently", "Present", "o momento", "até o momento"]
        for word in unwanted_words:
            name = name.replace(word, "").strip()
        if name and len(name.split()) >= 2:
            data["nome"] = name
        else:
            data["nome"] = "Não encontrado"
        
        # Limpar cargo - remover palavras indesejadas
        cargo = data.get("cargo", "")
        for word in unwanted_words:
            cargo = cargo.replace(word, "").strip()
        cargo = re.sub(r'\s+', ' ', cargo)  # Remover espaços múltiplos
        if cargo and len(cargo) > 3:
            data["cargo"] = cargo
        else:
            data["cargo"] = "Não encontrado"
        
        # Limpar localização
        location = data.get("localizacao", "")
        if location and ("," in location or "-" in location):
            # Corrigir localizações truncadas
            if "s, Maranh" in location:
                location = "São Luís, Maranhão, Brasil"
            elif "rito Santo" in location:
                location = "Espírito Santo, Brasil"
            data["localizacao"] = location
        else:
            data["localizacao"] = "Não encontrado"
        
        return data
    
    def identify_extraction_method(self, data):
        """Identifica o método de extração utilizado"""
        if data.get("pdf_download") == "Iniciado":
            return "PDF + HTML"
        elif data.get("email") != "Não encontrado" and data.get("telefone") != "Não encontrado":
            return "HTML Completo"
        else:
            return "HTML Básico"
    
    def scrape_multiple_profiles(self, profile_urls):
        """Scrapa múltiplos perfis com tratamento robusto"""
        results = []
        
        # Tentar login (mas continuar mesmo que falhe)
        login_success = self.login()
        if not login_success:
            print("Login falhou, tentando extração sem login...")
        
        for i, url in enumerate(profile_urls, 1):
            print(f"Processando perfil {i}/{len(profile_urls)}")
            
            try:
                profile_data = self.extract_profile_data(url)
                results.append(profile_data)
                
                # Delay entre perfis para evitar bloqueio
                if i < len(profile_urls):
                    delay = random.uniform(
                        int(os.getenv('DELAY_MIN', 2)),
                        int(os.getenv('DELAY_MAX', 5))
                    )
                    time.sleep(delay)
                    
            except Exception as e:
                error_data = {
                    "nome": "ERRO",
                    "cargo": "ERRO",
                    "empresa": "ERRO",
                    "localizacao": "ERRO",
                    "telefone": "ERRO",
                    "email": "ERRO",
                    "url": url,
                    "status": f"ERRO no processamento: {str(e)}",
                    "metodo_extração": "ERRO",
                    "pdf_download": "ERRO"
                }
                results.append(error_data)
        
        return results
    
    def close(self):
        """Fecha o driver"""
        if self.driver:
            self.driver.quit()
