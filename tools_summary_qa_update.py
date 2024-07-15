from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pymysql
import os
import markdown
def update_summary_qa_function(post_ID,content,llm):

    summary_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你的角色是美国留学专家，输入内容是一篇与美国留学相关的文章，根据输入的内容对全文进行总结，并在最后估计全文的阅读时间，输出内容250字左右，不分段，只包含总结内容不包含任何标题。""",
            ),
            ("human", "文章内容: {content}"),
        ]
    )
    summary_chain = summary_prompt | llm | StrOutputParser()
    summary = summary_chain.invoke({"content": content})
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是美国留学领域的专家。用户将输入一段关于美国留学相关的文章，请你根据该文章内容提出5个读者可能会感兴趣的问题，并分别提供详细的回答。\
                请确保每个问题都与该文章内容紧密相关，并对读者具有实用价值。输出结果请勿将所有问题集中在一起展示，应该按以下格式逐个显示问题和答案，每个问题后面紧接其对应的回答。以下是最终输出格式的例子：
                '大家都在问的问题：
                问题1: 美国大学申请的截止日期是什么时候？
                美国大学的申请截止日期通常在每年的1月1日或1月15日，但具体时间可能因学校而异。建议学生提前查阅各个大学的官方网站以获取准确信息。
                问题2: 美国留学需要准备哪些材料？
                申请美国留学通常需要准备以下材料：高中成绩单、托福或雅思成绩、SAT或ACT成绩、推荐信、个人陈述、课外活动证明等。不同的大学可能有额外的要求，建议学生仔细阅读申请指南。
                ...'
                请确保按照上述格式输出结果。""",
            ),
            ("human", "文章内容: {content}"),
        ]
    )
    qa_chain = qa_prompt | llm | StrOutputParser()
    qa = qa_chain.invoke({"content": content})
    connection = pymysql.connect(
        db=os.environ["db_name"],
        user=os.environ["db_user"],
        passwd=os.environ["db_pass"],
        host=os.environ["db_host"],
        port=3306,
        cursorclass=pymysql.cursors.DictCursor,
    )
    cursor = connection.cursor()
    query = """INSERT INTO fp_chatGPT.`posts`(`post_ID`, `Summary`, `QandA`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE `Summary`=%s,`QandA`=%s"""
    cursor.execute(
        query, (post_ID, summary, markdown.markdown(qa), summary, markdown.markdown(qa))
    )
    connection.commit()
    cursor.close()
    connection.close()
    return