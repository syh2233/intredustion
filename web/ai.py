from openai import OpenAI
import os


def new(system_prompt, user_prompt):
    api_key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            '缺少 API Key：请设置环境变量 DEEPSEEK_API_KEY（或 OPENAI_API_KEY）。'
        )

    base_url = os.environ.get('OPENAI_BASE_URL') or 'https://api.deepseek.com'
    model = os.environ.get('OPENAI_MODEL') or 'deepseek-chat'

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"{system_prompt}"},
            {"role": "user", "content": f"{user_prompt}"},
        ],
        stream=False,
    )

    return response.choices[0].message.content


if __name__ == '__main__':
    print(new('你是一个天气助手', '请告诉我今天的天气'))
