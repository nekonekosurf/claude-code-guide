---
layout: default
title: "Claude Code 活用ガイド - 応用編（章11〜17）"
---

[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)

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


```json
// settings.json（古いバージョンでは環境変数が必要な場合がある）
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
# Shift+Tab でプランモードに切り替え（Normal → Plan → Auto-Accept のサイクル）
# または /plan コマンドでプランモードに入る
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

マーケットプレイスで特に人気のあるプラグインカテゴリを紹介します。

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

---

[← 前: 設定編](config) | [次: チーム編 →](team)
