from abc import ABC, abstractmethod
from .document_parser import Document, Metadata


class IOutputGenerator(ABC):
    """输出生成器接口"""

    @abstractmethod
    async def generate(self, document: Document, metadata: Metadata) -> bytes:
        """生成EPUB文件

        Args:
            document: 处理后的文档
            metadata: 文档元数据

        Returns:
            EPUB文件的二进制数据
        """
        pass

    @abstractmethod
    async def validate_output(self, output: bytes) -> bool:
        """验证输出文件

        Args:
            output: EPUB文件的二进制数据

        Returns:
            验证是否通过
        """
        pass
