import os
import json
import time
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse

# 读取.env文件（修复路径+编码问题）
def load_env():
    # 直接取当前脚本所在目录，和.env同级
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    # 去除首尾引号和空格
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
    return env_vars

# 调用LLM API（核心修复：UTF-8编码处理）
def call_llm(prompt, env_vars):
    # 解析配置
    base_url = env_vars.get('BASE_URL', 'https://api.openai.com/v1')
    model = env_vars.get('MODEL', 'gpt-3.5-turbo')
    api_key = env_vars.get('API_KEY')
    temperature = float(env_vars.get('TEMPERATURE', '0.7'))
    max_tokens = int(env_vars.get('MAX_TOKENS', '1000'))
    
    if not api_key:
        raise ValueError("API_KEY not found in .env file")
    
    # 解析URL，自动识别http/https
    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path or '/'
    # 自动选择连接类型
    if parsed_url.scheme == 'https':
        conn = HTTPSConnection(host)
    else:
        conn = HTTPConnection(host)
    
    # 构建请求数据
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    # 开始计时
    start_time = time.time()
    
    # 核心修复：手动UTF-8编码请求体
    json_data = json.dumps(data, ensure_ascii=False)
    body = json_data.encode('utf-8')
    
    # 发送请求
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': f'Bearer {api_key}',
        'Content-Length': str(len(body))  # 必须手动指定长度，避免编码问题
    }
    
    try:
        # 拼接完整路径（避免重复/）
        full_path = f"{path.rstrip('/')}/chat/completions"
        conn.request('POST', full_path, body=body, headers=headers)
        response = conn.getresponse()
        response_data = json.loads(response.read().decode('utf-8'))
        
        # 检查API返回的错误
        if 'error' in response_data:
            raise Exception(f"API返回错误: {response_data['error']['message']}")
            
    finally:
        conn.close()
    
    # 结束计时
    end_time = time.time()
    duration = end_time - start_time
    
    # 提取token消耗
    usage = response_data.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    total_tokens = usage.get('total_tokens', 0)
    
    # 计算速度
    tokens_per_second = total_tokens / duration if duration > 0 else 0
    
    # 提取响应内容
    content = ""
    if 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0].get('message', {}).get('content', '')
    
    return {
        'content': content,
        'usage': {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        },
        'duration': duration,
        'tokens_per_second': tokens_per_second
    }

# 主函数
if __name__ == "__main__":
    try:
        # 加载环境变量
        env_vars = load_env()
        
        # 从.env读取PROMPT，没有则用默认值
        test_prompt = env_vars.get('PROMPT', "请简要介绍一下人工智能的发展历程")
        
        print("正在调用LLM API...")
        result = call_llm(test_prompt, env_vars)
        
        print("\n响应内容:")
        print(result['content'])
        print("\n统计信息:")
        print(f"提示词Token数: {result['usage']['prompt_tokens']}")
        print(f"完成Token数: {result['usage']['completion_tokens']}")
        print(f"总Token数: {result['usage']['total_tokens']}")
        print(f"响应时间: {result['duration']:.2f}秒")
        print(f"Token处理速度: {result['tokens_per_second']:.2f} tokens/秒")
        
    except Exception as e:
        print(f"错误: {e}")
        print("请确保已创建.env文件并填写正确的配置参数")
