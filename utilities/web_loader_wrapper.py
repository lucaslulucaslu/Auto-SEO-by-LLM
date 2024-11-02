from langchain_community.document_loaders import WebBaseLoader


def web_loader_wrapper(url):
    loader = WebBaseLoader(url, requests_kwargs={"timeout": 10}, raise_for_status=True)
    docs = loader.load()
    content = docs[0].page_content
    return content
