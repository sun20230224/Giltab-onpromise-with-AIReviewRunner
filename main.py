from typing import List, Any
import gitlab
import os
from itertools import dropwhile
import openai
from dataclasses import dataclass
import logging
import sys

logging.basicConfig(encoding='utf-8', level=logging.INFO)

@dataclass
class Diff:
     path: str
     diff: str

def get_required_env(var_name: str) -> str:
    """获取必需的环境变量，如果不存在则退出程序"""
    value = os.getenv(var_name)
    if not value:
        logging.error(f"❌ 错误: 环境变量 {var_name} 未设置")
        logging.error(f"请在 GitLab 项目的 Settings > CI/CD > Variables 中配置该变量")
        sys.exit(1)
    logging.info(f"✓ {var_name} 已配置")
    return value

# 从环境变量读取配置
logging.info("=== 开始读取配置 ===")
gitlab_base_url = os.getenv("GITLAB_BASE_URL", "https://git.dev.sample.com")
private_token = get_required_env("PAT")
openai_api_key = get_required_env("OPENAI_API_KEY")
openai_api_base = os.getenv("OPENAI_API_BASE", "https://one-api.sample.com/v1")

logging.info(f"GitLab URL: {gitlab_base_url}")
logging.info(f"OpenAI API Base: {openai_api_base}")
logging.info("=== 配置读取完成 ===\n")

gl = gitlab.Gitlab(url=gitlab_base_url, private_token=private_token)
openai.api_key = openai_api_key
openai.api_base = openai_api_base
def main():
     diffs, mr = get_diffs_from_mr()
     response = get_review(diffs)
     logging.info(response)
     mr.discussions.create({'body': response})
def get_review(diffs):
     user_message_line = ["Review the following code:"]
     for d in diffs:
         user_message_line.append(f"PATH: {d.path}; DIFF: {d.diff}")
     user_message = "\n".join(user_message_line)
     message = openai.ChatCompletion.create(
         model="glm-5",
         messages=[
             {
                 "role": "system",
                 "content": "You are a code reviewer on a Merge Request on Gitlab. Your responsibility is to review "
                            "the provided code and offer recommendations for enhancement. Identify any problematic "
                            "code snippets, highlight potential issues, and evaluate the overall quality of the code "
                            "you review. You will be given input in the format PATH: <path of the file changed>; "
                            "DIFF: <diff>. In diffs, plus signs (+) will mean the line has been added and minus "
                            "signs (-) will mean that the line has been removed. Lines will be separated by \\n."
             },
             {
                 "role": "user",
                 "content": user_message
             }
         ],
     )
     response = message['choices'][0]['message']['content']
     return response
def get_diffs_from_mr() -> (List[Diff], Any):
     project = gl.projects.get(os.environ["CI_PROJECT_PATH"])
     mr = project.mergerequests.get(id=os.environ["CI_MERGE_REQUEST_IID"])
     changes = mr.changes()
     diffs = [Diff(c['new_path'], sanitize_diff_content(c['diff'])) for c in changes['changes']]
     return diffs, mr
def sanitize_diff_content(diff: str):
     return "".join(list(dropwhile(lambda x: x != "@", diff[2:]))[2:])
if __name__ == "__main__":
     main()
