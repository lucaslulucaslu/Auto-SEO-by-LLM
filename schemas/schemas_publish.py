import operator
from typing import Annotated, List, TypedDict

from pydantic import BaseModel, Field


class DocumentType(BaseModel):
    topic: str
    url: str
    title: str
    summary: str


class OutlineSection(BaseModel):
    title: str = Field(description="section title.")
    description: str = Field(description="Section description.")
    words: str = Field(description="Estimate section word count.")


class OutlinesList(BaseModel):
    sections: list[OutlineSection]


class SummaryOutput(BaseModel):
    title: str = Field(description="title for the news article, must be in English")
    summary: str = Field(description="summary for the news article, must be in English")


class MorePoints(BaseModel):
    more: list[str] = Field(
        description="Search query for topics that can be discussed, the output search query should be purely in English."
    )


class MetaFormat(BaseModel):
    title: str = Field(
        description="与文章内容相关的文章中文标题，长度在20到30个中文字，用中文输出"
    )
    title_en: str = Field(
        description="与文章内容相关的文章英文标题，长度在10到20个英文单词，用英文输出"
    )
    image_query: str = Field(
        description="a detailed prompt to generate an image that based on the article content, should be in English, output only one image prompt"
    )
    image_filename: str = Field(
        description="a good name for the image file without file extension, should be in English"
    )
    image_alt_text: str = Field(
        description="生成图片的中文alt text，15个汉字以内，用中文输出"
    )
    image_alt_text_en: str = Field(
        description="alt text for generated image, 7 words max"
    )
    tags: List[str] = Field(description="与文章内容相关的中文标签，用中文输出")
    tags_en: List[str] = Field(description="与文章内容相关的英文标签，用英文输出")


class GraphState(TypedDict):
    url: str
    summary: str
    topics: list[str]
    documents: Annotated[list[DocumentType], operator.add]
    sections: list[OutlineSection]
    sections_en: list[OutlineSection]
    write_sections: Annotated[list, operator.add]
    write_sections_en: Annotated[list, operator.add]
    image_query: str
    title: str
    title_en: str
    content: str
    content_en: str
    tags: set
    tags_en: set
    image_url: str
    image_url_en: str
    image_ID: int
    image_ID_en: int
    image_filename: str
    image_alt: str = "美国续航教育大学相关新闻配图"
    image_alt_en: str = "Forward Pathway News Image"
