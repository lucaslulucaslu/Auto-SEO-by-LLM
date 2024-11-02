from typing import TypedDict

from pydantic import BaseModel, Field


class GraphState(TypedDict):
    post_ID: int
    URL: str
    post_title: str
    raw_html: str
    original_content: str
    text_content: str
    revised_content: str
    revises: list
    tags: set
    feature_image_ID: int


class ReviseSingle(BaseModel):
    comment: str = Field(description="文章内容具体修改意见")
    search_query: str = Field(
        description="文章内容修改所需资料的具体英文搜索词条，可以用该词条在Google上搜索所需的资料来修改文章"
    )


class ReviseOutput(BaseModel):
    revises: list[ReviseSingle] = Field(
        description="包含文章内容修改意见和具体搜索词条的数组"
    )


class PostTitleTags(BaseModel):
    title: str = Field(description="根据文章内容更新后的新标题")
    tags: list[str] = Field(description="根据文章内容生成的标签")
