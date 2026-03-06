---
layout: default
title: "Claude Code 活用ガイド - 基礎編（章1〜5）"
---

[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)

---



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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

---

[次: 設定編 →](config)
