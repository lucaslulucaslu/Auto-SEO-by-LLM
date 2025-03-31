from playwright.sync_api import sync_playwright
from utilities.web_loader_wrapper import web_loader_wrapper
from urllib.parse import urljoin
from playwright.sync_api import TimeoutError

def get_links_js(url, selector):
    hrefs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=10000)
        except TimeoutError as e:
            print(f"Error loading page: {e}")
        links = page.query_selector_all(selector)
        for link in links:
            hrefs.append(link.get_attribute('href'))
        browser.close()
        return hrefs

def get_content_js(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=10000)
        except TimeoutError as e:
            print(f"Error loading page: {e}")
        content = page.eval_on_selector('body', 'element => element.innerText')
        browser.close()
        return content
    
test_link ="https://www.rutgers.edu/news/all"
hrefs = get_links_js(test_link,'article.cc--news-card  h3 > a')
print(hrefs)
print("--------------------------------------------------")
print(get_content_js(urljoin(test_link,hrefs[0])))