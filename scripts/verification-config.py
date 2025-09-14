#!/usr/bin/env python3
# =============================================================================
# GitHub Asset Verification Script
# GitHub资产验证脚本
# 依赖: requests, python-dotenv (需提前安装：pip install requests python-dotenv)
# =============================================================================

import sys
import os
import requests
import base64
import re
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv


def load_environment() -> Tuple[Optional[str], Optional[str]]:
    """加载环境变量：GitHub访问令牌和目标组织/用户名"""
    load_dotenv(".mcp_env")
    github_token = os.environ.get("MCP_GITHUB_TOKEN")
    github_org = os.environ.get("GITHUB_EVAL_ORG")
    return github_token, github_org


def build_headers(github_token: str) -> Dict[str, str]:
    """构建GitHub API请求头（含授权信息）"""
    return {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }


def call_github_api(
    endpoint: str,
    headers: Dict[str, str],
    org: str,
    repo: str
) -> Tuple[bool, Optional[Dict]]:
    """调用GitHub API并返回（请求状态，响应数据）"""
    url = f"https://api.github.com/repos/{org}/{repo}/{endpoint}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            print(f"[API提示] {endpoint} 资源未找到（404）", file=sys.stderr)
            return False, None
        else:
            print(f"[API错误] {endpoint} 状态码：{response.status_code}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"[API异常] 调用 {endpoint} 失败：{str(e)}", file=sys.stderr)
        return False, None


def get_repo_file_content(
    file_path: str,
    headers: Dict[str, str],
    org: str,
    repo: str,
    branch: str = "main"
) -> Optional[str]:
    """获取指定分支下的文件内容（Base64解码）"""
    success, result = call_github_api(
        f"contents/{file_path}?ref={branch}", headers, org, repo
    )
    if not success or not result:
        return None

    try:
        return base64.b64decode(result.get("content", "")).decode("utf-8")
    except Exception as e:
        print(f"[文件解码错误] {file_path}：{str(e)}", file=sys.stderr)
        return None


def search_commits(
    headers: Dict[str, str],
    org: str,
    repo: str,
    commit_msg_pattern: str,
    max_commits: int = 10
) -> bool:
    """搜索包含指定消息模式的提交记录（支持模糊匹配）"""
    success, commits = call_github_api(
        f"commits?per_page={max_commits}", headers, org, repo
    )
    if not success:
        return False

    for commit in commits:
        if re.search(commit_msg_pattern, commit["commit"]["message"], re.IGNORECASE):
            return True
    return False


def verify_file_existence(
    config: Dict,
    headers: Dict[str, str],
    org: str,
    repo: str
) -> Tuple[bool, Optional[str]]:
    """验证目标文件是否存在于指定分支"""
    file_path = config["target_file"]["path"]
    branch = config["target_file"]["branch"]
    print(f"[1/4] 验证文件存在性：{file_path}（分支：{branch}）...")
    
    content = get_repo_file_content(file_path, headers, org, repo, branch)
    if not content:
        print(f"[错误] 文件 {file_path} 在 {branch} 分支中未找到", file=sys.stderr)
        return False, None
    print(f"[成功] 文件 {file_path} 存在")
    return True, content


def verify_file_structure(
    content: str,
    config: Dict
) -> bool:
    """验证文件是否包含必需的结构（如章节、关键词、表格头部）"""
    required_structures = config["required_structures"]
    print(f"[2/4] 验证文件结构：共需包含 {len(required_structures)} 个必需结构...")
    
    missing = []
    for struct in required_structures:
        if struct not in content:
            missing.append(struct)
    
    if missing:
        print(f"[错误] 缺失必需结构：{', '.join(missing)}", file=sys.stderr)
        return False
    print(f"[成功] 所有必需结构均存在")
    return True


def verify_content_accuracy(
    content: str,
    config: Dict
) -> bool:
    """验证文件内容是否符合预期规则（如统计数据、正则匹配、枚举值）"""
    content_rules = config["content_rules"]
    if not content_rules:
        print(f"[3/4 跳过] 未配置内容验证规则，直接通过")
        return True
    
    print(f"[3/4] 验证内容准确性：共需校验 {len(content_rules)} 条规则...")
    lines = content.split("\n")
    
    for rule in content_rules:
        rule_type = rule["type"]
        target = rule["target"]
        expected = rule["expected"]
        matched = False
        
        # 统计数据匹配
        if rule_type == "stat_match":
            for line in lines:
                if target in line:
                    match = re.search(r"(\d+(?:\.\d+)?)", line)
                    if match and str(match.group(1)) == str(expected):
                        matched = True
                        break
                if matched:
                    break
        
        # 正则匹配
        elif rule_type == "regex_match":
            if re.search(expected, content):
                matched = True
        
        # 固定文本匹配
        elif rule_type == "text_match":
            if expected in content:
                matched = True
        
        if not matched:
            print(f"[错误] 内容规则校验失败：{target} 预期 {expected}，实际未匹配", file=sys.stderr)
            return False
    
    print(f"[成功] 所有内容规则校验通过")
    return True


def verify_commit_record(
    config: Dict,
    headers: Dict[str, str],
    org: str,
    repo: str
) -> bool:
    """验证仓库是否存在符合预期的提交记录"""
    commit_config = config["commit_verification"]
    if not commit_config:
        print(f"[4/4 跳过] 未配置提交验证规则，直接通过")
        return True
    
    commit_msg_pattern = commit_config["msg_pattern"]
    max_commits = commit_config.get("max_commits", 10)
    print(f"[4/4] 验证提交记录：搜索包含「{commit_msg_pattern}」的最近 {max_commits} 条提交...")
    
    found = search_commits(headers, org, repo, commit_msg_pattern, max_commits)
    if not found:
        print(f"[错误] 未找到符合要求的提交记录", file=sys.stderr)
        return False
    print(f"[成功] 找到符合要求的提交记录")
    return True


def run_verification(verification_config: Dict) -> bool:
    """执行完整验证流程：环境检查 → 文件存在 → 结构验证 → 内容验证 → 提交验证"""
    print("=" * 50)
    print("开始执行GitHub资产验证")
    print("=" * 50)
    
    # 环境检查
    github_token, github_org = load_environment()
    if not github_token:
        print(f"[环境错误] 未配置MCP_GITHUB_TOKEN（需在.mcp_env中设置）", file=sys.stderr)
        return False
    if not github_org:
        print(f"[环境错误] 未配置GITHUB_EVAL_ORG（需在.mcp_env中设置）", file=sys.stderr)
        return False
    
    repo_name = verification_config["target_repo"]
    headers = build_headers(github_token)
    print(f"[环境就绪] 目标仓库：{github_org}/{repo_name}\n")

    # 文件存在性验证
    file_exists, file_content = verify_file_existence(verification_config, headers, github_org, repo_name)
    if not file_exists:
        return False

    # 文件结构验证
    structure_valid = verify_file_structure(file_content, verification_config)
    if not structure_valid:
        return False

    # 内容准确性验证
    content_valid = verify_content_accuracy(file_content, verification_config)
    if not content_valid:
        return False

    # 提交记录验证
    commit_valid = verify_commit_record(verification_config, headers, github_org, repo_name)
    if not commit_valid:
        return False

    # 所有步骤通过
    print("\n" + "=" * 50)
    print("✅ 所有验证步骤通过！")
    print(f"验证对象：{verification_config['target_file']['path']}")
    print(f"目标仓库：{github_org}/{repo_name}")
    print(f"验证分支：{verification_config['target_file']['branch']}")
    print(f"通过规则：4/4")
    if verification_config.get("commit_verification"):
        print(f"匹配提交：{verification_config['commit_verification']['msg_pattern']}")
    print("=" * 50)
    return True


if __name__ == "__main__":
    # ==========================
    # 验证配置（根据实际需求修改）
    # ==========================
    VERIFICATION_CONFIG = {
        # 目标仓库信息
        "target_repo": "example-repo",
        
        # 目标文件信息
        "target_file": {
            "path": "docs/analysis-report.md",
            "branch": "main"
        },
        
        # 必需结构
        "required_structures": [
            "# 项目分析报告",
            "## 执行摘要",
            "## 详细分析",
            "| 指标 | 数值 |",
            "## 结论"
        ],
        
        # 内容验证规则
        "content_rules": [
            {
                "type": "stat_match",
                "target": "总用户数：",
                "expected": "1000"
            },
            {
                "type": "regex_match",
                "target": "报告日期",
                "expected": r"\d{4}-\d{2}-\d{2}"
            },
            {
                "type": "text_match",
                "target": "审核状态",
                "expected": "审核状态：已批准"
            }
        ],
        
        # 提交记录验证
        "commit_verification": {
            "msg_pattern": "更新分析报告",
            "max_commits": 10
        }
    }

    # 执行验证
    success = run_verification(VERIFICATION_CONFIG)
    sys.exit(0 if success else 1)