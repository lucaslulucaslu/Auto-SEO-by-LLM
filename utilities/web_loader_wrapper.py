from langchain_community.document_loaders import WebBaseLoader
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError

def web_loader_wrapper(url):
    loader = WebBaseLoader(url, requests_kwargs={"timeout": 10}, raise_for_status=True)
    docs = loader.load()
    content = docs[0].page_content
    return content


def web_loader_docs(urls):
    loader = WebBaseLoader(urls, requests_kwargs={"timeout": 10}, raise_for_status=True)
    docs = loader.load()
    return docs

def get_links(url, selector):
    hrefs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=10000)
        except TimeoutError as _e:
            pass
        links = page.query_selector_all(selector)
        for link in links:
            hrefs.append(link.get_attribute('href'))
        browser.close()
        return hrefs

def web_loader_js(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=10000)
        except TimeoutError as _e:
            pass
        content = page.eval_on_selector("body", "element => element.innerText")
        browser.close()
        return content