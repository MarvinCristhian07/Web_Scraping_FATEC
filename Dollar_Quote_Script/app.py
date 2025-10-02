import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

# Imports do Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

# Constantes para os sites
URL_DOLAR = 'https://www.infomoney.com.br/ferramentas/cambio/'

# --------------------------------------------------------------------------------
# Introdução visual
# --------------------------------------------------------------------------------
print("")
print("█   █ █████ ████      █████ █   █ █████ █████ █████")
print("█   █ █     █   █     █     ██ ██ █   █ █   █   █")
print("█   █ █████ █   █ ███ █████ █ █ █ █████ ████    █")
print("█   █     █ █   █         █ █   █ █   █ █  █    █")
print("█████ █████ ████      █████ █   █ █   █ █   █   █")
print("")
print("█ █ █ █ ███████████████████████████████████ █ █ █ █")
print("              By. Marvin Cristhian")
print("")

# --------------------------------------------------------------------------------
# FUNÇÃO PARA RASPAR O DÓLAR (USD/BRL)
# --------------------------------------------------------------------------------
def raspar_dolar():
    print("-> Raspando cotação do Dólar com Selenium (para pegar o histórico)...")
    
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--ignore-certificate-errors')
    
    driver = None
    try:
        os.environ['WDM_SSL_VERIFY'] = '0'
        
        VERSAO_CHROME = "140"
        service = Service(ChromeDriverManager(driver_version=VERSAO_CHROME).install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver, languages=["pt-BR", "pt"], vendor="Google Inc.", platform="Win32")
        
        print("   -> Acessando a página...")
        driver.get(URL_DOLAR)
        
        print("   -> Esperando pela tabela de histórico...")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[contains(text(), 'Histórico de cotações')]")))
        
        html_completo = driver.page_source
        soup = BeautifulSoup(html_completo, 'html.parser')

        # PARTE 1: PEGAR O VALOR ATUAL
        valor_atual = None
        dolar_label = soup.find(lambda tag: tag.name == 'td' and 'Dólar Comercial' in tag.get_text())
        if dolar_label:
            parent_row = dolar_label.find_parent('tr')
            if parent_row:
                cells = parent_row.find_all('td')
                if len(cells) > 3:
                    preco_str = cells[3].get_text(strip=True)
                    valor_atual = float(preco_str.replace(',', '.').strip())

        # PARTE 2: PEGAR O HISTÓRICO
        historico_list = []
        titulo_historico = soup.find('h2', string=lambda text: text and 'histórico de cotações' in text.lower())
        
        if titulo_historico:
            print("   -> Título do histórico encontrado. Processando a tabela...")
            container_tabela = titulo_historico.find_next_sibling('div')
            if container_tabela:
                tabela_historico = container_tabela.find('table')
                if tabela_historico:
                    tbody = tabela_historico.find('tbody')
                    if tbody:
                        linhas = tbody.find_all('tr')
                        for linha in linhas:
                            celulas = linha.find_all('td')
                            if len(celulas) == 2:
                                data = celulas[0].get_text(strip=True)
                                valor_str = celulas[1].get_text(strip=True)
                                if data and valor_str:
                                    valor_float = float(valor_str.replace(',', '.'))
                                    historico_list.append({'data': data, 'valor': valor_float})
        
        return {
            "atual": valor_atual or "Valor atual não encontrado",
            "historico": historico_list
        }

    except Exception as e:
        return f"Erro ao processar a raspagem do Dólar: {e}"
    finally:
        if driver:
            driver.quit()

# --------------------------------------------------------------------------------
# FUNÇÃO PARA ANÁLISE DOS DADOS
# --------------------------------------------------------------------------------
def analisar_dados_dolar(valor_atual, historico):
    print("-> Analisando dados coletados...")
    if not historico:
        return {"analise_status": "Dados históricos insuficientes para análise."}

    todos_valores = [item['valor'] for item in historico]
    if isinstance(valor_atual, float):
        todos_valores.insert(0, valor_atual)

    if not todos_valores:
        return {"analise_status": "Nenhum valor encontrado para análise."}

    media = sum(todos_valores) / len(todos_valores)
    maior_valor = max(todos_valores)
    menor_valor = min(todos_valores)

    tendencia = "Estável"
    if len(todos_valores) >= 6:
        media_recente = sum(todos_valores[:3]) / 3
        media_antiga = sum(todos_valores[-3:]) / 3
        if media_recente > media_antiga * 1.01:
            tendencia = "Ascendente"
        elif media_recente < media_antiga * 0.99:
            tendencia = "Decrescente"

    return {
        "cotacao_media": round(media, 4),
        "maior_valor_periodo": maior_valor,
        "menor_valor_periodo": menor_valor,
        "tendencia": tendencia
    }

# --------------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL (MODIFICADA PARA SALVAR EM .TXT)
# --------------------------------------------------------------------------------
def agregar_e_salvar_dados():
    dados_dolar = raspar_dolar()
    
    analise = {}
    if isinstance(dados_dolar, dict):
        analise = analisar_dados_dolar(dados_dolar.get('atual'), dados_dolar.get('historico'))
        resultados = {
            "timestamp_raspagem": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dolar_atual_brl": dados_dolar.get('atual', 'Não encontrado'),
            "dolar_historico_brl": dados_dolar.get('historico', []),
            "analise_dados": analise
        }
    else:
        resultados = {
            "timestamp_raspagem": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "erro_msg": dados_dolar
        }

    # Exibição no terminal (sem alterações)
    print("\n--- Resultados Agregados ---")
    if 'erro_msg' in resultados:
        print(f"Ocorreu um erro: {resultados['erro_msg']}")
    else:
        dolar_val = resultados.get('dolar_atual_brl')
        if isinstance(dolar_val, float):
            print(f"Dólar Comercial Atual: R$ {dolar_val:.4f}")
        else:
            print(f"Dólar Comercial Atual: {dolar_val}")

        if resultados.get('dolar_historico_brl'):
            print(f"Encontrados {len(resultados['dolar_historico_brl'])} registros históricos.")
        
        if analise and 'analise_status' not in analise:
            print("\n--- Análise dos Dados ---")
            for chave, valor in analise.items():
                chave_formatada = chave.replace('_', ' ').replace('periodo', 'no período').capitalize()
                if isinstance(valor, float):
                    print(f"{chave_formatada}: R$ {valor:.4f}")
                else:
                    print(f"{chave_formatada}: {valor}")
    print("--------------------------")

    # --- MUDANÇA PRINCIPAL: LÓGICA PARA SALVAR EM TXT ---
    nome_arquivo = 'historico_dolar.txt'
    
    # Abrimos o arquivo em modo 'a' (append) para adicionar no final sem apagar o conteúdo antigo
    with open(nome_arquivo, 'a', encoding='utf-8') as f:
        f.write("==================================================\n")
        f.write(f"Registro de Raspagem: {resultados['timestamp_raspagem']}\n")
        f.write("==================================================\n\n")

        if 'erro_msg' in resultados:
            f.write(f"Ocorreu um erro durante a raspagem:\n")
            f.write(f"{resultados['erro_msg']}\n\n")
        else:
            # Escreve o valor atual
            f.write("--- DADOS ATUAIS ---\n")
            dolar_val = resultados['dolar_atual_brl']
            if isinstance(dolar_val, float):
                f.write(f"Dólar Comercial Atual: R$ {dolar_val:.4f}\n\n")
            else:
                f.write(f"Dólar Comercial Atual: {dolar_val}\n\n")

            # Escreve a análise
            analise_dados = resultados.get('analise_dados', {})
            if analise_dados and 'analise_status' not in analise_dados:
                f.write("--- ANÁLISE DOS DADOS ---\n")
                for chave, valor in analise_dados.items():
                    chave_formatada = chave.replace('_', ' ').replace('periodo', 'no período').capitalize()
                    if isinstance(valor, float):
                        f.write(f"{chave_formatada}: R$ {valor:.4f}\n")
                    else:
                        f.write(f"{chave_formatada}: {valor}\n")
                f.write("\n")

            # Escreve o histórico
            historico_brl = resultados.get('dolar_historico_brl', [])
            if historico_brl:
                f.write(f"--- HISTÓRICO DE COTAÇÕES ({len(historico_brl)} dias) ---\n")
                for item in historico_brl:
                    f.write(f"{item['data']}: R$ {item['valor']:.4f}\n")
                f.write("\n")
        
        f.write("\n\n") # Adiciona duas linhas extras para separar bem os registros

    print(f"\nDados salvos com sucesso em '{nome_arquivo}'.")


if __name__ == "__main__":
    agregar_e_salvar_dados()