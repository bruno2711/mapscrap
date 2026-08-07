import json
import os
import re
import time
import pandas as pd
from playwright.sync_api import Page, sync_playwright


def identificar_e_mapear_dados(informacoes_limpas):
    """Analisa a lista dinâmica de blocos e categoriza cada item nas colunas do CSV."""
    dados_mapeados = {
        "endereco": "",
        "telefone": "",
        "website": "",
        "faixa_preco": "",
        "outras_informacoes": [],
    }

    for info in informacoes_limpas:
        # 1. Telefone (Padrão com DDD/país)
        if re.search(r"\+?\d{2,3}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", info):
            dados_mapeados["telefone"] = info

        # 2. Website ou Link de Reserva
        elif re.search(
            r"(https?://|\.com|\.br|\.net|\.org|tagme|iFood)",
            info,
            re.IGNORECASE,
        ):
            if not dados_mapeados["website"]:
                dados_mapeados["website"] = info
            else:
                dados_mapeados["outras_informacoes"].append(info)

        # 3. Faixa de preço (Simbolizada por R$, $, ou 'por pessoa')
        elif re.search(r"(R\$|\$|\bpor pessoa\b)", info, re.IGNORECASE):
            dados_mapeados["faixa_preco"] = info

        # 4. Endereço
        elif re.search(
            r"(- RS|- SP|- RJ|\d{5}-\d{3}|R\.|Rua|Av\.|Avenida|Alameda|Praça)",
            info,
            re.IGNORECASE,
        ):
            dados_mapeados["endereco"] = info

        # 5. Outras informações
        else:
            dados_mapeados["outras_informacoes"].append(info)

    dados_mapeados["outras_informacoes"] = " | ".join(
        dados_mapeados["outras_informacoes"]
    )
    return dados_mapeados


def google_maps(page: Page, termo_busca: str):
    page.goto("https://www.google.com/maps")
    print("Abriu o Google Maps com sucesso")

    search_input = page.locator('input[role="combobox"]')
    search_input.wait_for(state="visible")

    # Digita exatamente o termo passado (sem cidade nem local fixo)
    search_input.fill(termo_busca)
    page.keyboard.press("Enter")

    page.wait_for_selector('div[role="feed"]', timeout=10000)
    print(f"Pesquisou por '{termo_busca}'")


def rolar_feed_para_mais_resultados(
    page: Page, max_tentativas_sem_novos: int = 5
):
    """Rola o painel lateral continuamente para pegar todos os resultados disponíveis."""
    feed = page.locator('div[role="feed"]')
    print("Iniciando rolagem para carregar mais resultados...")

    cards = page.locator('div[role="article"]')
    qtd_anterior = 0
    tentativas = 0

    while tentativas < max_tentativas_sem_novos:
        # Rola o elemento do feed até o fim
        feed.evaluate("el => el.scrollTop = el.scrollHeight")
        page.wait_for_timeout(2000)  # Aguarda carregar mais cards

        qtd_atual = cards.count()

        # Verifica se o Google indicou o fim da lista
        fim_da_lista = (
            page.locator(
                'span:has-text("Você chegou ao fim da lista")'
            ).count()
            > 0
            or page.locator(
                'span:has-text("You\'ve reached the end of the list")'
            ).count()
            > 0
        )

        if fim_da_lista:
            print("Chegou ao fim dos resultados do Google Maps.")
            break

        if qtd_atual == qtd_anterior:
            tentativas += 1
            print(
                f"Aguardando novos resultados... ({tentativas}/{max_tentativas_sem_novos})"
            )
        else:
            tentativas = 0
            qtd_anterior = qtd_atual
            print(f"Carregados até agora: {qtd_atual} locais")

    print(f"Total de resultados encontrados: {cards.count()}")


def extrair_links(page: Page):
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
    texto_limpo = re.sub(r"[\uE000-\uF8FF]", "", texto)
    return texto_limpo.strip()


def extrair_texto_bloco(bloco):
    raw_text = bloco.inner_text().strip()
    if not raw_text:
        return None

    linhas = [limpar_texto(line) for line in raw_text.split("\n")]
    linhas = [line for line in linhas if line]

    if not linhas:
        return None

    linhas_unicas = list(dict.fromkeys(linhas))
    return " - ".join(linhas_unicas)


def processar_e_salvar_dados(
    page: Page, links: list, nome_base: str = "resultados"
):
    lista_final_mapeada = []
    arquivo_jsonl = f"{nome_base}.jsonl"
    arquivo_csv = f"{nome_base}.csv"

    for idx, link in enumerate(links, start=1):
        try:
            page.goto(link["url"])
            page.wait_for_selector('div[role="main"]', timeout=10000)

            blocos = page.locator("div.RcCsl")
            qtd = blocos.count()

            informacoes_limpas = []

            for i in range(qtd):
                bloco = blocos.nth(i)

                # Parada ao encontrar o Plus Code
                if bloco.locator('[data-item-id="oloc"]').count() > 0:
                    break

                info_tratada = extrair_texto_bloco(bloco)
                if info_tratada:
                    informacoes_limpas.append(info_tratada)

            dados_categorizados = identificar_e_mapear_dados(informacoes_limpas)

            registro = {
                "nome": link.get("nome", ""),
                "url": link["url"],
                "telefone": dados_categorizados["telefone"],
                "website": dados_categorizados["website"],
                "endereco": dados_categorizados["endereco"],
                "faixa_preco": dados_categorizados["faixa_preco"],
                "outras_informacoes": dados_categorizados["outras_informacoes"],
            }

            lista_final_mapeada.append(registro)

            # Salva no JSONL em tempo real
            with open(arquivo_jsonl, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")

            print(f"[{idx}/{len(links)}] Salvo: {registro['nome']}")

        except Exception as e:
            print(f"Erro ao processar {link['url']}: {e}")

    # Salva tudo finalizado em CSV formatado para Excel
    if lista_final_mapeada:
        df = pd.DataFrame(lista_final_mapeada)
        df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig", sep=";")
        print(
            f"\nFinalizado! {len(lista_final_mapeada)} registros gravados em '{arquivo_csv}'."
        )


def main():
    # Passa apenas o termo genérico desejado sem localização vinculada
    termo = input("Digite o termo de busca (ex: 'restaurantes', 'cafeterias'): ").strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--start-maximized"])

        # Contexto sem geolocalização forçada (usa a geolocalização nativa do navegador/IP)
        context = browser.new_context(
            no_viewport=True,
            permissions=["geolocation"],
        )
        page = context.new_page()

        google_maps(page, termo_busca=termo)

        # Rola até o final para superar o limite de visualização inicial
        rolar_feed_para_mais_resultados(page, max_tentativas_sem_novos=5)

        links = extrair_links(page)
        print(f"Total de links coletados: {len(links)}")

        processar_e_salvar_dados(
            page, links, nome_base="extracao_restaurantes"
        )

        browser.close()


if __name__ == "__main__":
    main()