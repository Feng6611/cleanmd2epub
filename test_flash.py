import google.generativeai as genai
from cleanmd.config import GEMINI_API_KEY
import sys
from google.api_core import exceptions as google_exceptions
import time


def test_gemini_api():
    """测试 Gemini API 的基本连接和访问"""
    print("\n=== 开始测试 Gemini API ===")

    try:
        # 1. 测试 API 配置
        print("1. 配置 API...")
        genai.configure(
            api_key=GEMINI_API_KEY, transport="rest"  # 使用 REST 而不是 gRPC
        )
        print(f"✓ API Key 配置成功: {GEMINI_API_KEY[:8]}...")

        # 3. 测试模型实例化
        print("\n2. 创建模型实例...")
        model_name = "gemini-1.5-pro"  # 使用更稳定的模型
        model = genai.GenerativeModel(model_name)
        print(f"✓ 模型 '{model_name}' 创建成功")

        # 4. 测试基本生成功能
        print("\n3. 测试文本生成...")
        prompt = "用中文回复: 你好,这是一个测试消息。如果你收到了,请回复'连接成功'。"
        print("正在等待模型响应...")

        # 优化生成配置
        generation_config = {
            "temperature": 0.1,  # 降低随机性，提高响应的确定性
            "top_k": 40,  # 从概率最高的40个token中选择
            "top_p": 0.8,  # 累积概率阈值
            "max_output_tokens": 2048,  # 限制输出长度
        }

        # 添加安全设置
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
        ]

        # 添加重试逻辑
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                print("\n=== 模型响应 ===")
                print(response.text)
                print("================")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"尝试 {attempt + 1} 失败，{retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    raise e

        # 5. 测试流式响应
        print("\n4. 测试流式响应...")
        try:
            stream = model.generate_content(
                "用中文写一个简短的故事。",
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True,
            )

            print("\n=== 流式响应 ===")
            for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="")
            print("\n================")
        except Exception as e:
            print(f"流式响应测试失败: {str(e)}")

        print("\n✨ API 测试全部成功完成!")
        return True

    except google_exceptions.PermissionDenied as e:
        print(f"\n❌ API 权限错误: {str(e)}")
    except google_exceptions.ServiceUnavailable as e:
        print(f"\n❌ 服务不可用: {str(e)}")
    except google_exceptions.ResourceExhausted as e:
        print(f"\n❌ 配额超限: {str(e)}")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        print("\n故障排除建议:")
        print("1. 检查 API Key 是否正确")
        print("2. 检查网络连接")
        print("3. 确认 API 访问权限")
        print("4. 确认模型名称是否正确")
        print("5. 检查是否需要配置代理")
        print("6. 尝试使用 VPN 或代理服务器")
        return False


if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)
