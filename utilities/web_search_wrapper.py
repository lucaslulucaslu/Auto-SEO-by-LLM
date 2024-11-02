from langchain_community.utilities import GoogleSerperAPIWrapper

search = GoogleSerperAPIWrapper(type="news")


def web_search_wrapper(query):
    return search.results(query)
