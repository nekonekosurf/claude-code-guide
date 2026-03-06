---
layout: default
title: Home
---

# Claude Code マスターガイド

Claude Code の使い方・設定・Tips を網羅した包括的リファレンスです。

> **最終更新: 2026年3月7日**

Claude Code は Anthropic が提供するエージェント型コーディング環境です。ファイルの読み書き、コマンド実行、コード変更を自律的に行い、「何を作りたいか」を記述するだけで、コードベースの探索から実装まで一貫して処理します。

---

## ガイド一覧

<div class="nav-card" markdown="1">

### 📖 Claude Code 活用ガイド

| セクション | 内容 |
|---|---|
| [基礎編（章1〜5）](guide/basics) | はじめに、CLAUDE.md、エージェント、スキル、フック |
| [設定編（章6〜10）](guide/config) | MCP、権限、ワークフロー、コスト、IDE |
| [応用編（章11〜17）](guide/advanced) | トラブルシューティング、高度な使い方、プラグイン |
| [チーム編（章18〜24）](guide/team) | エコシステム、ツール比較、CI/CD、Agent SDK |
| [上級編（章25〜32）](guide/expert) | チュートリアル、プロンプト、TDD、デバッグ |

</div>

<div class="nav-card" markdown="1">

### 🔧 ローカルLLM構築ガイド

| セクション | 内容 |
|---|---|
| [基礎・設計編（章1〜5）](build/foundations) | はじめに、アーキテクチャ、技術スタック、vLLM、コアエージェント |
| [機能編A（章6〜8）](build/features) | Extended Thinking、マルチモデルルーティング、Agent Teams |
| [ファインチューニング（章9）](build/finetuning) | ファインチューニングと学習（専門知識の習得） |
| [機能編B（章10〜11）](build/features2) | RAG、高度な検索技法 |
| [運用・最適化編（章12〜15）](build/operations) | コスト、セキュリティ、メモリ管理、ロードマップ |
| [専門技術編（章16〜19 + 付録）](build/specialist) | Embedding Fine-tuning、学習 vs エージェント、Human-in-the-Loop |

</div>

---

<details markdown="1">
<summary>📖 活用ガイド全32章の目次</summary>

#### 基礎編

| 章 | 内容 |
|---|---|
| [1. はじめに](guide/basics#1-はじめに) | Claude Code の核心的な原則、コンテキストウィンドウ管理 |
| [2. CLAUDE.md の書き方と活用](guide/basics#2-claudemd-の書き方と活用) | 階層構造、効果的な書き方、実践例 |
| [3. カスタムエージェント](guide/basics#3-カスタムエージェント-claudeagents) | `.claude/agents/` によるエージェント定義 |
| [4. スキル](guide/basics#4-スキル-claudeskills) | `.claude/skills/` によるスキル定義 |
| [5. フック](guide/basics#5-フック-claudehooks) | `.claude/hooks/` によるイベント駆動処理 |

#### 連携・設定編

| 章 | 内容 |
|---|---|
| [6. MCP サーバー連携](guide/config#6-mcp-サーバー連携) | Model Context Protocol によるツール拡張 |
| [7. 権限・セキュリティ設定](guide/config#7-権限セキュリティ設定) | 許可ルール、セキュリティモデル |
| [8. ワークフロー・使い方 Tips](guide/config#8-ワークフロー使い方-tips) | 実践的な活用テクニック |
| [9. パフォーマンス・コスト最適化](guide/config#9-パフォーマンスコスト最適化) | トークン削減、効率化手法 |
| [10. IDE 連携](guide/config#10-ide-連携) | VS Code、JetBrains との統合 |

#### 応用編

| 章 | 内容 |
|---|---|
| [11. トラブルシューティング](guide/advanced#11-トラブルシューティング) | よくある問題と解決策 |
| [12. 高度な使い方](guide/advanced#12-高度な使い方) | マルチエージェント、CI/CD統合 |
| [13. プラグイン](guide/advanced#13-プラグイン) | プラグインシステムの活用 |
| [14. サンドボックス](guide/advanced#14-サンドボックス) | 安全な実行環境 |
| [15. ステータスライン](guide/advanced#15-ステータスライン) | ステータス表示のカスタマイズ |
| [16. 実際のユースケース・事例](guide/advanced#16-実際のユースケース事例) | 実プロジェクトでの活用事例 |
| [17. 情報源・参考リンク](guide/advanced#17-情報源参考リンク) | 公式ドキュメント、コミュニティリソース |

#### チーム・セキュリティ編

| 章 | 内容 |
|---|---|
| [18. エコシステム連携](guide/team#18-エコシステム連携---mcp-サーバー詳説ide-統合) | MCP サーバー詳説・IDE 統合 |
| [19. ツール比較](guide/team#19-ツール比較---claude-code-vs-cursor-vs-copilot-vs-aider) | Claude Code vs Cursor vs Copilot vs Aider |
| [20. CI/CD 統合](guide/team#20-cicd-統合---github-actions自動レビュー) | GitHub Actions・自動レビュー |
| [21. チーム開発](guide/team#21-チーム開発---claudemd-共有コードレビュー) | CLAUDE.md 共有・コードレビュー |
| [22. セキュリティ](guide/team#22-セキュリティ---パーミッション機密情報サンドボックス) | パーミッション・機密情報・サンドボックス |
| [23. Agent SDK](guide/team#23-agent-sdk---カスタムエージェント構築) | カスタムエージェント構築 |
| [24. FAQ・トラブルシューティング詳説](guide/team#24-faqトラブルシューティング詳説) | よくある質問と詳細な解決策 |

#### 実践・上級編

| 章 | 内容 |
|---|---|
| [25. 初心者チュートリアル](guide/expert#25-初心者チュートリアル---インストールから初回利用まで) | インストールから初回利用まで |
| [26. プロンプトエンジニアリング](guide/expert#26-プロンプトエンジニアリング---効果的な指示の出し方) | 効果的な指示の出し方 |
| [27. 料金・プラン完全ガイド](guide/expert#27-料金プラン完全ガイド) | プラン比較、コスト管理 |
| [28. Git 連携詳細](guide/expert#28-git-連携詳細---ブランチマージpr-レビュー) | ブランチ・マージ・PR レビュー |
| [29. TDD 連携](guide/expert#29-tdd-連携---テスト駆動開発ワークフロー) | テスト駆動開発ワークフロー |
| [30. デバッグ機能](guide/expert#30-デバッグ機能---エラー解析ログ分析) | エラー解析・ログ分析 |
| [31. ツール比較 2026年版](guide/expert#31-ツール比較-2026年版---cursor--copilot--aider--windsurf--cline) | Cursor / Copilot / Aider / Windsurf / Cline |
| [32. 大規模プロジェクト](guide/expert#32-大規模プロジェクト---モノレポ複数言語コンテキスト制限対策) | モノレポ・複数言語・コンテキスト制限対策 |

</details>

<details markdown="1">
<summary>🔧 構築ガイド全19章の目次</summary>

#### 基礎・設計編

| 章 | 内容 |
|---|---|
| [1. はじめに](build/foundations#1-はじめに) | ローカルLLMエージェント構築の目的と概要 |
| [2. アーキテクチャ概要](build/foundations#2-アーキテクチャ概要) | システム全体の設計と構成要素 |
| [3. 技術スタック選択](build/foundations#3-技術スタック選択) | フレームワーク・ライブラリの選定基準 |
| [4. vLLMセットアップ](build/foundations#4-vllmセットアップ) | vLLM によるモデルサーバー構築手順 |
| [5. コアエージェント実装](build/foundations#5-コアエージェント実装) | エージェントのコア機能実装 |

#### 高度な機能編

| 章 | 内容 |
|---|---|
| [6. Extended Thinking（深い推論）](build/features#6-extended-thinking深い推論) | 多段階推論・思考チェーンの実装 |
| [7. マルチモデルルーティング](build/features#7-マルチモデルルーティング) | 複数モデルの動的切り替え |
| [8. サブエージェント・Agent Teams](build/features#8-サブエージェントagent-teams) | マルチエージェント協調システム |
| [9. ファインチューニングと学習](build/finetuning#9-ファインチューニングと学習専門知識の習得) | 専門知識の習得・モデルカスタマイズ |
| [10. RAG（検索拡張生成）](build/features2#10-rag検索拡張生成) | ベクトル検索によるコンテキスト強化 |
| [11. 高度な検索技法](build/features2#11-高度な検索技法) | ハイブリッド検索・再ランキング |

#### 運用・最適化編

| 章 | 内容 |
|---|---|
| [12. 費用・コスト](build/operations#12-費用コスト) | ハードウェア・クラウドのコスト試算 |
| [13. セキュリティ・サンドボックス](build/operations#13-セキュリティサンドボックス) | 安全な実行環境の構築 |
| [14. セッション・メモリ管理](build/operations#14-セッションメモリ管理) | 会話履歴・長期記憶の実装 |
| [15. 実装ロードマップ](build/operations#15-実装ロードマップ) | フェーズ別の実装計画 |

#### 専門技術編

| 章 | 内容 |
|---|---|
| [16. Embedding Fine-tuning](build/specialist#16-embedding-fine-tuning検索精度の向上) | 検索精度の向上 |
| [17. 学習 vs エージェント](build/specialist#17-学習-vs-エージェント---何をどこまでやるか) | 何をどこまでやるか |
| [18. Human-in-the-Loop](build/specialist#18-human-in-the-loop人間が関与すべきポイント) | 人間が関与すべきポイント |
| [19. エキスパートフィードバック収集システム](build/specialist#19-エキスパートフィードバック収集システム) | 継続的な品質改善の仕組み |

#### 付録

| 付録 | 内容 |
|---|---|
| [付録A: ライセンス一覧](build/specialist#付録a-ライセンス一覧) | 使用ライブラリのライセンス |
| [付録B: 参考リンク](build/specialist#付録b-参考リンク) | 公式ドキュメント・論文・コミュニティ |

</details>

---

## 関連ドキュメント

| ドキュメント | 内容 |
|---|---|
| [OpenClaw ガイド](docs/openclaw.md) | オープンソースAIエージェント「OpenClaw」の完全ガイド。機能比較、アーキテクチャ、セットアップ方法 |

---

## このガイドについて

本ガイドは Claude Code を最大限に活用するための実践的なリファレンスです。基本的な設定から高度なマルチエージェント構成まで、段階的に学べる構成になっています。

各章は独立して読めるよう設計されていますので、必要な部分から参照してください。
