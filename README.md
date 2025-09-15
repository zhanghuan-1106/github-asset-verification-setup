# GitHub资产验证前置准备

## 项目说明
本目录包含GitHub资产验证脚本所需的所有前置物料，用于测试验证功能的完整性和准确性。

## 文件结构
github-asset-verification-setup/
├── .mcp_env # 环境配置文件
├── docs/analysis-report.md # 分析报告文档
├── config/project-config.yaml # 项目配置文件
├── data/test-data.json # 测试数据文件
├── scripts/verification-config.py # 验证配置脚本
└── README.md # 说明文档
 使用步骤

1. **创建GitHub仓库**
   ```bash
   # 创建名为 github-asset-verification-setup 的仓库
   ```
2. **配置环境变量**
   ```bash
    # 编辑 .mcp_env 文件，填入真实的GitHub token和组织名
    MCP_GITHUB_TOKEN=ghp_your_actual_token_here
    GITHUB_EVAL_ORG=your-organization-name
   ```
3. **上传文件到GitHub**
   ```bash
    # 将 docs/analysis-report.md 上传到仓库
    # 可选：上传其他配置文件和数据文件
   ```
4. **创建提交记录**
   ```bash
    # 确保有包含"分析报告"关键词的提交记录
    git commit -m "添加Claude AI协作分析报告"
    git commit -m "更新分析报告：添加用户统计数据"
    git commit -m "fix: 修复分析报告格式问题"
   ```
4. **运行验证脚本**
   ```bash
    python github_asset_verifier.py
   ```   


