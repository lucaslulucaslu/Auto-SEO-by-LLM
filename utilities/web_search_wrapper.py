from langchain_community.utilities import GoogleSerperAPIWrapper


def web_search_wrapper(query, type="news"):
    search = GoogleSerperAPIWrapper(type=type)
    return search.results(query)
