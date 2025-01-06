import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pypandoc
import yaml
from datetime import datetime
from PIL import Image
import aiohttp
import asyncio
import aiofiles

from ..interfaces.output_generator import IOutputGenerator
from ..interfaces.document_parser import Document, Metadata, ContentBlock
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EPUBGenerator(IOutputGenerator):
    """EPUB 生成器实现类"""

    def __init__(self, config: Config):
        """初始化 EPUB 生成器

        Args:
            config: 配置对象
        """
        self.config = config
        self.template_dir = Path(config.template_dir)
        self.style_dir = self.template_dir / "styles"
        self.temp_dir = Path(config.temp_dir)
        self.assets_dir = Path(config.assets_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, document: Document, metadata: Metadata) -> bytes:
        """生成 EPUB 文件

        Args:
            document: 处理后的文档
            metadata: 文档元数据

        Returns:
            EPUB 文件的二进制数据
        """
        try:
            # 1. 创建临时工作目录
            with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp_dir:
                temp_dir = Path(temp_dir)

                # 2. 处理封面图片
                cover_path = await self._process_cover(metadata, temp_dir)
                if cover_path:
                    metadata.cover_image = str(cover_path.relative_to(temp_dir))
                    logger.info(f"设置封面图片路径: {metadata.cover_image}")

                # 3. 生成 YAML 元数据文件
                metadata_file = temp_dir / "metadata.yaml"
                await self._write_metadata(metadata_file, metadata)

                # 4. 生成临时 Markdown 文件
                content_file = temp_dir / "content.md"
                self._write_content(content_file, document)

                # 5. 复制样式文件
                style_file = self.style_dir / "epub.css"
                if style_file.exists():
                    target_style = temp_dir / "style.css"
                    target_style.write_text(style_file.read_text())
                    logger.info("已复制样式文件")

                # 6. 使用 pandoc 生成 EPUB
                output_file = temp_dir / "output.epub"
                self._generate_epub(
                    content_file=content_file,
                    metadata_file=metadata_file,
                    style_file=style_file if style_file.exists() else None,
                    output_file=output_file,
                    temp_dir=temp_dir,
                )

                # 7. 读取生成的文件
                return output_file.read_bytes()

        except Exception as e:
            logger.error(f"EPUB 生成失败: {e}")
            raise

    async def _process_cover(
        self, metadata: Metadata, temp_dir: Path
    ) -> Optional[Path]:
        """处理封面图片

        Args:
            metadata: 文档元数据
            temp_dir: 临时目录

        Returns:
            处理后的封面图片路径
        """
        # 创建图片目录
        images_dir = temp_dir / "images"
        images_dir.mkdir(exist_ok=True)
        target_path = images_dir / "cover.jpg"

        # 获取封面图片路径
        cover_path = None

        # 1. 尝试从豆瓣元数据获取封面
        if hasattr(metadata, "douban_metadata") and metadata.douban_metadata:
            cover_url = metadata.douban_metadata.get("cover_url")
            if cover_url:
                logger.info(f"尝试从豆瓣下载封面图片: {cover_url}")
                if await self._download_cover_image(cover_url, target_path):
                    logger.info(f"成功下载豆瓣封面图片到: {target_path}")
                    return target_path

        # 2. 尝试使用本地封面图片
        if not cover_path and hasattr(metadata, "cover_image") and metadata.cover_image:
            source_path = Path(metadata.cover_image)
            if source_path.exists():
                logger.info(f"使用本地封面图片: {source_path}")
                try:
                    with Image.open(source_path) as img:
                        # 调整大小
                        img = self._resize_cover(img)
                        # 保存
                        img.save(target_path, "JPEG", quality=95)
                        logger.info(f"成功处理并保存本地封面图片到: {target_path}")
                        return target_path
                except Exception as e:
                    logger.error(f"处理本地封面图片失败: {e}")

        # 3. 尝试使用默认封面
        if not cover_path:
            default_cover = Path(self.config.default_cover)
            if default_cover.exists():
                logger.info(f"使用默认封面图片: {default_cover}")
                try:
                    with Image.open(default_cover) as img:
                        # 调整大小
                        img = self._resize_cover(img)
                        # 保存
                        img.save(target_path, "JPEG", quality=95)
                        logger.info(f"成功处理并保存默认封面图片到: {target_path}")
                        return target_path
                except Exception as e:
                    logger.error(f"处理默认封面图片失败: {e}")

        # 4. 如果所有方法都失败了，生成文字封面
        logger.info("尝试生成文字封面")
        text_cover = await self._generate_text_cover(metadata, images_dir)
        if text_cover and text_cover.exists():
            try:
                # 复制到目标位置
                import shutil

                shutil.copy2(text_cover, target_path)
                logger.info(f"成功生成并保存文字封面到: {target_path}")
                return target_path
            except Exception as e:
                logger.error(f"复制文字封面失败: {e}")

        logger.warning("所有封面处理方法都失败了")
        return None

    async def _download_cover_image(self, url: str, target_path: Path) -> bool:
        """下载封面图片

        Args:
            url: 图片 URL
            target_path: 目标路径

        Returns:
            是否下载成功
        """
        try:
            logger.info(f"开始下载封面图片: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        # 验证是否为有效的图片
                        from io import BytesIO

                        try:
                            img = Image.open(BytesIO(content))
                            img.verify()  # 验证图片完整性
                            # 如果验证通过，保存图片
                            target_path.write_bytes(content)
                            logger.info(f"封面图片下载成功: {target_path}")
                            return True
                        except Exception as e:
                            logger.error(f"下载的文件不是有效的图片: {e}")
                            return False
                    else:
                        logger.error(f"下载封面图片失败: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"下载封面图片时发生错误: {e}")
            return False

    def _resize_cover(self, img: Image.Image) -> Image.Image:
        """调整封面图片大小

        Args:
            img: 原始图片

        Returns:
            调整后的图片
        """
        target_width = self.config.cover_width
        target_height = self.config.cover_height

        # 计算目标尺寸
        width, height = img.size
        ratio = min(target_width / width, target_height / height)
        new_size = (int(width * ratio), int(height * ratio))

        # 调整大小
        if ratio < 1:  # 只有当图片太大时才缩小
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        return img

    async def _generate_text_cover(
        self, metadata: Metadata, images_dir: Path
    ) -> Optional[Path]:
        """生成文字封面

        Args:
            metadata: 文档元数据
            images_dir: 图片目录

        Returns:
            生成的封面图片路径
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            # 创建空白图片
            width = self.config.cover_width
            height = self.config.cover_height
            img = Image.new("RGB", (width, height), self.config.cover_background)
            draw = ImageDraw.Draw(img)

            # 尝试加载字体
            try:
                # 尝试使用系统字体
                font_path = "/System/Library/Fonts/PingFang.ttc"  # macOS 系统字体
                title_font = ImageFont.truetype(font_path, size=60)
                author_font = ImageFont.truetype(font_path, size=40)
            except Exception:
                # 如果无法加载系统字体，使用默认字体
                title_font = ImageFont.load_default()
                author_font = ImageFont.load_default()

            # 获取标题和作者
            title = metadata.title or "未命名"
            author = metadata.author or "佚名"

            # 计算文本位置
            title_lines = textwrap.wrap(title, width=15)  # 根据宽度换行
            y = height // 3  # 从三分之一处开始绘制标题

            # 绘制标题
            for line in title_lines:
                # 计算文本宽度以居中
                text_width = draw.textlength(line, font=title_font)
                x = (width - text_width) // 2
                draw.text((x, y), line, font=title_font, fill="black")
                y += 80  # 行间距

            # 绘制作者
            text_width = draw.textlength(author, font=author_font)
            x = (width - text_width) // 2
            y = height * 2 // 3  # 在底部三分之二处绘制作者
            draw.text((x, y), author, font=author_font, fill="black")

            # 保存图片
            target_path = images_dir / "text_cover.jpg"
            img.save(target_path, "JPEG", quality=95)
            logger.info(f"成功生成文字封面: {target_path}")
            return target_path

        except Exception as e:
            logger.error(f"生成文字封面失败: {e}")
            return None

    async def _write_metadata(self, metadata_file: Path, metadata: Metadata) -> None:
        """写入元数据文件"""
        yaml_data = {
            "title": metadata.title or "未命名",
            "author": metadata.author or "佚名",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "language": "zh-CN",
        }

        # 添加基本元数据
        if metadata.publisher:
            yaml_data["publisher"] = metadata.publisher
        if metadata.isbn:
            yaml_data["identifier"] = [{"type": "isbn", "text": metadata.isbn}]
        if metadata.description:
            yaml_data["description"] = metadata.description

        # 添加豆瓣元数据
        if hasattr(metadata, "douban_metadata") and metadata.douban_metadata:
            douban_data = metadata.douban_metadata
            # 使用豆瓣评分作为副标题
            if "rating" in douban_data:
                yaml_data["subtitle"] = f"豆瓣评分：{douban_data['rating']}"
            # 添加出版日期
            if "publish_date" in douban_data:
                yaml_data["date"] = douban_data["publish_date"]
            # 使用豆瓣简介（如果本地描述为空）
            if not metadata.description and "description" in douban_data:
                yaml_data["description"] = douban_data["description"]

        # 添加封面图片路径（如果存在）
        if hasattr(metadata, "cover_image") and metadata.cover_image:
            yaml_data["cover-image"] = metadata.cover_image
            logger.info(f"设置封面图片路径: {metadata.cover_image}")

        # 添加 EPUB 特定设置
        yaml_data.update(
            {
                # 文档类设置
                "documentclass": "book",
                "classoption": ["oneside", "UTF8"],
                # 页面设置
                "geometry": {
                    "paperwidth": "100%",  # 使用百分比适配阅读器宽度
                    "paperheight": "100%",  # 使用百分比适配阅读器高度
                    "margin": "2em",  # 使用相对单位
                    "marginparwidth": "0pt",
                    "marginparsep": "0pt",
                },
                # 字体设置
                "mainfont": "Noto Serif CJK SC",
                "CJKmainfont": "Noto Serif CJK SC",
                "sansfont": "Noto Sans CJK SC",
                "CJKsansfont": "Noto Sans CJK SC",
                "monofont": "Sarasa Mono SC",
                # 目录设置
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "chapter-number": True,
                "toc-title": "目录",
                # EPUB 特定设置
                "epub-chapter-level": 1,
                "epub-subdirectory": "EPUB",
                # 版权信息
                "rights": f"版权所有 © {datetime.now().year} {metadata.author if metadata.author else '作者'}",
                # 其他设置
                "lang": "zh-CN",
                "dir": "ltr",
            }
        )

        metadata_file.write_text(
            yaml.dump(yaml_data, allow_unicode=True, sort_keys=False)
        )

    def _write_content(self, content_file: Path, document: Document) -> None:
        """写入内容文件"""
        content = []

        # 添加前置内容
        frontmatter = next(
            (block for block in document.blocks if block.block_type == "frontmatter"),
            None,
        )

        if frontmatter:
            # 处理前置内容，添加适当的分隔和格式
            front_content = frontmatter.content.strip()
            if front_content:
                content.extend(
                    [
                        "---",  # YAML 元数据分隔符
                        "",
                        "# 前言",
                        "",
                        front_content,
                        "",
                        "---",
                        "",
                    ]
                )

        # 添加目录标记
        content.extend(
            [
                "\\toc",  # pandoc 目录标记
                "",
                "\\newpage",
                "",
            ]
        )

        # 添加正文内容
        for block in document.blocks:
            if block.block_type == "content":
                # 处理章节内容
                chapter_content = block.content.strip()
                if chapter_content:
                    # 确保章节之间有足够的分隔
                    content.extend(
                        [
                            "",
                            chapter_content,
                            "",
                            "\\newpage",  # pandoc 分页标记
                            "",
                        ]
                    )

        # 写入文件
        content_file.write_text("\n".join(content))

    def _generate_epub(
        self,
        content_file: Path,
        metadata_file: Path,
        style_file: Optional[Path],
        output_file: Path,
        temp_dir: Path,
    ) -> None:
        """使用 pandoc 生成 EPUB"""
        # 基础参数
        args = [
            "--from",
            "markdown+east_asian_line_breaks+hard_line_breaks",
            "--to",
            "epub3",
            "--metadata-file",
            str(metadata_file),
            "--toc",
            "--toc-depth=3",
            "--number-sections",
            "--split-level=1",  # 替换 epub-chapter-level
            "--standalone",
            "--epub-subdirectory=EPUB",
            "--epub-embed-font=false",  # 不嵌入字体，使用系统字体
            "--variable=documentclass:book",
            "--top-level-division=chapter",
            "--wrap=none",  # 不自动换行
            "--resource-path",
            str(temp_dir),  # 使用临时目录作为资源路径
            "--data-dir",
            str(temp_dir),  # 添加数据目录
        ]

        # 添加样式文件
        if style_file:
            args.extend(["--css", str(style_file)])

        # 生成 EPUB
        try:
            pypandoc.convert_file(
                str(content_file), "epub3", outputfile=str(output_file), extra_args=args
            )
            logger.info(f"成功生成 EPUB 文件: {output_file}")
        except Exception as e:
            logger.error(f"生成 EPUB 失败: {e}")
            # 检查资源文件是否存在
            if "cover.jpg" in str(e):
                logger.error("封面图片不存在，请检查 images/cover.jpg 文件")
            raise

    async def validate_output(self, output: bytes) -> bool:
        """验证 EPUB 文件

        Args:
            output: EPUB 文件的二进制数据

        Returns:
            验证是否通过
        """
        try:
            # 保存到临时文件
            temp_path = self.temp_dir / "temp.epub"
            temp_path.write_bytes(output)

            # 使用 epubcheck 验证（如果可用）
            result = pypandoc.convert_file(
                str(temp_path), "plain", format="epub", extra_args=["--quiet"]
            )
            return True
        except Exception as e:
            logger.error(f"EPUB validation failed: {e}")
            return False
        finally:
            if temp_path.exists():
                temp_path.unlink()

    async def _download_cover(self, url: str, path: Path) -> None:
        """下载封面图片

        Args:
            url: 图片URL
            path: 保存路径
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(path, mode="wb") as f:
                            await f.write(await response.read())
                            logger.info(f"封面图片已保存到: {path}")
                    else:
                        logger.warning(f"下载封面图片失败: HTTP {response.status}")
        except Exception as e:
            logger.error(f"下载封面图片时出错: {e}")
