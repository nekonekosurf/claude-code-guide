---
layout: default
title: "Claude Code 活用ガイド - 設定編（章6〜10）"
---
{% raw %}

[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)

---


## 6. MCP サーバー連携

### 6.1 MCP とは

MCP（Model Context Protocol）は AI ツール統合のためのオープンソース標準である。MCP サーバーを接続することで、Claude Code から外部ツール、データベース、API にアクセスできる [^9]。

### 6.2 MCP サーバーの追加方法

#### HTTP サーバー（推奨）

<details>
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

### 6.3 人気の MCP サーバー

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

<details>
<summary>| `user` | `~/.claude.json` | 個人・全プロジェクト |（Bash）</summary>

```bash
# プロジェクトスコープで追加
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp

# ユーザースコープで追加
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

</details>

### 6.5 MCP 管理コマンド

<details>
<summary>6.5 MCP 管理コマンド（Bash）</summary>

```bash
claude mcp list              # 一覧表示
claude mcp get github        # 詳細確認
claude mcp remove github     # 削除
/mcp                         # Claude Code 内でステータス確認・OAuth認証
```

</details>

### 6.6 `.mcp.json` での環境変数展開

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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
| `"ultrathink"` | 約32K | 複雑なアーキテクチャ決定、深い分析 |

> **注意**: 2026年現在、extended thinking はデフォルトで有効になっており、`/effort` コマンドで低/中/高/最大を制御できる [^11]。

### 8.2 探索 → 計画 → 実装 → コミットの4フェーズ

<details>
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

<details>
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

<details>
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

<details>
<summary>セッションの再開（Bash）</summary>

```bash
claude --continue    # 最新の会話を再開
claude --resume      # 最近のセッションから選択
/rename              # セッションに名前を付ける（例: "oauth-migration"）
```

</details>

### 8.5 サブエージェントの活用

コンテキストが最も重要なリソースであるため、サブエージェントの活用が強力：

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

<details>
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

---

[← 前: 基礎編](basics) | [次: 応用編 →](advanced)
{% endraw %}
