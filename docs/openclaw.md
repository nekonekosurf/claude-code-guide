---
layout: default
title: OpenClaw ガイド
---

# OpenClaw - オープンソースAIエージェント完全ガイド

## 目次

- [OpenClawとは](#openclawとは)
- [歴史と背景](#歴史と背景)
- [主な機能と特徴](#主な機能と特徴)
- [アーキテクチャ](#アーキテクチャ)
- [インストールとセットアップ](#インストールとセットアップ)
- [スキルエコシステム](#スキルエコシステム)
- [Claude Codeとの比較](#claude-codeとの比較)
- [セキュリティとプライバシー](#セキュリティとプライバシー)
- [NanoClaw（軽量代替）](#nanoclaw軽量代替)
- [ユースケース](#ユースケース)
- [メリットとデメリット](#メリットとデメリット)
- [リンクとリソース](#リンクとリソース)

---

## OpenClawとは

OpenClaw（旧称: Clawdbot / Moltbot）は、**無料・オープンソースの自律型AIエージェント**である。自分のマシン上で動作し、WhatsApp、Telegram、Slack、Discord、Signal、iMessage、Microsoft Teamsなど、日常的に使うメッセージングアプリからAIに指示を出せる「パーソナルAIアシスタント」として設計されている。

Claude、GPT、Gemini、DeepSeek、Llamaなど複数のLLMに対応し、メール管理、カレンダー操作、ファイル操作、ブラウザ自動化、シェルコマンド実行、リマインダー設定など、幅広いタスクを自律的に実行できる。

2026年1月末のリリース後、**1週間で10万GitHub Stars**を獲得し、GitHub史上最速で成長したオープンソースリポジトリの一つとなった。

---

## 歴史と背景

### 開発者: Peter Steinberger

OpenClawの開発者はオーストリア出身のソフトウェアエンジニア **Peter Steinberger** 氏。PDF SDK企業「PSPDFKit」を13年間経営した後、2025年4月にAIの「パラダイムシフト」を実感し、AIエージェント開発に転向した。

### 名称変遷

| 時期 | 名称 | 経緯 |
|------|------|------|
| 2025年11月 | **Clawdbot** | Anthropicのチャットボット「Claude」にちなんで命名、GitHub公開 |
| 2026年1月27日 | **Moltbot** | Anthropicからの商標に関する指摘を受けて改名（ロブスターテーマは継続） |
| 2026年1月30日 | **OpenClaw** | 3日後に再度改名し現在の名称に |

### その後の展開

- 2026年1月末: Moltbookプロジェクトの人気もあり爆発的にバイラル化
- 2026年2月14日: Steinberger氏がOpenAIに入社、プロジェクトはオープンソース財団に移管すると発表
- Sam AltmanやMark Zuckerbergの関心を集める

---

## 主な機能と特徴

### コア機能

- **メール管理**: 受信トレイの自動トリアージ、返信ドラフト作成、日次サマリー
- **カレンダー管理**: スケジュール確認、予定作成・変更
- **メッセージング**: 12以上のプラットフォームに対応（WhatsApp、Telegram、Slack等）
- **ブラウザ自動化**: Web操作、情報収集
- **ファイル操作**: ローカルファイルの作成・編集・管理
- **シェルコマンド実行**: ターミナルコマンドの実行
- **スマートホーム制御**: IoTデバイスの操作
- **フライトチェックイン**: 航空会社への自動チェックイン

### 技術的特徴

- **永続メモリ**: セッション間でメモリが持続（数週間にわたり記憶を保持）
- **ハートビートスケジューラ**: 定期的にタスクを自動実行
- **マルチチャネルセッション管理**: 複数のメッセージングプラットフォームを横断
- **50以上のインテグレーション**: 多様なサービスとの接続
- **セルフホスト**: データは自分のマシンに保持（SaaS型ではない）

---

## アーキテクチャ

OpenClawのアーキテクチャは、AIエージェントの基本パターン（エージェントループ、ツール使用、コンテキスト注入、永続メモリ）をクリーンに実装したものである。

### 主要設定ファイル

| ファイル | 役割 |
|----------|------|
| **SOUL.md** | エージェントの「魂」。性格、価値観、長期的な指示を定義。起動時に最初に読み込まれる |
| **HEARTBEAT.md** | プロアクティブなタスク実行スケジュール。30分ごとに起動し、自動的にタスクを実行 |
| **AGENTS.md** | エージェントへの指示を格納 |
| **TOOLS.md** | 利用可能なツール・能力を定義 |
| **IDENTITY.md** | エージェントの表示名やアバター等のプレゼンテーション設定 |
| **USER.md** | ユーザーのコンテキスト情報 |
| **MEMORY.md** | 永続メモリストレージ |

### SOUL.md の役割

SOUL.mdはOpenClawのメモリアーキテクチャの基盤であり、エージェントの一貫した振る舞いを保証する。記述が具体的であるほど、エージェントの動作が安定する。

### HEARTBEAT.md の役割

ハートビートメカニズムにより、OpenClawは「リアクティブ」ではなく「プロアクティブ」に動作する。30分ごとに起動し、エージェントのファイルを読み通して「ユーザーのために何かすべきことがあるか」を判断する。

---

## インストールとセットアップ

### 前提条件

- **Node.js 22** 以上（必須。それ以前のバージョンではエラーが発生）
- 対応OS: macOS、Linux、Windows（WSL2経由）
- AIプロバイダーのAPIキー（Anthropic推奨）

### インストール手順

#### 1. オンボーディングウィザード（推奨）

```bash
openclaw onboard --install-daemon
```

ウィザードに従い以下を設定:
- ゲートウェイの設定
- ワークスペースの設定
- チャネル（メッセージングアプリ）の接続
- スキルのインストール

#### 2. Docker Compose を使用する場合

```bash
# docker-setup.sh を使用
docker compose up -d
```

#### 3. クラウドデプロイ

- DigitalOcean 1-Click Deploy が利用可能
- Cloudflare Workers 上での実行も可能（`cloudflare/moltworker`）

### 管理UI

インストール後、以下のURLでコントロールUIにアクセスできる:

```
http://127.0.0.1:18789/
```

ここでエージェントの監視、メモリの確認、スキル管理、設定変更が可能。

### 所要時間

Node.jsのダウンロードから最初のメッセージ送信まで、**約15〜20分**。

---

## スキルエコシステム

### ClawHub

OpenClawには **ClawHub** というスキルレジストリがあり、2026年2月末時点で **13,729以上** のコミュニティ製スキルが公開されている。

スキルはモジュール式の機能パッケージで、API呼び出し、データベースクエリ、ドキュメント取得、ワークフロー実行などを再利用可能なコンポーネントとしてパッケージ化したもの。

### スキルの例

- メッセージングプラットフォーム連携
- 暗号通貨取引ボット
- 生産性ユーティリティ
- API連携ツール

### セキュリティ上の注意

ClawHubは誰でもスキルを公開できるため、悪意あるスキルの混入リスクがある。セキュリティ企業 Koi Security の監査では、2,857スキル中 **341個が悪意あるスキル** と判定された（うち335個は単一の組織的キャンペーンに遡る）。

---

## Claude Codeとの比較

### 基本的な違い

| 項目 | OpenClaw | Claude Code |
|------|----------|-------------|
| **種別** | 汎用パーソナルAIエージェント | コーディング特化CLI |
| **動作環境** | メッセージングアプリ経由 | ターミナル内 |
| **主な用途** | 日常業務の自動化（メール、カレンダー等） | コード開発・リファクタリング |
| **メモリ** | 永続メモリ（数週間保持） | セッション単位（リセット） |
| **LLM** | 複数対応（Claude, GPT, Gemini等） | Claude専用（Opus 4.6等） |
| **コスト** | 本体無料（API費用のみ） | サブスクリプション or API費用 |
| **セキュリティ** | 自己管理（脆弱性報告多数） | Anthropic管理のサンドボックス環境 |
| **オープンソース** | はい | いいえ |

### 使い分け

- **コーディングが主な課題** → **Claude Code** が優位。Opus 4.6の推論能力とContext Compactionにより、複雑なリファクタリングでもコードを壊すリスクが低い
- **日常タスクの自動化が主な課題** → **OpenClaw** が優位。メール、会議、メッセージ、リマインダーなど多数の小タスクを処理できる

### セキュリティモデルの違い

Claude Codeはサンドボックス環境で動作し、権限が明示的かつ細粒度で管理される。Anthropicが専任のセキュリティインフラを維持し、定期監査を実施している。

OpenClawはシェルアクセス、ブラウザ制御、メール送信をループ内で自律的に実行できる強力さを持つが、攻撃対象面が広く、プロジェクトはまだ若い。

---

## セキュリティとプライバシー

### 報告された脆弱性

| CVE | 深刻度 | 内容 |
|-----|--------|------|
| CVE-2026-25253 | CVSS 8.8 (高) | WebSocketオリジンヘッダーバイパスによるリモートコード実行 |
| CVE-2026-25157 | 高 | コマンドインジェクション |
| CVE-2026-24763 | 高 | コマンドインジェクション |
| その他6件 | 各種 | SSRF、認証欠如、パストラバーサル |

### 主なリスク

1. **資格情報の漏洩**: 露出したインスタンスから認証情報やデータが流出する可能性
2. **プロンプトインジェクション**: LLMを騙してガードレールを回避させ、データ漏洩やバックドア設置、システム破壊を実行させる攻撃
3. **メモリ汚染**: エージェントの永続状態を改ざんし、攻撃者の指示に従わせる
4. **悪意あるスキル**: ClawHubの341個の悪意あるスキルが情報窃取マルウェアを配信
5. **40,000以上の露出インスタンス**: 設定不備によりインターネットに公開されたインスタンスが多数存在

### 各組織の評価

- **Palo Alto Networks**: 「2026年最大の内部脅威になり得る」
- **Cisco**: サードパーティスキルがユーザーの認知なしにデータ窃取とプロンプトインジェクションを実行することを確認
- **オランダデータ保護局**: 機密データを扱うシステムへのデプロイを警告
- **Malwarebytes**: 安全に使用するための詳細ガイドを公開
- **AI研究者 Gary Marcus**: 「起こるべくして起こる災害」

### 安全に使用するための推奨事項

- 専用の仮想マシンまたは分離された物理システムで実行
- 特権のない専用の資格情報を使用
- 非機密データのみにアクセスを制限
- ClawHubのスキルは慎重に監査してからインストール
- 最新バージョンへの更新を常に維持

---

## NanoClaw（軽量代替）

### 概要

**NanoClaw** は、OpenClawのセキュリティ問題を解決するために設計された軽量代替プロジェクト。コンテナ内で動作し、Anthropic Agent SDKを直接使用する。

### OpenClawとの違い

| 項目 | OpenClaw | NanoClaw |
|------|----------|----------|
| 実行環境 | ホスト上で直接実行 | コンテナ内で分離実行 |
| ベース | 独自実装 | Anthropic Agent SDK |
| 拡張方法 | ClawHub経由でスキル追加 | Claude Codeスキル（`.claude/skills/`） |
| セキュリティ | 課題あり | コンテナによる分離で強化 |
| 設計思想 | 機能豊富 | ミニマル |

NanoClaw はスキルの追加も `/add-telegram` のようなClaude Codeスキルを通じて行う「AI-native」な設計となっている。

---

## ユースケース

### 個人向け

- **受信トレイゼロ**: メールの自動トリアージ、返信ドラフト、日次ダイジェスト
- **スケジュール管理**: カレンダーの確認、予定の作成・リマインダー
- **旅行**: フライトチェックイン、旅程管理
- **情報収集**: 定期的なニューススキャン、要約作成
- **スマートホーム**: IoTデバイスの音声/テキスト制御

### 開発者向け

- ファイル操作、シェルコマンド実行
- コードレビュー支援
- API連携の自動化
- 定期タスクの自動実行

### ビジネス向け

- チーム間のコミュニケーション自動化
- レポート生成の自動化
- データ収集と分析の定期実行

---

## メリットとデメリット

### メリット

- **完全オープンソース・無料**: 本体のコストはゼロ（API費用のみ）
- **セルフホスト**: データが自分の管理下にある（SaaSにデータを渡さない）
- **マルチLLM対応**: Claude、GPT、Gemini、DeepSeek、Llama等を自由に選択
- **マルチプラットフォーム**: 12以上のメッセージングアプリから利用可能
- **永続メモリ**: コンテキストがセッション間で保持される
- **プロアクティブ動作**: ハートビートにより能動的にタスクを実行
- **豊富なスキルエコシステム**: 13,000以上のコミュニティ製スキル
- **カスタマイズ性**: SOUL.mdで性格や動作を細かく制御

### デメリット

- **重大なセキュリティリスク**: 複数のCVEが報告されており、攻撃対象面が広い
- **プライバシー懸念**: メール、カレンダー等の機密情報へのアクセス権限が必要
- **プロンプトインジェクション脆弱性**: LLMベースのエージェント固有のリスク
- **悪意あるスキルの存在**: ClawHubの品質管理が不十分
- **セットアップの複雑さ**: APIキー設定、チャネル接続等の初期設定が必要
- **API費用**: 本体は無料だがLLMのAPI費用が発生（トークン消費が大きい）
- **プロジェクトの若さ**: 2025年11月公開、まだ安定性に課題
- **創設者の離脱**: Peter SteinbergerがOpenAIに移籍、プロジェクトの今後に不確実性

---

## リンクとリソース

### 公式

- [OpenClaw公式サイト](https://openclaw.ai/)
- [GitHub - openclaw/openclaw](https://github.com/openclaw/openclaw)
- [OpenClaw公式ドキュメント](https://docs.openclaw.ai/)
- [OpenClaw紹介ブログ](https://openclaw.ai/blog/introducing-openclaw)

### ガイド・チュートリアル

- [How to Install OpenClaw (2026) - Medium](https://medium.com/@guljabeen222/how-to-install-openclaw-2026-the-complete-step-by-step-guide-516b74c163b9)
- [What is OpenClaw - Milvus Blog](https://milvus.io/blog/openclaw-formerly-clawdbot-moltbot-explained-a-complete-guide-to-the-autonomous-ai-agent.md)
- [OpenClaw AI Agent Masterclass - HelloPM](https://hellopm.co/openclaw-ai-agent-masterclass/)
- [DigitalOceanでOpenClawを実行する方法](https://www.digitalocean.com/community/tutorials/how-to-run-openclaw)

### 比較・分析

- [OpenClaw vs Claude Code - DataCamp](https://www.datacamp.com/blog/openclaw-vs-claude-code)
- [OpenClaw vs Claude Code - Unite.AI](https://www.unite.ai/openclaw-vs-claude-code-remote-control-agents/)
- [The Ultimate Guide to AI Agents in 2026 - DEV Community](https://dev.to/tech_croc_f32fbb6ea8ed4/the-ultimate-guide-to-ai-agents-in-2026-openclaw-vs-claude-cowork-vs-claude-code-395h)

### セキュリティ

- [Running OpenClaw safely - Microsoft Security Blog](https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/)
- [OpenClaw Security - CrowdStrike](https://www.crowdstrike.com/en-us/blog/what-security-teams-need-to-know-about-openclaw-ai-super-agent/)
- [OpenClaw Security Risks - Bitsight](https://www.bitsight.com/blog/openclaw-ai-security-risks-exposed-instances)
- [OpenClaw: What is it and can you use it safely? - Malwarebytes](https://www.malwarebytes.com/blog/news/2026/02/openclaw-what-is-it-and-can-you-use-it-safely)
- [Personal AI Agents like OpenClaw Are a Security Nightmare - Cisco](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare)

### 関連プロジェクト

- [NanoClaw - GitHub](https://github.com/qwibitai/nanoclaw) - 軽量・セキュア版の代替
- [IronClaw - GitHub](https://github.com/nearai/ironclaw) - Rust実装版（プライバシー・セキュリティ重視）
- [ClawSec - GitHub](https://github.com/prompt-security/clawsec) - セキュリティスキルスイート
- [Awesome OpenClaw Skills](https://github.com/VoltAgent/awesome-openclaw-skills) - 5,400以上のスキルコレクション

### メディア

- [OpenClaw - Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [Peter Steinberger - Lex Fridman Podcast #491](https://lexfridman.com/peter-steinberger-transcript/)
- [OpenClaw creator Peter Steinberger joins OpenAI - TechCrunch](https://techcrunch.com/2026/02/15/openclaw-creator-peter-steinberger-joins-openai/)
- [Who is OpenClaw creator Peter Steinberger? - Fortune](https://fortune.com/2026/02/19/openclaw-who-is-peter-steinberger-openai-sam-altman-anthropic-moltbook/)

---

*最終更新: 2026年3月1日*
