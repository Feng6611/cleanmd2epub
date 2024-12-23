import os
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
logger.info("已加载环境变量")

# Gemini API配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("未找到 GEMINI_API_KEY 环境变量，请在 .env 文件中设置")
logger.info("已配置 Gemini API Key")

# Gemini 模型配置
GEMINI_MODEL = "gemini-2.0-flash-exp"  # 更新为最新的 Flash 模型
TEMPERATURE = 0.6  # 较低的温度以保持输出的一致性
TOP_P = 1
TOP_K = 40
logger.info(f"使用模型: {GEMINI_MODEL}")

# 文本分段配置
MAX_CHUNK_SIZE = 3000  # 调整为描述文档中的值
MIN_CHUNK_SIZE = 2000  # 调整为描述文档中的值
TARGET_RATIO = 0.8  # 目标分块大小比例(相对于最大值)
logger.info(
    f"分段大小配置: 最大={MAX_CHUNK_SIZE}, 最小={MIN_CHUNK_SIZE}, 目标比例={TARGET_RATIO}"
)

# 分段标记
MARKDOWN_HEADERS = ["# ", "## ", "### ", "#### ", "##### ", "###### "]
MARKDOWN_SEPARATORS = ["---", "***", "___"]

# API请求配置
API_RETRY_DELAY = 70  # 调整为描述文档中的值
MAX_RETRIES = 5  # 最大重试次数（符合描述）
logger.info(f"API配置: 重试次数={MAX_RETRIES}, 重试延迟={API_RETRY_DELAY}秒")

# EPUB转换配置
EPUB_CONFIG = {
    "toc": True,  # 是否生成目录
    "toc_depth": 2,  # 目录深度
    "language": "zh-CN",  # 默认语言
    "cover_image": None,  # 封面图片路径（默认为None）
    "css": None,  # 自定义CSS文件路径（默认为None）
    "template": None,  # 自定义模板文件路径（默认为None）
}

# 输出目录配置
OUTPUT_DIR = "output"  # 主输出目录
CHUNKS_DIR = "chunks"  # 分段结果目录
CLEANED_DIR = "cleaned"  # 清洗结果目录
OUTPUT_SUFFIX = "_cleaned"  # 清洗后文件的后缀
EPUB_SUFFIX = "_final"  # EPUB文件后缀

# 创建必要的目录结构
for dir_path in [
    OUTPUT_DIR,
    os.path.join(OUTPUT_DIR, CHUNKS_DIR),
    os.path.join(OUTPUT_DIR, CLEANED_DIR),
]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"创建目录: {dir_path}")


# 创建 Config 类来统一管理配置
class Config:
    """配置类"""

    def __init__(self):
        # Gemini API 配置
        self.MODEL = GEMINI_MODEL
        self.API_KEY = GEMINI_API_KEY

        # 生成参数配置
        self.TEMPERATURE = TEMPERATURE
        self.TOP_P = TOP_P
        self.TOP_K = TOP_K
        self.MAX_TOKENS = 2048

        # 分段配置
        self.MAX_CHUNK_SIZE = MAX_CHUNK_SIZE
        self.MIN_CHUNK_SIZE = MIN_CHUNK_SIZE
        self.TARGET_RATIO = TARGET_RATIO
        self.MARKDOWN_HEADERS = MARKDOWN_HEADERS
        self.MARKDOWN_SEPARATORS = MARKDOWN_SEPARATORS

        # API 重试配置
        self.MAX_RETRIES = MAX_RETRIES
        self.RETRY_DELAY = API_RETRY_DELAY

        # EPUB转换配置
        self.EPUB_CONFIG = EPUB_CONFIG
        self.EPUB_SUFFIX = EPUB_SUFFIX

        # 输出目录配置
        self.OUTPUT_DIR = OUTPUT_DIR
        self.CHUNKS_DIR = CHUNKS_DIR
        self.CLEANED_DIR = CLEANED_DIR
        self.OUTPUT_SUFFIX = OUTPUT_SUFFIX

    def check_pandoc(self):
        """检查pandoc是否已安装"""
        try:
            import pypandoc

            version = pypandoc.get_pandoc_version()
            logger.info(f"检测到pandoc版本: {version}")
            return True
        except (ImportError, OSError):
            logger.error("未检测到pandoc，请先安装: https://pandoc.org/installing.html")
            return False


# 创建全局配置实例
config = Config()

# 检查pandoc安装
if not config.check_pandoc():
    logger.warning("pandoc未安装，EPUB转换功能将不可用")
