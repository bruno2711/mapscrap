import json
import os
import re
import time
import urllib.request
from datetime import date
import pandas as pd
from playwright.sync_api import Page, expect, sync_playwright

def obter_geolocalizacao_automatica():
    """Busca as coordenadas geográficas automáticas baseadas no IP público atual."""
    try:
        # Consulta API gratuita de IP (retorna lat/lon do seu provedor/conexão)
        with urllib.request.urlopen(
            "https://ipapi.co/json/", timeout=5
        ) as response:
            dados = json.loads(response.read().decode())
            latitude = dados.get("latitude")
            longitude = dados.get("longitude")

            print(
                f"Localização detectada via IP: {dados.get('city')}, {dados.get('region')} ({latitude}, {longitude})"
            )
            return {"latitude": latitude, "longitude": longitude}
    except Exception as e:
        print(f"Não foi possível obter geolocalização automática: {e}")
        # Retorna None caso falhe (o Google Maps tentará usar o IP direto da requisição)
        return None


def google_maps(page: Page):
    page.goto("https://www.google.com/maps")
    print("Abriu o Google Maps com sucesso")
    buscar = input("Digite o que voce quer buscar: ")
    # Preenche a busca e confirma
    search_input = page.locator('input[role="combobox"]')
    search_input.wait_for(state="visible")
    search_input.fill(buscar)
    page.keyboard.press("Enter")

    # Aguarda os resultados carregarem na tela
    page.wait_for_selector('div[role="feed"]', timeout=10000)
    print("Pesquisou restaurantes em São Paulo com sucesso")


def extrair_links(page: Page):
    feed = page.locator('div[role="feed"]')

    # Opcional: Rola um pouco o feed para carregar mais resultados na tela
    for _ in range(3):
        feed.evaluate("el => el.scrollTop += 1000")
        page.wait_for_timeout(1000)

    # Localiza todos os cards de resultado
    cards = page.locator('div[role="article"]')
    count = cards.count()

    links = []
    for i in range(count):
        anchor = cards.nth(i).locator("a.hfpxzc")
        href = anchor.get_attribute("href")
        nome = anchor.get_attribute("aria-label")

        if href:
            links.append({"nome": nome, "url": href})

    return links


def limpar_texto(texto):
    """Remove ícones Unicode privados do Google (\ue000 até \uf8ff) e espaços sobressalentes."""
    texto_limpo = re.sub(r"[\uE000-\uF8FF]", "", texto)
    return texto_limpo.strip()


def extrair_texto_bloco(bloco):
    """Pega o texto do bloco e limpa."""
    raw_text = bloco.inner_text().strip()
    if not raw_text:
        return None

    # Divide por linhas, limpa os ícones de cada uma e remove valores vazios
    linhas = [limpar_texto(line) for line in raw_text.split("\n")]
    linhas = [line for line in linhas if line]

    if not linhas:
        return None

    # Remove duplicidades mantendo a ordem
    linhas_unicas = list(dict.fromkeys(linhas))

    # Junta os itens do bloco em uma única linha
    return " - ".join(linhas_unicas)


def salvar_informacoes(
    page: Page, links: list, arquivo_saida="restaurantes.jsonl"
):
    resultados = []

    for link in links:
        try:
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
                "nome": link.get("nome"),
                "url": link["url"],
                "informacoes": informacoes_limpas,
            }

            # Salva imediatamente a linha no arquivo .jsonl (modo 'a' = append)
            with open(arquivo_saida, mode="a", encoding="utf-8") as f:
                f.write(
                    json.dumps(dados_restaurante, ensure_ascii=False) + "\n"
                )

            print(f"Salvo no JSONL: {link.get('nome')} | {link['url']}")
            resultados.append(dados_restaurante)

        except Exception as e:
            print(f"Erro ao processar {link['url']}: {e}")

    return resultados


def main():
    # Obtém a localização atual do dispositivo/rede dinamicamente
    coords = obter_geolocalizacao_automatica()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--start-maximized"])

        # Prepara os parâmetros do contexto
        context_args = {
            "no_viewport": True,
            "permissions": ["geolocation"],  # Concede permissão automaticamente
        }

        # Se detectou coordenadas via IP, injeta no contexto do navegador
        if coords:
            context_args["geolocation"] = coords

        context = browser.new_context(**context_args)
        page = context.new_page()

        google_maps(page)

        links = extrair_links(page)
        print(f"Total encontrado: {len(links)}")

        salvar_informacoes(page, links, arquivo_saida="restaurantes.jsonl")
        browser.close()


if __name__ == "__main__":
    main()