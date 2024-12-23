# Cleanmd

使用 Google Gemini AI 清洗和优化 OCR 生成的 Markdown 文件，提高文档的可读性和结构性。

## 功能特点

- 🤖 利用 Google Gemini AI 进行智能文本处理
- 📝 优化 OCR 生成的 Markdown 文件格式
- 🔄 批量处理多个文件
- 🎯 提高文档的可读性和结构性
- 💡 智能识别和修复常见的 OCR 错误
- 🌐 支持中英文文档处理

## 系统要求

- Python 3.10 或更高版本
- Pandoc 3.0.0 或更高版本
- Google Gemini API 密钥

## 安装

### 1. 安装 Python 依赖

```bash
# 创建并激活虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate  # Windows

# 安装包
pip install cleanmd
```

### 2. 安装 Pandoc

macOS:
```bash
brew install pandoc
```

Linux:
```bash
sudo apt-get install pandoc
```

Windows:
```bash
choco install pandoc
```

### 3. 配置环境变量

创建 `.env` 文件并添加你的 Google Gemini API 密钥：

```env
GOOGLE_API_KEY=your_api_key_here
```

## 使用方法

### 命令行使用

```bash
cleanmd input.md                  # 处理单个文件
cleanmd input_dir/ --output out/  # 处理整个目录
```

### Python API 使用

```python
from cleanmd import clean_markdown

# 处理单个文件
clean_markdown("input.md", "output.md")

# 处理目录
clean_markdown("input_dir/", "output_dir/")
```

## 配置选项

在项目根目录创建 `config.yaml` 文件来自定义处理选项：

```yaml
input:
  encoding: utf-8
  recursive: true
  
output:
  format: markdown
  clean_level: moderate  # basic, moderate, aggressive
  
processing:
  batch_size: 10
  max_retries: 3
  timeout: 30
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black .
```

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交 Pull Requests！对于重大更改，请先开 issue 讨论您想要更改的内容。

## 常见问题

1. **Q: 为什么需要安装 Pandoc？**  
   A: Pandoc 用于处理不同格式间的文档转换，确保最佳的格式兼容性。

2. **Q: 支持哪些输入格式？**  
   A: 主要支持 Markdown 格式，特别是 OCR 软件生成的 Markdown 文件。

3. **Q: 如何获取 Google Gemini API 密钥？**  
   A: 访问 [Google AI Studio](https://ai.google.dev/) 创建项目并获取 API 密钥。

## 更新日志

### 0.1.0 (2024-01)
- 初始版本发布
- 支持基本的 Markdown 清洗功能
- 添加命令行界面
- 集成 Google Gemini API 