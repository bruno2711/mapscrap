import os
import re
import time
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
        
        browser.close()

if __name__ == "__main__":
    main()