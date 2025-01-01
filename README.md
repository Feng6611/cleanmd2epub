# cleanmd2epub

使用 Gemini 清洗 MD 文件并生成 EPUB 电子书。

## 功能特点

- 使用 Gemini API 智能清洗 Markdown 文件
- 自动获取豆瓣图书元数据
- 生成美观的 EPUB 电子书
- 支持缓存和断点续传
- 异步处理提高性能

## 安装

```bash
# 克隆仓库
git clone https://github.com/username/cleanmd2epub.git
cd cleanmd2epub

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

## 配置

1. 复制环境变量示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，设置必要的环境变量：
```env
API_KEY=your_gemini_api_key_here
CACHE_DIR=~/.cache/cleanmd2epub
CACHE_EXPIRE_DAYS=7
MAX_BLOCK_SIZE=1000
MAX_RETRIES=3
RETRY_DELAY=1
OUTPUT_DIR=output
TEMPLATE_DIR=templates
```

## 使用方法

```bash
# 清洗单个文件
cleanmd2epub clean input.md

# 清洗并生成 EPUB
cleanmd2epub convert input.md -o output.epub

# 批量处理目录
cleanmd2epub convert path/to/dir -o output/dir
```

## 开发

```bash
# 运行测试
pytest

# 运行带覆盖率的测试
pytest --cov=src tests/

# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/ tests/
```

## 项目结构

```
cleanmd2epub/
├── src/                # 源代码
│   ├── core/          # 核心模块
│   ├── interfaces/    # 接口定义
│   ├── utils/         # 工具函数
│   └── cli/           # 命令行接口
├── tests/             # 测试代码
├── templates/         # EPUB 模板
└── docs/             # 文档
```

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件 