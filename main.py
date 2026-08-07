import os
import re
import time
import json
from datetime import date
import pandas as pd
from playwright.sync_api import Page, expect, sync_playwright

def google_maps(page: Page):
    page.goto('https://www.google.com/maps/')
    print("abriu o google maps com sucesso")
    
    # Preenche a busca e confirma
    search_input = page.locator('input[role="combobox"]')
    search_input.wait_for(state="visible")
    search_input.fill("Restaurantes em São Paulo")
    page.keyboard.press("Enter")
    
    # Aguarda os resultados carregarem na tela
    page.wait_for_selector('div[role="feed"]', timeout=10000)
    print("pesquisou restaurantes em São Paulo com sucesso")

def extrair_links(page: Page):
    # Localiza todos os cards de resultado
    cards = page.locator('div[role="article"]')
    count = cards.count()
    
    links = []
    for i in range(count):
        # Pega a tag <a> interna que contém a URL do local
        anchor = cards.nth(i).locator('a.hfpxzc')
        href = anchor.get_attribute('href')
        nome = anchor.get_attribute('aria-label')
        
        if href:
            links.append({"nome": nome, "url": href})
            
    return links

def get_safe_text(page, selector, timeout=1000):
    """Retorna o texto do elemento se ele existir na página, senão retorna None sem travar a execução."""
    locator = page.locator(selector).first
    try:
        # Tenta esperar pelo elemento por no máximo 1 segundo
        locator.wait_for(state="attached", timeout=timeout)
        return locator.inner_text().strip()
    except Exception:
        return None


def salvar_informacoes(page, links):
    # Trata a faixa de preço para pegar apenas o valor principal, ignorando o "Informado por X pessoas"
    raw_preco = get_safe_text(page, ".MNVeJb")
    faixa_preco = raw_preco.split("\n")[0] if raw_preco else None

    dados_restaurante = {
        "endereco": get_safe_text(
            page, 'button[data-item-id="address"] .Io6YTe'
        ),
        "localizacao": get_safe_text(
            page, 'button[data-item-id="locatedin"] .Io6YTe'
        ),
        "status_horario": get_safe_text(page, ".ZDu9vd"),
        "faixa_preco": faixa_preco,
        "website": get_safe_text(
            page, 'a[data-item-id="authority"] .Io6YTe'
        ),
        "telefone": get_safe_text(
            page, 'button[data-item-id^="phone:"] .Io6YTe'
        ),
    }

    print(dados_restaurante)
    return dados_restaurante

def limpar_texto(texto):
    # Remove ícones Unicode privados do Google (\ue000 até \uf8ff) e espaços sobressalentes
    texto_limpo = re.sub(r"[\uE000-\uF8FF]", "", texto)
    return texto_limpo.strip()

def extrair_texto_bloco(bloco):
    # Pega o texto do bloco e limpa
    raw_text = bloco.inner_text().strip()
    if not raw_text:
        return None

    # Divide por linhas, limpa os ícones de cada uma e remove valores vazios
    linhas = [limpar_texto(line) for line in raw_text.split("\n")]
    linhas = [line for line in linhas if line]

    if not linhas:
        return None

    # Remove duplicidades mantendo a ordem (ex: no caso do 'tagme.com.br')
    linhas_unicas = list(dict.fromkeys(linhas))

    # Retorna como string única se for apenas 1 item, ou junta os itens do bloco
    return " - ".join(linhas_unicas)


def salvar_informacoes(page, links):
    resultados = []

    for link in links:
        page.goto(link["url"])

        # Aguarda o painel lateral carregar
        page.wait_for_selector('div[role="main"]', timeout=10000)

        blocos = page.locator("div.RcCsl")
        qtd = blocos.count()

        informacoes_limpas = []

        for i in range(qtd):
            bloco = blocos.nth(i)

            # PARADA: Se encontrou o Plus Code (data-item-id="oloc"), encerra o loop no restaurante
            if bloco.locator('[data-item-id="oloc"]').count() > 0:
                break

            # Processa e limpa os dados do bloco imediatamente
            info_tratada = extrair_texto_bloco(bloco)
            if info_tratada:
                informacoes_limpas.append(info_tratada)

        dados_restaurante = {
            "url": link["url"],
            "informacoes": informacoes_limpas,
        }

        # Exibe o resultado limpo imediatamente
        print(json.dumps(dados_restaurante, indent=2, ensure_ascii=False))
        resultados.append(dados_restaurante)

    return resultados

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        google_maps(page)
        
        # Chamada síncrona direta sem corrotina
        links = extrair_links(page)
        print(f"Total encontrado: {len(links)}")
        print(links)
        salvar_informacoes(page, links)
        browser.close()

if __name__ == "__main__":
    main()