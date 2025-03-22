import base64
import os
import re

import markdown2
import markdownify
import pandas as pd
import pymysql
import requests
from bs4 import BeautifulSoup

from utilities.llm_wrapper import llm_wrapper

wp_url = "https://www.forwardpathway.com/wp-json/wp/v2"
wp_post_url = wp_url + "/posts"
wp_media_url = wp_url + "/media"
wp_tag_url = wp_url + "/tags"

wp_url_en = "https://www.forwardpathway.us/wp-json/wp/v2"
wp_post_url_en = wp_url_en + "/posts"
wp_media_url_en = wp_url_en + "/media"
wp_tag_url_en = wp_url_en + "/tags"

user_id = os.environ["wordpress_username"]
# user app password can be created in the user/edit user/application password
user_app_password = os.environ["wordpress_pass"]
credentials = user_id + ":" + user_app_password
token = base64.b64encode(credentials.encode())
header = {"Authorization": "Basic " + token.decode("utf-8")}

user_id_en = os.environ["wordpress_username_fpus"]
# user app password can be created in the user/edit user/application password
user_app_password_en = os.environ["wordpress_pass_fpus"]
credentials_en = user_id_en + ":" + user_app_password_en
token_en = base64.b64encode(credentials_en.encode())
header_en = {"Authorization": "Basic " + token_en.decode("utf-8")}


def set_news_url_flag(url=""):
    if len(url) > 0:
        connection = pymysql.connect(
            db=os.environ["db_name"],
            user=os.environ["db_user"],
            passwd=os.environ["db_pass"],
            host=os.environ["db_host"],
            port=3306,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cursor = connection.cursor()
        query = "UPDATE fp_chatGPT.news_urls SET post=1 WHERE url=%s"
        cursor.execute(query, url)
        connection.commit()
        cursor.close()
        connection.close()
    return


def get_news_urls():
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()

    query = "SELECT url FROM fp_chatGPT.news_urls WHERE post IS NULL OR post = 0 ORDER BY RAND() LIMIT 1"
    rows_count = cursor.execute(query)
    if rows_count > 0:
        rows = cursor.fetchall()
        urls = [row["url"] for row in rows]
    else:
        urls = []
    cursor.close()
    connection.close()
    return urls


def get_rewrite_post_ID():
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    query = """SELECT t3.ID FROM (SELECT t2.ID,t2.post_modified FROM fp_forwardpathway.`wp_mmcp_term_relationships` t1
JOIN fp_forwardpathway.wp_mmcp_posts t2 ON t2.ID=t1.object_id AND t2.post_status="publish"
AND t2.ID NOT IN (SELECT post_id FROM fp_chatGPT.void_posts)
WHERE t1.`term_taxonomy_id` IN (3,2294,2295,2293,2180,1,1758,35,2350,2351,36,1278,6,3579,3580,3577,3627)
GROUP BY t2.ID ORDER BY t2.post_modified ASC LIMIT 10) t3
ORDER BY RAND() LIMIT 1"""
    cursor.execute(query)
    row = cursor.fetchone()
    post_ID = int(row["ID"])
    cursor.close()
    connection.close()
    return post_ID


def get_keywords_list(lang_type="cn"):
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    query = """select efa,ranking FROM fp_IPEDS.latest_information"""
    cursor.execute(query)
    row = cursor.fetchone()
    ranking_year = row["ranking"]
    efa_year = row["efa"]

    if lang_type == "cn":
        query = """SELECT t1.cname as keyword,concat("https://www.forwardpathway.com/",t1.postid) as url,t2.term_id as tag_id, t3.rank
        FROM fp_ranking.`colleges` t1
        LEFT JOIN fp_forwardpathway.`wp_mmcp_terms` t2 ON t1.cname=REPLACE(t2.name,"相关新闻","") AND t2.name LIKE "%相关新闻"
        LEFT JOIN fp_ranking.us_rankings t3 ON t3.postid=t1.postid AND t3.year={} AND t3.type=1""".format(
            ranking_year
        )
        cursor.execute(query)
        rows = cursor.fetchall()
        keywords_array = []
        for row in rows:
            keywords_array = keywords_array + [row]
        query = """SELECT keyword, url,Null,Null FROM fp_chatGPT.keywords"""
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            keywords_array = keywords_array + [row]
    else:
        query = """SELECT t2.post_title as keyword,concat("https://www.forwardpathway.us/",t2.post_name) as url,t5.term_id as tag_id,t4.rank
            FROM fpus_colleges.transform t1
            JOIN fpus_wordpress.wp_posts t2 ON t2.ID=t1.postid
            JOIN fp_IPEDS.EFA t6 ON t6.UNITID=t1.unitid AND t6.Year={} AND t6.EFALEVEL=1 AND t6.EFTOTLT>1000
            LEFT JOIN fp_ranking.colleges t3 ON t3.unitid=t1.unitid
            LEFT JOIN fp_ranking.us_rankings t4 ON t4.postid=t3.postid AND t4.type=1 AND t4.year={}
            LEFT JOIN fpus_wordpress.wp_terms t5 ON t5.name=t2.post_title""".format(
            efa_year, ranking_year
        )
        cursor.execute(query)
        rows = cursor.fetchall()
        keywords_array = []
        for row in rows:
            keywords_array = keywords_array + [row]
    cursor.close()
    connection.close()

    keywords = pd.DataFrame(
        keywords_array, columns=["keyword", "url", "tag_id", "rank"]
    )
    keywords = keywords.reset_index(drop=True)

    keywords = keywords.reindex(
        keywords["keyword"].str.len().sort_values(ascending=False).index
    ).reset_index(drop=True)

    return (ranking_year, keywords)


def insert_keyword_url(content, lang_type="cn"):
    soup = BeautifulSoup(content, "html.parser")
    tags = set()
    n = 0
    if lang_type == "cn":
        ranking_string = (
            """<span class="current_usnews_ranking">"""
            + """（{}USNews<a href="https://www.forwardpathway.com/ranking">美国大学排名</a>：{}）</span>"""
        )
        (ranking_year, keywords) = get_keywords_list(lang_type="cn")
    else:
        ranking_string = (
            """ <span class="current_usnews_ranking">"""
            + """(<a href="https://www.forwardpathway.us/us-colleges-ranking">{} USNews Ranking</a>: {}) </span>"""
        )
        (ranking_year, keywords) = get_keywords_list(lang_type="en")
    for key, row in keywords.iterrows():
        keyword = row["keyword"].replace("-Main Campus", "")
        url = row["url"]
        tag_id = row["tag_id"]
        rank = row["rank"]
        new_tag = soup.new_tag("a", href=url)
        new_tag.string = keyword
        void_tags_a = ["a"]
        void_tags_h = ["h1", "h2", "h3", "h4"]
        pattern = re.compile(keyword)
        results = soup.find_all(string=pattern)
        for string_element in results:
            parents_set = set([x.name for x in string_element.parents])
            if any([x in parents_set for x in void_tags_a]):
                continue
            if not pd.isna(tag_id):
                tags.add(tag_id)
            if any([x in parents_set for x in void_tags_h]):
                continue
            if pd.isna(rank) or n > 0:
                new_element = BeautifulSoup(
                    string_element.replace(keyword, str(new_tag), 1), "html.parser"
                )
            else:
                new_element = BeautifulSoup(
                    string_element.replace(
                        keyword,
                        str(new_tag) + ranking_string.format(ranking_year, int(rank)),
                        1,
                    ),
                    "html.parser",
                )
            string_element = string_element.replace_with(new_element)
            n = n + 1
            break
    return (str(soup), tags)


def retrieve_wordpress_post(post_ID, lang_type="cn"):
    if lang_type == "en":
        response = requests.get(wp_post_url_en + "/" + str(post_ID), headers=header_en)
    else:
        response = requests.get(wp_post_url + "/" + str(post_ID), headers=header)
    return response


def retrieve_wordpress_image(image_ID, lang_type="cn"):
    if lang_type == "en":
        response = requests.get(
            wp_media_url_en + "/" + str(image_ID), headers=header_en
        )
    else:
        response = requests.get(wp_media_url + "/" + str(image_ID), headers=header)
    return response


def check_insert_image(content, feature_image_ID, lang_type="cn"):
    if content.find("<img") > 0:
        return content
    elif feature_image_ID > 0:
        response = retrieve_wordpress_image(feature_image_ID, lang_type).json()
        image_url = response["guid"]["rendered"]
        alt_text = response["alt_text"]
        content_sep = len(content) // 3
        content = content[:content_sep] + content[content_sep:].replace(
            """</p>\n""",
            """</p>\n<img src="{}" alt="{}">""".format(image_url, alt_text),
            1,
        )
    else:
        content = content  # here we can generate image from Dall-E
    return content


def post_wordpress_post(
    post_title,
    post_body,
    post_ID=-1,
    categories=-1,
    tags=-1,
    featured_media_id=-1,
    lang_type="cn",
    comment_status=-1,
):

    post_data = {
        "title": post_title,
        "content": post_body,
        # "comment_status": "closed",
        # "categories": [3627],  # 美国大学相关新闻category
        # "tags": list(tags),
        "status": "publish",
        # "featured_media": featured_media_id,
    }
    if categories != -1:
        post_data["categories"] = categories
    if tags != -1:
        post_data["tags"] = list(tags)
    if featured_media_id != -1:
        post_data["featured_media"] = featured_media_id
    if comment_status != -1:
        post_data["comment_status"] = comment_status
    if lang_type == "en":
        url = wp_post_url_en
        h = header_en
    else:
        url = wp_post_url
        h = header
    if post_ID != -1:
        url = url + "/" + str(post_ID)

    response = requests.post(url, headers=h, json=post_data)
    return response


def post_wordpress_file(file_path, lang_type="cn"):
    with open(file_path, "rb") as file:
        media = {
            "file": file,
            "caption": "LLM_auto_post_file_" + file_path,
        }
        if lang_type == "en":
            response = requests.post(wp_media_url_en, headers=header_en, files=media)
        else:
            response = requests.post(wp_media_url, headers=header, files=media)
    return response


def tags_to_IDs(tag_names=[]):
    tags = set()
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    for tag_name in tag_names:
        tag_name = tag_name.replace("&", "&amp;")
        query = """SELECT t1.term_id FROM fp_forwardpathway.wp_mmcp_terms t1 \
            JOIN fp_forwardpathway.wp_mmcp_term_taxonomy t2 ON t2.term_id=t1.term_id AND t2.taxonomy="post_tag" WHERE t1.name=%s"""
        rows_count = cursor.execute(query, tag_name)
        if rows_count > 0:
            result = cursor.fetchone()
            tags.add(result["term_id"])
        else:
            tag_data = {"name": tag_name}
            response = requests.post(wp_tag_url, headers=header, json=tag_data)
            tags.add(response.json()["id"])

    cursor.close()
    connection.close()
    return tags


def tags_to_IDs_en(tag_names=[]):
    tags = set()
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    for tag_name in tag_names:
        tag_name = tag_name.replace("&", "&amp;")
        query = """SELECT t1.term_id FROM fpus_wordpress.wp_terms t1 JOIN fpus_wordpress.wp_term_taxonomy t2 ON t2.term_id=t1.term_id \
            AND t2.taxonomy="post_tag" WHERE t1.name=%s"""
        rows_count = cursor.execute(query, tag_name)
        if rows_count > 0:
            result = cursor.fetchone()
            tags.add(result["term_id"])
        else:
            tag_data = {"name": tag_name}
            response = requests.post(wp_tag_url_en, headers=header_en, json=tag_data)
            tags.add(response.json()["id"])

    cursor.close()
    connection.close()
    return tags


def update_summary_qa(post_ID, content):

    system_prompt = """你的角色是美国留学专家，输入内容是一篇与美国留学相关的文章，根据输入的内容对全文进行总结，并在最后根据文章长度估计全文的阅读时间，\
        输出内容250字左右，不分段，只包含总结内容不包含任何标题。"""
    user_prompt = f"文章内容: {content}"
    summary = llm_wrapper(system_prompt, user_prompt).strip()
    system_prompt = """你是美国留学领域的专家。用户将输入一段关于美国留学相关的文章，请你根据该文章内容提出5个读者可能会感兴趣的问题，并分别提供详细的回答。\
                请确保每个问题都与该文章内容紧密相关，并对读者具有实用价值。输出结果请勿将所有问题集中在一起展示，应该按以下格式逐个显示问题和答案，每个问题后面紧接其对应的回答。以下是最终输出格式的例子：
                '大家都在问的问题：
                问题1: 美国大学申请的截止日期是什么时候？
                美国大学的申请截止日期通常在每年的1月1日或1月15日，但具体时间可能因学校而异。建议学生提前查阅各个大学的官方网站以获取准确信息。
                问题2: 美国留学需要准备哪些材料？
                申请美国留学通常需要准备以下材料：高中成绩单、托福或雅思成绩、SAT或ACT成绩、推荐信、个人陈述、课外活动证明等。不同的大学可能有额外的要求，建议学生仔细阅读申请指南。
                ...'
                请确保按照上述格式输出结果。"""
    user_prompt = f"文章内容: {content}"
    qa = llm_wrapper(system_prompt, user_prompt).strip()
    qa = markdown2.markdown(qa).replace("</p>\n\n<p>", "</p>\n<p>")
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    query = """INSERT INTO fp_chatGPT.`posts`(`post_ID`, `Summary`, `QandA`) VALUES (%s,%s,%s) \
        ON DUPLICATE KEY UPDATE `Summary`=%s,`QandA`=%s"""
    cursor.execute(query, (post_ID, summary, qa, summary, qa))
    connection.commit()
    cursor.close()
    connection.close()
    return


def image_insert_fuc(content):
    paragraphs = content.split("\n\n")
    middle_index = len(paragraphs) // 2
    paragraphs.insert(middle_index, "[image_placeholder]")
    new_content = "\n\n".join(paragraphs)
    return new_content


def replace_amcharts_code(content):
    amcharts = re.finditer(r"""\[amcharts id="chart\-(\d+)"\]""", content)
    for amchart in amcharts:
        amchart_id = amchart.group(1)
        content = content.replace(
            """[amcharts id="chart-{}"]""".format(amchart_id),
            """<div id="amcharts-{}">[amcharts id="chart-{}"]</div>""".format(
                amchart_id, amchart_id
            ),
        )
    return content


def replace_videos_code(content):
    videos = re.finditer(r"""\[video poster="(.*)" src="(.*)"\]""", content)
    for video in videos:
        video_poster = video.group(1)
        video_src = video.group(2)
        content = content.replace(
            """[video poster="{}" src="{}"]""".format(video_poster, video_src),
            """<figure class="wp-block-video"><video controls="" poster="{}" preload="none" src="{}"></video></figure>""".format(
                video_poster, video_src
            ),
        )
    return content


def html_to_markdown(raw_html: str):
    soup_content = BeautifulSoup(raw_html, "html.parser")
    imgs = soup_content.find_all("img")
    remove_attrs = set(["srcset", "class", "decoding", "height", "sizes", "width"])
    for img in imgs:
        img_attrs = dict(img.attrs)
        for img_attr in img_attrs:
            if img_attr in remove_attrs:
                del img.attrs[img_attr]
    if soup_content is not None:
        elements = soup_content.find_all(
            True,
            class_=[
                "crp_related",
                "topBanner",
                "bottomBanner",
                "wp-block-advgb-summary",
                "yoast-table-of-contents",
                "exclusiveStatement",
                "companyLocation",
                "CommentsAndShare",
                "AI_Summary",
                "AI_QA",
                "btn-group",
                "current_usnews_ranking",
            ],
        )
        for element in elements:
            element.decompose()  # delete elements in class array
        elements = soup_content.find_all(
            True,
            id=[
                "crp_related",
            ],
        )
        for element in elements:
            element.decompose()  # delete elements in id array
        elements = soup_content.findAll(["svg", "style", "script", "noscript"])
        for element in elements:
            element.decompose()  # delete elements of other types like scripts and style
        amcharts = soup_content.find_all("div", id=re.compile("^amcharts-"))
        for amchart_element in amcharts:  # replace amcharts with amcharts shortcode
            amchart_id = amchart_element.get("id").replace("amcharts-", "")
            amchart_element.replace_with(
                """[amcharts id="chart-{}"]""".format(amchart_id)
            )

        videos = soup_content.find_all("figure", class_="wp-block-video")
        for video in videos:
            video_poster = video.video.attrs["poster"]
            video_src = video.video.attrs["src"]
            video.replace_with(
                """[video poster="{}" src="{}"]""".format(video_poster, video_src)
            )
    content = markdownify.markdownify(str(soup_content), escape_misc=False)
    return content
