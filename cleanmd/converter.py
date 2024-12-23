import logging
import asyncio
from pathlib import Path
from cleanmd import config

logger = logging.getLogger(__name__)


class MarkdownConverter:
    """
    Markdown格式转换器

    主要职责:
    1. 将Markdown文件转换为其他格式(如EPUB)
    2. 处理转换过程中的错误
    3. 保存转换结果
    """

    def __init__(self):
        """初始化转换器"""
        self.epub_config = config.EPUB_CONFIG

    async def convert_to_epub(self, input_file: str, output_file: str) -> None:
        """
        将Markdown文件转换为EPUB格式

        Args:
            input_file: 输入的Markdown文件路径
            output_file: 输出的EPUB文件路径
        """
        try:
            logger.info(f"开始转换EPUB: {input_file}")

            # 构建基本命令
            cmd = [
                "pandoc",
                input_file,
                "-o",
                output_file,
                "--from",
                "markdown",
                "--to",
                "epub",
            ]

            # 添加目录相关配置
            if self.epub_config["toc"]:
                cmd.append("--toc")
                cmd.extend(["--toc-depth", str(self.epub_config["toc_depth"])])

            # 添加封面图片（如果存在）
            if (
                self.epub_config["cover_image"]
                and Path(self.epub_config["cover_image"]).exists()
            ):
                cmd.extend(["--epub-cover-image", self.epub_config["cover_image"]])

            # 添加CSS（如果存在）
            if self.epub_config["css"] and Path(self.epub_config["css"]).exists():
                cmd.extend(["--css", self.epub_config["css"]])

            # 添加元数据
            file_stem = Path(input_file).stem
            cmd.extend(
                [
                    "--metadata",
                    f"title={file_stem}",
                    "--metadata",
                    "author=Cleanmd",
                    "--metadata",
                    f"lang={self.epub_config['language']}",
                ]
            )

            # 异步执行转换命令
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"EPUB转换成功: {output_file}")
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                raise Exception(f"EPUB转换失败: {error_msg}")

        except Exception as e:
            logger.error(f"EPUB转换出错: {str(e)}")
            raise
