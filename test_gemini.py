import os
import google.generativeai as genai
import asyncio
from dotenv import load_dotenv


async def test_gemini():
    # 加载环境变量
    load_dotenv()

    # 配置 API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("错误: 未设置 GEMINI_API_KEY 环境变量")
        return

    genai.configure(api_key=api_key)

    try:
        # 获取默认模型
        model = genai.GenerativeModel("gemini-pro")

        # 发送测试请求
        response = await model.generate_content_async(
            "你好,这是一个测试消息。请用中文回复。"
        )

        print("API 请求成功!")
        print("响应内容:", response.text)

    except Exception as e:
        print("API 请求失败:", str(e))


if __name__ == "__main__":
    asyncio.run(test_gemini())
