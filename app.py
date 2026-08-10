import json
import re
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
from playwright.async_api import async_playwright

app = FastAPI(
    title="Google Maps Scraper API",
    version="1.0.0",
    description="API de extração dinâmica de leads do Google Maps",
)

# Armazenamento temporário de status (em produção, usar PostgreSQL/Redis)
JOBS_DB = {}


class ScrapeRequest(BaseModel):
    termo: str
    max_resultados: int = 20


def identificar_e_mapear_dados(informacoes_limpas):
    dados_mapeados = {
        "endereco": "",
        "telefone": "",
        "website": "",
        "faixa_preco": "",
        "outras_informacoes": [],
    }

    for info in informacoes_limpas:
        if re.search(r"\+?\d{2,3}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", info):
            dados_mapeados["telefone"] = info
        elif re.search(
            r"(https?://|\.com|\.br|\.net|\.org|tagme|iFood)",
            info,
            re.IGNORECASE,
        ):
            if not dados_mapeados["website"]:
                dados_mapeados["website"] = info
            else:
                dados_mapeados["outras_informacoes"].append(info)
        elif re.search(r"(R\$|\$|\bpor pessoa\b)", info, re.IGNORECASE):
            dados_mapeados["faixa_preco"] = info
        elif re.search(
            r"(- RS|- SP|- RJ|\d{5}-\d{3}|R\.|Rua|Av\.|Avenida|Alameda|Praça)",
            info,
            re.IGNORECASE,
        ):
            dados_mapeados["endereco"] = info
        else:
            dados_mapeados["outras_informacoes"].append(info)

    dados_mapeados["outras_informacoes"] = " | ".join(
        dados_mapeados["outras_informacoes"]
    )
    return dados_mapeados


async def executar_scraping_job(job_id: str, termo: str, max_resultados: int):
    """Executa a raspagem de forma assíncrona em segundo plano."""
    JOBS_DB[job_id] = {"status": "processing", "progresso": 0}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(permissions=["geolocation"])
        page = await context.new_page()

        try:
            await page.goto("https://www.google.com/maps")
            search_input = page.locator('input[role="combobox"]')
            await search_input.wait_for(state="visible")
            await search_input.fill(termo)
            await page.keyboard.press("Enter")

            await page.wait_for_selector('div[role="feed"]', timeout=15000)

            # Rolar feed
            feed = page.locator('div[role="feed"]')
            cards = page.locator('div[role="article"]')

            while await cards.count() < max_resultados:
                await feed.evaluate("el => el.scrollTop = el.scrollHeight")
                await page.wait_for_timeout(2000)

                fim_da_lista = (
                    await page.locator(
                        'span:has-text("Você chegou ao fim da lista")'
                    ).count()
                    > 0
                )
                if fim_da_lista:
                    break

            # Extrair links
            qtd = await cards.count()
            links = []
            for i in range(min(qtd, max_resultados)):
                anchor = cards.nth(i).locator("a.hfpxzc")
                href = await anchor.get_attribute("href")
                nome = await anchor.get_attribute("aria-label")
                if href:
                    links.append({"nome": nome, "url": href})

            # Processar cada link
            resultados = []
            for idx, link in enumerate(links, start=1):
                try:
                    await page.goto(link["url"])
                    await page.wait_for_selector(
                        'div[role="main"]', timeout=10000
                    )

                    blocos = page.locator("div.RcCsl")
                    qtd_blocos = await blocos.count()
                    info_limpas = []

                    for b in range(qtd_blocos):
                        bloco = blocos.nth(b)
                        if (
                            await bloco.locator(
                                '[data-item-id="oloc"]'
                            ).count()
                            > 0
                        ):
                            break
                        txt = (await bloco.inner_text()).strip()
                        if txt:
                            info_limpas.append(txt.replace("\n", " - "))

                    dados = identificar_e_mapear_dados(info_limpas)
                    resultados.append(
                        {
                            "nome": link.get("nome", ""),
                            "url": link["url"],
                            "telefone": dados["telefone"],
                            "website": dados["website"],
                            "endereco": dados["endereco"],
                            "faixa_preco": dados["faixa_preco"],
                            "outras_informacoes": dados["outras_informacoes"],
                        }
                    )
                except Exception:
                    continue

            # Salvar em CSV
            filename = f"job_{job_id}.csv"
            df = pd.DataFrame(resultados)
            df.to_csv(filename, index=False, encoding="utf-8-sig", sep=";")

            JOBS_DB[job_id] = {
                "status": "completed",
                "total_extraido": len(resultados),
                "arquivo": filename,
            }

        except Exception as e:
            JOBS_DB[job_id] = {"status": "failed", "erro": str(e)}

        finally:
            await browser.close()


@app.post("/v1/scrape", status_code=202)
async def iniciar_scraping(
    payload: ScrapeRequest, background_tasks: BackgroundTasks
):
    import uuid

    job_id = str(uuid.uuid4())[:8]

    # Envia a tarefa para rodar em segundo plano sem travar a resposta da API
    background_tasks.add_task(
        executar_scraping_job, job_id, payload.termo, payload.max_resultados
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "mensagem": "Extração iniciada em segundo plano.",
        "checar_status": f"/v1/jobs/{job_id}",
    }


@app.get("/v1/jobs/{job_id}")
async def checar_status(job_id: str):
    if job_id not in JOBS_DB:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    job = JOBS_DB[job_id]
    if job["status"] == "completed":
        return {
            "job_id": job_id,
            "status": "completed",
            "total_extraido": job["total_extraido"],
            "download_url": f"/v1/jobs/{job_id}/download",
        }

    return {"job_id": job_id, "status": job["status"]}


@app.get("/v1/jobs/{job_id}/download")
async def download_resultado(job_id: str):
    if job_id not in JOBS_DB or JOBS_DB[job_id]["status"] != "completed":
        raise HTTPException(
            status_code=400, detail="Arquivo ainda não está pronto."
        )

    filename = JOBS_DB[job_id]["arquivo"]
    return FileResponse(
        path=filename, filename=f"leads_{job_id}.csv", media_type="text/csv"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)