# Claude Code マスターガイド

> Claude Code の使い方・設定・Tips を網羅した包括的リファレンス（2026年3月版）

---

## 目次

- [1. はじめに](#1-はじめに)
- [2. CLAUDE.md の書き方と活用](#2-claudemd-の書き方と活用)
- [3. カスタムエージェント (.claude/agents/)](#3-カスタムエージェント-claudeagents)
- [4. スキル (.claude/skills/)](#4-スキル-claudeskills)
- [5. フック (.claude/hooks/)](#5-フック-claudehooks)
- [6. MCP サーバー連携](#6-mcp-サーバー連携)
- [7. 権限・セキュリティ設定](#7-権限セキュリティ設定)
- [8. ワークフロー・使い方 Tips](#8-ワークフロー使い方-tips)
- [9. パフォーマンス・コスト最適化](#9-パフォーマンスコスト最適化)
- [10. IDE 連携](#10-ide-連携)
- [11. トラブルシューティング](#11-トラブルシューティング)
- [12. 高度な使い方](#12-高度な使い方)
- [13. プラグイン](#13-プラグイン)
- [14. サンドボックス](#14-サンドボックス)
- [15. ステータスライン](#15-ステータスライン)
- [16. 実際のユースケース・事例](#16-実際のユースケース事例)
- [17. 情報源・参考リンク](#17-情報源参考リンク)
- [18. エコシステム連携 - MCP サーバー詳説・IDE 統合](#18-エコシステム連携---mcp-サーバー詳説ide-統合)
- [19. ツール比較 - Claude Code vs Cursor vs Copilot vs Aider](#19-ツール比較---claude-code-vs-cursor-vs-copilot-vs-aider)
- [20. CI/CD 統合 - GitHub Actions・自動レビュー](#20-cicd-統合---github-actions自動レビュー)
- [21. チーム開発 - CLAUDE.md 共有・コードレビュー](#21-チーム開発---claudemd-共有コードレビュー)
- [22. セキュリティ - パーミッション・機密情報・サンドボックス](#22-セキュリティ---パーミッション機密情報サンドボックス)
- [23. Agent SDK - カスタムエージェント構築](#23-agent-sdk---カスタムエージェント構築)
- [24. FAQ・トラブルシューティング詳説](#24-faqトラブルシューティング詳説)

---

## 1. はじめに

Claude Code は Anthropic が提供するエージェント型コーディング環境である。従来のチャットボットとは異なり、ファイルの読み書き、コマンド実行、コード変更を自律的に行うことができる。ユーザーは「何を作りたいか」を記述するだけで、Claude がコードベースの探索、計画立案、実装まで一貫して行う。

### Claude Code の核心的な原則

Claude Code を効果的に使いこなす上で最も重要な原則は **コンテキストウィンドウの管理** である。Claude のコンテキストウィンドウには会話全体、読み込んだファイル、コマンド出力が全て含まれ、これが埋まるにつれてパフォーマンスが低下する。このガイドで紹介するベストプラクティスの多くは、この制約を踏まえたものである [^1]。

---

## 2. CLAUDE.md の書き方と活用

### 2.1 CLAUDE.md とは

CLAUDE.md は Claude Code が毎回の会話の開始時に読み込む特別なファイルであり、ビルドコマンド、コードスタイル、ワークフロールールなど、コードだけからは推測できない永続的なコンテキストを Claude に提供する [^1][^2]。

### 2.2 CLAUDE.md の階層構造

CLAUDE.md は以下の場所に配置でき、それぞれスコープが異なる：

| 配置場所 | スコープ | 用途 |
|---------|---------|------|
| `~/.claude/CLAUDE.md` | 全プロジェクト共通 | 個人の開発スタイル、グローバル設定 |
| `./CLAUDE.md`（プロジェクトルート） | プロジェクト全体 | git にコミットしてチームで共有 |
| `./CLAUDE.local.md` | プロジェクトローカル | `.gitignore` に追加して個人用に |
| 親ディレクトリの `CLAUDE.md` | モノレポ用 | `root/CLAUDE.md` と `root/foo/CLAUDE.md` の両方が読み込まれる |
| 子ディレクトリの `CLAUDE.md` | ディレクトリ固有 | そのディレクトリのファイル作業時にオンデマンドで読み込み |

### 2.3 効果的な CLAUDE.md の書き方

#### 基本原則

- **50〜100行に収める**：ルートの CLAUDE.md は簡潔に。詳細は `@import` で分割する [^2]
- **毎セッション読み込まれる**ことを意識し、広く適用される内容のみ記載
- **各行について「この行がなければ Claude はミスをするか？」と自問**し、不要なら削除
- 強調が必要な場合は `IMPORTANT` や `YOU MUST` で優先度を上げる

#### 書くべき内容と書くべきでない内容

| 書くべき内容 | 書くべきでない内容 |
|-------------|-------------------|
| Claude が推測できない Bash コマンド | コードを読めばわかること |
| デフォルトと異なるコードスタイルルール | 標準的な言語規約（Claude は既に知っている） |
| テスト手順とテストランナーの指定 | 詳細な API ドキュメント（リンクで代替） |
| リポジトリの作法（ブランチ命名、PR 規約） | 頻繁に変わる情報 |
| プロジェクト固有のアーキテクチャ判断 | 長い説明やチュートリアル |
| 開発環境の癖（必要な環境変数など） | ファイルごとのコードベース説明 |
| よくあるゴッチャや非自明な挙動 | 「きれいなコードを書け」のような自明な指示 |

#### 実践的な CLAUDE.md の例

```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance

# Build commands
- Test: `npm run test -- --watch=false`
- Lint: `npm run lint`
- Typecheck: `npx tsc --noEmit`

# Architecture
- Backend: Express.js with TypeScript
- Database: PostgreSQL with Prisma ORM
- Frontend: React 19 with Vite

# IMPORTANT
- NEVER commit directly to main. Always create a feature branch.
- YOU MUST run tests before creating a PR.
```

#### @import による外部ファイルの読み込み

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

### 2.4 CLAUDE.md のアンチパターン

1. **巨大すぎる CLAUDE.md**：長すぎるとルールが埋もれて無視される。Claude が何度も同じミスをする場合、ファイルが長すぎてルールが見落とされている可能性がある
2. **自明な内容の記載**：Claude が既に知っている標準規約を繰り返し書くのは無駄
3. **頻繁に変わる情報の記載**：バージョン番号やデプロイURL等は環境変数やスクリプトで管理すべき
4. **CLAUDE.md をフック代わりに使う**：毎回必ず実行されるべき処理はフックで保証する [^1]

#### `/init` コマンドの活用

`/init` を実行すると、現在のプロジェクト構造を分析してスターターの CLAUDE.md を自動生成してくれる。日本語で生成したい場合は `/init "日本語で作成してください"` とパラメータを追加する [^3]。

---

## 3. カスタムエージェント (.claude/agents/)

### 3.1 サブエージェントとは

サブエージェントは特定のタスクを処理する専門AIアシスタントである。各サブエージェントは独自のコンテキストウィンドウ、カスタムシステムプロンプト、特定のツールアクセス、独立した権限を持つ [^4][^5]。

サブエージェントのメリット：
- **コンテキストの保持**：探索や実装をメイン会話から分離
- **制約の強制**：使用可能なツールを限定
- **設定の再利用**：ユーザーレベルのエージェントで全プロジェクトに適用
- **動作の特化**：特定ドメインに集中したシステムプロンプト
- **コスト制御**：Haiku 等の安価なモデルにタスクをルーティング

### 3.2 ビルトインサブエージェント

| エージェント | モデル | ツール | 用途 |
|------------|-------|--------|------|
| **Explore** | Haiku（高速） | 読み取り専用 | ファイル検索、コード分析、コードベース探索 |
| **Plan** | 継承 | 読み取り専用 | プランモード時のコードベースリサーチ |
| **General-purpose** | 継承 | 全ツール | 複雑な調査、マルチステップ操作、コード変更 |
| **Bash** | 継承 | - | 別コンテキストでのターミナルコマンド実行 |

### 3.3 YAML Frontmatter の全オプション

サブエージェントは Markdown ファイルに YAML frontmatter を付けて定義する。

```yaml
---
name: code-reviewer           # 必須: 一意の識別子（小文字・ハイフン）
description: Reviews code     # 必須: いつ委譲すべきかの説明
tools: Read, Glob, Grep       # 任意: 使用可能ツール（省略時は全ツール継承）
disallowedTools: Write, Edit  # 任意: 拒否ツール
model: sonnet                 # 任意: sonnet / opus / haiku / inherit
permissionMode: default       # 任意: default / acceptEdits / dontAsk / bypassPermissions / plan
maxTurns: 50                  # 任意: 最大ターン数
skills:                       # 任意: 起動時にロードするスキル
  - api-conventions
mcpServers:                   # 任意: 利用可能な MCP サーバー
  - slack
hooks:                        # 任意: ライフサイクルフック
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
memory: user                  # 任意: user / project / local（永続メモリ）
background: false             # 任意: バックグラウンド実行
isolation: worktree           # 任意: worktree で隔離実行
---

You are a code reviewer. Analyze code and provide actionable feedback.
```

### 3.4 エージェントの配置場所と優先度

| 配置場所 | スコープ | 優先度 |
|---------|---------|--------|
| `--agents` CLI フラグ | 現在のセッション | 1（最高） |
| `.claude/agents/` | プロジェクト | 2 |
| `~/.claude/agents/` | 全プロジェクト | 3 |
| プラグインの `agents/` | プラグイン有効時 | 4（最低） |

### 3.5 実践的なエージェント例

#### セキュリティレビューアー

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---

You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```

#### デバッガー

```markdown
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior
tools: Read, Edit, Bash, Grep, Glob
---

You are an expert debugger specializing in root cause analysis.

When invoked:
1. Capture error message and stack trace
2. Identify reproduction steps
3. Isolate the failure location
4. Implement minimal fix
5. Verify solution works
```

#### CLI からの一時的なエージェント定義

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

### 3.6 エージェントの管理

- `/agents` コマンドでインタラクティブに管理（表示、作成、編集、削除）
- `claude agents` でコマンドラインから一覧表示
- セッション開始時にロードされるため、手動追加後はセッション再起動が必要

---

## 4. スキル (.claude/skills/)

### 4.1 スキルとは

スキルは Claude の能力を拡張するツールである。`SKILL.md` ファイルに指示を書くだけで Claude のツールキットに追加される。関連するタスクのとき Claude が自動的に使用するか、`/skill-name` で直接呼び出せる [^6]。

> **注意**: 以前の `.claude/commands/` は skills に統合された。既存のコマンドファイルはそのまま動作するが、スキルにはディレクトリサポート、frontmatter、自動ロード等の追加機能がある。

### 4.2 スキルの配置場所

| レベル | パス | スコープ |
|-------|------|---------|
| エンタープライズ | マネージド設定 | 組織全体 |
| 個人 | `~/.claude/skills/<name>/SKILL.md` | 全プロジェクト |
| プロジェクト | `.claude/skills/<name>/SKILL.md` | このプロジェクトのみ |
| プラグイン | `<plugin>/skills/<name>/SKILL.md` | プラグイン有効時 |

### 4.3 SKILL.md の書き方

```yaml
---
name: fix-issue                    # 任意: /コマンド名（省略時はディレクトリ名）
description: Fix a GitHub issue    # 推奨: 使用タイミングの説明
argument-hint: "[issue-number]"    # 任意: 引数のヒント
disable-model-invocation: true     # 任意: Claude の自動呼び出しを無効化
user-invocable: true               # 任意: /メニューから非表示にする場合 false
allowed-tools: Read, Grep          # 任意: 許可ツール
model: sonnet                      # 任意: 使用モデル
context: fork                      # 任意: fork でサブエージェント実行
agent: Explore                     # 任意: context: fork 時のエージェント型
hooks:                             # 任意: スキルスコープのフック
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/check.sh"
---

Fix GitHub issue $ARGUMENTS following our coding standards.

1. Read the issue description with `gh issue view $ARGUMENTS`
2. Understand the requirements
3. Implement the fix
4. Write tests
5. Create a commit
```

### 4.4 文字列置換

| 変数 | 説明 |
|------|------|
| `$ARGUMENTS` | スキル呼び出し時に渡された全引数 |
| `$ARGUMENTS[N]` / `$N` | N番目の引数（0始まり） |
| `${CLAUDE_SESSION_ID}` | 現在のセッションID |

### 4.5 動的コンテキスト注入

`` !`command` `` 構文でシェルコマンドを事前実行し、結果をスキルに埋め込める：

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

### 4.6 呼び出し制御

| frontmatter | ユーザー | Claude | コンテキスト |
|-------------|---------|--------|-------------|
| （デフォルト） | 呼び出し可 | 呼び出し可 | 説明文は常にコンテキスト内、本文は呼び出し時にロード |
| `disable-model-invocation: true` | 呼び出し可 | 呼び出し不可 | 説明文もコンテキスト外 |
| `user-invocable: false` | 呼び出し不可 | 呼び出し可 | 説明文は常にコンテキスト内 |

### 4.7 実用的なスキル例

#### API 規約スキル（参照型）

```yaml
---
name: api-conventions
description: REST API design conventions for our services
---

# API Conventions
- Use kebab-case for URL paths
- Use camelCase for JSON properties
- Always include pagination for list endpoints
- Version APIs in the URL path (/v1/, /v2/)
```

#### デプロイスキル（タスク型）

```yaml
---
name: deploy
description: Deploy the application to production
context: fork
disable-model-invocation: true
---

Deploy the application:
1. Run the test suite
2. Build the application
3. Push to the deployment target
4. Verify the deployment succeeded
```

#### コードベース可視化スキル

スキルディレクトリにスクリプトをバンドルし、インタラクティブなHTMLビジュアライゼーションを生成する高度なパターンも可能 [^6]。

---

## 5. フック (.claude/hooks/)

### 5.1 フックとは

フックは Claude Code のライフサイクルの特定ポイントで自動的にシェルコマンドや LLM プロンプトを実行するユーザー定義のトリガーである。CLAUDE.md の指示が「推奨」なのに対し、フックは **決定論的で確実に実行される** [^7][^8]。

### 5.2 フックイベント一覧

| イベント | 発火タイミング | ブロック可能 |
|---------|--------------|-------------|
| `SessionStart` | セッション開始・再開時 | No |
| `UserPromptSubmit` | プロンプト送信時（処理前） | Yes |
| `PreToolUse` | ツール呼び出し実行前 | Yes |
| `PermissionRequest` | 権限ダイアログ表示時 | Yes |
| `PostToolUse` | ツール呼び出し成功後 | No |
| `PostToolUseFailure` | ツール呼び出し失敗後 | No |
| `Notification` | 通知送信時 | No |
| `SubagentStart` | サブエージェント起動時 | No |
| `SubagentStop` | サブエージェント完了時 | Yes |
| `Stop` | Claude の応答完了時 | Yes |
| `TeammateIdle` | チームメイトがアイドルになる時 | Yes |
| `TaskCompleted` | タスク完了マーク時 | Yes |
| `ConfigChange` | 設定ファイル変更時 | Yes |
| `WorktreeCreate` | ワークツリー作成時 | Yes |
| `WorktreeRemove` | ワークツリー削除時 | No |
| `PreCompact` | コンテキスト圧縮前 | No |
| `SessionEnd` | セッション終了時 | No |

### 5.3 設定場所

| 場所 | スコープ | 共有可能 |
|-----|---------|---------|
| `~/.claude/settings.json` | 全プロジェクト | No |
| `.claude/settings.json` | プロジェクト | Yes（git コミット） |
| `.claude/settings.local.json` | プロジェクト（ローカル） | No（gitignore） |
| マネージドポリシー | 組織全体 | Yes |
| プラグインの `hooks/hooks.json` | プラグイン有効時 | Yes |
| スキル/エージェントの frontmatter | コンポーネント実行中 | Yes |

### 5.4 設定構造

フック設定は3階層のネスト構造：

```json
{
  "hooks": {
    "PostToolUse": [           // 1. フックイベント
      {
        "matcher": "Write|Edit",  // 2. マッチャーグループ（正規表現）
        "hooks": [                // 3. フックハンドラー
          {
            "type": "command",
            "command": "npx prettier --write $(jq -r '.tool_input.file_path')"
          }
        ]
      }
    ]
  }
}
```

### 5.5 フックハンドラーの種類

| タイプ | 説明 | デフォルトタイムアウト |
|-------|------|---------------------|
| `command` | シェルコマンドを実行 | 600秒 |
| `prompt` | LLM に単発評価を依頼 | 30秒 |
| `agent` | ツール付きサブエージェントを起動 | 60秒 |

### 5.6 終了コードの意味

| 終了コード | 意味 |
|-----------|------|
| **0** | 成功。stdout の JSON を解析 |
| **2** | ブロッキングエラー。stderr がエラーメッセージとしてフィードバック |
| **その他** | 非ブロッキングエラー。verbose モードで表示 |

### 5.7 実用的なフック例

#### ファイル編集後に自動フォーマット

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write 2>/dev/null; exit 0"
          }
        ]
      }
    ]
  }
}
```

#### 危険なコマンドのブロック

```bash
#!/bin/bash
# .claude/hooks/block-rm.sh
COMMAND=$(jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q 'rm -rf'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Destructive command blocked by hook"
    }
  }'
else
  exit 0
fi
```

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-rm.sh"
          }
        ]
      }
    ]
  }
}
```

#### ESLint の自動実行

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx eslint --fix 2>/dev/null; exit 0"
          }
        ]
      }
    ]
  }
}
```

#### 停止前の品質チェック（プロンプトフック）

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if Claude should stop: $ARGUMENTS. Check if all tasks are complete and tests pass.",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

#### 非同期テスト実行

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/run-tests-async.sh",
            "async": true,
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```

### 5.8 フック管理

- `/hooks` でインタラクティブに管理
- 設定の直接編集は次回セッション開始時に反映
- `"disableAllHooks": true` で一時的に全フックを無効化

---

## 6. MCP サーバー連携

### 6.1 MCP とは

MCP（Model Context Protocol）は AI ツール統合のためのオープンソース標準である。MCP サーバーを接続することで、Claude Code から外部ツール、データベース、API にアクセスできる [^9]。

### 6.2 MCP サーバーの追加方法

#### HTTP サーバー（推奨）

```bash
# 基本構文
claude mcp add --transport http <name> <url>

# 例: Notion に接続
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Bearer トークン付き
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

#### SSE サーバー（非推奨、HTTP を推奨）

```bash
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

#### ローカル stdio サーバー

```bash
claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable \
  -- npx -y airtable-mcp-server
```

### 6.3 人気の MCP サーバー

| サーバー | 用途 |
|---------|------|
| **GitHub** | PR管理、イシュー操作、コードレビュー |
| **Sentry** | エラートラッキング、パフォーマンス監視 |
| **Notion** | ドキュメント管理、ナレッジベース |
| **PostgreSQL (dbhub)** | データベースクエリ |
| **Figma** | デザインアセット取得 |
| **Slack** | チーム連携、通知 |
| **Playwright** | ブラウザテスト自動化 |
| **Perplexity** | ウェブリサーチ |
| **Sequential Thinking** | 複雑な問題分解 |
| **Context7** | 最新ドキュメント参照 |

### 6.4 スコープ管理

| スコープ | 保存場所 | 共有 |
|---------|---------|------|
| `local`（デフォルト） | `~/.claude.json` | 個人・プロジェクト固有 |
| `project` | `.mcp.json`（プロジェクトルート） | git でチーム共有 |
| `user` | `~/.claude.json` | 個人・全プロジェクト |

```bash
# プロジェクトスコープで追加
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp

# ユーザースコープで追加
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

### 6.5 MCP 管理コマンド

```bash
claude mcp list              # 一覧表示
claude mcp get github        # 詳細確認
claude mcp remove github     # 削除
/mcp                         # Claude Code 内でステータス確認・OAuth認証
```

### 6.6 `.mcp.json` での環境変数展開

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

### 6.7 Claude Code 自体を MCP サーバーとして使う

```bash
claude mcp serve
```

Claude Desktop から接続する設定：

```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "claude",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

---

## 7. 権限・セキュリティ設定

### 7.1 権限モード

| モード | 動作 |
|-------|------|
| `default` | 標準的な権限チェック（プロンプト表示） |
| `acceptEdits` | ファイル編集を自動承認 |
| `plan` | 読み取り専用（プランモード） |
| `dontAsk` | 権限プロンプトを自動拒否（明示許可ツールは動作） |
| `bypassPermissions` | 全権限チェックをスキップ |

### 7.2 allowedTools の設定

`/permissions` コマンドで許可するツールをホワイトリスト設定できる：

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test *)",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Task(Explore)"
    ]
  }
}
```

パーミッションルール構文：
- `Bash(npm test)` - 完全一致
- `Bash(git diff *)` - プレフィックスマッチ（`*` の前にスペースが必要）
- `Skill(commit)` - スキルの制御

### 7.3 --dangerously-skip-permissions

```bash
claude --dangerously-skip-permissions
```

**用途**: CI/CD パイプライン、リンティング修正、ボイラープレート生成など、承認なしで連続実行したい場合 [^10]。

**重要な注意事項**:
- 任意のコマンドが実行可能になるため、**データ損失、システム破損、データ流出のリスク**がある
- **インターネットアクセスのないサンドボックス環境でのみ使用すべき**
- Docker コンテナ等の隔離環境が推奨
- 本番の開発マシンでの使用は避ける

**安全な代替アプローチ**:

```bash
# allowedTools でツールを制限して使う
claude -p "Fix lint errors" \
  --allowedTools "Read,Edit,Bash(npm run lint *)"
```

### 7.4 サンドボックス

`/sandbox` でOS レベルの分離を有効化。ファイルシステムとネットワークアクセスを制限しつつ、定義された境界内で自由に作業できる。

---

## 8. ワークフロー・使い方 Tips

### 8.1 効果的なプロンプトの書き方

#### 自己検証手段を与える（最も効果的）

Claude に自分の作業を検証する手段を与えることが、最も効果の高い方法である [^1]。

| 戦略 | Before | After |
|------|--------|-------|
| **検証基準を提供** | "メール検証関数を実装して" | "validateEmail 関数を書いて。テストケース: user@example.com は true、invalid は false。実装後にテストを実行して" |
| **UI を視覚的に検証** | "ダッシュボードを良くして" | "[スクショ貼付] このデザインを実装して。結果のスクショを撮って元と比較し、差分を修正して" |
| **根本原因に対処** | "ビルドが失敗している" | "このエラーでビルドが失敗する: [エラー貼付]。修正してビルド成功を確認して。エラーを抑制せず根本原因に対処して" |

#### 具体的なコンテキストを与える

```
# Bad
"テストを追加して"

# Good
"foo.py のユーザーがログアウトしたケースのテストを書いて。モックは避けて。"

# Bad
"カレンダーウィジェットを追加して"

# Good
"ホームページの既存ウィジェットの実装を見てパターンを理解して。
HotDogWidget.php が良い例。そのパターンに従って新しいカレンダーウィジェットを実装して。"
```

#### リッチコンテンツの提供方法

- **`@` でファイル参照**：`@src/auth/login.ts` で直接参照
- **画像を貼り付け**：コピー&ペーストまたはドラッグ&ドロップ
- **URL を提供**：ドキュメントや API リファレンスのリンク
- **パイプでデータ入力**：`cat error.log | claude`

#### 思考の深さを制御するトリガーワード

| ワード | 思考トークン数 | 用途 |
|-------|--------------|------|
| `"think"` | 約4K | 簡単な問題 |
| `"think hard"` / `"megathink"` | 約10K | 中程度の問題 |
| `"ultrathink"` | 約32K | 複雑なアーキテクチャ決定、深い分析 |

> **注意**: 2026年現在、extended thinking はデフォルトで有効になっており、`/effort` コマンドで低/中/高/最大を制御できる [^11]。

### 8.2 探索 → 計画 → 実装 → コミットの4フェーズ

```
1. 【探索】プランモードで読み取り専用調査
   > read /src/auth and understand how we handle sessions

2. 【計画】実装計画の作成
   > I want to add Google OAuth. What files need to change? Create a plan.
   (Ctrl+G で計画をエディタで編集可能)

3. 【実装】ノーマルモードで実装
   > implement the OAuth flow from your plan. Write tests and fix failures.

4. 【コミット】
   > commit with a descriptive message and open a PR
```

### 8.3 Claude にインタビューさせる

大きな機能の場合、最初にClaudeにインタビューさせると効果的：

```
I want to build [brief description]. Interview me in detail using the
AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and
tradeoffs. Don't ask obvious questions, dig into the hard parts.

Keep interviewing until we've covered everything, then write a complete
spec to SPEC.md.
```

仕様完成後、新しいセッションで実装すると、クリーンなコンテキストで作業できる。

### 8.4 セッション管理

#### 早めの軌道修正

- **`Esc`**: Claude を途中で停止（コンテキストは保持）
- **`Esc + Esc`** / **`/rewind`**: リワインドメニューで前の状態に復元
- **`"Undo that"`**: Claude に変更を取り消させる
- **`/clear`**: 無関係なタスク間でコンテキストをリセット

**2回同じ問題を修正しても直らなければ `/clear` して、学んだことを含むより良いプロンプトで再スタート** [^1]。

#### コンテキストの積極的な管理

```bash
/clear                        # タスク間でコンテキスト全リセット
/compact                      # 会話を要約して圧縮
/compact Focus on API changes # 指示付き圧縮
```

- `/rewind` → メッセージチェックポイントを選択 → 「Summarize from here」で部分圧縮
- CLAUDE.md に圧縮指示を追加：`"When compacting, always preserve the full list of modified files and any test commands"`

#### セッションの再開

```bash
claude --continue    # 最新の会話を再開
claude --resume      # 最近のセッションから選択
/rename              # セッションに名前を付ける（例: "oauth-migration"）
```

### 8.5 サブエージェントの活用

コンテキストが最も重要なリソースであるため、サブエージェントの活用が強力：

```
# 調査の委譲（メインコンテキストを汚さない）
Use subagents to investigate how our auth system handles token refresh

# 並行リサーチ
Research the authentication, database, and API modules in parallel
using separate subagents

# 検証
Use a subagent to review this code for edge cases
```

### 8.6 Git ワークフロー（ワークツリー・並行作業）

Git Worktree を使うと、同じリポジトリの複数ブランチを同時にチェックアウトし、各ブランチで独立した Claude セッションを実行できる [^12]。

#### ワークツリーの作成と使用

```bash
# --worktree フラグでワークツリーを作成して Claude を起動
claude --worktree feature-auth

# サブエージェントでワークツリー隔離
# エージェントの frontmatter に isolation: worktree を追加
```

#### 並行開発パターン

1. **Session A**: Feature X を実装
2. **Session B**: Bug fix Y を修正
3. **Session C**: テスト追加

各セッションは独立したファイルとブランチで作業し、互いに干渉しない。

#### Writer/Reviewer パターン

| Session A（Writer） | Session B（Reviewer） |
|--------------------|----------------------|
| `Implement a rate limiter` | |
| | `Review the rate limiter in @src/middleware/rateLimiter.ts` |
| `Here's the review feedback: [output]. Address these issues.` | |

### 8.7 CI/CD 統合（GitHub Actions）

```yaml
name: Claude Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code
      - name: Review PR
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude -p "Review the changes in this PR for code quality,
          security issues, and best practices. Provide actionable feedback." \
          --output-format json \
          --allowedTools "Read,Grep,Glob,Bash(git diff *)"
```

### 8.8 テスト駆動開発との組み合わせ

```
1. "Write failing tests for the new user registration feature"
2. "Now implement the code to make all tests pass"
3. "Refactor the implementation while keeping tests green"
```

別セッションでテストを書き、別セッションで実装するパターンも効果的。

### 8.9 チーム開発での活用

- **CLAUDE.md を git にコミット**してチームで共有
- **プロジェクトスコープのスキルとエージェント**を `.claude/` に配置
- **`.mcp.json`** でMCPサーバー設定を共有
- **コードレビューのためのサブエージェント**を標準化

---

## 9. パフォーマンス・コスト最適化

### 9.1 モデル選択と切り替え

タクティカルなモデル切り替えでコストを60〜80%削減できる [^13]。

| モデル | 特徴 | コスト | 推奨用途 |
|-------|------|-------|---------|
| **Sonnet** | Opus の90%の能力、2倍の速度 | 中 | デフォルト。大半の開発タスク |
| **Haiku** | 最もコスト効率が良い | 低（Sonnet の約1/4） | 簡単なタスク、コードサーチ |
| **Opus** | 最高の推論能力 | 高（Sonnet の約5倍） | 複雑なアーキテクチャ決定、深い分析 |
| **OpusPlan** | ハイブリッド | 可変 | 計画にOpus、実行にSonnet |

#### モデル切り替えコマンド

```bash
/model haiku      # Haiku に切り替え
/model sonnet     # Sonnet に切り替え
/model opus       # Opus に切り替え
```

### 9.2 /compact の使い方

`/compact` は会話履歴を要約して圧縮し、各メッセージと共に送信されるトークン数を削減する。長いセッションでコストを40〜60%カットできる [^13]。

```bash
/compact                         # 標準圧縮
/compact Focus on the API changes  # 指示付き圧縮（何を残すか）
```

- 自動圧縮はコンテキスト制限に近づくと自動発火（約95%）
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` で閾値を調整可能（例: `50`）

### 9.3 トークン節約テクニック

1. **`/clear` を頻繁に使う**：無関係なタスク間でコンテキストをリセット
2. **サブエージェントで調査を分離**：大量のファイル読み込みをメインコンテキストに入れない
3. **プロンプトキャッシュ**：Claude Code は自動でプロンプトキャッシュを使用
4. **探索にはHaikuを使う**：`Explore` サブエージェントはデフォルトでHaikuを使用
5. **具体的なファイル指定**：`@src/auth/login.ts` のように直接参照し、不要な探索を減らす
6. **`/effort` で思考の深さを制御**：low/medium/high/max で調整

### 9.4 ステータスラインでのトークン使用量監視

カスタムステータスラインを設定してコンテキスト使用量を継続的に追跡できる。`/statusline` コマンドで設定。

---

## 10. IDE 連携

### 10.1 VS Code 連携

VS Code 拡張機能が最も成熟した IDE 統合を提供する [^14]。

#### インストール

1. `Cmd+Shift+X`（Mac）/ `Ctrl+Shift+X`（Windows/Linux）で拡張機能ビューを開く
2. "Claude Code" を検索してインストール

#### 主な機能

- ネイティブグラフィカルチャットパネル
- チェックポイントベースの Undo
- `@` メンションでファイル参照
- 並行会話
- 差分ビューでの変更提案
- 診断情報の共有

#### ターミナルでの使用

統合ターミナル（`Ctrl+`）から `claude` コマンドを直接実行することも可能。

### 10.2 JetBrains 連携

1. Settings > Plugins > Marketplace で "Claude Code" を検索してインストール
2. Claude Code CLI を IDE の統合ターミナル内で実行
3. 変更提案は IDE の差分ビューで表示

### 10.3 ターミナルでの使い方

```bash
# 基本的な起動
claude

# 特定のディレクトリで起動
claude --cwd /path/to/project

# 追加ディレクトリの参照
claude --add-dir /path/to/shared-libs

# プロンプトを直接渡して実行
claude -p "Explain this project"

# 前回の会話を再開
claude --continue
```

---

## 11. トラブルシューティング

### 11.1 よくある問題と解決策

#### インストール・セットアップ

| 問題 | 解決策 |
|------|--------|
| インストール失敗 | Node.js を 18.0 以上に更新。`npm cache clean --force` 後に再インストール |
| "Invalid API key" エラー | Anthropic コンソールでキーを確認。余分なスペースや文字がないか確認 |
| コマンドが見つからない | `npm install -g @anthropic-ai/claude-code` でグローバルインストール |

#### パフォーマンス問題

| 問題 | 解決策 |
|------|--------|
| 応答が遅い | `/clear` でコンテキストリセット。プロンプトを具体的にして不要なスキャンを減らす |
| コンテキスト超過 | `/compact` で圧縮。サブエージェントで調査を分離 |
| 同じミスを繰り返す | CLAUDE.md が長すぎないか確認。`/clear` して再スタート |

#### MCP 関連

| 問題 | 解決策 |
|------|--------|
| MCP 接続エラー | `claude --mcp-debug` でデバッグ。`/mcp` で状態確認 |
| OAuth 認証失敗 | `/mcp` から再認証。ブラウザが開かない場合はURLを手動コピー |
| MCP 起動タイムアウト | `MCP_TIMEOUT=10000 claude` でタイムアウトを延長 |

#### ファイル権限

| 問題 | 解決策 |
|------|--------|
| ファイルを変更できない | プロジェクトディレクトリの書き込み権限を確認 |
| 権限プロンプトが多すぎる | `/permissions` で安全なコマンドを許可リストに追加 |

### 11.2 デバッグ方法

```bash
# バージョン確認
claude --version

# デバッグモードで起動
claude --debug

# verbose モードの切り替え（セッション中）
Ctrl+O

# MCP デバッグ
claude --mcp-debug

# 接続テスト
ping claude.ai

# API キー確認
echo $ANTHROPIC_API_KEY
```

### 11.3 よくある失敗パターンと対策

| パターン | 問題 | 対策 |
|---------|------|------|
| **キッチンシンクセッション** | 1つのセッションで無関係なタスクを混ぜる | タスク間で `/clear` |
| **修正の連鎖** | 2回以上修正しても直らない | `/clear` して学んだことを含む新プロンプト |
| **肥大化した CLAUDE.md** | 重要なルールが埋もれる | 定期的に剪定。不要な行を削除 |
| **検証なしの信頼** | もっともらしいがエッジケースを扱わない実装 | テスト、スクリプト、スクショで検証 |
| **無限探索** | スコープなしの調査でコンテキスト消費 | 調査範囲を限定するかサブエージェントを使用 |

---

## 12. 高度な使い方

### 12.1 Agent Teams（並行エージェント）

Agent Teams は複数の Claude Code インスタンスをチームとして協調させる実験的機能である。1つのセッションがチームリードとなり、タスク割り当て、結果の統合を行う。各チームメイトは独立したコンテキストウィンドウで作業し、直接メッセージで通信できる [^17]。

#### 有効化

```json
// settings.json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

#### Agent Teams vs サブエージェント

| | サブエージェント | Agent Teams |
|--|----------------|-------------|
| コンテキスト | 独自。結果は呼び出し元に返る | 独自。完全に独立 |
| コミュニケーション | メインエージェントにのみ報告 | チームメイト間で直接メッセージ |
| 協調 | メインエージェントが全管理 | 共有タスクリストで自己協調 |
| 最適な用途 | 結果だけが重要な集中タスク | 議論や協力が必要な複雑作業 |
| トークンコスト | 低（結果を要約して返す） | 高（各チームメイトが独立インスタンス） |

#### チームの起動

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

#### 表示モード

| モード | 説明 | 設定 |
|-------|------|------|
| `in-process` | 全チームメイトがメインターミナル内で実行。`Shift+Down` で切り替え | デフォルト |
| `tmux` / `iterm2` | 各チームメイトが独自のペインを持つ。全員の出力を同時に確認可能 | `"teammateMode": "tmux"` |

#### 品質ゲートの強制

`TeammateIdle` フックでチームメイトの停止前にチェック、`TaskCompleted` フックでタスク完了前にテスト実行等を強制できる。

#### 推奨チームサイズ

- 3〜5人のチームメイトで開始
- チームメイト1人あたり5〜6タスクが目安
- 並行作業の価値が明確な場合にのみスケールアップ

#### 最適なユースケース

- **リサーチ・レビュー**: 複数の観点で同時調査
- **新機能・モジュール**: ファイル衝突なく分担
- **仮説検証デバッグ**: 競合する仮説を並行テスト
- **クロスレイヤー変更**: フロントエンド/バックエンド/テストを分担

### 12.2 Plan Mode

Plan Mode は Claude を読み取り専用モードに切り替え、コードベースの探索と計画立案を行う。コードの変更は行わない。

```
# Ctrl+G でプランモードに切り替え
# プランモード中はファイル読み取りと質問のみ

# 使用例
> Read the auth module and create a plan to add OAuth support
```

Plan Mode は以下の場合に特に有効：
- 不慣れなコードベースの理解
- 複数ファイルにまたがる変更の計画
- アプローチが不明確な場合

**スコープが明確で小さな変更（タイポ修正、ログ追加等）ではスキップしてよい。**

### 12.3 ヘッドレスモード（--print, -p）

非対話型で Claude Code を実行する。CI パイプライン、pre-commit フック、自動ワークフローに最適 [^15]。

```bash
# ワンショットクエリ
claude -p "Explain what this project does"

# JSON 出力
claude -p "List all API endpoints" --output-format json

# ストリーミング JSON
claude -p "Analyze this log file" --output-format stream-json

# 構造化出力（JSON Schema）
claude -p "Extract function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}}}'

# ツール制限付き
claude -p "Run tests and fix failures" \
  --allowedTools "Bash,Read,Edit"

# 会話の継続
claude -p "Review this codebase" --output-format json
claude -p "Now focus on database queries" --continue

# セッション ID 指定で再開
session_id=$(claude -p "Start a review" --output-format json | jq -r '.session_id')
claude -p "Continue that review" --resume "$session_id"

# システムプロンプトの追加
gh pr diff "$1" | claude -p \
  --append-system-prompt "You are a security engineer." \
  --output-format json
```

### 12.4 SDK を使ったカスタム統合

Claude Code は Python と TypeScript の SDK を提供しており、プログラマティックな制御が可能：

- 構造化出力
- ツール承認コールバック
- ネイティブメッセージオブジェクト
- ストリーミングレスポンス

詳細: [Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)

### 12.5 ファンアウトパターン（大規模バッチ処理）

```bash
# 1. タスクリストを生成
claude -p "List all Python files needing migration" > files.txt

# 2. 並行実行
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)" &
done
wait
```

### 12.6 チェックポイントとリワインド

Claude の全アクションはチェックポイントを作成する。`Esc + Esc` または `/rewind` でリワインドメニューを開き：

- 会話のみ復元
- コードのみ復元
- 両方復元
- 選択したメッセージから要約

チェックポイントはセッション間で永続化されるため、ターミナルを閉じても後でリワインドできる。

---

## 13. プラグイン

### 13.1 プラグインとは

プラグインはスキル、フック、サブエージェント、MCP サーバーを単一のインストール可能な単位にバンドルしたものである。2026年2月時点で9,000以上のプラグインが利用可能 [^18]。

### 13.2 プラグインのインストール

```bash
# マーケットプレイスの追加
/plugin marketplace add user-or-org/repo-name

# プラグインのブラウズとインストール
/plugin

# コマンドラインからインストール
claude plugin install <plugin-name>

# ローカル開発テスト
claude --plugin-dir ./your-plugin
```

### 13.3 プラグインの構造

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json      # マニフェスト（必須）
├── .mcp.json             # MCP サーバー設定（任意）
├── commands/             # スラッシュコマンド（任意）
├── agents/               # サブエージェント（任意）
├── skills/               # スキル（任意）
├── hooks/
│   └── hooks.json        # フック設定（任意）
└── README.md
```

`plugin.json` の例：

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "author": "username",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

### 13.4 推奨プラグインカテゴリ

- **コードインテリジェンス**: 型付き言語向けのシンボルナビゲーション、自動エラー検出
- **マルチエージェントワークフロー**: Claude Taskmaster、Claude-Flow、Squad
- **GUI & IDE クライアント**: Claudia、Web UI、Neovim Extension
- **プラグインテンプレート**: Awesome Claude Code、Subagents Collection

### 13.5 マーケットプレイスの作成

GitHub リポジトリに `marketplace.json` を追加するだけで独自のマーケットプレイスを作成できる：

```json
// marketplace.json
{
  "plugins": [
    {
      "name": "my-plugin",
      "path": "./plugins/my-plugin"
    }
  ]
}
```

---

## 14. サンドボックス

### 14.1 サンドボックスとは

サンドボックスは OS レベルのファイルシステム・ネットワーク隔離を提供する機能である。権限プロンプトの代わりに事前定義された境界内で自由に作業できる [^19]。

### 14.2 OS 別の実装

| OS | 実装技術 |
|-----|---------|
| macOS | Seatbelt（App Sandbox） - カーネルレベルの制限 |
| Linux / WSL2 | bubblewrap (bwrap) - Flatpak で使用される軽量サンドボックス |
| WSL1 | 非サポート（bubblewrap に必要なカーネル機能がない） |

### 14.3 有効化と設定

```bash
# Claude Code 内でサンドボックスを有効化
/sandbox
```

### 14.4 隔離境界

#### ファイルシステム

- **書き込み**: カレントワーキングディレクトリとそのサブディレクトリのみ
- **読み取り**: システム全体（明示的に拒否されたディレクトリを除く）

#### ネットワーク

- **デフォルト**: 全ネットワークアクセスが拒否
- **許可リスト**: 明示的に許可されたドメインのみアクセス可能
- 空の `allowedDomains` リスト = ネットワークアクセスなし

### 14.5 サンドボックスモード

- **Auto-allow モード**: サンドボックス内で Bash コマンドを自動実行。サンドボックスできないコマンド（許可されていないホストへのネットワークアクセス等）は通常の権限フローにフォールバック
- `--dangerously-skip-permissions` より安全に自律作業を実現

---

## 15. ステータスライン

### 15.1 ステータスラインとは

ステータスラインは Claude Code の画面下部に表示されるカスタマイズ可能なバーである。任意のシェルスクリプトを設定でき、JSON セッションデータを stdin で受け取って表示する [^20]。

### 15.2 設定方法

```bash
# Claude Code 内で対話的に設定
/statusline
```

`/statusline` を実行すると Claude がスクリプトを生成してくれる。

### 15.3 表示可能な情報

- コンテキストウィンドウの使用率
- トークン消費量・コスト
- Git ステータス（ブランチ、変更ファイル数）
- 現在のモデル
- セッション時間
- カスタムメトリクス

### 15.4 手動設定例

`~/.claude/settings.json` にスクリプトパスを追加：

```json
{
  "statusline": {
    "command": "~/.claude/scripts/statusline.sh"
  }
}
```

ステータスラインスクリプトの例：

```bash
#!/bin/bash
# stdin から JSON セッションデータを読み取る
INPUT=$(cat)
CONTEXT_PCT=$(echo "$INPUT" | jq -r '.context_window_percent // "?"')
MODEL=$(echo "$INPUT" | jq -r '.model // "unknown"')
echo "Context: ${CONTEXT_PCT}% | Model: ${MODEL}"
```

### 15.5 コミュニティツール

- **ccstatusline**: React + Ink ベースの高度にカスタマイズ可能なステータスライン
- **starship-claude**: Starship スタイルのプリセット

### 15.6 パフォーマンスの注意

- ステータスラインスクリプトはアクティブセッション中に頻繁に実行される
- 出力は短く保つ（バー幅は限られている）
- 遅い操作（`git status` 等）はキャッシュする

---

## 16. 実際のユースケース・事例

### 16.1 OSS 開発での活用

- **Anthropic 社内**: 約12名のエンジニアチームで1日60〜100の内部リリース、エンジニア1人あたり1日約5つの PR [^16]
- **claude-code-infrastructure-showcase**: 6ヶ月以上の実環境テストを経たインフラ。40%以上の効率改善を報告
- **Hugging Face**: Claude Code Skills を使って1日1,000以上のML実験を実行 [^6]

### 16.2 大規模プロジェクトでの実践

#### 大規模リファクタリング

```
1. Plan Mode でコードベースを分析
   > Analyze the entire /src directory and identify all deprecated API usages

2. サブエージェントで並行調査
   > Use subagents to investigate each module independently

3. ファンアウトで並行修正
   for file in $(cat deprecated-files.txt); do
     claude -p "Update $file to use the new API" --allowedTools "Edit"
   done

4. テスト実行で検証
   > Run the full test suite and fix any regressions
```

#### 新規機能開発（Claude にインタビューさせるパターン）

```
1. 要件インタビュー → SPEC.md 生成
2. /clear で新セッション
3. Plan Mode で設計
4. 実装 → テスト → レビュー → コミット
```

### 16.3 一人開発での活用

#### 効果的なワークフロー

1. **コードベースの理解**: `claude` を起動して質問。「このプロジェクトのアーキテクチャを説明して」
2. **機能実装**: 具体的なプロンプトで実装依頼。テストケースを必ず含める
3. **コードレビュー**: セキュリティレビューアーエージェントでセルフレビュー
4. **ドキュメント生成**: コードベースを分析してREADME等を自動生成
5. **バグ修正**: エラーメッセージとスタックトレースを貼り付けて修正依頼

#### データサイエンスでの活用

```
# Jupyter Notebook の変換
> Transform this exploratory notebook into a production pipeline

# データ分析
> Analyze the data in data/sales.csv and create visualizations
```

### 16.4 チーム開発のベストプラクティス

1. **CLAUDE.md をバージョン管理**：チーム全員が同じ規約を共有
2. **プロジェクトスキルを標準化**：`.claude/skills/` にチーム共通のワークフロー
3. **カスタムエージェントの共有**：`.claude/agents/` でコードレビューアー等を標準化
4. **MCP サーバーの共有**：`.mcp.json` でプロジェクトスコープのMCP設定
5. **CI/CD 統合**：PR レビュー、セキュリティ監査をヘッドレスモードで自動化

---

## 17. 情報源・参考リンク

### Anthropic 公式ドキュメント

- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Create Custom Subagents](https://code.claude.com/docs/en/sub-agents)
- [Extend Claude with Skills](https://code.claude.com/docs/en/skills)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
- [Configure Permissions](https://code.claude.com/docs/en/permissions)
- [Run Claude Code Programmatically (Headless)](https://code.claude.com/docs/en/headless)
- [Common Workflows](https://code.claude.com/docs/en/common-workflows)
- [Model Configuration](https://code.claude.com/docs/en/model-config)
- [Use Claude Code in VS Code](https://code.claude.com/docs/en/vs-code)
- [Troubleshooting](https://code.claude.com/docs/en/troubleshooting)
- [Claude Code のベストプラクティス（日本語）](https://code.claude.com/docs/ja/best-practices)

### Anthropic 公式ドキュメント（追加）

- [Orchestrate Teams of Claude Code Sessions](https://code.claude.com/docs/en/agent-teams)
- [Create and Distribute a Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Sandboxing](https://code.claude.com/docs/en/sandboxing)
- [Customize Your Status Line](https://code.claude.com/docs/en/statusline)
- [Automate Workflows with Hooks (Guide)](https://code.claude.com/docs/en/hooks-guide)
- [Interactive Mode](https://code.claude.com/docs/en/interactive-mode)
- [Checkpointing](https://code.claude.com/docs/en/checkpointing)
- [Features Overview (Extend Claude Code)](https://code.claude.com/docs/en/features-overview)

### コミュニティリソース

- [Writing a Good CLAUDE.md - HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [How to Write a Good CLAUDE.md File - Builder.io](https://www.builder.io/blog/claude-md-guide)
- [Claude Code's Custom Agent Framework - DEV Community](https://dev.to/therealmrmumba/claude-codes-custom-agent-framework-changes-everything-4o4m)
- [How I Split Claude Code Into 12 Specialized Sub-Agents - DEV Community](https://dev.to/matkarimov099/how-i-split-claude-code-into-12-specialized-sub-agents-for-my-react-project-3jh8)
- [Claude Code Hooks: Complete Guide with 20+ Examples - DEV Community](https://dev.to/lukaszfryc/claude-code-hooks-complete-guide-with-20-ready-to-use-examples-2026-dcg)
- [Mastering Git Worktrees with Claude Code - Medium](https://medium.com/@dtunai/mastering-git-worktrees-with-claude-code-for-parallel-development-workflow-41dc91e645fe)
- [Shipping Faster with Claude Code and Git Worktrees - incident.io](https://incident.io/blog/shipping-faster-with-claude-code-and-git-worktrees)
- [How I Use Every Claude Code Feature - Shrivu Shankar](https://blog.sshh.io/p/how-i-use-every-claude-code-feature)
- [awesome-claude-code - GitHub](https://github.com/hesreallyhim/awesome-claude-code)
- [shanraisshan/claude-code-best-practice - GitHub](https://github.com/shanraisshan/claude-code-best-practice)
- [Best MCP Servers for Claude Code - MCPcat](https://mcpcat.io/guides/best-mcp-servers-for-claude-code/)

### コミュニティリソース（追加）

- [Claude Code Agent Teams: The Complete Guide 2026 - claudefast](https://claudefa.st/blog/guide/agents/agent-teams)
- [From Tasks to Swarms: Agent Teams in Claude Code - alexop.dev](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
- [Claude Code Plugins Guide - Composio](https://composio.dev/blog/claude-code-plugin)
- [How to Build Claude Code Plugins - DataCamp](https://www.datacamp.com/tutorial/how-to-build-claude-code-plugins)
- [Claude Code Sandboxing: OS-level Isolation - Anthropic Engineering](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Docker Sandboxes: Run Claude Code Safely - Docker](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/)
- [The Ultimate Claude Code Guide - DEV Community](https://dev.to/holasoymalva/the-ultimate-claude-code-guide-every-hidden-trick-hack-and-power-feature-you-need-to-know-2l45)
- [Parallel AI Coding with Git Worktrees - Agent Interviews](https://docs.agentinterviews.com/blog/parallel-ai-coding-with-gitworktrees/)
- [Claude Code Troubleshooting Guide - ClaudeLog](https://claudelog.com/troubleshooting/)
- [Creating The Perfect Claude Code Status Line - aihero.dev](https://www.aihero.dev/creating-the-perfect-claude-code-status-line)

### 日本語リソース

- [Claude Code を使いこなすためのベストプラクティス - ENECHANGE Developer Blog](https://tech.enechange.co.jp/entry/2026/02/16/195000)
- [Claude Code ベストプラクティスが公式ドキュメント化されたので日本語訳した](https://www.pnkts.net/2026/01/22/claude-code-best-practices-ja)
- [Claude Codeベストプラクティス2026 - Qiita](https://qiita.com/dai_chi/items/63b15050cc1280c45f86)
- [Claude Code公式ベストプラクティス完全解説 - note](https://note.com/samurai_worker/n/ncf736866aab6)
- [Claude Codeの使い方完全ガイド - カゴヤ](https://www.kagoya.jp/howto/engineer/hpc/use-claudecode/)

### 学習リソース

- [Claude Code Best Practices: The 2026 Guide - Morph](https://www.morphllm.com/claude-code-best-practices)
- [Claude Code Guide: Professional Setup - wmedia.es](https://wmedia.es/en/writing/claude-code-professional-guide-frontend-ai)
- [Claude Skills and CLAUDE.md: A Practical Guide - gend.co](https://www.gend.co/blog/claude-skills-claude-md-guide)
- [Claude Code Hooks: A Practical Guide - DataCamp](https://www.datacamp.com/tutorial/claude-code-hooks)
- [How Claude Code is built - Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/how-claude-code-is-built)
- [How to Reduce Claude Code Costs - thecaio.ai](https://www.thecaio.ai/blog/reduce-claude-code-costs)

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
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
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
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
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
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
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
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: ビルドログ取得
        id: get-logs
        run: |
          # 失敗したジョブのログを取得
          gh run view ${{ github.event.workflow_run.id }} --log-failed > build-errors.txt 2>&1 || true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
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
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
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
    ANTHROPIC_VERTEX_PROJECT_ID: ${{ steps.auth.outputs.project_id }}
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
