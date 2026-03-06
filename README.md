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
- [25. 初心者チュートリアル - インストールから初回利用まで](#25-初心者チュートリアル---インストールから初回利用まで)
- [26. プロンプトエンジニアリング - 効果的な指示の出し方](#26-プロンプトエンジニアリング---効果的な指示の出し方)
- [27. 料金・プラン完全ガイド](#27-料金プラン完全ガイド)
- [28. Git 連携詳細 - ブランチ・マージ・PR レビュー](#28-git-連携詳細---ブランチマージpr-レビュー)
- [29. TDD 連携 - テスト駆動開発ワークフロー](#29-tdd-連携---テスト駆動開発ワークフロー)
- [30. デバッグ機能 - エラー解析・ログ分析](#30-デバッグ機能---エラー解析ログ分析)
- [31. ツール比較 2026年版 - Cursor / Copilot / Aider / Windsurf / Cline](#31-ツール比較-2026年版---cursor--copilot--aider--windsurf--cline)
- [32. 大規模プロジェクト - モノレポ・複数言語・コンテキスト制限対策](#32-大規模プロジェクト---モノレポ複数言語コンテキスト制限対策)

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

<details markdown="1">
<summary>実践的な CLAUDE.md の例（Markdown）</summary>

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

</details>

#### @import による外部ファイルの読み込み

<details markdown="1">
<summary>@import による外部ファイルの読み込み（Markdown）</summary>

```markdown
See @README.md for project overview and @package.json for available npm commands.

# Additional Instructions
- Git workflow: @docs/git-instructions.md
- Personal overrides: @~/.claude/my-project-instructions.md
```

</details>

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

Claude Code にはあらかじめ用途別のビルトインサブエージェントが用意されており、特定タスクを効率的に処理できます。

| エージェント | モデル | ツール | 用途 |
|------------|-------|--------|------|
| **Explore** | Haiku（高速） | 読み取り専用 | ファイル検索、コード分析、コードベース探索 |
| **Plan** | 継承 | 読み取り専用 | プランモード時のコードベースリサーチ |
| **General-purpose** | 継承 | 全ツール | 複雑な調査、マルチステップ操作、コード変更 |
| **Bash** | 継承 | - | 別コンテキストでのターミナルコマンド実行 |

### 3.3 YAML Frontmatter の全オプション

サブエージェントは Markdown ファイルに YAML frontmatter を付けて定義する。

<details markdown="1">
<summary>サブエージェントは Markdown ファイルに YAML frontmatter を付けて定義する。（YAML）</summary>

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

</details>

### 3.4 エージェントの配置場所と優先度

エージェントは複数の場所に配置でき、スコープと優先度が異なります。同名のエージェントがある場合は優先度の高いものが使用されます。

| 配置場所 | スコープ | 優先度 |
|---------|---------|--------|
| `--agents` CLI フラグ | 現在のセッション | 1（最高） |
| `.claude/agents/` | プロジェクト | 2 |
| `~/.claude/agents/` | 全プロジェクト | 3 |
| プラグインの `agents/` | プラグイン有効時 | 4（最低） |

### 3.5 実践的なエージェント例

#### セキュリティレビューアー

<details markdown="1">
<summary>セキュリティレビューアー（Markdown）</summary>

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

</details>

#### デバッガー

<details markdown="1">
<summary>デバッガー（Markdown）</summary>

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

</details>

#### CLI からの一時的なエージェント定義

<details markdown="1">
<summary>CLI からの一時的なエージェント定義（Bash）</summary>

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

</details>

### 3.6 エージェントの管理

エージェントは以下の方法で管理できます。

- `/agents` コマンドでインタラクティブに管理（表示、作成、編集、削除）
- `claude agents` でコマンドラインから一覧表示
- セッション開始時にロードされるため、手動追加後はセッション再起動が必要

---

## 4. スキル (.claude/skills/)

### 4.1 スキルとは

スキルは Claude の能力を拡張するツールである。`SKILL.md` ファイルに指示を書くだけで Claude のツールキットに追加される。関連するタスクのとき Claude が自動的に使用するか、`/skill-name` で直接呼び出せる [^6]。

> **注意**: 以前の `.claude/commands/` は skills に統合された。既存のコマンドファイルはそのまま動作するが、スキルにはディレクトリサポート、frontmatter、自動ロード等の追加機能がある。

### 4.2 スキルの配置場所

スキルはスコープに応じて異なるディレクトリに配置します。プロジェクト固有のスキルはリポジトリにコミットしてチームで共有できます。

| レベル | パス | スコープ |
|-------|------|---------|
| エンタープライズ | マネージド設定 | 組織全体 |
| 個人 | `~/.claude/skills/<name>/SKILL.md` | 全プロジェクト |
| プロジェクト | `.claude/skills/<name>/SKILL.md` | このプロジェクトのみ |
| プラグイン | `<plugin>/skills/<name>/SKILL.md` | プラグイン有効時 |

### 4.3 SKILL.md の書き方

<details markdown="1">
<summary>4.3 SKILL.md の書き方（YAML）</summary>

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

</details>

### 4.4 文字列置換

スキル内では以下の変数を使って動的な値を埋め込めます。

| 変数 | 説明 |
|------|------|
| `$ARGUMENTS` | スキル呼び出し時に渡された全引数 |
| `$ARGUMENTS[N]` / `$N` | N番目の引数（0始まり） |
| `${CLAUDE_SESSION_ID}` | 現在のセッションID |

### 4.5 動的コンテキスト注入

`` !`command` `` 構文でシェルコマンドを事前実行し、結果をスキルに埋め込める：

<details markdown="1">
<summary>`` !`command` `` 構文でシェルコマンドを事前実行し、結果をスキルに埋め込める（YAML）</summary>

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

</details>

### 4.6 呼び出し制御

frontmatter の設定によって、ユーザーと Claude のどちらからスキルを呼び出せるかを制御できます。

| frontmatter | ユーザー | Claude | コンテキスト |
|-------------|---------|--------|-------------|
| （デフォルト） | 呼び出し可 | 呼び出し可 | 説明文は常にコンテキスト内、本文は呼び出し時にロード |
| `disable-model-invocation: true` | 呼び出し可 | 呼び出し不可 | 説明文もコンテキスト外 |
| `user-invocable: false` | 呼び出し不可 | 呼び出し可 | 説明文は常にコンテキスト内 |

### 4.7 実用的なスキル例

#### API 規約スキル（参照型）

<details markdown="1">
<summary>API 規約スキル（参照型）（YAML）</summary>

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

</details>

#### デプロイスキル（タスク型）

<details markdown="1">
<summary>デプロイスキル（タスク型）（YAML）</summary>

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

</details>

#### コードベース可視化スキル

スキルディレクトリにスクリプトをバンドルし、インタラクティブなHTMLビジュアライゼーションを生成する高度なパターンも可能 [^6]。

---

## 5. フック (.claude/hooks/)

### 5.1 フックとは

フックは Claude Code のライフサイクルの特定ポイントで自動的にシェルコマンドや LLM プロンプトを実行するユーザー定義のトリガーである。CLAUDE.md の指示が「推奨」なのに対し、フックは **決定論的で確実に実行される** [^7][^8]。

### 5.2 フックイベント一覧

フックは以下のライフサイクルイベントで発火します。「ブロック可能」な場合は、フックの応答によってその操作を中止できます。

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
| `InstructionsLoaded` | CLAUDE.md または `.claude/rules/*.md` がコンテキストにロードされた時 | No |
| `SessionEnd` | セッション終了時 | No |

### 5.3 設定場所

フック設定は複数の場所に記述でき、それぞれスコープと共有可能かどうかが異なります。

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

<details markdown="1">
<summary>フック設定は3階層のネスト構造（JSON）</summary>

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

</details>

### 5.5 フックハンドラーの種類

フックハンドラーは3種類あり、それぞれ用途とタイムアウトが異なります。

| タイプ | 説明 | デフォルトタイムアウト |
|-------|------|---------------------|
| `command` | シェルコマンドを実行 | 600秒 |
| `prompt` | LLM に単発評価を依頼 | 30秒 |
| `agent` | ツール付きサブエージェントを起動 | 60秒 |

### 5.6 終了コードの意味

コマンドフックの終了コードによって、Claude Code の挙動が変わります。

| 終了コード | 意味 |
|-----------|------|
| **0** | 成功。stdout の JSON を解析 |
| **2** | ブロッキングエラー。stderr がエラーメッセージとしてフィードバック |
| **その他** | 非ブロッキングエラー。verbose モードで表示 |

### 5.7 実用的なフック例

#### ファイル編集後に自動フォーマット

<details markdown="1">
<summary>ファイル編集後に自動フォーマット（JSON）</summary>

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

</details>

#### 危険なコマンドのブロック

<details markdown="1">
<summary>危険なコマンドのブロック（Bash）</summary>

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

</details>

<details markdown="1">
<summary>```（JSON）</summary>

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

</details>

#### ESLint の自動実行

<details markdown="1">
<summary>ESLint の自動実行（JSON）</summary>

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

</details>

#### 停止前の品質チェック（プロンプトフック）

<details markdown="1">
<summary>停止前の品質チェック（プロンプトフック）（JSON）</summary>

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

</details>

#### 非同期テスト実行

<details markdown="1">
<summary>非同期テスト実行（JSON）</summary>

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

</details>

### 5.8 フック管理

フックの設定と管理には以下の方法が使えます。

- `/hooks` でインタラクティブに管理
- 設定の直接編集は次回セッション開始時に反映
- `"disableAllHooks": true` で一時的に全フックを無効化

---

## 6. MCP サーバー連携

### 6.1 MCP とは

MCP（Model Context Protocol）は AI ツール統合のためのオープンソース標準である。MCP サーバーを接続することで、Claude Code から外部ツール、データベース、API にアクセスできる [^9]。

### 6.2 MCP サーバーの追加方法

#### HTTP サーバー（推奨）

<details markdown="1">
<summary>HTTP サーバー（推奨）（Bash）</summary>

```bash
# 基本構文
claude mcp add --transport http <name> <url>

# 例: Notion に接続
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Bearer トークン付き
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

</details>

#### SSE サーバー（非推奨、HTTP を推奨）

```bash
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

#### ローカル stdio サーバー

```bash
claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable \
  -- npx -y airtable-mcp-server
```

### 6.3 MCP サーバーの探し方

2025年9月に **MCP Registry**（公式カタログ）が正式ローンチされた。MCP の発見・管理の標準的な入口となっており、Claude Code の `/mcp` コマンドからも参照できる。また MCP は Linux Foundation の **Agentic AI Foundation** に移管され、オープンガバナンス体制に移行している。

- 公式レジストリ: `https://registry.modelcontextprotocol.io`
- 仕様バージョン: 2025-11-05（非同期・ステートレス・サーバーID対応）

### 6.4 人気の MCP サーバー

よく使われる MCP サーバーとその用途をまとめます。公式・コミュニティ製合わせて数千のサーバーが公開されています。

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

MCP サーバーの設定はスコープによって保存場所が異なります。チームで共有する場合は `project` スコープを使います。

| スコープ | 保存場所 | 共有 |
|---------|---------|------|
| `local`（デフォルト） | `~/.claude.json` | 個人・プロジェクト固有 |
| `project` | `.mcp.json`（プロジェクトルート） | git でチーム共有 |
| `user` | `~/.claude.json` | 個人・全プロジェクト |

<details markdown="1">
<summary>| `user` | `~/.claude.json` | 個人・全プロジェクト |（Bash）</summary>

```bash
# プロジェクトスコープで追加
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp

# ユーザースコープで追加
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

</details>

### 6.5 MCP 管理コマンド

<details markdown="1">
<summary>6.5 MCP 管理コマンド（Bash）</summary>

```bash
claude mcp list              # 一覧表示
claude mcp get github        # 詳細確認
claude mcp remove github     # 削除
/mcp                         # Claude Code 内でステータス確認・OAuth認証
```

</details>

### 6.6 `.mcp.json` での環境変数展開

<details markdown="1">
<summary>6.6 `.mcp.json` での環境変数展開（JSON）</summary>

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

</details>

### 6.7 Claude Code 自体を MCP サーバーとして使う

```bash
claude mcp serve
```

Claude Desktop から接続する設定：

<details markdown="1">
<summary>Claude Desktop から接続する設定（JSON）</summary>

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

</details>

---

## 7. 権限・セキュリティ設定

### 7.1 権限モード

Claude Code は用途に応じた権限モードを提供しており、自動化の程度とセキュリティのバランスを調整できます。

| モード | 動作 |
|-------|------|
| `default` | 標準的な権限チェック（プロンプト表示） |
| `acceptEdits` | ファイル編集を自動承認 |
| `plan` | 読み取り専用（プランモード） |
| `dontAsk` | 権限プロンプトを自動拒否（明示許可ツールは動作） |
| `bypassPermissions` | 全権限チェックをスキップ |

### 7.2 allowedTools の設定

`/permissions` コマンドで許可するツールをホワイトリスト設定できる：

<details markdown="1">
<summary>`/permissions` コマンドで許可するツールをホワイトリスト設定できる（JSON）</summary>

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

</details>

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

<details markdown="1">
<summary>安全な代替アプローチ**（Bash）</summary>

```bash
# allowedTools でツールを制限して使う
claude -p "Fix lint errors" \
  --allowedTools "Read,Edit,Bash(npm run lint *)"
```

</details>

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

<details markdown="1">
<summary>具体的なコンテキストを与える（テキスト）</summary>

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

</details>

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
| `"ultrathink"` | 約32K | 複雑なアーキテクチャ決定、深い分析（high effort モードを明示的に有効化） |

> **注意**: バージョン 2.1.68（2026-03-04）で `ultrathink` が再導入された。現在は `medium effort` がデフォルトであり、`ultrathink` はプロンプトに含めることで high effort モードを明示的に起動するキーワードとして機能する。`/effort` コマンドでも低/中/高/最大を制御できる [^11]。

### 8.2 探索 → 計画 → 実装 → コミットの4フェーズ

<details markdown="1">
<summary>8.2 探索 → 計画 → 実装 → コミットの4フェーズ（テキスト）</summary>

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

</details>

### 8.3 Claude にインタビューさせる

大きな機能の場合、最初にClaudeにインタビューさせると効果的：

<details markdown="1">
<summary>大きな機能の場合、最初にClaudeにインタビューさせると効果的（テキスト）</summary>

```
I want to build [brief description]. Interview me in detail using the
AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and
tradeoffs. Don't ask obvious questions, dig into the hard parts.

Keep interviewing until we've covered everything, then write a complete
spec to SPEC.md.
```

</details>

仕様完成後、新しいセッションで実装すると、クリーンなコンテキストで作業できる。

### 8.4 セッション管理

#### 早めの軌道修正

- **`Esc`**: Claude を途中で停止（コンテキストは保持）
- **`Esc + Esc`** / **`/rewind`**: リワインドメニューで前の状態に復元
- **`"Undo that"`**: Claude に変更を取り消させる
- **`/clear`**: 無関係なタスク間でコンテキストをリセット

**2回同じ問題を修正しても直らなければ `/clear` して、学んだことを含むより良いプロンプトで再スタート** [^1]。

#### コンテキストの積極的な管理

<details markdown="1">
<summary>コンテキストの積極的な管理（Bash）</summary>

```bash
/clear                        # タスク間でコンテキスト全リセット
/compact                      # 会話を要約して圧縮
/compact Focus on API changes # 指示付き圧縮
```

</details>

- `/rewind` → メッセージチェックポイントを選択 → 「Summarize from here」で部分圧縮
- CLAUDE.md に圧縮指示を追加：`"When compacting, always preserve the full list of modified files and any test commands"`

#### セッションの再開

<details markdown="1">
<summary>セッションの再開（Bash）</summary>

```bash
claude --continue    # 最新の会話を再開
claude --resume      # 最近のセッションから選択
/rename              # セッションに名前を付ける（例: "oauth-migration"）
```

</details>

### 8.5 サブエージェントの活用

コンテキストが最も重要なリソースであるため、サブエージェントの活用が強力：

<details markdown="1">
<summary>コンテキストが最も重要なリソースであるため、サブエージェントの活用が強力（テキスト）</summary>

```
# 調査の委譲（メインコンテキストを汚さない）
Use subagents to investigate how our auth system handles token refresh

# 並行リサーチ
Research the authentication, database, and API modules in parallel
using separate subagents

# 検証
Use a subagent to review this code for edge cases
```

</details>

### 8.6 Git ワークフロー（ワークツリー・並行作業）

Git Worktree を使うと、同じリポジトリの複数ブランチを同時にチェックアウトし、各ブランチで独立した Claude セッションを実行できる [^12]。

#### ワークツリーの作成と使用

<details markdown="1">
<summary>ワークツリーの作成と使用（Bash）</summary>

```bash
# --worktree フラグでワークツリーを作成して Claude を起動
claude --worktree feature-auth

# サブエージェントでワークツリー隔離
# エージェントの frontmatter に isolation: worktree を追加
```

</details>

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

<details markdown="1">
<summary>8.7 CI/CD 統合（GitHub Actions）（YAML）</summary>

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

</details>

### 8.8 テスト駆動開発との組み合わせ

<details markdown="1">
<summary>8.8 テスト駆動開発との組み合わせ（テキスト）</summary>

```
1. "Write failing tests for the new user registration feature"
2. "Now implement the code to make all tests pass"
3. "Refactor the implementation while keeping tests green"
```

</details>

別セッションでテストを書き、別セッションで実装するパターンも効果的。

### 8.9 チーム開発での活用

チーム全体で Claude Code を活用するには、設定ファイルや共通ワークフローをリポジトリで共有することが重要です。

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

<details markdown="1">
<summary>モデル切り替えコマンド（Bash）</summary>

```bash
/model haiku      # Haiku に切り替え
/model sonnet     # Sonnet に切り替え
/model opus       # Opus に切り替え
```

</details>

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

<details markdown="1">
<summary>10.3 ターミナルでの使い方（Bash）</summary>

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

</details>

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

<details markdown="1">
<summary>11.2 デバッグ方法（Bash）</summary>

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

</details>

### 11.3 よくある失敗パターンと対策

Claude Code を使ううえでよく陥るアンチパターンとその対策をまとめます。

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

Agent Teams は複数の Claude Code インスタンスをチームとして協調させる機能である。2026年時点では正式機能として利用可能（実験的フラグ不要）。1つのセッションがチームリードとなり、タスク割り当て、結果の統合を行う。各チームメイトは独立したコンテキストウィンドウで作業し、直接メッセージで通信できる。また、会話をまたいだ自動記録・想起のメモリ機能が追加されている [^17]。

#### 有効化

<details markdown="1">
<summary>有効化（JSON）</summary>

```json
// settings.json（古いバージョンでは環境変数が必要な場合がある）
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

</details>

#### Agent Teams vs サブエージェント

| | サブエージェント | Agent Teams |
|--|----------------|-------------|
| コンテキスト | 独自。結果は呼び出し元に返る | 独自。完全に独立 |
| コミュニケーション | メインエージェントにのみ報告 | チームメイト間で直接メッセージ |
| 協調 | メインエージェントが全管理 | 共有タスクリストで自己協調 |
| 最適な用途 | 結果だけが重要な集中タスク | 議論や協力が必要な複雑作業 |
| トークンコスト | 低（結果を要約して返す） | 高（各チームメイトが独立インスタンス） |

#### チームの起動

<details markdown="1">
<summary>チームの起動（テキスト）</summary>

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

</details>

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

<details markdown="1">
<summary>コード例（テキスト）</summary>

```
# Shift+Tab でプランモードに切り替え（Normal → Plan → Auto-Accept のサイクル）
# または /plan コマンドでプランモードに入る
# プランモード中はファイル読み取りと質問のみ

# 使用例
> Read the auth module and create a plan to add OAuth support
```

</details>

Plan Mode は以下の場合に特に有効：
- 不慣れなコードベースの理解
- 複数ファイルにまたがる変更の計画
- アプローチが不明確な場合

**スコープが明確で小さな変更（タイポ修正、ログ追加等）ではスキップしてよい。**

### 12.3 ヘッドレスモード（--print, -p）

非対話型で Claude Code を実行する。CI パイプライン、pre-commit フック、自動ワークフローに最適 [^15]。

<details markdown="1">
<summary>コード例（Bash）</summary>

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

</details>

### 12.4 SDK を使ったカスタム統合

Claude Code は Python と TypeScript の SDK を提供しており、プログラマティックな制御が可能：

- 構造化出力
- ツール承認コールバック
- ネイティブメッセージオブジェクト
- ストリーミングレスポンス

詳細: [Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)

### 12.5 ファンアウトパターン（大規模バッチ処理）

<details markdown="1">
<summary>12.5 ファンアウトパターン（大規模バッチ処理）（Bash）</summary>

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

</details>

### 12.6 チェックポイントとリワインド

Checkpoints は Claude Code 2.0 で正式リリースされた機能で、ユーザープロンプトごとに自動でファイルシステムの状態と会話を保存する。保存期間は **30日間**。git とは独立した補完機能として機能する。

#### 基本操作

`Esc + Esc` または `/rewind` でリワインドメニューを開き、以下を選択できる：

- **会話のみ復元** — コードは変更せず会話履歴だけを戻す
- **コードのみ復元** — 会話はそのままでファイルの変更だけを元に戻す
- **両方復元** — 会話とコードの両方を指定した時点に戻す
- **選択したメッセージから要約** — 部分圧縮でコンテキストを整理する

#### git との使い分け方針

| 場面 | 推奨 |
|------|------|
| 試行錯誤中の軽いロールバック | Checkpoints（`/rewind`） |
| リリース・レビュー単位での管理 | git commit |
| 30日以上保持したい変更履歴 | git |

チェックポイントはセッション間で永続化されるため、ターミナルを閉じても後でリワインドできる。

---

## 13. プラグイン

### 13.1 プラグインとは

プラグインはスキル、フック、サブエージェント、MCP サーバーを単一のインストール可能な単位にバンドルしたものである。2026年2月時点で9,000以上のプラグインが利用可能 [^18]。

### 13.2 プラグインのインストール

<details markdown="1">
<summary>13.2 プラグインのインストール（Bash）</summary>

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

</details>

### 13.3 プラグインの構造

<details markdown="1">
<summary>13.3 プラグインの構造（テキスト）</summary>

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

</details>

`plugin.json` の例：

<details markdown="1">
<summary>`plugin.json` の例（JSON）</summary>

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

</details>

### 13.4 推奨プラグインカテゴリ

マーケットプレイスで特に人気のあるプラグインカテゴリを紹介します。

- **コードインテリジェンス**: 型付き言語向けのシンボルナビゲーション、自動エラー検出
- **マルチエージェントワークフロー**: Claude Taskmaster、Claude-Flow、Squad
- **GUI & IDE クライアント**: Claudia、Web UI、Neovim Extension
- **プラグインテンプレート**: Awesome Claude Code、Subagents Collection

### 13.5 マーケットプレイスの作成

GitHub リポジトリに `marketplace.json` を追加するだけで独自のマーケットプレイスを作成できる：

<details markdown="1">
<summary>GitHub リポジトリに `marketplace.json` を追加するだけで独自のマーケットプレイスを作成できる（JSON）</summary>

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

</details>

---

## 14. サンドボックス

### 14.1 サンドボックスとは

サンドボックスは OS レベルのファイルシステム・ネットワーク隔離を提供する機能である。権限プロンプトの代わりに事前定義された境界内で自由に作業できる [^19]。

### 14.2 OS 別の実装

サンドボックスの実装技術は OS によって異なります。

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

サンドボックス有効時の主な動作モードについて説明します。

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

ステータスラインには以下の情報を表示できます。シェルスクリプトで自由にカスタマイズできます。

- コンテキストウィンドウの使用率
- トークン消費量・コスト
- Git ステータス（ブランチ、変更ファイル数）
- 現在のモデル
- セッション時間
- カスタムメトリクス

### 15.4 手動設定例

`~/.claude/settings.json` にスクリプトパスを追加：

<details markdown="1">
<summary>`~/.claude/settings.json` にスクリプトパスを追加（JSON）</summary>

```json
{
  "statusline": {
    "command": "~/.claude/scripts/statusline.sh"
  }
}
```

</details>

ステータスラインスクリプトの例：

<details markdown="1">
<summary>ステータスラインスクリプトの例（Bash）</summary>

```bash
#!/bin/bash
# stdin から JSON セッションデータを読み取る
INPUT=$(cat)
CONTEXT_PCT=$(echo "$INPUT" | jq -r '.context_window_percent // "?"')
MODEL=$(echo "$INPUT" | jq -r '.model // "unknown"')
echo "Context: ${CONTEXT_PCT}% | Model: ${MODEL}"
```

</details>

### 15.5 コミュニティツール

コミュニティが作成したステータスライン用ツールです。

- **ccstatusline**: React + Ink ベースの高度にカスタマイズ可能なステータスライン
- **starship-claude**: Starship スタイルのプリセット

### 15.6 パフォーマンスの注意

ステータスラインは高頻度で実行されるため、パフォーマンスに注意が必要です。

- ステータスラインスクリプトはアクティブセッション中に頻繁に実行される
- 出力は短く保つ（バー幅は限られている）
- 遅い操作（`git status` 等）はキャッシュする

---

## 16. 実際のユースケース・事例

### 16.1 OSS 開発での活用

実際に Claude Code を活用している事例を紹介します。

- **Anthropic 社内**: 約12名のエンジニアチームで1日60〜100の内部リリース、エンジニア1人あたり1日約5つの PR [^16]
- **claude-code-infrastructure-showcase**: 6ヶ月以上の実環境テストを経たインフラ。40%以上の効率改善を報告
- **Hugging Face**: Claude Code Skills を使って1日1,000以上のML実験を実行 [^6]

### 16.2 大規模プロジェクトでの実践

#### 大規模リファクタリング

<details markdown="1">
<summary>大規模リファクタリング（テキスト）</summary>

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

</details>

#### 新規機能開発（Claude にインタビューさせるパターン）

<details markdown="1">
<summary>新規機能開発（Claude にインタビューさせるパターン）（テキスト）</summary>

```
1. 要件インタビュー → SPEC.md 生成
2. /clear で新セッション
3. Plan Mode で設計
4. 実装 → テスト → レビュー → コミット
```

</details>

### 16.3 一人開発での活用

#### 効果的なワークフロー

1. **コードベースの理解**: `claude` を起動して質問。「このプロジェクトのアーキテクチャを説明して」
2. **機能実装**: 具体的なプロンプトで実装依頼。テストケースを必ず含める
3. **コードレビュー**: セキュリティレビューアーエージェントでセルフレビュー
4. **ドキュメント生成**: コードベースを分析してREADME等を自動生成
5. **バグ修正**: エラーメッセージとスタックトレースを貼り付けて修正依頼

#### データサイエンスでの活用

<details markdown="1">
<summary>データサイエンスでの活用（テキスト）</summary>

```
# Jupyter Notebook の変換
> Transform this exploratory notebook into a production pipeline

# データ分析
> Analyze the data in data/sales.csv and create visualizations
```

</details>

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

<details markdown="1">
<summary>コード例（JSON）</summary>

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

</details>

環境変数（`${GITHUB_TOKEN}` 等）はローカルの `.env` や CI シークレットから読み込まれ、`.mcp.json` 自体に機密情報を含めずに済む。

### 18.4 カスタム MCP サーバーの開発

社内ツールや独自 API を MCP サーバーとして公開することも可能：

<details markdown="1">
<summary>社内ツールや独自 API を MCP サーバーとして公開することも可能（Python）</summary>

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

</details>

<details markdown="1">
<summary>```（JSON）</summary>

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

</details>

### 18.5 IDE 統合の詳細設定

#### VS Code 拡張機能の高度な設定

VS Code の `settings.json` で Claude Code 拡張機能を細かく制御できる：

<details markdown="1">
<summary>VS Code の `settings.json` で Claude Code 拡張機能を細かく制御できる（JSON）</summary>

```json
{
  "claude-code.autoStart": true,
  "claude-code.model": "claude-sonnet-4-6",
  "claude-code.contextWindowWarningThreshold": 0.8,
  "claude-code.showStatusBar": true,
  "claude-code.diffView": "side-by-side"
}
```

</details>

#### JetBrains 系 IDE の統合

| IDE | プラグイン名 | 特記事項 |
|-----|------------|---------|
| IntelliJ IDEA | Claude Code | Java/Kotlin プロジェクトとの統合が優秀 |
| PyCharm | Claude Code | Python インタープリタの自動検出 |
| WebStorm | Claude Code | TypeScript の型情報を活用 |
| GoLand | Claude Code | Go モジュールの構造を認識 |

JetBrains IDE での差分ビューは IDE ネイティブの比較ツールを使用するため、既存のコードレビューワークフローと自然に統合できる。

#### Neovim / Vim での使用

<details markdown="1">
<summary>Neovim / Vim での使用（Lua）</summary>

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

</details>

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

<details markdown="1">
<summary>最も生産性が高いのは複数ツールを組み合わせる戦略である（テキスト）</summary>

```
日常のコーディング    → Cursor（リアルタイム補完）
                          +
複雑なリファクタリング → Claude Code（大規模変更）
                          +
CI/CD の自動化       → Claude Code GitHub Actions
```

</details>

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

<details markdown="1">
<summary>PR・Issue コメントへの応答（YAML）</summary>

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

</details>

#### PR の自動コードレビュー

<details markdown="1">
<summary>PR の自動コードレビュー（YAML）</summary>

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

</details>

#### セキュリティ監査（定期実行）

<details markdown="1">
<summary>セキュリティ監査（定期実行）（YAML）</summary>

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

</details>

#### ビルド失敗時の自動デバッグ

<details markdown="1">
<summary>ビルド失敗時の自動デバッグ（YAML）</summary>

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

</details>

### 20.4 @claude コマンドの活用

PR や Issue のコメントで以下のように使う：

<details markdown="1">
<summary>PR や Issue のコメントで以下のように使う（text）</summary>

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

</details>

### 20.5 コスト管理

GitHub Actions での Claude 利用には二重のコストが発生する：

| コスト種別 | 内容 | 管理方法 |
|-----------|------|---------|
| GitHub Actions 分数 | Ubuntu runner の実行時間 | `timeout-minutes` で制限 |
| API トークン | Claude への入出力トークン数 | `--max-turns` で反復回数を制限 |

<details markdown="1">
<summary>| API トークン | Claude への入出力トークン数 | `--max-turns` で反復回数を制限 |（YAML）</summary>

```yaml
# コスト管理の例
- uses: anthropics/claude-code-action@v1
  timeout-minutes: 10          # Actions の実行時間上限
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude_args: "--max-turns 5 --model claude-sonnet-4-6"  # ターン数とモデル指定
```

</details>

### 20.6 AWS Bedrock / Google Vertex AI との統合

コストやデータ主権の要件がある企業向けに、クラウドプロバイダー経由での利用も可能：

<details markdown="1">
<summary>コストやデータ主権の要件がある企業向けに、クラウドプロバイダー経由での利用も可能（YAML）</summary>

```yaml
# AWS Bedrock 利用例
- uses: anthropics/claude-code-action@v1
  with:
    use_bedrock: "true"
    claude_args: "--model us.anthropic.claude-sonnet-4-6 --max-turns 10"
  env:
    AWS_REGION: us-west-2
```

</details>

<details markdown="1">
<summary>```（YAML）</summary>

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

</details>

---

## 21. チーム開発 - CLAUDE.md 共有・コードレビュー

### 21.1 チーム向け CLAUDE.md の設計

チーム開発で最も重要なのは **CLAUDE.md を git にコミットしてチーム全員が同じルールを共有すること** である。個人の好みと違う場合は `CLAUDE.local.md` を使う。

#### チーム向け CLAUDE.md テンプレート

<details markdown="1">
<summary>チーム向け CLAUDE.md テンプレート（Markdown）</summary>

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

</details>

### 21.2 チーム共通エージェントの整備

`.claude/agents/` にチーム共有のエージェントを配置し、git で管理する：

#### PR レビューエージェント

<details markdown="1">
<summary>PR レビューエージェント（Markdown）</summary>

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

</details>

#### ドキュメント生成エージェント

<details markdown="1">
<summary>ドキュメント生成エージェント（Markdown）</summary>

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

</details>

### 21.3 CLAUDE.md の継続的改善

CLAUDE.md は一度書いて終わりではなく、継続的に改善する：

#### CLAUDE.md 改善サイクル

<details markdown="1">
<summary>CLAUDE.md 改善サイクル（テキスト）</summary>

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

</details>

#### よくある追加ルールの例

<details markdown="1">
<summary>よくある追加ルールの例（Markdown）</summary>

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

</details>

### 21.4 コードレビューワークフロー

#### ヒューマン + AI のハイブリッドレビュー

<details markdown="1">
<summary>ヒューマン + AI のハイブリッドレビュー（テキスト）</summary>

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

</details>

#### ローカルでの事前レビュー

PR を出す前にローカルで Claude にレビューさせることで、レビュー往復を削減できる：

<details markdown="1">
<summary>PR を出す前にローカルで Claude にレビューさせることで、レビュー往復を削減できる（Bash）</summary>

```bash
# git の差分をレビューさせる
git diff main...HEAD | claude -p "このコードの差分をレビューして。セキュリティとコード品質に注目して"

# 特定ファイルのレビュー
claude -p "src/auth/login.py のセキュリティレビューをして" \
  --allowedTools "Read,Grep,Glob"
```

</details>

### 21.5 ナレッジの蓄積と共有

#### プロジェクト固有の知識をスキルに蓄積

<details markdown="1">
<summary>プロジェクト固有の知識をスキルに蓄積（Markdown）</summary>

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

</details>

---

## 22. セキュリティ - パーミッション・機密情報・サンドボックス

### 22.1 セキュリティの基本方針

Claude Code のセキュリティは **最小権限の原則** に基づく。デフォルトでは読み取り専用であり、ファイル変更やコマンド実行には明示的な許可が必要。これは開発者が知らない間に重要なファイルが変更されることを防ぐ [^23]。

### 22.2 許可ツールの適切な設定

#### 許可リストによる最小権限付与

<details markdown="1">
<summary>許可リストによる最小権限付与（JSON）</summary>

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

</details>

#### 作業種別ごとの権限設定

<details markdown="1">
<summary>作業種別ごとの権限設定（Bash）</summary>

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

</details>

### 22.3 機密情報の管理

#### 絶対にやってはいけないこと

<details markdown="1">
<summary>絶対にやってはいけないこと（Markdown）</summary>

```markdown
# 危険な CLAUDE.md の例（やってはいけない）
API_KEY=sk-prod-xxxxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@prod-db:5432/myapp
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

</details>

#### 正しい機密情報の管理方法

<details markdown="1">
<summary>正しい機密情報の管理方法（Markdown）</summary>

```markdown
# 安全な CLAUDE.md の例
## 設定
API キーは環境変数 `API_KEY` から取得。`.env` ファイルを参照。
DB 接続は `DATABASE_URL` 環境変数を使用。
```

</details>

<details markdown="1">
<summary>```（Bash）</summary>

```bash
# .env（.gitignore に追加）
API_KEY=sk-prod-xxxxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@prod-db:5432/myapp
```

</details>

<details markdown="1">
<summary>```（Bash）</summary>

```bash
# .gitignore
.env
.env.local
.env.production
*.pem
*.key
secrets/
```

</details>

#### シークレットスキャン

Claude Code を使ってシークレットのスキャンを行うことも可能：

<details markdown="1">
<summary>Claude Code を使ってシークレットのスキャンを行うことも可能（Bash）</summary>

```bash
claude -p "このコードベースをスキャンして、ハードコードされた API キー、
パスワード、トークン、シークレットを見つけてください。
ファイルパスと行番号を報告してください。修正は行わないこと。" \
  --allowedTools "Read,Glob,Grep"
```

</details>

### 22.4 サンドボックスの活用

サンドボックスは OS レベルの隔離を提供し、Claude が意図しないファイルやネットワークにアクセスすることを防ぐ：

<details markdown="1">
<summary>サンドボックスは OS レベルの隔離を提供し、Claude が意図しないファイルやネットワークにアクセスすることを防ぐ（Bash）</summary>

```bash
# サンドボックスを有効化（セッション内）
/sandbox

# サンドボックス有効化後の動作
# - 書き込み: カレントディレクトリ以下のみ
# - 読み取り: システム全体（制限ディレクトリ除く）
# - ネットワーク: デフォルトは全拒否
```

</details>

#### サンドボックスのネットワーク設定

<details markdown="1">
<summary>サンドボックスのネットワーク設定（JSON）</summary>

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

</details>

### 22.5 企業環境でのセキュリティ対策

#### 組織レベルのポリシー設定

企業の IT/セキュリティチームは管理ポリシーを通じて Claude Code の動作を制御できる：

<details markdown="1">
<summary>企業の IT/セキュリティチームは管理ポリシーを通じて Claude Code の動作を制御できる（JSON）</summary>

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

</details>

#### MCP ゲートウェイによる集中管理

MCP サーバーへのアクセスを MCP ゲートウェイを通じて統制することで、監査ログの取得とアクセス制御が可能：

<details markdown="1">
<summary>MCP サーバーへのアクセスを MCP ゲートウェイを通じて統制することで、監査ログの取得とアクセス制御が可能（JSON）</summary>

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

</details>

### 22.6 セキュリティインシデント対応

Claude Code が予期しない動作をした場合の対処：

<details markdown="1">
<summary>Claude Code が予期しない動作をした場合の対処（Bash）</summary>

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

</details>

#### フックによる安全策

<details markdown="1">
<summary>フックによる安全策（JSON）</summary>

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

</details>

<details markdown="1">
<summary>```（Bash）</summary>

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

</details>

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

<details markdown="1">
<summary>Python（Bash）</summary>

```bash
# uv を使う場合（推奨）
uv init my-agent && cd my-agent
uv add claude-agent-sdk

# pip を使う場合
pip install claude-agent-sdk
```

</details>

#### TypeScript

<details markdown="1">
<summary>TypeScript（Bash）</summary>

```bash
npm init -y
npm install @anthropic-ai/claude-agent-sdk
npm install -D typescript tsx @types/node
```

</details>

#### 認証設定

<details markdown="1">
<summary>認証設定（Bash）</summary>

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

</details>

### 23.3 基本的な使い方

#### Python の例

<details markdown="1">
<summary>Python の例（Python）</summary>

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

</details>

#### TypeScript の例

<details markdown="1">
<summary>TypeScript の例（TypeScript）</summary>

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

</details>

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

<details markdown="1">
<summary>カスタムツール承認コールバック（Python）</summary>

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

</details>

### 23.5 実用的なエージェント例

#### コードマイグレーションエージェント

<details markdown="1">
<summary>コードマイグレーションエージェント（Python）</summary>

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

</details>

#### ドキュメント生成エージェント

<details markdown="1">
<summary>ドキュメント生成エージェント（Python）</summary>

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

</details>

#### MCP サーバーを使ったエージェント

<details markdown="1">
<summary>MCP サーバーを使ったエージェント（Python）</summary>

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

</details>

### 23.6 エラーハンドリングとリトライ

<details markdown="1">
<summary>23.6 エラーハンドリングとリトライ（Python）</summary>

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

</details>

### 23.7 本番環境へのデプロイ

#### Docker コンテナでの運用

<details markdown="1">
<summary>Docker コンテナでの運用（Dockerfile）</summary>

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

</details>

<details markdown="1">
<summary>```（YAML）</summary>

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

</details>

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

<details markdown="1">
<summary>A:** 権限の問題。以下を確認（Bash）</summary>

```bash
# 現在の権限設定を確認
/permissions

# 特定コマンドを許可リストに追加
# settings.json の permissions.allow に追加する
```

</details>

#### Q: サブエージェントとメインエージェントでファイルを共有するには？

**A:** サブエージェントはメインエージェントと同じファイルシステムを使用するため、ファイルを介した共有が可能：

<details markdown="1">
<summary>A:** サブエージェントはメインエージェントと同じファイルシステムを使用するため、ファイルを介した共有が可能（テキスト）</summary>

```
# メインエージェント
Use a subagent to investigate the auth module.
The subagent should write findings to /tmp/auth-analysis.md

# 結果の利用
Read /tmp/auth-analysis.md and implement the improvements
```

</details>

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

<details markdown="1">
<summary>接続・認証エラー（Bash）</summary>

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

</details>

#### パフォーマンスが遅い場合

<details markdown="1">
<summary>パフォーマンスが遅い場合（Bash）</summary>

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

</details>

#### フックが動作しない場合

<details markdown="1">
<summary>フックが動作しない場合（Bash）</summary>

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

</details>

#### MCP サーバーが接続できない場合

<details markdown="1">
<summary>MCP サーバーが接続できない場合（Bash）</summary>

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

</details>

#### Windows (WSL) での問題

<details markdown="1">
<summary>Windows (WSL) での問題（Bash）</summary>

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

</details>

#### Git 操作の問題

<details markdown="1">
<summary>Git 操作の問題（Bash）</summary>

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

</details>

### 24.3 パフォーマンスチューニング

#### 大規模コードベースでの最適化

<details markdown="1">
<summary>大規模コードベースでの最適化（Markdown）</summary>

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

</details>

#### バッチ処理の最適化

<details markdown="1">
<summary>バッチ処理の最適化（Python）</summary>

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

</details>

### 24.4 デバッグのベストプラクティス

#### エラーメッセージの読み方

<details markdown="1">
<summary>エラーメッセージの読み方（テキスト）</summary>

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

</details>

#### ログの活用

<details markdown="1">
<summary>ログの活用（Bash）</summary>

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

</details>

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

## 25. 初心者チュートリアル - インストールから初回利用まで

### 25.1 前提条件

Claude Code を利用するには以下が必要である。

| 要件 | 内容 |
|------|------|
| OS | macOS 10.15+、Linux（主要ディストリビューション）、Windows 11（ネイティブ対応） |
| Claude.ai アカウント | Pro プラン以上（$20/月）が必要 |
| ターミナル | macOS はターミナル.app または iTerm2、Linux は任意のシェル、Windows は PowerShell または WSL2 |
| インターネット接続 | 必須（Claude API との通信に使用） |

Node.js は **不要**である。2025年後半からネイティブインストーラーが提供されており、Node.js なしで動作する。

---

### 25.2 インストール手順

#### macOS / Linux（推奨: npm 経由）

<details markdown="1">
<summary>macOS / Linux（推奨: npm 経由）（Bash）</summary>

```bash
# npm がある場合（最も広く使われている方法）
npm install -g @anthropic-ai/claude-code

# インストール確認
claude --version
```

</details>

#### macOS（Homebrew 経由）

<details markdown="1">
<summary>macOS（Homebrew 経由）（Bash）</summary>

```bash
brew install claude-code

# 自動更新は行われないため、定期的にアップデートすること
brew upgrade claude-code
```

</details>

#### Windows

PowerShell を **管理者として実行** し、以下を入力する。

```powershell
npm install -g @anthropic-ai/claude-code
```

WSL2（Windows Subsystem for Linux）を使う場合は Linux の手順と同じである。

#### インストールのトラブルシューティング

<details markdown="1">
<summary>インストールのトラブルシューティング（Bash）</summary>

```bash
# npm のパーミッションエラーが出た場合
sudo npm install -g @anthropic-ai/claude-code

# または nvm を使って Node.js を管理するとパーミッション問題が回避できる
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
npm install -g @anthropic-ai/claude-code
```

</details>

---

### 25.3 初回起動とログイン

#### ステップ 1: プロジェクトディレクトリに移動

Claude Code は **起動したディレクトリをプロジェクトルート** として認識する。必ずプロジェクトのルートで起動すること。

```bash
cd ~/projects/my-app
claude
```

#### ステップ 2: ブラウザ認証

初回起動時にブラウザが自動的に開き、Claude.ai のログイン画面が表示される。

1. Claude.ai アカウントでログインする
2. 「Claude Code に権限を付与する」を承認する
3. ブラウザを閉じてターミナルに戻る

認証完了後、ターミナルに以下が表示される。

<details markdown="1">
<summary>認証完了後、ターミナルに以下が表示される。（テキスト）</summary>

```
Welcome to Claude Code!
Type your request below. Press Ctrl+C to exit.

>
```

</details>

#### ステップ 3: 権限モードの選択

初回起動時に権限モードを確認される。

| モード | 説明 | 推奨場面 |
|--------|------|---------|
| **Suggested（推奨）** | 各操作ごとに承認を求める | 初心者、本番環境 |
| **Auto-accept edits** | ファイル編集は自動承認 | 慣れてきたら |
| **Full auto** | 全操作を自動承認 | CI/CD、熟練者 |

初心者は **Suggested** を選択する。

---

### 25.4 最初の操作を試す

#### プロジェクトの概要を把握する

```
> このプロジェクトの構成を説明してください
```

Claude がプロジェクト内のファイルを読み込み、構成と目的を説明する。

#### CLAUDE.md を自動生成する

```
> /init
```

このコマンドでプロジェクトを自動分析し、ビルドコマンドやテストコマンドを含む `CLAUDE.md` を生成する。生成後に内容を確認して必要に応じて編集する。

#### 簡単なコード変更を依頼する

```
> README.md にインストール手順のセクションを追加してください
```

Claude がファイルを読み込み、変更案を提示する。変更を承認する前に必ず内容を確認すること。

---

### 25.5 よく使うコマンド一覧（初心者向け）

最初に覚えておくと便利なコマンドをまとめました。

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプを表示 |
| `/init` | CLAUDE.md を自動生成 |
| `/clear` | 会話をリセット（コンテキストをクリア） |
| `/permissions` | 権限設定を変更 |
| `Esc` | Claude の処理を中断 |
| `Esc Esc` または `/rewind` | 直前の変更を元に戻す |
| `Ctrl+C` | Claude Code を終了 |

---

### 25.6 初心者が陥りがちなミス

**1. ルートディレクトリ以外で起動する**

<details markdown="1">
<summary>1. ルートディレクトリ以外で起動する**（Bash）</summary>

```bash
# 悪い例: ホームディレクトリから起動
cd ~
claude

# 良い例: プロジェクトルートから起動
cd ~/projects/my-app
claude
```

</details>

**2. 変更を確認せずに承認する**

Claude が提案する変更は必ず内容を確認してから承認すること。特に削除操作やデータベースへの書き込みには注意が必要である。

**3. 1回で全てを頼む**

<details markdown="1">
<summary>3. 1回で全てを頼む**（テキスト）</summary>

```
# 悪い例: 曖昧で大きすぎる指示
> このアプリを完成させてください

# 良い例: 具体的で小さな単位の指示
> src/auth/login.ts にメールアドレスのバリデーション関数を追加してください。
> 正規表現でチェックし、無効な場合は InvalidEmailError を throw すること。
```

</details>

**4. コンテキストが溜まりすぎる**

長時間の作業後は `/clear` でコンテキストをリセットし、新しいタスクを始めること。コンテキストが蓄積するとパフォーマンスが低下する。

---

### 25.7 次のステップ

初回利用後は以下の順で学習を進めることを推奨する。

1. **CLAUDE.md の整備**（2章参照）: プロジェクト固有のルールを定義する
2. **Plan Mode の活用**（8章参照）: `Shift+Tab` で計画モードに切り替え（または `/plan` コマンド）、実装前に計画を立てる
3. **スキルの作成**（4章参照）: よく使うワークフローを自動化する
4. **Git 連携**（28章参照）: ブランチ作成から PR まで自然言語で操作する

---

## 26. プロンプトエンジニアリング - 効果的な指示の出し方

### 26.1 Claude Code プロンプティングの基本原則

Claude Code（特に Claude 4.x モデル）は **指示されたことを文字通りに実行する** という特性を持つ。「良い感じに」「適切に」といった曖昧な指示よりも、具体的な期待値を明示した指示のほうが格段に良い結果を生む。

#### 5つの基本原則

1. **具体性**: 何をどこにどのように実装するかを明示する
2. **検証可能性**: 成功・失敗の判断基準を与える
3. **文脈提供**: なぜその変更が必要かを説明する
4. **スコープ限定**: 影響範囲を明確にする
5. **段階的指示**: 大きなタスクは小さなステップに分割する

---

### 26.2 良いプロンプトと悪いプロンプトの比較

#### ファイル修正

<details markdown="1">
<summary>ファイル修正（テキスト）</summary>

```
# 悪い例（曖昧）
バグを直してください

# 良い例（具体的）
src/utils/email.ts の validateEmail 関数を修正してください。
現在の問題: "user+tag@example.com" のようなプラス記号を含むアドレスが false を返す。
期待する動作: RFC 5321 に準拠した全ての有効なアドレスを true と判定する。
修正後は npm test でテストが全てパスすることを確認してください。
```

</details>

#### 新機能実装

<details markdown="1">
<summary>新機能実装（テキスト）</summary>

```
# 悪い例（範囲不明）
ログイン機能を追加してください

# 良い例（範囲・制約・検証が明確）
src/auth/ ディレクトリに JWT ベースのログイン機能を追加してください。

要件:
- POST /api/auth/login エンドポイントを作成（email, password を受け取る）
- bcrypt でパスワードを検証する（既存の User モデルを参照）
- 認証成功時に 24 時間有効な JWT を返す
- 既存の authMiddleware.ts のパターンに倣うこと

制約:
- 新しいライブラリは追加しない（jsonwebtoken と bcryptjs は既存）
- 既存のテストを壊さないこと

実装後: npm test src/auth/ を実行してテストが通ることを確認してください
```

</details>

#### コードレビュー

<details markdown="1">
<summary>コードレビュー（テキスト）</summary>

```
# 悪い例
このコードをレビューしてください

# 良い例
@src/services/payment.ts をレビューしてください。
特に以下の点に注目してください：
1. セキュリティ上の問題（SQLインジェクション、XSS、認証の抜けなど）
2. エラーハンドリングの漏れ
3. 競合状態（race condition）の可能性
問題を見つけた場合は、その行番号と修正案を示してください
```

</details>

---

### 26.3 コンテキストの与え方

#### @ 参照を使ったファイル指定

<details markdown="1">
<summary>@ 参照を使ったファイル指定（テキスト）</summary>

```
# 関連ファイルを明示的に参照する
@src/models/User.ts と @src/controllers/authController.ts を読んで、
ログアウト処理でセッションが正しく破棄されているか確認してください
```

</details>

#### エラーメッセージをそのまま貼る

<details markdown="1">
<summary>エラーメッセージをそのまま貼る（テキスト）</summary>

```
以下のエラーが発生しています。根本原因を特定して修正してください：

TypeError: Cannot read properties of undefined (reading 'userId')
    at AuthMiddleware.verify (/app/src/middleware/auth.ts:23:45)
    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)

src/middleware/auth.ts の23行目付近を調べてください
```

</details>

#### スクリーンショットを貼り付ける

UI の問題はスクリーンショットを直接ペーストすることで、文章での説明よりも正確に伝えられる。

<details markdown="1">
<summary>UI の問題はスクリーンショットを直接ペーストすることで、文章での説明よりも正確に伝えられる。（テキスト）</summary>

```
[スクリーンショットを貼り付け]
この画面のボタンが Safari でクリックできない問題を修正してください。
Chrome では正常に動作しています。
```

</details>

---

### 26.4 Plan Mode の活用

複雑なタスクは先に計画を立ててから実装することで、間違った方向への実装を防ぐことができる。

```bash
# Shift+Tab で Plan Mode に切り替え（Normal → Plan → Auto-Accept のサイクル）
# または /plan コマンドを使用
# Plan Mode 中は Claude はファイルを読むだけで変更しない
```

<details markdown="1">
<summary>```（テキスト）</summary>

```
[Plan Mode]
> OAuth 2.0 によるGoogle ログインを追加したい。
> 現在の認証フロー（src/auth/ 配下）を調べて、どのファイルを変更する必要があるか、
> どのような順序で実装するかを計画してください。
> ライブラリは passport.js を使います。
```

</details>

Claude が計画を提示したら、`Ctrl+G` でエディタに計画を開いて修正できる。納得できたら Normal Mode に切り替えて実装を指示する。

---

### 26.5 Claude へのインタビュー手法

大きな機能追加の前に Claude に質問させることで、見落としを防ぐことができる。

<details markdown="1">
<summary>大きな機能追加の前に Claude に質問させることで、見落としを防ぐことができる。（テキスト）</summary>

```
決済機能を追加したいと思っています。
AskUserQuestion ツールを使って、実装に必要な情報を私にインタビューしてください。
技術的な実装方法、UI/UX、エッジケース、セキュリティ上の考慮事項について
詳しく質問してください。自明な質問は避け、難しい部分を掘り下げてください。
全ての情報が揃ったら、SPEC.md に完全な仕様書を書いてください。
```

</details>

インタビュー完了後、`/clear` で新しいセッションを開始し、`@SPEC.md` を参照して実装を依頼する。

---

### 26.6 段階的な指示の技法

#### 探索 → 計画 → 実装 の分離

<details markdown="1">
<summary>探索 → 計画 → 実装 の分離（テキスト）</summary>

```
# ステップ 1: 探索（Plan Mode）
> src/database/ の構成を理解して、
> 現在のマイグレーション管理の方法を説明してください

# ステップ 2: 計画（Plan Mode）
> users テーブルに last_login カラムを追加するマイグレーションを作成するには
> どのようなファイルを作成・変更する必要がありますか？

# ステップ 3: 実装（Normal Mode）
> 計画に基づいてマイグレーションを実装してください。
> 実装後に npm run migrate:latest を実行して成功することを確認してください
```

</details>

#### チェックリストを与える

<details markdown="1">
<summary>チェックリストを与える（テキスト）</summary>

```
以下のチェックリストを満たす API エンドポイントを実装してください：

- [ ] POST /api/users - ユーザー作成
- [ ] GET /api/users/:id - ユーザー取得
- [ ] PUT /api/users/:id - ユーザー更新
- [ ] DELETE /api/users/:id - ユーザー削除
- [ ] 各エンドポイントに認証ミドルウェアを適用
- [ ] エラーレスポンスは共通フォーマット（error.ts 参照）を使う
- [ ] 各エンドポイントのユニットテストを作成
- [ ] OpenAPI ドキュメントに追加

完了したチェックリストを最後に報告してください
```

</details>

---

### 26.7 CLAUDE.md でプロンプトを省力化する

毎回同じ指示を書かなくていいように、プロジェクト共通のルールは `CLAUDE.md` に記載する。

<details markdown="1">
<summary>毎回同じ指示を書かなくていいように、プロジェクト共通のルールは `CLAUDE.md` に記載する。（Markdown）</summary>

```markdown
# CLAUDE.md の例

## 実装ルール
- 新機能は必ずユニットテストを追加すること
- エラーハンドリングは src/errors/AppError.ts を継承すること
- API レスポンスは src/types/ApiResponse.ts の型に準拠すること
- console.log は使わず logger.ts の関数を使うこと

## 確認コマンド
- テスト: `npm test`
- 型チェック: `npx tsc --noEmit`
- リント: `npm run lint`
- ビルド: `npm run build`

## 変更後の確認
コードを変更したら必ず型チェックとリントを実行し、エラーがないことを確認すること
```

</details>

---

### 26.8 プロンプトのアンチパターン

避けるべきプロンプトのパターンと、より良い代替表現を示します。

| アンチパターン | 問題 | 改善策 |
|--------------|------|--------|
| 「きれいなコードに直して」 | 「きれい」の定義が曖昧 | 具体的なルール（DRY、関数の行数制限など）を指定 |
| 「最適化してください」 | 何を最適化するかが不明 | 「実行速度」「メモリ使用量」「可読性」を明示 |
| 「バグを全部直して」 | スコープが広すぎる | 特定のファイルやテストケースを指定 |
| 「適切にエラーハンドリングして」 | 「適切」の解釈が人によって異なる | どのエラーをどう処理するか具体的に指定 |
| 「〇〇を実装して（詳細なし）」 | Claude が余分なものを作る可能性がある | 使用するライブラリ、パターン、制約を明示 |

---

## 27. 料金・プラン完全ガイド

### 27.1 プラン一覧（2026年3月時点）

2026年3月時点での Claude.ai のプランと Claude Code の利用可否をまとめます。

| プラン | 月額 | 主な特徴 | Claude Code |
|-------|------|---------|-------------|
| **Free** | $0 | 1日の利用制限あり、Claude 4.5 Sonnet のみ | 制限あり |
| **Pro** | $20/月（年払い $17/月） | Free の 5 倍の利用量、優先アクセス | 含む |
| **Max 5x** | $100/月 | Pro の 5 倍の利用量、Extended Thinking | 含む |
| **Max 20x** | $200/月 | Pro の 20 倍の利用量、最新機能の優先アクセス | 含む |
| **Team** | $25〜$30/ユーザー/月（年払い） | 共有ワークスペース、管理機能 | 制限あり |
| **Team Premium** | $150/ユーザー/月 | Claude Code ターミナルアクセス含む | フルアクセス |
| **Enterprise** | 要相談 | SSO、監査ログ、カスタム契約 | フルアクセス |

---

### 27.2 各プランの詳細

#### Free プラン
- 1日の使用量制限があり、混雑時は制限が変動する
- Claude 4.5 Sonnet のみ使用可能
- Claude Code は試験的に利用可能だが、頻繁に制限に達する
- **推奨利用者**: 機能を試したいユーザー

#### Pro プラン（$20/月）
- Free の 5 倍の使用量、利用量は 5〜8 時間ごとにリセット
- Google Workspace 連携
- Claude Code を含む全機能にアクセス可能
- 混雑時の優先アクセス
- **推奨利用者**: 個人開発者、Claude Code をメインで使う開発者

#### Max プラン（$100 または $200/月）
- $100 プラン: Pro の 5 倍の使用量（週単位でリセット）
- $200 プラン: Pro の 20 倍の使用量（週単位でリセット）
- Extended Thinking（深い推論）機能
- Memory 機能（会話をまたいだ記憶）
- 新モデルと新機能への優先アクセス
- **推奨利用者**: 大規模なコードベースを扱うヘビーユーザー、コンサルタント

#### Team プラン（$25〜$30/ユーザー/月）
- 共有ワークスペースと管理コンソール
- チームメンバー間でのナレッジ共有
- Claude Code は標準シート（$25）では制限があり、プレミアムシート（$150）でフルアクセス
- **推奨利用者**: 開発チーム全体で使う場合

#### Enterprise プラン
- カスタム価格・カスタム利用量
- シングルサインオン（SSO）
- 監査ログと SIEM 統合
- データ処理契約（DPA）
- IP インデムニティ
- 専任サポート
- **推奨利用者**: 大企業、医療・金融などコンプライアンス要件がある組織

---

### 27.3 API 直接利用の料金（2026年3月時点）

Claude Code を API キーで直接利用する場合のモデル別料金です。ヘビーユーザーはプランとの比較が重要です。

| モデル | 入力 (1Mトークン) | 出力 (1Mトークン) | 特徴 |
|-------|-----------------|-----------------|------|
| Claude Haiku 4.5 | $1 | $5 | 高速・低コスト |
| Claude Sonnet 4.5 | $3 | $15 | バランス型 |
| Claude Sonnet 4.6 | $3 | $15 | 最新、コーディング最強 |
| Claude Opus 4.6 | $5 | $25 | 最高性能、複雑な推論 |

**コスト削減オプション**:
- **プロンプトキャッシング**: 繰り返し使う文書を事前キャッシュして最大 90% 削減
- **バッチ処理**: Batch API で非同期処理すると 50% 削減
- **Sonnet vs Opus 使い分け**: 単純なタスクは Sonnet、複雑な推論は Opus

---

### 27.4 コスト計算の実例

#### 個人開発者の月間コスト試算

<details markdown="1">
<summary>個人開発者の月間コスト試算（テキスト）</summary>

```
シナリオ: 毎日 4 時間 Claude Code を使って開発する個人開発者

Pro プラン ($20/月):
- コーディングセッション: 平均 50K トークン/時間 × 4 時間 × 22 日
- 月間推定消費: 4.4M トークン
- Pro プランの使用量上限: 約 5M トークン/月（混雑によって変動）
→ Pro プランで概ね収まる

Max 5x プラン ($100/月):
- 上記の 5 倍の余裕
- 大規模リファクタリングや複数プロジェクト並行作業に適している
```

</details>

#### API 経由の場合のコスト試算

<details markdown="1">
<summary>API 経由の場合のコスト試算（テキスト）</summary>

```
シナリオ: Claude Code を API で使い、月間 10M 入力トークン + 2M 出力トークン

Claude Sonnet 4.6:
- 入力: 10M × $3/M = $30
- 出力: 2M × $15/M = $30
- 合計: $60/月

→ Max プラン ($100/月) と比較すると API の方が安い場合がある
→ ただし、Max プランは使用量の保証があり、高負荷時でも安定して使える
```

</details>

**注意**: API 経由のヘビーコーディングでは月間 $3,650 を超えることもある。Claude Code を大量に使うなら Max プランの $200/月 の方が大幅に安い。

---

### 27.5 プラン選択のフローチャート

<details markdown="1">
<summary>27.5 プラン選択のフローチャート（テキスト）</summary>

```
Claude Code を使いたい？
  │
  ├── 試してみたいだけ
  │     → Free プラン（制限に達したら Pro を検討）
  │
  ├── 個人開発・副業
  │     → Pro プラン ($20/月)
  │     └── 月の途中で制限に達することが多い？
  │           → Max 5x プラン ($100/月)
  │
  ├── フリーランス・コンサルタント（複数プロジェクト）
  │     → Max 20x プラン ($200/月)
  │
  ├── 開発チーム（5名以上）
  │     → Team プラン ($30/ユーザー/月)
  │     └── 全員が Claude Code をフル活用？
  │           → Team Premium ($150/ユーザー/月)
  │
  └── 大企業・コンプライアンス要件あり
        → Enterprise プラン（要問い合わせ）
```

</details>

---

## 28. Git 連携詳細 - ブランチ・マージ・PR レビュー

### 28.1 概要

Claude Code の Git 連携は、自然言語のインストラクションを Git コマンドに変換する機能である。ブランチ作成から PR のマージまでを、ターミナルで `git` コマンドを手動入力することなく実行できる。`gh` CLI がインストールされていると GitHub との連携が格段に便利になる。

<details markdown="1">
<summary>コード例（Bash）</summary>

```bash
# gh CLI のインストール（推奨）
# macOS
brew install gh

# Linux
sudo apt install gh

# 認証
gh auth login
```

</details>

---

### 28.2 ブランチ管理

#### ブランチの作成

<details markdown="1">
<summary>ブランチの作成（テキスト）</summary>

```
# 機能ブランチを作成する
> 通知システムを追加するためのフィーチャーブランチを作成してください

# Claude が実行するコマンド（内部的に）
git checkout -b feature/add-notification-system
```

</details>

CLAUDE.md にブランチ命名規則を定義すると、Claude が規則に従ったブランチ名を自動生成する。

<details markdown="1">
<summary>CLAUDE.md にブランチ命名規則を定義すると、Claude が規則に従ったブランチ名を自動生成する。（Markdown）</summary>

```markdown
# CLAUDE.md
## Git ルール
- ブランチ命名: feature/<説明>、fix/<説明>、hotfix/<説明>、chore/<説明>
- コミットメッセージ: Conventional Commits 形式（feat:, fix:, docs:, refactor: 等）
- main への直接プッシュは禁止
```

</details>

#### ブランチ間の移動と状態確認

<details markdown="1">
<summary>ブランチ間の移動と状態確認（テキスト）</summary>

```
> 現在のブランチとその変更状況を教えてください

> main ブランチに切り替えて最新状態に更新してください
```

</details>

---

### 28.3 コミット管理

#### コンベンショナルコミットの自動生成

```
> ここまでの変更をコミットしてください
```

Claude はステージングされた差分を分析し、以下のような Conventional Commits 形式のメッセージを自動生成する。

<details markdown="1">
<summary>コード例（テキスト）</summary>

```
feat(auth): JWT トークンリフレッシュ機能を追加

- /api/auth/refresh エンドポイントを追加
- リフレッシュトークンの有効期限を 7 日間に設定
- 期限切れトークンの自動無効化処理を実装
```

</details>

#### 複数コミットへの分割

<details markdown="1">
<summary>複数コミットへの分割（テキスト）</summary>

```
> この変更は論理的に 3 つのコミットに分けられます。
> それぞれのコミットとして適切にステージングしてコミットしてください：
> 1. データモデルの変更
> 2. API エンドポイントの追加
> 3. テストの追加
```

</details>

---

### 28.4 マージコンフリクトの解決

#### 基本的なコンフリクト解決

<details markdown="1">
<summary>基本的なコンフリクト解決（テキスト）</summary>

```
> main ブランチをマージしようとしたらコンフリクトが発生しました。
> コンフリクトを解決してください。
> 優先方針: 最新の main ブランチの変更を優先するが、
> src/auth/ 配下の変更は私のブランチのものを維持すること
```

</details>

Claude はコンフリクトマーカー（`<<<<<<<`、`=======`、`>>>>>>>`）を解析し、それぞれの変更の意図を理解した上で解決策を提案する。

**自動解決できるコンフリクトの種類**:
- import 文の追加・順序変更
- 重複しない行の追加
- フォーマットの変更
- コメントの追加

**人間の判断が必要なコンフリクト**:
- 同じロジックの異なる実装
- ビジネスルールに関わる変更
- データ構造の競合

#### コンフリクト解決の手動確認

<details markdown="1">
<summary>コンフリクト解決の手動確認（テキスト）</summary>

```
> src/models/User.ts にコンフリクトがあります。
> 両方のブランチの変更内容を説明してから、最適な解決策を提案してください。
> 変更を適用する前に私が承認できるよう、差分を表示してください。
```

</details>

---

### 28.5 プルリクエストの作成と管理

#### PR の自動作成

```
> 現在のブランチの変更を main にマージするための PR を作成してください
```

Claude が自動で実行する処理:
1. ブランチ上の全コミットを分析
2. 変更内容のサマリーを作成
3. `gh pr create` でテンプレートに沿った PR を作成

生成される PR の例:

<details markdown="1">
<summary>生成される PR の例（Markdown）</summary>

```markdown
## 概要
JWT ベースの認証機能を実装しました。

## 変更内容
- POST /api/auth/login エンドポイントを追加
- JWT トークン生成・検証ロジックを実装
- 認証ミドルウェアを全 API エンドポイントに適用

## テスト
- ユニットテスト: 15件追加（全てパス）
- 手動テスト: ログイン/ログアウト/トークンリフレッシュを確認

## 注意事項
JWT_SECRET 環境変数の設定が必要です（.env.example を参照）
```

</details>

#### PR のレビュー依頼と対応

```
> PR #42 のレビューコメントを確認して、指摘された問題を修正してください
```

```
> PR #42 に以下のコメントが来ました。対応してください：
> "Error handling is missing in the token refresh endpoint"
```

---

### 28.6 Git Worktree を使った並列開発

Claude Code は `--worktree` フラグで隔離された Git worktree セッションを起動できる。これにより、同じリポジトリで複数の作業を並行して進められる。

<details markdown="1">
<summary>コード例（Bash）</summary>

```bash
# worktree を使ったセッション起動
claude --worktree

# または手動で worktree を作成してから起動
git worktree add ../my-app-feature feature/new-auth
cd ../my-app-feature
claude
```

</details>

**活用場面**:
- 本番バグの緊急修正と機能開発を同時進行
- A/B で異なる実装アプローチを試す
- レビュー待ちの PR と次の機能開発を並行作業

---

### 28.7 CI/CD との連携

#### GitHub Actions での自動 PR レビュー

`.github/workflows/claude-review.yml` を設定すると、PR 作成時に Claude が自動でレビューを行う。

<details markdown="1">
<summary>コード例（YAML）</summary>

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            このPRをレビューしてください。
            - セキュリティの問題
            - パフォーマンスの問題
            - テストの漏れ
            - コーディング規約の違反
            問題がある場合はコメントで指摘し、修正案を提示してください。
```

</details>

#### コミット前のフック

`.claude/settings.json` で pre-commit フックを設定する。

<details markdown="1">
<summary>`.claude/settings.json` で pre-commit フックを設定する。（JSON）</summary>

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "npm run lint -- --fix && npm run typecheck"
          }
        ]
      }
    ]
  }
}
```

</details>

---

### 28.8 Git ワークフローのベストプラクティス

Claude Code を使った Git 作業で特に効果的なベストプラクティスをまとめます。

| プラクティス | 説明 |
|------------|------|
| 作業開始前にブランチを作る | `> 新機能の開発を始めます。適切なブランチを作ってください` |
| 小さな単位でコミットする | 1つの論理的な変更 = 1コミットを守る |
| PR 前に最新の main を取り込む | `> main の最新変更をこのブランチにマージしてください` |
| コンフリクトを恐れない | Claude に任せて解決策を確認してから適用する |
| コミット履歴を活用する | `> このファイルの git 履歴を調べて、このロジックがどう変遷したか教えてください` |

---

## 29. TDD 連携 - テスト駆動開発ワークフロー

### 29.1 Claude Code と TDD の課題

Claude Code は自然に「実装を書いてからテストを書く」という順序で動作する。TDD（テスト駆動開発）の Red-Green-Refactor サイクルを守らせるには、**明示的な指示と仕組み作り**が必要である。

**Claude のデフォルト行動（問題）**:
1. 機能全体を実装する
2. その実装に合わせたテストを書く
3. テストは当然パスする（= テストとして機能していない）

**TDD の正しいサイクル**:
1. 失敗するテストを書く（RED）
2. テストをパスさせる最小限の実装を書く（GREEN）
3. テストを壊さずにコードをきれいにする（REFACTOR）

---

### 29.2 基本的な TDD プロンプト

#### テストファーストを明示する

<details markdown="1">
<summary>テストファーストを明示する（テキスト）</summary>

```
重要: TDD で開発してください。実装より先にテストを書いてください。

validateEmail(email: string): boolean 関数を TDD で実装してください。

ステップ:
1. まず failing test を書いてください（この時点では実装しないこと）
2. テストが RED（失敗）であることを npm test で確認してください
3. テストをパスする最小限の実装を書いてください
4. テストが GREEN（成功）であることを確認してください
5. コードをリファクタリングし、テストが引き続きパスすることを確認してください

テストケース:
- "user@example.com" → true
- "invalid-email" → false
- "user+tag@example.com" → true（プラス記号は有効）
- "" → false（空文字列）
```

</details>

---

### 29.3 TDD スキルの定義

`.claude/skills/tdd/SKILL.md` を作成して TDD を自動化する。

<details markdown="1">
<summary>`.claude/skills/tdd/SKILL.md` を作成して TDD を自動化する。（Markdown）</summary>

```markdown
---
name: tdd
description: テスト駆動開発（Red-Green-Refactor）サイクルを強制する
triggers:
  - "TDDで"
  - "テスト駆動で"
  - "テストファーストで"
  - "実装して"
  - "機能を追加して"
---

# TDD ワークフロー

このスキルが呼ばれた場合、必ず以下の順序で作業すること。

## Phase 1: RED（テストを書く）
1. 要件を理解する
2. 失敗するテストを書く
3. `npm test -- --testPathPattern=<対象ファイル>` を実行してテストが失敗することを確認する
4. 失敗が確認できるまで実装コードを書かないこと

## Phase 2: GREEN（実装する）
1. テストをパスする最小限のコードを書く
2. `npm test -- --testPathPattern=<対象ファイル>` を実行して全テストがパスすることを確認する
3. 過剰な実装をしないこと（テストをパスするだけで十分）

## Phase 3: REFACTOR（改善する）
1. コードの重複を除去する
2. 変数名・関数名を改善する
3. `npm test` を実行して全テストが引き続きパスすることを確認する

各フェーズの完了後に「Phase X 完了: [状態]」を報告すること。
```

</details>

---

### 29.4 サブエージェントを使ったテスト隔離

「コンテキスト汚染」（実装を知っているとテストを甘く書く）を防ぐために、テスト作成と実装を別のサブエージェントに分担させる。

<details markdown="1">
<summary>コード例（テキスト）</summary>

```
TDD でユーザー登録機能を実装してください。

手順:
1. サブエージェントを使って、実装を見ずにテストを書いてください
   - 入力: 要件仕様（@docs/user-registration-spec.md）のみ参照可
   - 出力: src/__tests__/userRegistration.test.ts

2. テストを実行して全て失敗することを確認してください

3. 別のサブエージェントを使って、テストだけを見て最小限の実装を書いてください
   - 入力: 書かれたテストファイルのみ参照可
   - 出力: src/services/userRegistration.ts

4. テストを実行して全てパスすることを確認してください

5. メインセッションでリファクタリングを行い、テストがパスし続けることを確認してください
```

</details>

---

### 29.5 テストタイプ別の TDD アプローチ

#### ユニットテスト（Jest / Vitest）

<details markdown="1">
<summary>ユニットテスト（Jest / Vitest）（テキスト）</summary>

```
src/utils/dateFormatter.ts に formatDate(date: Date, format: string): string 関数を
TDD で実装してください。

テストフレームワーク: Jest
テストファイルの場所: src/__tests__/dateFormatter.test.ts

カバーすべきケース:
- "YYYY-MM-DD" フォーマット
- "MM/DD/YYYY" フォーマット
- 無効な日付（null、undefined）への対応
- タイムゾーンの考慮（UTC で処理）
```

</details>

#### E2E テスト（Playwright）

<details markdown="1">
<summary>E2E テスト（Playwright）（テキスト）</summary>

```
Playwright で TDD を使い、ログインフォームをテストしてください。

Red フェーズ（先に書くテスト）:
- tests/login.spec.ts を作成
- 正しい認証情報でのログイン成功
- 間違ったパスワードでのエラーメッセージ表示
- メールアドレス未入力でのバリデーションエラー

テストを実行して全て失敗することを確認してから、
実装（src/app/login/page.tsx）に進んでください
```

</details>

---

### 29.6 TDD フックの設定

`.claude/settings.json` でテスト実行を強制するフックを設定する。

<details markdown="1">
<summary>`.claude/settings.json` でテスト実行を強制するフックを設定する。（JSON）</summary>

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "if [[ '${file}' == *'.test.'* ]]; then echo 'Test file written. Confirm it FAILS before implementing:'; npm test -- --testPathPattern='${file}' --passWithNoTests 2>&1 | tail -20; fi"
          }
        ]
      }
    ]
  }
}
```

</details>

このフックにより、テストファイルを書いた後に自動でそのテストが実行され、失敗しているかどうかを確認できる。

---

### 29.7 CLAUDE.md での TDD ルール定義

<details markdown="1">
<summary>29.7 CLAUDE.md での TDD ルール定義（Markdown）</summary>

```markdown
# CLAUDE.md

## 開発フロー（TDD）
1. 機能追加・バグ修正は必ず TDD で行うこと
2. 実装コードよりも先にテストを書くこと
3. テストが RED（失敗）であることを確認してから実装を始めること
4. テストをパスする最小限のコードのみを書くこと
5. テストが GREEN になってからリファクタリングを行うこと

## テストコマンド
- 単一ファイルテスト: `npm test -- --testPathPattern=<pattern>`
- 全テスト: `npm test`
- カバレッジ付き: `npm test -- --coverage`

## テスト配置ルール
- ユニットテスト: `src/__tests__/<name>.test.ts`
- E2E テスト: `tests/<name>.spec.ts`
- テストユーティリティ: `src/__tests__/helpers/`
```

</details>

---

## 30. デバッグ機能 - エラー解析・ログ分析

### 30.1 デバッグ機能の概要

Claude Code のデバッグ能力は以下の 4 つの側面がある。

| 機能 | 説明 |
|------|------|
| エラー解析 | スタックトレースから根本原因を特定 |
| ログ分析 | ターミナル出力をリアルタイムで解析 |
| 段階的追跡 | コードの実行フローを step-by-step で追う |
| 仮説検証 | 複数の原因候補を提示して絞り込む |

---

### 30.2 エラーメッセージのデバッグ

#### スタックトレースを直接貼り付ける

<details markdown="1">
<summary>スタックトレースを直接貼り付ける（テキスト）</summary>

```
以下のエラーを修正してください。根本原因を特定してから修正すること。
エラーを隠す（try-catch で握りつぶす）のは禁止。

エラー内容:
TypeError: Cannot read properties of undefined (reading 'map')
    at ProductList.render (/src/components/ProductList.tsx:34:23)
    at renderWithHooks (/node_modules/react-dom/cjs/react-dom.development.js:12883:18)

状況:
- 商品一覧ページに初回アクセスした時のみ発生
- 2回目以降のアクセスでは発生しない
- products state が初期状態では undefined の可能性がある
```

</details>

#### 複数ファイルにまたがるバグ

<details markdown="1">
<summary>複数ファイルにまたがるバグ（テキスト）</summary>

```
@src/hooks/useProducts.ts と @src/components/ProductList.tsx を両方確認して、
products が undefined になる可能性のある箇所を全て特定してください。

その後、最も可能性の高い根本原因から順に修正案を提示してください。
確実性の低い修正から始めないこと。
```

</details>

---

### 30.3 ログ分析ワークフロー

#### ターミナル出力のパイプ

<details markdown="1">
<summary>ターミナル出力のパイプ（Bash）</summary>

```bash
# テスト出力を Claude に送る
npm test 2>&1 | claude -p "テスト失敗の根本原因を分析して修正方法を提示してください"

# ビルドエラーを送る
npm run build 2>&1 | claude -p "ビルドエラーを分析して修正してください"

# サーバーログを送る
cat server.log | claude -p "エラーパターンを分析し、最も緊急度の高い問題を報告してください"
```

</details>

#### ログに詳細情報を追加させる

<details markdown="1">
<summary>ログに詳細情報を追加させる（テキスト）</summary>

```
現在のコードにデバッグログを追加してください。
以下の箇所に console.log を入れて、データの流れを追跡できるようにしてください：

1. src/services/paymentService.ts の processPayment 関数の入口
2. 各 API 呼び出しの前後
3. エラーハンドリングブロック内

ログフォーマット: [DEBUG][<関数名>] <メッセージ>: <値>

デバッグが完了したら、追加したログを削除することを忘れないでください
```

</details>

---

### 30.4 ノウハウ集: バグタイプ別デバッグ手順

#### 非同期処理のバグ

<details markdown="1">
<summary>非同期処理のバグ（テキスト）</summary>

```
src/api/userApi.ts で Promise が正しく処理されていない可能性があります。

以下を確認してください：
1. async/await の使い忘れ
2. Promise のエラーハンドリングが漏れている箇所
3. 競合状態（race condition）が発生しうる非同期処理の並列実行

テストコードで再現するケースを作成してから修正してください
```

</details>

#### パフォーマンス問題

<details markdown="1">
<summary>パフォーマンス問題（テキスト）</summary>

```
アプリのホームページの読み込みが遅くなりました（3秒以上）。

@src/pages/index.tsx を分析して：
1. 不必要な再レンダリングを引き起こしている箇所
2. データフェッチの最適化できる箇所
3. 大きなバンドルサイズを引き起こしているインポート

各問題の修正優先度と期待される改善幅を示してください
```

</details>

#### 環境依存バグ

<details markdown="1">
<summary>環境依存バグ（テキスト）</summary>

```
本番環境でのみ発生するエラーです。ローカルでは再現しません。

エラー: DATABASE_URL environment variable is not set
スタック: src/config/database.ts:12

本番環境と開発環境の設定ファイルの違いを分析して、
環境変数の取り扱いに問題がないか確認してください。
@.env.example と @src/config/ を調べてください
```

</details>

---

### 30.5 /debug コマンドとデバッグセッション管理

<details markdown="1">
<summary>30.5 /debug コマンドとデバッグセッション管理（テキスト）</summary>

```
# セッション中のデバッグ支援
/debug

# 長いデバッグセッションのコンテキスト圧縮
# （デバッグの結論を保持しつつコンテキストを節約）
/compact デバッグのまとめを保持して。バグの根本原因と修正内容を記録すること
```

</details>

#### バックグラウンドでのログ監視

<details markdown="1">
<summary>バックグラウンドでのログ監視（テキスト）</summary>

```
# テストを実行しながらメインの作業を継続する
npm run test:watch > test-output.log 2>&1 &

# テスト結果が変わったときに Claude に分析させる
tail -f test-output.log | claude -p "新しいテスト失敗が検出されたらすぐに報告してください"
```

</details>

---

### 30.6 getDiagnostics ツールの活用

Claude Code には `getDiagnostics` ツールが組み込まれており、TypeScript や ESLint などの言語サーバーの診断情報を自動取得できる。

<details markdown="1">
<summary>コード例（テキスト）</summary>

```
ファイルを編集した後、TypeScript の型エラーと ESLint の警告を全てチェックして、
エラーがあれば修正してください。
エラーがなくなるまで繰り返してください。
```

</details>

このような指示を与えると、Claude は `getDiagnostics` を使って自動的にエラーを確認し、全てのエラーが解消されるまでループして修正を続ける。

---

### 30.7 デバッグ記録の CLAUDE.md への反映

発見したバグや解決策を CLAUDE.md に記録することで、将来の同じ問題を回避できる。

<details markdown="1">
<summary>発見したバグや解決策を CLAUDE.md に記録することで、将来の同じ問題を回避できる。（テキスト）</summary>

```
今回発見した以下の問題を CLAUDE.md の「既知の問題」セクションに追記してください：

- React の useEffect で cleanup 関数を返さないとメモリリークが発生する
  （src/hooks/useWebSocket.ts を参照）
- Windows 環境でパスの区切り文字が / でなく \ になる問題
  （path.join を使うことで回避）
```

</details>

---

## 31. ツール比較 2026年版 - Cursor / Copilot / Aider / Windsurf / Cline / Kiro

### 31.1 ツールの位置づけ

2026年現在、AI コーディングツールは大きく3つのカテゴリに分かれる。

| カテゴリ | ツール | 特徴 |
|---------|-------|------|
| **ターミナルエージェント** | Claude Code、Aider、OpenCode | コードベース全体を対象に自律的に動作 |
| **AI 統合 IDE** | Cursor、Windsurf、Kiro | VS Code ベースで AI をエディタに深く統合 |
| **IDE プラグイン** | GitHub Copilot、Cline（Roo-Code） | 既存の IDE に後付けで AI を追加 |

---

### 31.2 主要ツールの詳細比較

#### Claude Code（Anthropic）

| 項目 | 詳細 |
|------|------|
| **タイプ** | ターミナルエージェント + IDE 拡張 |
| **料金** | Pro $20/月または API 従量課金 |
| **コンテキスト** | 200K〜1M トークン（Opus 4.6） |
| **強み** | 20+ ファイルの大規模変更、アーキテクチャ設計、コード品質 |
| **弱み** | IDE ではない（コンテキストスイッチ必要）、学習コスト高め |
| **適した作業** | リファクタリング、アーキテクチャ変更、複雑なバグ修正 |

#### Cursor

| 項目 | 詳細 |
|------|------|
| **タイプ** | AI 統合 IDE（VS Code フォーク） |
| **料金** | $20/月（Pro）、無料プランあり |
| **コンテキスト** | 実効 60〜80K トークン |
| **強み** | オートコンプリートが最高品質、UI が洗練されている、1〜10 ファイルの変更 |
| **弱み** | 大規模変更でのエージェントの幻覚、拡張機能との競合 |
| **適した作業** | 日常的なコーディング、小〜中規模のリファクタリング |

#### GitHub Copilot（Microsoft/GitHub）

| 項目 | 詳細 |
|------|------|
| **タイプ** | IDE プラグイン |
| **料金** | $10/月（個人）、$19/月（Business）|
| **コンテキスト** | 64K トークン |
| **強み** | VS Code / JetBrains との深い統合、GitHub との連携、Workspace 機能 |
| **弱み** | エージェント機能が他社より遅れている、大規模タスクに弱い |
| **適した作業** | GitHub Actions、既存ユーザーの日常コーディング補助 |

#### Aider

| 項目 | 詳細 |
|------|------|
| **タイプ** | ターミナルエージェント（OSS） |
| **料金** | 無料（BYOK: 自分の API キーを使用） |
| **コンテキスト** | 使用モデルに依存（Sonnet 4.6 で 200K） |
| **強み** | 完全無料・オープンソース、任意のモデルを使える、Git 統合が優秀 |
| **弱み** | UI がシンプル、設定の学習コストがある |
| **適した作業** | コスト重視のユーザー、ローカルモデルを使いたいケース |

#### Windsurf（Codeium）

| 項目 | 詳細 |
|------|------|
| **タイプ** | AI 統合 IDE（VS Code フォーク） |
| **料金** | $15/月（Pro）、無料プランあり |
| **コンテキスト** | Flows による持続的セッション |
| **強み** | 価格が最も安い、Cascade システムでの自然な協働、Multi-cursor |
| **弱み** | 1000+ ファイルのプロジェクトでパフォーマンス低下、拡張エコシステムが小さい |
| **適した作業** | コスト重視で IDE 型が欲しい場合、中規模プロジェクト |

#### Cline / Roo-Code（OSS）

| 項目 | 詳細 |
|------|------|
| **タイプ** | VS Code 拡張 |
| **料金** | 無料（BYOK） |
| **コンテキスト** | 使用モデルに依存 |
| **強み** | VS Code から離れない、任意のモデルを使える、活発なコミュニティ |
| **弱み** | 公式サポートなし、モデルの品質に依存 |
| **適した作業** | VS Code ユーザーでコストを抑えたい場合 |

#### Kiro（Amazon）

| 項目 | 詳細 |
|------|------|
| **タイプ** | AI 統合 IDE（VS Code ベース） |
| **料金** | 未公開（2025年7月リリース、プレビュー段階） |
| **コンテキスト** | セッションをまたいだ永続コンテキスト |
| **強み** | 「Spec-driven development」（仕様書→コード自動生成）、AWS/GitHub との深い統合、Amazon 社内での大規模実績 |
| **弱み** | AWS サービス以外との統合は限定的、2026年2月に AWS 障害を引き起こした事例あり |
| **適した作業** | AWS インフラと連携した開発、仕様書ドリブンの大規模プロジェクト |

---

### 31.3 機能比較マトリクス

2026年版のツール比較マトリクスです（A=優秀、B=良好、C=基本的）。

| 機能 | Claude Code | Cursor | Copilot | Aider | Windsurf | Cline | Kiro |
|------|:-----------:|:------:|:-------:|:-----:|:--------:|:-----:|:----:|
| 大規模リファクタリング（20+ ファイル） | A | B | C | B | C | B | B |
| インラインオートコンプリート | C | A | A | C | B | B | B |
| 自然言語でのコード生成 | A | A | B | A | A | A | A |
| Git 統合 | A | B | B | A | B | B | B |
| テスト生成 | A | B | B | A | B | B | B |
| コードベース質問応答 | A | B | C | B | B | B | B |
| デバッグ支援 | A | B | B | B | B | B | B |
| PR レビュー自動化 | A | C | B | C | C | C | B |
| カスタマイズ性 | A | B | C | A | B | A | B |
| コスト効率（重量ユーザー） | B | B | B | A | A | A | B |
| AWS/クラウド統合 | B | C | B | C | C | C | A |

（A=優秀、B=良好、C=基本的）

---

### 31.4 ツール選択ガイド

<details markdown="1">
<summary>31.4 ツール選択ガイド（テキスト）</summary>

```
どのツールを選ぶべきか？

質問 1: コストを最小化したい？
  → YES: Aider または Cline（BYOK で使用するモデルのコストのみ）
  → NO: 次の質問へ

質問 2: IDE の操作感を維持したい？
  → YES: Cursor（$20/月）または Windsurf（$15/月）
  → NO: 次の質問へ

質問 3: 20+ファイルの大規模変更が多い？
  → YES: Claude Code（Pro $20/月 または Max $100〜200/月）
  → NO: Cursor で日常作業 + Claude Code で大規模作業のハイブリッド

実際のプロ開発者の使い方:
- Copilot（日常）+ Claude Code（複雑なタスク）: $30〜40/月
- Cursor（メイン IDE）+ Claude Code（アーキテクチャ作業）: $40/月
- Windsurf（コスト重視）+ Aider（大規模変更）: $15/月〜（APIコスト別途）
```

</details>

---

### 31.5 2026年のトレンド

1. **ターミナルエージェントの台頭**: Cursor や Copilot などの IDE 型よりも、Claude Code や Aider のようなエージェント型が複雑なタスクで優位に立ってきている

2. **BYOK（Bring Your Own Key）の普及**: Cline、Aider などのオープンソースツールにより、任意のモデルを使えるエコシステムが成熟している

3. **ツールの組み合わせが主流**: 1つのツールに限定せず、タスクに応じて使い分けるハイブリッドアプローチが増えている

4. **モデルの汎化**: 各ツールが複数のモデルに対応しており、ツールとモデルの選択が分離しつつある

---

## 32. 大規模プロジェクト - モノレポ・複数言語・コンテキスト制限対策

### 32.1 大規模プロジェクトの課題

Claude Code のコンテキストウィンドウは最大 200K〜1M トークン（Opus 4.6 ベータ）だが、大規模プロジェクトでは以下の課題がある。

| 課題 | 症状 | 原因 |
|------|------|------|
| コンテキスト汚染 | Claude が以前の指示を「忘れる」 | コンテキストが関係ない情報で埋まる |
| スコープクリープ | 関係ないファイルを変更する | コードベース全体が見えると不必要に変更する |
| パフォーマンス低下 | 応答が遅くなる、指示を無視する | コンテキストウィンドウの末尾近くでは品質が落ちる |
| コスト増大 | API コストが予想外に高くなる | 大量のトークンを消費する |

---

### 32.2 モノレポの CLAUDE.md 設計

#### 階層構造による CLAUDE.md の分割

<details markdown="1">
<summary>階層構造による CLAUDE.md の分割（テキスト）</summary>

```
monorepo/
├── CLAUDE.md          # リポジトリ共通ルール（常に読み込まれる）
├── apps/
│   ├── frontend/
│   │   └── CLAUDE.md  # フロントエンド固有ルール
│   └── backend/
│       └── CLAUDE.md  # バックエンド固有ルール
└── packages/
    ├── ui/
    │   └── CLAUDE.md  # UI コンポーネントライブラリルール
    └── utils/
        └── CLAUDE.md  # ユーティリティパッケージルール
```

</details>

**ルート CLAUDE.md（共通ルール）**:

<details markdown="1">
<summary>ルート CLAUDE.md（共通ルール）**（Markdown）</summary>

```markdown
# monorepo/CLAUDE.md

## リポジトリ構成
- apps/frontend: React + TypeScript の Web アプリ
- apps/backend: Node.js + Express の API サーバー
- packages/ui: 共有 UI コンポーネント
- packages/utils: 共有ユーティリティ関数

## パッケージマネージャー
- pnpm を使用: `pnpm install`, `pnpm -r run build`
- ワークスペース: `pnpm --filter @myapp/frontend run dev`

## コミットルール
- Conventional Commits 形式
- スコープはパッケージ名を使う: feat(frontend):, fix(backend):

## 禁止事項
- ルートの package.json に直接依存関係を追加しない
- packages/ 配下から apps/ に直接 import しない
```

</details>

**フロントエンド固有 CLAUDE.md**:

<details markdown="1">
<summary>フロントエンド固有 CLAUDE.md**（Markdown）</summary>

```markdown
# apps/frontend/CLAUDE.md

## 技術スタック
- React 18, TypeScript, Vite, Tailwind CSS
- 状態管理: Zustand
- テスト: Vitest + React Testing Library

## コンポーネントルール
- コンポーネントは packages/ui から import する
- ローカルの UI コンポーネントは src/components/ に置く
- ページコンポーネントは src/pages/ に置く

## テストコマンド
- 単一: `pnpm test -- src/components/Button.test.tsx`
- 全体: `pnpm test`
- カバレッジ: `pnpm test:coverage`
```

</details>

---

### 32.3 コンテキスト制限への対策

#### 対策 1: 作業前にスコープを明示する

<details markdown="1">
<summary>対策 1: 作業前にスコープを明示する（テキスト）</summary>

```
作業スコープを宣言してください：
- 作業対象: apps/backend/src/auth/ のみ
- 参照可能: packages/utils/src/crypto.ts
- 変更禁止: apps/frontend/, packages/ui/

このスコープを厳守して、JWT 認証の実装を行ってください
```

</details>

#### 対策 2: /clear を積極的に使う

<details markdown="1">
<summary>対策 2: /clear を積極的に使う（テキスト）</summary>

```
# タスクとタスクの間には必ず /clear を使う
/clear

# 新しいタスクには必要なコンテキストを明示して再開する
> apps/backend の payment サービスを修正します。
> @apps/backend/src/services/payment.ts と
> @apps/backend/src/__tests__/payment.test.ts を読んでから始めてください
```

</details>

#### 対策 3: サブエージェントで調査を分離する

<details markdown="1">
<summary>対策 3: サブエージェントで調査を分離する（テキスト）</summary>

```
サブエージェントを使って以下を調査してください：
1. apps/backend で使われている全てのデータベース接続パターン
2. packages/utils に移動できそうな重複コード
3. TypeScript の型エラーが出ているファイル一覧

調査結果のサマリーだけを返してください（コードの中身は不要）
```

</details>

#### 対策 4: claudeMdExcludes を使う

`.claude/settings.json` で不要なディレクトリの CLAUDE.md を除外できる。

<details markdown="1">
<summary>`.claude/settings.json` で不要なディレクトリの CLAUDE.md を除外できる。（JSON）</summary>

```json
{
  "claudeMdExcludes": [
    "legacy/**",
    "node_modules/**",
    "archived/**"
  ]
}
```

</details>

#### 対策 5: コンテキスト使用量の監視

ステータスラインでリアルタイムにコンテキスト使用量を監視する（15章参照）。

<details markdown="1">
<summary>ステータスラインでリアルタイムにコンテキスト使用量を監視する（15章参照）。（Bash）</summary>

```bash
# .claude/statusline.sh の例（コンテキスト使用率を表示）
#!/bin/bash
CONTEXT_USAGE="${CLAUDE_CONTEXT_TOKENS_USED:-0}"
CONTEXT_MAX="${CLAUDE_CONTEXT_TOKENS_MAX:-200000}"
PERCENT=$((CONTEXT_USAGE * 100 / CONTEXT_MAX))

if [ $PERCENT -gt 80 ]; then
  echo "CONTEXT: ${PERCENT}% [WARNING: /compact を実行してください]"
else
  echo "CONTEXT: ${PERCENT}%"
fi
```

</details>

---

### 32.4 複数言語プロジェクトの設定

#### ポリグロットなモノレポの例

<details markdown="1">
<summary>ポリグロットなモノレポの例（テキスト）</summary>

```
fullstack-app/
├── backend/          Python (FastAPI)
├── frontend/         TypeScript (React)
├── mobile/           Swift (iOS) + Kotlin (Android)
├── ml/               Python (PyTorch)
└── infra/            HCL (Terraform)
```

</details>

**ルート CLAUDE.md でポリシーを統一**:

<details markdown="1">
<summary>ルート CLAUDE.md でポリシーを統一**（Markdown）</summary>

```markdown
# fullstack-app/CLAUDE.md

## 言語別コーディング規約
- Python: Black フォーマット, mypy 型チェック, pytest
- TypeScript: Prettier, ESLint, Vitest
- Swift: SwiftLint, XCTest
- Kotlin: ktlint, JUnit
- HCL: terraform fmt, tflint

## 共通ルール
- API 定義は openapi/schema.yaml で管理（全言語で共有）
- 環境変数は .env.example に必ず記載する
- 全ての変更にはテストを追加すること

## 言語別テストコマンド
- Python: `cd backend && pytest`
- TypeScript: `cd frontend && npm test`
- Mobile: Xcode でテスト実行
```

</details>

---

### 32.5 大規模マイグレーションの実行

#### fan-out パターン（並列処理）

<details markdown="1">
<summary>fan-out パターン（並列処理）（Bash）</summary>

```bash
#!/bin/bash
# 大規模ファイル変換の例: React Class コンポーネント → Function コンポーネント

# ステップ 1: 対象ファイルリストを生成
claude -p "apps/frontend/src で React.Component を継承している全ファイルをリストアップしてください" \
  --output-format json > class-components.json

# ステップ 2: 各ファイルを並列で変換
cat class-components.json | jq -r '.[]' | while read file; do
  claude -p "
    $file を React Function コンポーネントに変換してください。
    要件:
    - useState, useEffect 等の Hooks を使う
    - Props の型定義は維持する
    - 変換後に TypeScript エラーがないことを確認する
    変換できたら OK、できなかったら SKIP と返してください
  " \
  --allowedTools "Read,Edit,Bash(npx tsc --noEmit)" \
  --output-format json &
done

wait
echo "全ファイルの変換完了"
```

</details>

#### 段階的マイグレーション

<details markdown="1">
<summary>段階的マイグレーション（テキスト）</summary>

```
大規模なデータベーススキーマ変更を行います。
一度に全部変更せず、以下の順序で段階的に進めてください：

フェーズ 1（今回）: users テーブルに新しいカラムを追加（後方互換）
フェーズ 2（次回）: 新カラムを使うように API を更新
フェーズ 3（翌週）: 古いカラムを参照しているコードを全て更新
フェーズ 4（その後）: 古いカラムを削除

現在はフェーズ 1 のみを実行してください。
フェーズ 2 以降のための TODO コメントを残してください
```

</details>

---

### 32.6 MCP を使ったコードベース検索の強化

大規模コードベースでは MCP（Model Context Protocol）サーバーを使ったセマンティック検索が効果的である。

<details markdown="1">
<summary>コード例（Bash）</summary>

```bash
# Zilliz Claude Context MCP サーバーのインストール（コードベースのセマンティック検索）
claude mcp add zilliz-code-search

# 使用例
> MCP ツールを使って、エラーハンドリングが不足している箇所を
> コードベース全体から検索してください（grep ではなくセマンティック検索を使う）
```

</details>

---

### 32.7 大規模プロジェクトのベストプラクティスまとめ

<details markdown="1">
<summary>32.7 大規模プロジェクトのベストプラクティスまとめ（Markdown）</summary>

```markdown
# 大規模プロジェクト作業時のチェックリスト

## セッション開始時
- [ ] 作業するディレクトリから claude を起動したか
- [ ] 作業スコープを CLAUDE.md または プロンプトで明示したか
- [ ] 前回のセッションが残っている場合は /clear したか

## 作業中
- [ ] コンテキスト使用率が 80% を超えていないか（超えたら /compact）
- [ ] 関係ないファイルを読み込んでいないか
- [ ] 変更対象以外のファイルを変更していないか

## タスク完了時
- [ ] テストが全て通っているか
- [ ] TypeScript/リントエラーがないか
- [ ] 変更したファイルの一覧を確認したか
- [ ] コミットとブランチ名が規約に従っているか

## 定期的に
- [ ] CLAUDE.md が最新の状態か（新しい規約や FAQ を反映）
- [ ] .claude/settings.json のフックが機能しているか
- [ ] 不要になったスキルや設定を削除したか
```

</details>

---

[^25]: [Claude Code Setup - Anthropic 公式](https://code.claude.com/docs/ja/setup)
[^26]: [Prompt Engineering Best Practices - Anthropic 公式](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
[^27]: [Claude AI Pricing 2026 - Global GPT](https://www.glbgpt.com/hub/claude-ai-pricing-2026-the-ultimate-guide-to-plans-api-costs-and-limits/)
[^28]: [Git Integration - SFEIR Institute](https://institute.sfeir.com/en/claude-code/claude-code-git-integration/)
[^29]: [Forcing Claude Code to TDD - alexop.dev](https://alexop.dev/posts/custom-tdd-workflow-claude-code-vue/)
[^30]: [Cursor vs Windsurf vs Claude Code 2026 - DEV Community](https://dev.to/pockit_tools/cursor-vs-windsurf-vs-claude-code-in-2026-the-honest-comparison-after-using-all-three-3gof)
[^31]: [Claude Code Monorepo Best Practices - DEV Community](https://dev.to/anvodev/how-i-organized-my-claudemd-in-a-monorepo-with-too-many-contexts-37k7)
[^32]: [Manage Claude Context in Large Projects - Arsturn](https://www.arsturn.com/blog/how-to-actually-manage-context-in-large-coding-projects-with-claude)
