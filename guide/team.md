---
layout: default
title: "Claude Code 活用ガイド - チーム編（章18〜24）"
---

[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)

---



## 18. エコシステム連携 - MCP サーバー詳説・IDE 統合

### 18.1 MCP エコシステムの全体像

MCP（Model Context Protocol）は Anthropic が策定したオープンソース標準であり、Claude Code をあらゆる外部ツールやサービスに接続するための共通プロトコルである。2026年3月時点では数千のサードパーティ MCP サーバーが公開されており、データベース、コード検索、ブラウザ自動化、クラウドサービスなど多様な用途に対応している [^9]。

### 18.2 MCP サーバーの種類と選び方

#### 接続タイプ別の比較

| タイプ | 通信方式 | 推奨場面 | 特徴 |
|-------|---------|---------|------|
| **HTTP** | REST/WebSocket | クラウドサービス、公開 API | 設定が簡単。認証はヘッダーで管理 |
| **SSE** | Server-Sent Events | リアルタイム配信が必要な場合 | HTTP に置き換えが推奨 |
| **stdio** | 標準入出力 | ローカルツール、CLIラッパー | プロセス起動が必要。開発環境向け |

#### 用途別おすすめ MCP サーバー（2026年）

| カテゴリ | サーバー | 用途 |
|---------|---------|------|
| **バージョン管理** | GitHub MCP | PR 管理、Issue 操作、コードレビュー自動化 |
| **ドキュメント** | Context7 | 最新ライブラリドキュメントを動的取得 |
| **データベース** | dbhub (PostgreSQL) | SQL クエリ、スキーマ探索 |
| **モニタリング** | Sentry | エラートラッキング、パフォーマンス分析 |
| **設計** | Figma | デザイントークン・コンポーネント取得 |
| **コミュニケーション** | Slack | メッセージ送信、チャンネル操作 |
| **テスト** | Playwright | E2E テスト自動化、ブラウザ操作 |
| **リサーチ** | Perplexity | Web 検索、情報収集 |
| **タスク管理** | Linear / Jira | チケット管理、スプリント操作 |
| **ノート** | Notion | ドキュメント管理、ナレッジベース |

### 18.3 チームで MCP サーバーを共有する

`.mcp.json` をプロジェクトルートに配置して git にコミットすると、チーム全員が同じ MCP 設定を共有できる：


```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    },
    "sentry": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp",
      "headers": {
        "Authorization": "Bearer ${SENTRY_AUTH_TOKEN}"
      }
    }
  }
}
```


環境変数（`${GITHUB_TOKEN}` 等）はローカルの `.env` や CI シークレットから読み込まれ、`.mcp.json` 自体に機密情報を含めずに済む。

### 18.4 カスタム MCP サーバーの開発

社内ツールや独自 API を MCP サーバーとして公開することも可能：


```python
# 簡易 MCP サーバー (Python)
from mcp import Server, Tool
import json

server = Server("my-internal-api")

@server.tool("get_employee_info")
async def get_employee_info(employee_id: str) -> str:
    """社内人事システムから従業員情報を取得"""
    # 社内 API への接続
    data = fetch_from_hr_system(employee_id)
    return json.dumps(data)

if __name__ == "__main__":
    server.run_stdio()
```



```json
// .mcp.json に追加
{
  "mcpServers": {
    "hr-system": {
      "type": "stdio",
      "command": "python3",
      "args": [".claude/mcp-servers/hr_server.py"]
    }
  }
}
```


### 18.5 IDE 統合の詳細設定

#### VS Code 拡張機能の高度な設定

VS Code の `settings.json` で Claude Code 拡張機能を細かく制御できる：


```json
{
  "claude-code.autoStart": true,
  "claude-code.model": "claude-sonnet-4-6",
  "claude-code.contextWindowWarningThreshold": 0.8,
  "claude-code.showStatusBar": true,
  "claude-code.diffView": "side-by-side"
}
```


#### JetBrains 系 IDE の統合

| IDE | プラグイン名 | 特記事項 |
|-----|------------|---------|
| IntelliJ IDEA | Claude Code | Java/Kotlin プロジェクトとの統合が優秀 |
| PyCharm | Claude Code | Python インタープリタの自動検出 |
| WebStorm | Claude Code | TypeScript の型情報を活用 |
| GoLand | Claude Code | Go モジュールの構造を認識 |

JetBrains IDE での差分ビューは IDE ネイティブの比較ツールを使用するため、既存のコードレビューワークフローと自然に統合できる。

#### Neovim / Vim での使用


```lua
-- ~/.config/nvim/init.lua
-- Claude Code をターミナルウィンドウで起動するキーバインド
vim.keymap.set('n', '<leader>cc', function()
  vim.cmd('terminal claude')
  vim.cmd('startinsert')
end, { desc = 'Claude Code を起動' })

-- 選択範囲をファイルに保存して Claude に渡す
vim.keymap.set('v', '<leader>cr', function()
  vim.cmd("'<,'>write /tmp/claude_context.txt")
  vim.cmd('terminal claude -p "このコードをレビューして: @/tmp/claude_context.txt"')
end, { desc = 'Claude でコードレビュー' })
```


---

## 19. ツール比較 - Claude Code vs Cursor vs Copilot vs Aider

### 19.1 ツール概要

主要な AI コーディングツールの概要を比較します。

| ツール | 形態 | 主な特徴 | 価格帯 |
|-------|------|---------|-------|
| **Claude Code** | CLI / IDE拡張 | エージェント型、200K コンテキスト、ターミナル中心 | API従量課金 |
| **Cursor** | スタンドアロンエディタ | VS Code 互換、Composer モード、マルチファイル編集 | $20/月〜 |
| **GitHub Copilot** | IDE 拡張 | リアルタイム補完、IDE ネイティブ統合 | $10/月〜 |
| **Aider** | CLI | OSS、マルチモデル対応、git 統合 | モデル API 費のみ |

### 19.2 アーキテクチャの違い

#### Claude Code
ターミナル内で動作するエージェントであり、ファイルシステム全体にアクセスしてコードベースを自律的に操作する。専用エディタを持たず、ユーザーの既存エディタを活かす設計。コンテキストウィンドウは 200,000 トークンであり、30,000 行超のコードベースでも一括分析が可能 [^21]。

#### Cursor
VS Code をベースとした独立したエディタ。AI 機能がエディタ全体に深く統合されており、Composer モードでマルチファイルの変更を管理する。Tab 補完の精度が高く、日常的なコーディングで素早く補完を受け取れる。

#### GitHub Copilot
IDE の拡張機能として動作し、インライン補完を主軸とする。Microsoft のインフラに統合されており、GitHub との親和性が高い。Copilot Chat で会話型の質問もできるが、ファイルシステムへの自律的なアクセスは限定的。

#### Aider
OSS の CLI ツール。GPT-4、Claude、Gemini など複数モデルに対応。すべての変更を自動的に git コミットするため変更追跡が容易。IDE に依存しない汎用性が強み。

### 19.3 機能比較マトリクス

各ツールの機能を詳細に比較した一覧表です。

| 機能 | Claude Code | Cursor | Copilot | Aider |
|------|:-----------:|:------:|:-------:|:-----:|
| コンテキスト長（最大） | 200K | 128K | 64K | 200K+ |
| 自律的なファイル変更 | 優秀 | 良好 | 限定的 | 良好 |
| リアルタイム補完 | - | 優秀 | 優秀 | - |
| マルチファイル編集 | 優秀 | 優秀 | 限定的 | 良好 |
| エージェント機能 | 優秀 | 良好 | 基本的 | 基本的 |
| カスタムエージェント | 優秀 | - | - | - |
| フック・自動化 | 優秀 | 限定的 | 限定的 | - |
| MCP 連携 | 優秀 | 基本的 | - | - |
| OSS | 部分的 | - | - | 完全 |
| CI/CD 統合 | 優秀 | - | 良好 | 良好 |
| IDE 統合 | 良好 | 優秀 | 優秀 | 良好 |
| コスト制御 | 細かく設定可 | 月額固定 | 月額固定 | 柔軟 |

### 19.4 ユースケース別推奨

#### Claude Code が最適な場面
- **大規模リファクタリング**: 数百ファイルにまたがる変更、依存関係の整理
- **コードベース分析**: 初めてのプロジェクト把握、アーキテクチャ調査
- **自動化ワークフロー**: CI/CD、定期的なコード品質チェック
- **セキュリティ監査**: コードベース全体の脆弱性スキャン
- **ドキュメント生成**: コードから README、API ドキュメントを自動生成
- **カスタムエージェント構築**: ドメイン固有の専門エージェントを作りたい場合

#### Cursor が最適な場面
- **日常的な機能開発**: 新機能の実装、バグ修正
- **GUI 重視の開発者**: エディタ統合 UI が好みの場合
- **TypeScript/React 開発**: フロントエンド開発との親和性が高い
- **チャットベースのコーディング**: コードを見ながら対話したい場合

#### GitHub Copilot が最適な場面
- **GitHub エコシステムに深く依存**: Actions、Codespaces との統合
- **インライン補完が主な用途**: コーディング速度の向上
- **企業での標準ツール**: 大企業での一括ライセンス管理

#### Aider が最適な場面
- **OSS プロジェクト**: コスト最小で AI 支援コーディングを試す
- **マルチモデル比較**: 複数モデルを使い分けたい
- **git 中心のワークフロー**: 全変更の自動コミットが欲しい

### 19.5 組み合わせての活用

最も生産性が高いのは複数ツールを組み合わせる戦略である：


```
日常のコーディング    → Cursor（リアルタイム補完）
                          +
複雑なリファクタリング → Claude Code（大規模変更）
                          +
CI/CD の自動化       → Claude Code GitHub Actions
```


Cursor と Claude Code を同時に使う場合、Cursor で編集中のファイルを Claude Code に `@` で参照させることで両者を連携できる。

---

## 20. CI/CD 統合 - GitHub Actions・自動レビュー

### 20.1 Claude Code GitHub Actions とは

Claude Code GitHub Actions は Claude Code を GitHub ワークフローに統合する公式の仕組みである。PR や Issue のコメントで `@claude` とメンションするだけで Claude が反応し、コードの分析・実装・修正を自動実行する [^22]。

**主なユースケース：**
- PR の自動コードレビュー
- Issue からの自動実装
- ビルド失敗時の自動デバッグ
- 定期的なセキュリティ監査
- ドキュメントの自動更新

### 20.2 セットアップ手順

#### 方法1: `/install-github-app` コマンド（推奨）

Claude Code ターミナルで以下を実行すると、対話的にセットアップが完了する：

```bash
/install-github-app
```

このコマンドは以下を自動処理する：
1. GitHub App のインストール案内
2. `ANTHROPIC_API_KEY` シークレットの設定案内
3. ワークフローファイルの生成

#### 方法2: 手動セットアップ

1. [GitHub App をインストール](https://github.com/apps/claude)
2. リポジトリシークレットに `ANTHROPIC_API_KEY` を追加
3. `.github/workflows/claude.yml` を作成

### 20.3 基本ワークフロー

#### PR・Issue コメントへの応答


```yaml
# .github/workflows/claude.yml
name: Claude Code
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]

jobs:
  claude:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
          # @claude メンションに自動応答
```


#### PR の自動コードレビュー


```yaml
name: Automated Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
          prompt: |
            このPRのコードをレビューしてください：
            1. コード品質とベストプラクティスへの準拠
            2. セキュリティ上の問題
            3. パフォーマンスへの影響
            4. テストカバレッジの充足度
            具体的で実行可能なフィードバックをPRコメントとして投稿してください。
          claude_args: "--max-turns 5"
```


#### セキュリティ監査（定期実行）


```yaml
name: Weekly Security Audit
on:
  schedule:
    - cron: "0 9 * * 1"  # 毎週月曜 9:00 UTC

jobs:
  security-audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
          prompt: |
            このコードベースのセキュリティ監査を実施してください：
            - SQLインジェクション、XSS等の脆弱性
            - ハードコードされた機密情報
            - 安全でない依存関係
            - 認証・認可の問題
            発見した問題は優先度付きでGitHub Issueとして報告してください。
          claude_args: "--max-turns 10 --model claude-opus-4-6"
```


#### ビルド失敗時の自動デバッグ


```yaml
name: Auto Debug
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  debug:
    if: ${{% raw %}}{{ github.event.workflow_run.conclusion == 'failure' }}{{% endraw %}}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: ビルドログ取得
        id: get-logs
        run: |
          # 失敗したジョブのログを取得
          gh run view ${{% raw %}}{{ github.event.workflow_run.id }}{{% endraw %}} --log-failed > build-errors.txt 2>&1 || true
        env:
          GITHUB_TOKEN: ${{% raw %}}{{ secrets.GITHUB_TOKEN }}{{% endraw %}}
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
          prompt: |
            ビルドが失敗しました。build-errors.txt のエラーを分析し、
            根本原因を特定して修正案を提案してください。
            可能であれば修正を実装してPRを作成してください。
          claude_args: "--max-turns 15"
```


### 20.4 @claude コマンドの活用

PR や Issue のコメントで以下のように使う：


```text
# 機能実装を依頼
@claude このIssueの説明に基づいてユーザー認証機能を実装してください

# バグ修正を依頼
@claude TypeError が発生しています。user_dashboard.py の 42 行目を修正してください

# コードレビューを依頼
@claude このPRのセキュリティ上の問題点を指摘してください

# リファクタリングを依頼
@claude src/utils.py を読みやすくリファクタリングしてください

# テスト追加を依頼
@claude このコードのユニットテストを追加してください
```


### 20.5 コスト管理

GitHub Actions での Claude 利用には二重のコストが発生する：

| コスト種別 | 内容 | 管理方法 |
|-----------|------|---------|
| GitHub Actions 分数 | Ubuntu runner の実行時間 | `timeout-minutes` で制限 |
| API トークン | Claude への入出力トークン数 | `--max-turns` で反復回数を制限 |


```yaml
# コスト管理の例
- uses: anthropics/claude-code-action@v1
  timeout-minutes: 10          # Actions の実行時間上限
  with:
    anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
    claude_args: "--max-turns 5 --model claude-sonnet-4-6"  # ターン数とモデル指定
```


### 20.6 AWS Bedrock / Google Vertex AI との統合

コストやデータ主権の要件がある企業向けに、クラウドプロバイダー経由での利用も可能：


```yaml
# AWS Bedrock 利用例
- uses: anthropics/claude-code-action@v1
  with:
    use_bedrock: "true"
    claude_args: "--model us.anthropic.claude-sonnet-4-6 --max-turns 10"
  env:
    AWS_REGION: us-west-2
```



```yaml
# Google Vertex AI 利用例
- uses: anthropics/claude-code-action@v1
  with:
    use_vertex: "true"
    claude_args: "--model claude-sonnet-4@20250514 --max-turns 10"
  env:
    ANTHROPIC_VERTEX_PROJECT_ID: ${{% raw %}}{{ steps.auth.outputs.project_id }}{{% endraw %}}
    CLOUD_ML_REGION: us-east5
```


---

## 21. チーム開発 - CLAUDE.md 共有・コードレビュー

### 21.1 チーム向け CLAUDE.md の設計

チーム開発で最も重要なのは **CLAUDE.md を git にコミットしてチーム全員が同じルールを共有すること** である。個人の好みと違う場合は `CLAUDE.local.md` を使う。

#### チーム向け CLAUDE.md テンプレート


```markdown
# プロジェクト: [プロジェクト名]

## 技術スタック
- Backend: Python 3.12 + FastAPI
- Frontend: TypeScript 5 + React 19 + Vite
- Database: PostgreSQL 16 with SQLAlchemy
- Cache: Redis 7
- Container: Docker + docker-compose

## ビルドコマンド
- テスト実行: `make test` （pytest + vitest）
- Linting: `make lint` （ruff + eslint）
- 型チェック: `make typecheck` （pyright + tsc --noEmit）
- ローカル起動: `make dev`

## コーディング規約
- Python: ruff で自動フォーマット。型ヒントは必須
- TypeScript: strict モード。any 型は禁止
- API: RESTful、kebab-case パス、camelCase JSON
- テスト: 新機能には必ずユニットテストを追加

## ブランチ・コミット規約
- ブランチ: `feature/`, `fix/`, `refactor/` プレフィックス
- コミット: Conventional Commits 形式（feat:, fix:, docs:, etc.）
- PR: main への直接 push 禁止。必ず PR を経由する

## IMPORTANT
- YOU MUST run `make lint && make typecheck` before committing
- NEVER commit secrets or API keys
- Always write tests for new API endpoints
- Migration ファイルは手動で確認してから commit すること

## 禁止事項
- `# type: ignore` コメントを追加しない
- `console.log` をコードに残さない
- 本番 DB に直接アクセスするスクリプトを作らない
```


### 21.2 チーム共通エージェントの整備

`.claude/agents/` にチーム共有のエージェントを配置し、git で管理する：

#### PR レビューエージェント


```markdown
---
name: pr-reviewer
description: PR のコードを包括的にレビューする。コード品質、セキュリティ、パフォーマンスをチェック
tools: Read, Grep, Glob, Bash
model: opus
---

あなたはシニアソフトウェアエンジニアとして PR レビューを行います。

## レビュー観点

### コード品質
- 可読性・保守性
- 単一責任原則の遵守
- 適切なエラーハンドリング
- コードの重複がないか

### セキュリティ
- 入力バリデーション
- SQL インジェクション、XSS リスク
- 認証・認可の正しい実装
- 機密情報のハードコーディング

### パフォーマンス
- N+1 クエリ問題
- 不必要なデータ取得
- キャッシュの適切な利用

### テスト
- テストカバレッジ
- エッジケースの考慮
- モックの適切な使用

## 出力形式
各問題について以下を記載：
1. 問題箇所（ファイル名と行番号）
2. 問題の深刻度（Critical / Warning / Info）
3. 具体的な改善案

最後に総合評価（Approve / Request Changes）を明記すること。
```


#### ドキュメント生成エージェント


```markdown
---
name: doc-generator
description: コードからドキュメントを自動生成する。API ドキュメント、README、設計書
tools: Read, Write, Glob, Grep
model: sonnet
---

あなたはテクニカルライターです。コードを読んで正確なドキュメントを生成します。

## ドキュメント生成ルール
- 実際のコードから情報を取得し、憶測で書かない
- コード例は実際に動作するものを使用
- 日本語で記述（コードコメント・API 名は英語のまま）
- Markdown 形式、見出しは適切な階層構造

## 生成する内容
- 関数・クラスの用途と引数の説明
- 使用例（curl コマンド、コードスニペット）
- エラーコードと意味
- 依存関係
```


### 21.3 CLAUDE.md の継続的改善

CLAUDE.md は一度書いて終わりではなく、継続的に改善する：

#### CLAUDE.md 改善サイクル


```
1. 問題の発見
   Claude が繰り返し同じミスをする
   → CLAUDE.md にルールを追加

2. 不要なルールの削除
   毎月末に全ルールを見直す
   「このルールがなければ Claude はミスをするか？」と自問
   不要なルールは削除して軽量化

3. チームでの合意
   CLAUDE.md の変更は PR で行い、レビューを受ける
   ルールの理由をコメントで明記
```


#### よくある追加ルールの例


```markdown
# CLAUDE.md への追加例

## よくあるミス（チームで発見済み）
- テストファイルのパスは `tests/` ではなく `test/` が正しい
- データベース接続は `db.session` ではなく `get_db()` ヘルパーを使う
- 日付は常に UTC で扱い、表示時のみローカライズする
- 設定値は `config.py` から読む。直接 `os.environ` は使わない

## 新メンバー向け注意事項
- ローカル開発は `make dev` で起動。直接 `python main.py` は使わない
- Secrets Manager から取得するため、初回は `make setup-secrets` が必要
```


### 21.4 コードレビューワークフロー

#### ヒューマン + AI のハイブリッドレビュー


```
1. 開発者が PR を作成
   ↓
2. Claude Code が自動レビュー（GitHub Actions）
   - セキュリティ問題を検出
   - コードスタイルの違反を指摘
   - テストの欠如を報告
   ↓
3. 開発者が Claude のフィードバックを確認・対応
   ↓
4. チームメンバーがヒューマンレビュー
   - アーキテクチャの判断
   - ビジネスロジックの正確性
   - チームの文化・慣習への適合
   ↓
5. マージ
```


#### ローカルでの事前レビュー

PR を出す前にローカルで Claude にレビューさせることで、レビュー往復を削減できる：


```bash
# git の差分をレビューさせる
git diff main...HEAD | claude -p "このコードの差分をレビューして。セキュリティとコード品質に注目して"

# 特定ファイルのレビュー
claude -p "src/auth/login.py のセキュリティレビューをして" \
  --allowedTools "Read,Grep,Glob"
```


### 21.5 ナレッジの蓄積と共有

#### プロジェクト固有の知識をスキルに蓄積


```markdown
# .claude/skills/architecture-guide/SKILL.md
---
name: architecture-guide
description: プロジェクトのアーキテクチャ、設計原則、パターンについて説明する
---

# アーキテクチャガイド

## ディレクトリ構造
- `src/domain/` - ビジネスロジック（フレームワーク非依存）
- `src/infrastructure/` - DB、API、外部サービスとの接続
- `src/application/` - ユースケース、アプリケーションサービス
- `src/presentation/` - API エンドポイント、リクエスト/レスポンス

## 設計原則
- 依存性逆転: domain は infrastructure に依存しない
- 集約ルート: 関連エンティティは集約ルート経由でアクセス
- コマンド/クエリ分離: 状態変更と読み取りは分ける

## よく使うパターン
- Repository パターン: DB アクセスの抽象化
- Unit of Work: トランザクション管理
- Event Sourcing: 一部のドメインで採用
```


---

## 22. セキュリティ - パーミッション・機密情報・サンドボックス

### 22.1 セキュリティの基本方針

Claude Code のセキュリティは **最小権限の原則** に基づく。デフォルトでは読み取り専用であり、ファイル変更やコマンド実行には明示的な許可が必要。これは開発者が知らない間に重要なファイルが変更されることを防ぐ [^23]。

### 22.2 許可ツールの適切な設定

#### 許可リストによる最小権限付与


```json
// .claude/settings.json
{
  "permissions": {
    "allow": [
      "Read",                    // ファイル読み取り（常に許可）
      "Glob",                    // ファイル検索（常に許可）
      "Grep",                    // コード検索（常に許可）
      "Bash(npm run test *)",    // テスト実行のみ
      "Bash(npm run lint)",      // Lint のみ
      "Bash(npm run build)",     // ビルドのみ
      "Bash(git status)",        // git 読み取り系
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git push *)"
    ],
    "deny": [
      "Bash(rm -rf *)",          // 再帰削除は禁止
      "Bash(sudo *)",            // sudo は禁止
      "Bash(curl * | bash)",     // パイプでの実行は禁止
      "Bash(wget * -O- | sh)"    // 同上
    ]
  }
}
```


#### 作業種別ごとの権限設定


```bash
# 読み取り専用の分析タスク
claude -p "このコードベースのアーキテクチャを分析して" \
  --allowedTools "Read,Glob,Grep"

# テストの修正のみ許可
claude -p "失敗しているテストを修正して" \
  --allowedTools "Read,Edit,Bash(npm run test *),Glob,Grep"

# 完全な開発権限（信頼できる環境のみ）
claude --permission-mode acceptEdits
```


### 22.3 機密情報の管理

#### 絶対にやってはいけないこと


```markdown
# 危険な CLAUDE.md の例（やってはいけない）
API_KEY=sk-prod-xxxxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@prod-db:5432/myapp
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```


#### 正しい機密情報の管理方法


```markdown
# 安全な CLAUDE.md の例
## 設定
API キーは環境変数 `API_KEY` から取得。`.env` ファイルを参照。
DB 接続は `DATABASE_URL` 環境変数を使用。
```



```bash
# .env（.gitignore に追加）
API_KEY=sk-prod-xxxxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@prod-db:5432/myapp
```



```bash
# .gitignore
.env
.env.local
.env.production
*.pem
*.key
secrets/
```


#### シークレットスキャン

Claude Code を使ってシークレットのスキャンを行うことも可能：


```bash
claude -p "このコードベースをスキャンして、ハードコードされた API キー、
パスワード、トークン、シークレットを見つけてください。
ファイルパスと行番号を報告してください。修正は行わないこと。" \
  --allowedTools "Read,Glob,Grep"
```


### 22.4 サンドボックスの活用

サンドボックスは OS レベルの隔離を提供し、Claude が意図しないファイルやネットワークにアクセスすることを防ぐ：


```bash
# サンドボックスを有効化（セッション内）
/sandbox

# サンドボックス有効化後の動作
# - 書き込み: カレントディレクトリ以下のみ
# - 読み取り: システム全体（制限ディレクトリ除く）
# - ネットワーク: デフォルトは全拒否
```


#### サンドボックスのネットワーク設定


```json
// .claude/settings.json
{
  "sandbox": {
    "allowedDomains": [
      "api.github.com",
      "registry.npmjs.org",
      "pypi.org"
    ]
  }
}
```


### 22.5 企業環境でのセキュリティ対策

#### 組織レベルのポリシー設定

企業の IT/セキュリティチームは管理ポリシーを通じて Claude Code の動作を制御できる：


```json
// マネージドポリシー（IT部門が設定）
{
  "policies": {
    "disableTelemetry": true,          // テレメトリを無効化
    "allowedMcpServers": [             // 承認済み MCP のみ
      "https://internal-mcp.company.com"
    ],
    "forbiddenCommands": [             // 禁止コマンド
      "ssh *",
      "scp *",
      "rsync * root@*"
    ],
    "requireSandbox": true             // サンドボックス強制
  }
}
```


#### MCP ゲートウェイによる集中管理

MCP サーバーへのアクセスを MCP ゲートウェイを通じて統制することで、監査ログの取得とアクセス制御が可能：


```json
// .mcp.json - 全接続をゲートウェイ経由に
{
  "mcpServers": {
    "gateway": {
      "type": "http",
      "url": "https://mcp-gateway.company.internal/mcp",
      "headers": {
        "Authorization": "Bearer ${EMPLOYEE_TOKEN}",
        "X-Employee-ID": "${EMPLOYEE_ID}"
      }
    }
  }
}
```


### 22.6 セキュリティインシデント対応

Claude Code が予期しない動作をした場合の対処：


```bash
# セッションを即時停止
Ctrl+C

# 最後の変更を取り消す
/rewind

# git で変更を確認
git diff HEAD

# 全変更を元に戻す（注意: 作業が失われる）
git checkout .

# 特定ファイルだけ元に戻す
git checkout HEAD -- path/to/file.py
```


#### フックによる安全策


```json
// 危険なコマンドを事前ブロック
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/security-check.sh"
          }
        ]
      }
    ]
  }
}
```



```bash
#!/bin/bash
# .claude/hooks/security-check.sh
COMMAND=$(cat | jq -r '.tool_input.command // ""')

# 危険なパターンを検出
DANGEROUS_PATTERNS=(
  "rm -rf /"
  "dd if="
  "mkfs"
  "> /dev/"
  "curl.*|.*bash"
  "wget.*|.*sh"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$pattern"; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"危険なコマンドパターンを検出しました: '"$pattern"'"}}' >&2
    exit 2
  fi
done

exit 0
```


---

## 23. Agent SDK - カスタムエージェント構築

### 23.1 Agent SDK とは

Claude Agent SDK は Claude Code を動かすエージェントループをプログラマティックに制御するためのライブラリである。Python と TypeScript の両方で提供され、ファイル読み書き、コマンド実行、MCP サーバー接続など Claude Code と同じツールをプログラムから扱える [^24]。

**主なユースケース：**
- カスタム自動化スクリプト
- 社内ツールへの Claude 統合
- CI/CD パイプラインの構築
- バッチ処理・定期実行ジョブ
- マルチエージェントシステム

### 23.2 インストールと基本設定

#### Python


```bash
# uv を使う場合（推奨）
uv init my-agent && cd my-agent
uv add claude-agent-sdk

# pip を使う場合
pip install claude-agent-sdk
```


#### TypeScript


```bash
npm init -y
npm install @anthropic-ai/claude-agent-sdk
npm install -D typescript tsx @types/node
```


#### 認証設定


```bash
# .env
ANTHROPIC_API_KEY=your-api-key-here

# AWS Bedrock 経由の場合
CLAUDE_CODE_USE_BEDROCK=1
AWS_REGION=us-west-2

# Google Vertex AI 経由の場合
CLAUDE_CODE_USE_VERTEX=1
ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
CLOUD_ML_REGION=us-east5
```


### 23.3 基本的な使い方

#### Python の例


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


async def run_agent(prompt: str):
    """Claude エージェントを実行してメッセージをストリーミング"""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob", "Grep", "Bash"],
            permission_mode="acceptEdits",
            system_prompt="あなたは経験豊富な Python エンジニアです。",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"ツール呼び出し: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"完了: {message.subtype}")
            return message


asyncio.run(run_agent("utils.py のバグを修正してください"))
```


#### TypeScript の例


```typescript
import { query, ClaudeAgentOptions } from "@anthropic-ai/claude-agent-sdk";

async function runAgent(prompt: string) {
  for await (const message of query({
    prompt,
    options: {
      allowedTools: ["Read", "Edit", "Glob", "Grep", "Bash"],
      permissionMode: "acceptEdits",
      systemPrompt: "あなたは経験豊富な TypeScript エンジニアです。",
    } satisfies ClaudeAgentOptions,
  })) {
    if (message.type === "assistant" && message.message?.content) {
      for (const block of message.message.content) {
        if ("text" in block) {
          console.log(block.text);
        } else if ("name" in block) {
          console.log(`ツール呼び出し: ${block.name}`);
        }
      }
    } else if (message.type === "result") {
      console.log(`完了: ${message.subtype}`);
    }
  }
}

runAgent("tsconfig.json の設定を strict モードに更新してください");
```


### 23.4 高度な設定オプション

#### ClaudeAgentOptions の全パラメータ

| パラメータ | 型 | 説明 | デフォルト |
|-----------|---|------|----------|
| `allowedTools` | `string[]` | 使用可能なツールリスト | 全ツール |
| `permissionMode` | `string` | 権限モード | `"default"` |
| `systemPrompt` | `string` | カスタムシステムプロンプト | なし |
| `maxTurns` | `number` | 最大ターン数 | 制限なし |
| `mcpServers` | `object` | MCP サーバー設定 | なし |
| `model` | `string` | 使用モデル | Sonnet |
| `cwd` | `string` | 作業ディレクトリ | 現在のディレクトリ |
| `env` | `object` | 環境変数の追加 | なし |

#### カスタムツール承認コールバック


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def my_approval_handler(tool_name: str, tool_input: dict) -> bool:
    """カスタムツール承認ロジック"""
    # Bash コマンドは追加確認
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if "rm" in command or "sudo" in command:
            print(f"危険なコマンドをブロック: {command}")
            return False
    return True


async def main():
    async for message in query(
        prompt="コードをクリーンアップしてください",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash"],
            permission_mode="default",
            can_use_tool=my_approval_handler,  # カスタム承認
        ),
    ):
        pass


asyncio.run(main())
```


### 23.5 実用的なエージェント例

#### コードマイグレーションエージェント


```python
import asyncio
import os
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def migrate_file(file_path: str) -> bool:
    """単一ファイルを Python 3.12 の新構文に移行"""
    result = None
    async for message in query(
        prompt=f"""
        {file_path} を Python 3.12 の新機能を使って最適化してください：
        - match/case 文の活用
        - TypeVarTuple と ParamSpec の型ヒント
        - tomllib の使用（configparser の代替）
        変更は最小限にして、動作を変えないでください。
        """,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit"],
            permission_mode="acceptEdits",
            cwd=str(Path(file_path).parent),
        ),
    ):
        if isinstance(message, ResultMessage):
            result = message

    return result is not None and result.subtype == "success"


async def migrate_project(src_dir: str):
    """プロジェクト全体を並列移行"""
    python_files = list(Path(src_dir).rglob("*.py"))
    print(f"{len(python_files)} ファイルを移行します...")

    # 並列実行（最大5並行）
    semaphore = asyncio.Semaphore(5)

    async def migrate_with_limit(f):
        async with semaphore:
            success = await migrate_file(str(f))
            status = "OK" if success else "FAIL"
            print(f"[{status}] {f}")

    await asyncio.gather(*[migrate_with_limit(f) for f in python_files])


asyncio.run(migrate_project("./src"))
```


#### ドキュメント生成エージェント


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def generate_api_docs(api_file: str) -> str:
    """API ファイルから Markdown ドキュメントを生成"""
    docs = []

    async for message in query(
        prompt=f"""
        {api_file} の API エンドポイントを分析して、以下の形式で Markdown ドキュメントを生成してください：

        ## エンドポイント名
        **Method:** GET/POST/etc.
        **Path:** /api/v1/xxx

        ### 説明
        何をするエンドポイントか

        ### リクエスト
        - Body/Query パラメータ（型と必須/任意）

        ### レスポンス
        - 成功時のレスポンス例（JSON）
        - エラー時のレスポンス

        ### 使用例
        curl コマンド例

        ファイルには書き込まず、ドキュメントテキストだけ出力してください。
        """,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep"],  # 読み取りのみ
            permission_mode="default",
        ),
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    docs.append(block.text)

    return "\n".join(docs)


# 使用例
async def main():
    doc = await generate_api_docs("src/api/users.py")
    with open("docs/api/users.md", "w") as f:
        f.write(doc)
    print("ドキュメントを生成しました: docs/api/users.md")


asyncio.run(main())
```


#### MCP サーバーを使ったエージェント


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def github_pr_review(pr_number: int):
    """GitHub MCP を使って PR を自動レビュー"""
    async for message in query(
        prompt=f"""
        GitHub PR #{pr_number} をレビューしてください：
        1. GitHub MCP を使って PR の差分を取得
        2. コードの品質、セキュリティ、パフォーマンスを評価
        3. 問題があればコメントを投稿
        4. 問題がなければ Approve
        """,
        options=ClaudeAgentOptions(
            allowed_tools=["mcp__github__get_pull_request",
                          "mcp__github__create_pull_request_review",
                          "mcp__github__add_pull_request_review_comment"],
            permission_mode="acceptEdits",
            mcp_servers={
                "github": {
                    "type": "http",
                    "url": "https://api.githubcopilot.com/mcp/",
                    "headers": {
                        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"
                    }
                }
            },
        ),
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)


asyncio.run(github_pr_review(142))
```


### 23.6 エラーハンドリングとリトライ


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.exceptions import AgentError, RateLimitError


async def resilient_agent(prompt: str, max_retries: int = 3):
    """エラーハンドリング付きエージェント"""
    for attempt in range(max_retries):
        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=["Read", "Edit"],
                    permission_mode="acceptEdits",
                    max_turns=20,
                ),
            ):
                if isinstance(message, ResultMessage):
                    if message.subtype == "success":
                        return True
                    else:
                        print(f"エージェントが失敗: {message.subtype}")
                        return False

        except RateLimitError:
            wait_time = 2 ** attempt  # 指数バックオフ
            print(f"レート制限。{wait_time}秒後にリトライ...")
            await asyncio.sleep(wait_time)

        except AgentError as e:
            print(f"エージェントエラー (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise

    return False
```


### 23.7 本番環境へのデプロイ

#### Docker コンテナでの運用


```dockerfile
# Dockerfile
FROM node:20-slim

# Claude Code CLI のインストール
RUN npm install -g @anthropic-ai/claude-code

# Python SDK のインストール
RUN pip3 install claude-agent-sdk

WORKDIR /app
COPY . .

# 非 root ユーザーで実行（セキュリティ）
RUN useradd -m agent
USER agent

CMD ["python3", "agent.py"]
```



```yaml
# docker-compose.yml
services:
  agent:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./workspace:/app/workspace  # 作業ディレクトリのみマウント
    restart: unless-stopped
```


---

## 24. FAQ・トラブルシューティング詳説

### 24.1 よくある質問（FAQ）

#### Q: Claude Code はどのくらいのコストがかかる？

**A:** コストはトークン消費量に依存する。目安：

| 作業内容 | トークン消費量 | 概算コスト（Sonnet） |
|---------|-------------|-------------------|
| 小さなバグ修正 | ~5K tokens | ~$0.02 |
| 機能実装（100行） | ~20K tokens | ~$0.08 |
| 大規模リファクタリング | ~100K tokens | ~$0.40 |
| コードベース全体分析 | ~200K tokens | ~$0.80 |

コスト削減のポイント：
- `/compact` で会話を圧縮
- タスク間で `/clear` を使う
- 探索タスクは Haiku モデルで実行
- 具体的なファイルを `@` で直接指定

#### Q: Claude が同じミスを繰り返す場合は？

**A:** 以下の順で対処する：

1. **一時的な解決**: `/clear` してコンテキストをリセット、より具体的なプロンプトで再スタート
2. **恒久的な解決**: CLAUDE.md に「IMPORTANT: [具体的なルール]」を追加
3. **フックによる強制**: 重要なルールはフックで機械的に強制する

#### Q: 機密ファイルを誤って Claude に読ませてしまったら？

**A:** Claude Code はサーバーに送信するコンテキストのログを残す。以下を確認する：

1. セッションを終了して `~/.claude/` のログを確認
2. 機密情報が含まれているセッションログを削除
3. 該当する機密情報（API キー、パスワード等）を無効化・ローテーション
4. CLAUDE.md や `.gitignore` に機密ファイルのパスを追記

#### Q: Claude が「実行できない」と言ってコマンドを拒否する場合は？

**A:** 権限の問題。以下を確認：


```bash
# 現在の権限設定を確認
/permissions

# 特定コマンドを許可リストに追加
# settings.json の permissions.allow に追加する
```


#### Q: サブエージェントとメインエージェントでファイルを共有するには？

**A:** サブエージェントはメインエージェントと同じファイルシステムを使用するため、ファイルを介した共有が可能：


```
# メインエージェント
Use a subagent to investigate the auth module.
The subagent should write findings to /tmp/auth-analysis.md

# 結果の利用
Read /tmp/auth-analysis.md and implement the improvements
```


#### Q: Claude Code をオフライン環境で使うには？

**A:** Claude Code 自体は Anthropic API に接続が必要だが、以下の代替方法がある：

1. **AWS Bedrock**: VPC 内に閉じたプライベートエンドポイントが利用可能
2. **Google Vertex AI**: プロジェクト内のリソースのみにアクセスを制限可能
3. **オンプレミス**: 現時点では公式サポートなし

#### Q: チームメンバーに Claude Code を導入するには？

**A:** 段階的な導入が効果的：

1. **フェーズ1**: 個人の生産性向上（読み取り専用から始める）
2. **フェーズ2**: CLAUDE.md とエージェントの共有
3. **フェーズ3**: CI/CD 統合と自動化
4. **フェーズ4**: カスタムプラグイン・MCP サーバーの開発

### 24.2 トラブルシューティング詳説

#### 接続・認証エラー


```bash
# API キーの確認
echo $ANTHROPIC_API_KEY | head -c 20  # 最初の20文字だけ表示

# 接続テスト
claude -p "Hello" --max-turns 1

# プロキシ経由の接続が必要な環境
export HTTPS_PROXY=http://proxy.company.com:8080
export HTTP_PROXY=http://proxy.company.com:8080
claude
```


#### パフォーマンスが遅い場合


```bash
# コンテキストのサイズを確認
/context-usage  # コンテキスト使用量を表示

# 段階的な対処
1. /compact でコンテキストを圧縮
2. /clear でコンテキストをリセット（最終手段）
3. より具体的なファイルを @で直接指定
4. サブエージェントに調査を委譲

# モデルを軽量なものに切り替え
/model haiku    # 高速・低コスト
/model sonnet   # バランス型（デフォルト）
```


#### フックが動作しない場合


```bash
# フック設定の確認
/hooks

# フックのデバッグ（verbose モードで実行ログを確認）
Ctrl+O  # verbose モードのトグル

# フックスクリプトの権限確認
ls -la .claude/hooks/
chmod +x .claude/hooks/*.sh  # 実行権限を付与

# フックのテスト実行
bash .claude/hooks/your-hook.sh <<< '{"tool_input": {"command": "echo test"}}'
```


#### MCP サーバーが接続できない場合


```bash
# MCP デバッグモードで起動
claude --mcp-debug

# MCP サーバーのステータス確認
/mcp

# タイムアウトを延長（デフォルトは60秒）
MCP_TIMEOUT=30000 claude

# stdio サーバーの直接テスト
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  npx -y @your-org/your-mcp-server
```


#### Windows (WSL) での問題


```bash
# WSL2 の確認（WSL1 はサンドボックス非対応）
wsl --status

# WSL2 へのアップグレード
wsl --set-version Ubuntu 2

# パス区切り文字の問題
# Claude Code は WSL のパス（/mnt/c/...）を使う
# Windows パス（C:\...）は使用不可

# Node.js のバージョン確認
node --version  # 18.0 以上が必要
```


#### Git 操作の問題


```bash
# Claude が git コマンドを使えない場合
git config --global --list  # git 設定確認
git config --global user.email "you@example.com"
git config --global user.name "Your Name"

# サブモジュールがある場合の初期化
git submodule update --init --recursive

# 大きなファイルで git が遅い場合
git config core.preloadindex true
git config core.fscache true
```


### 24.3 パフォーマンスチューニング

#### 大規模コードベースでの最適化


```markdown
# CLAUDE.md に追加するパフォーマンス指示

## 大規模コードベースでの作業ルール
- 全ファイルを読み込む前に Grep でターゲットを絞ること
- ディレクトリ全体ではなく特定ファイルを @で指定すること
- 探索タスクはサブエージェントに委譲すること
- 100行を超える出力はファイルに書き出すこと

## 禁止事項（パフォーマンス）
- `cat` で 1000 行を超えるファイルを読み込まない
- `find / -name "*.py"` のようなルートからの検索をしない
- 不要な依存ファイルを全て読み込まない
```


#### バッチ処理の最適化


```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def process_files_optimally(file_list: list[str]):
    """ファイルを最適な並列数で処理"""
    # CPU コア数 × 2 を上限に設定
    max_concurrent = min(len(file_list), 8)
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def process_one(f: str):
        async with semaphore:
            result_text = []
            async for message in query(
                prompt=f"@{f} のコードを最適化してください",
                options=ClaudeAgentOptions(
                    allowed_tools=["Read", "Edit"],
                    permission_mode="acceptEdits",
                    max_turns=10,  # 無限ループ防止
                ),
            ):
                if hasattr(message, "content"):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text.append(block.text)
            return {"file": f, "output": "\n".join(result_text)}

    tasks = [process_one(f) for f in file_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = [r for r in results if isinstance(r, dict)]
    errors = [r for r in results if isinstance(r, Exception)]

    print(f"成功: {len(success)}, エラー: {len(errors)}")
    return success
```


### 24.4 デバッグのベストプラクティス

#### エラーメッセージの読み方


```
# Claude Code の典型的なエラーメッセージ

# 権限エラー
"Permission denied: This tool is not in the allowed list"
→ /permissions で許可リストに追加

# コンテキスト超過
"Context window limit reached"
→ /compact を実行するか /clear でリセット

# タイムアウト
"Tool execution timed out after Xs"
→ コマンドの実行時間を確認。CLAUDE_TOOL_TIMEOUT 環境変数で調整

# MCP 接続エラー
"Failed to connect to MCP server: connection refused"
→ サーバーが起動しているか確認。claude --mcp-debug で詳細を確認
```


#### ログの活用


```bash
# デバッグログの有効化
CLAUDE_DEBUG=1 claude

# verbose モード（セッション中）
Ctrl+O

# ログファイルの場所
ls ~/.claude/logs/  # セッションごとのログ

# 最新のログを確認
tail -f ~/.claude/logs/$(ls -t ~/.claude/logs/ | head -1)
```


---

[^21]: [Best AI Coding Assistants 2026 - YUV.AI](https://yuv.ai/learn/compare/ai-coding-assistants)
[^22]: [Claude Code GitHub Actions - Anthropic 公式](https://code.claude.com/docs/en/github-actions)
[^23]: [Security - Claude Code Docs](https://code.claude.com/docs/en/security)
[^24]: [Agent SDK overview - Anthropic 公式](https://platform.claude.com/docs/en/agent-sdk/overview)

---

## 脚注

[^1]: [Best Practices for Claude Code - Anthropic 公式](https://code.claude.com/docs/en/best-practices)
[^2]: [Writing a Good CLAUDE.md - HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
[^3]: [Claude Code のベストプラクティス - 日本語公式](https://code.claude.com/docs/ja/best-practices)
[^4]: [Create Custom Subagents - Anthropic 公式](https://code.claude.com/docs/en/sub-agents)
[^5]: [Claude Code's Custom Agent Framework - DEV Community](https://dev.to/therealmrmumba/claude-codes-custom-agent-framework-changes-everything-4o4m)
[^6]: [Extend Claude with Skills - Anthropic 公式](https://code.claude.com/docs/en/skills)
[^7]: [Hooks Reference - Anthropic 公式](https://code.claude.com/docs/en/hooks)
[^8]: [Claude Code Hooks: Complete Guide - DEV Community](https://dev.to/lukaszfryc/claude-code-hooks-complete-guide-with-20-ready-to-use-examples-2026-dcg)
[^9]: [Connect Claude Code to tools via MCP - Anthropic 公式](https://code.claude.com/docs/en/mcp)
[^10]: [Claude Code --dangerously-skip-permissions: Safe Usage Guide](https://www.ksred.com/claude-code-dangerously-skip-permissions-when-to-use-it-and-when-you-absolutely-shouldnt/)
[^11]: [What is UltraThink in Claude Code - ClaudeLog](https://claudelog.com/faqs/what-is-ultrathink/)
[^12]: [Mastering Git Worktrees with Claude Code - Medium](https://medium.com/@dtunai/mastering-git-worktrees-with-claude-code-for-parallel-development-workflow-41dc91e645fe)
[^13]: [Model Configuration - Anthropic 公式](https://code.claude.com/docs/en/model-config)
[^14]: [Use Claude Code in VS Code - Anthropic 公式](https://code.claude.com/docs/en/vs-code)
[^15]: [Run Claude Code Programmatically - Anthropic 公式](https://code.claude.com/docs/en/headless)
[^16]: [How Claude Code is built - Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built)
[^17]: [Orchestrate teams of Claude Code sessions - Anthropic 公式](https://code.claude.com/docs/en/agent-teams)
[^18]: [Claude Code Plugins: Best Plugins, Installation & Build Guide 2026 - Morph](https://www.morphllm.com/claude-code-plugins)
[^19]: [Sandboxing - Anthropic 公式](https://code.claude.com/docs/en/sandboxing)
[^20]: [Customize your status line - Anthropic 公式](https://code.claude.com/docs/en/statusline)

---

> このガイドは 2026年2月24日 時点の情報に基づいています。Claude Code は活発に開発が進められており、最新情報は [公式ドキュメント](https://code.claude.com/docs/) を参照してください。

---

---

[← 前: 応用編](advanced) | [次: 上級編 →](expert)
