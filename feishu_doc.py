# feishu_doc.py
# -*- coding: utf-8 -*-
import logging
import json
import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.wiki.v2 import CreateSpaceNodeRequest, ListSpaceNodeRequest, Node
from typing import List, Dict, Any, Optional
from config import get_config
import datetime

logger = logging.getLogger(__name__)


class FeishuDocManager:
    """飞书云文档管理器 (基于官方 SDK lark-oapi)"""

    def __init__(self,  app_id: str = None, app_secret: str = None, folder_token: str = None, space_id: str = None):
        self.config = get_config()
        self.app_id = app_id or self.config.feishu_app_id
        self.app_secret = app_secret or self.config.feishu_app_secret
        self.folder_token = folder_token or self.config.feishu_folder_token
        self.space_id = space_id or self.config.feishu_space_id

        # 初始化 SDK 客户端
        # SDK 会自动处理 tenant_access_token 的获取和刷新，无需人工干预
        if self.is_configured():
            self.client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .log_level(lark.LogLevel.INFO) \
                .build()
        else:
            self.client = None

    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.app_id and self.app_secret)

    def is_wiki_configured(self) -> bool:
        """检查知识空间配置是否完整"""
        return bool(self.space_id)

    def create_daily_doc(self, title: str, content_md: str) -> Optional[str]:
        """
        创建日报文档
        """
        if not self.client or not self.is_configured():
            logger.warning("飞书 SDK 未初始化或配置缺失，跳过创建")
            return None
        if self.is_wiki_configured():
            return self.create_daily_doc_to_wiki(title, content_md)

        try:
            # 1. 创建文档
            # 使用官方 SDK 的 Builder 模式构造请求
            create_request = CreateDocumentRequest.builder() \
                .request_body(CreateDocumentRequestBody.builder()
                              .folder_token(self.folder_token)
                              .title(title)
                              .build()) \
                .build()

            response = self.client.docx.v1.document.create(create_request)

            if not response.success():
                logger.error(f"创建文档失败: {response.code} - {response.msg} - {response.error}")
                return None

            doc_id = response.data.document.document_id
            # 这里的 domain 只是为了生成链接，实际访问会重定向
            doc_url = f"https://feishu.cn/docx/{doc_id}"
            logger.info(f"飞书文档创建成功: {title} (ID: {doc_id})")

            # 2. 解析 Markdown 并写入内容
            # 将 Markdown 转换为 SDK 需要的 Block 对象列表
            blocks = self._markdown_to_sdk_blocks(content_md)

            # 飞书 API 限制每次写入 Block 数量（建议 50 个左右），分批写入
            batch_size = 50
            doc_block_id = doc_id  # 文档本身也是一个 block

            for i in range(0, len(blocks), batch_size):
                batch_blocks = blocks[i:i + batch_size]

                # 构造批量添加块的请求
                batch_add_request = CreateDocumentBlockChildrenRequest.builder() \
                    .document_id(doc_id) \
                    .block_id(doc_block_id) \
                    .request_body(CreateDocumentBlockChildrenRequestBody.builder()
                                  .children(batch_blocks)  # SDK 需要 Block 对象列表
                                  .index(-1)  # 追加到末尾
                                  .build()) \
                    .build()

                write_resp = self.client.docx.v1.document_block_children.create(batch_add_request)

                if not write_resp.success():
                    logger.error(f"写入文档内容失败(批次{i}): {write_resp.code} - {write_resp.msg}")

            logger.info(f"文档内容写入完成")
            return doc_url

        except Exception as e:
            logger.error(f"飞书文档操作异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def check_wiki_parent_node(self) -> str:
        """
        检查以当前时间的 "2026年1月归档" 形式为标题的节点是否存在，不存在的话就先创建，作为日报文档的父节点，返回节点token
        """
        list_request = ListSpaceNodeRequest.builder() \
            .space_id(self.space_id) \
            .build()
        list_response = self.client.wiki.v2.space_node.list(list_request)
        if not list_response.success():
            print(f"搜索文档失败: {list_response.code} - {list_response.msg} - {list_response.error}")
            return None
        title = f"{datetime.date.today().year}年{datetime.date.today().month}月归档"
        for node in list_response.data.items:
            if node.title == title:
                logger.info(f"父节点已存在: {title} (Token: {node.node_token})")
                return node.node_token
        
        # 创建父节点
        create_request = CreateSpaceNodeRequest.builder() \
            .space_id(self.space_id) \
            .request_body(Node.builder() \
            .node_type('origin') \
            .obj_type('docx') \
            .title(title) \
            .build()) \
            .build()
        create_response = self.client.wiki.v2.space_node.create(create_request)
        if not create_response.success():
            logger.error(f"创建节点失败: {create_response.code} - {create_response.msg} - {create_response.error}")
            return None
        logger.info(f"父节点已创建: {title} (Token: {create_response.data.node.node_token})")
        return create_response.data.node.node_token

    def create_daily_doc_to_wiki(self, title: str, content_md: str) -> Optional[str]:
        """
        创建日报文档到知识空间
        """
        if not self.client or not self.is_configured() or not self.is_wiki_configured():
            logger.warning("飞书 SDK 未初始化或配置缺失，跳过创建")
            return None

        try:
            # 1. 检查父节点是否存在，不存在的话就先创建
            parent = self.check_wiki_parent_node()
            if not parent:
                logger.error("父节点检查或创建失败")
                return None

            # 2. 创建文档节点
            # 使用官方 SDK 的 Builder 模式构造请求
            create_request = CreateSpaceNodeRequest.builder() \
                .space_id(self.space_id) \
                .request_body(Node.builder() \
                .parent_node_token(parent) \
                .node_type('origin') \
                .obj_type('docx') \
                .title(title) \
                .build()) \
                .build()

            response = self.client.wiki.v2.space_node.create(create_request)
            if not response.success():
                logger.error(f"创建文档失败: {response.code} - {response.msg} - {response.error}")
                return None

            doc_id = response.data.node.node_token
            # 这里的 domain 只是为了生成链接，实际访问会重定向
            doc_url = f"https://feishu.cn/wiki/{doc_id}"
            logger.info(f"飞书知识空间文档创建成功: {title} (ID: {doc_id}, URL: {doc_url})")

            # 2. 解析 Markdown 并写入内容
            # 将 Markdown 转换为 SDK 需要的 Block 对象列表
            blocks = self._markdown_to_sdk_blocks(content_md)

            # 飞书 API 限制每次写入 Block 数量（建议 50 个左右），分批写入
            batch_size = 50
            doc_block_id = doc_id  # 文档本身也是一个 block

            for i in range(0, len(blocks), batch_size):
                batch_blocks = blocks[i:i + batch_size]

                # 构造批量添加块的请求
                batch_add_request = CreateDocumentBlockChildrenRequest.builder() \
                    .document_id(doc_id) \
                    .block_id(doc_block_id) \
                    .request_body(CreateDocumentBlockChildrenRequestBody.builder()
                                  .children(batch_blocks)  # SDK 需要 Block 对象列表
                                  .index(-1)  # 追加到末尾
                                  .build()) \
                    .build()

                write_resp = self.client.docx.v1.document_block_children.create(batch_add_request)

                if not write_resp.success():
                    logger.error(f"写入文档内容失败(批次{i}): {write_resp.code} - {write_resp.msg}")

            logger.info(f"知识空间文档内容写入完成")
            return doc_url

        except Exception as e:
            logger.error(f"飞书文档操作异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _markdown_to_sdk_blocks(self, md_text: str) -> List[Block]:
        """
        将简单的 Markdown 转换为飞书 SDK 的 Block 对象
        """
        blocks = []
        lines = md_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 默认普通文本 (Text = 2)
            block_type = 2
            text_content = line

            # 识别标题
            if line.startswith('# '):
                block_type = 3  # H1
                text_content = line[2:]
            elif line.startswith('## '):
                block_type = 4  # H2
                text_content = line[3:]
            elif line.startswith('### '):
                block_type = 5  # H3
                text_content = line[4:]
            elif line.startswith('---'):
                # 分割线
                blocks.append(Block.builder()
                              .block_type(22)
                              .divider(Divider.builder().build())
                              .build())
                continue

            # 构造 Text 类型的 Block
            # SDK 的结构嵌套比较深: Block -> Text -> elements -> TextElement -> TextRun -> content
            text_run = TextRun.builder() \
                .content(text_content) \
                .text_element_style(TextElementStyle.builder().build()) \
                .build()

            text_element = TextElement.builder() \
                .text_run(text_run) \
                .build()

            text_obj = Text.builder() \
                .elements([text_element]) \
                .style(TextStyle.builder().build()) \
                .build()

            # 根据 block_type 放入正确的属性容器
            block_builder = Block.builder().block_type(block_type)

            if block_type == 2:
                block_builder.text(text_obj)
            elif block_type == 3:
                block_builder.heading1(text_obj)
            elif block_type == 4:
                block_builder.heading2(text_obj)
            elif block_type == 5:
                block_builder.heading3(text_obj)

            blocks.append(block_builder.build())

        return blocks