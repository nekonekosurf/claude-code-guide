---
layout: default
title: "Claude Code 活用ガイド - 上級編（章25〜32）"
---

[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)

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


```bash
# npm がある場合（最も広く使われている方法）
npm install -g @anthropic-ai/claude-code

# インストール確認
claude --version
```


#### macOS（Homebrew 経由）


```bash
brew install claude-code

# 自動更新は行われないため、定期的にアップデートすること
brew upgrade claude-code
```


#### Windows

PowerShell を **管理者として実行** し、以下を入力する。

```powershell
npm install -g @anthropic-ai/claude-code
```

WSL2（Windows Subsystem for Linux）を使う場合は Linux の手順と同じである。

#### インストールのトラブルシューティング


```bash
# npm のパーミッションエラーが出た場合
sudo npm install -g @anthropic-ai/claude-code

# または nvm を使って Node.js を管理するとパーミッション問題が回避できる
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
npm install -g @anthropic-ai/claude-code
```


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


```
Welcome to Claude Code!
Type your request below. Press Ctrl+C to exit.

>
```


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


```bash
# 悪い例: ホームディレクトリから起動
cd ~
claude

# 良い例: プロジェクトルートから起動
cd ~/projects/my-app
claude
```


**2. 変更を確認せずに承認する**

Claude が提案する変更は必ず内容を確認してから承認すること。特に削除操作やデータベースへの書き込みには注意が必要である。

**3. 1回で全てを頼む**


```
# 悪い例: 曖昧で大きすぎる指示
> このアプリを完成させてください

# 良い例: 具体的で小さな単位の指示
> src/auth/login.ts にメールアドレスのバリデーション関数を追加してください。
> 正規表現でチェックし、無効な場合は InvalidEmailError を throw すること。
```


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


```
# 悪い例（曖昧）
バグを直してください

# 良い例（具体的）
src/utils/email.ts の validateEmail 関数を修正してください。
現在の問題: "user+tag@example.com" のようなプラス記号を含むアドレスが false を返す。
期待する動作: RFC 5321 に準拠した全ての有効なアドレスを true と判定する。
修正後は npm test でテストが全てパスすることを確認してください。
```


#### 新機能実装


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


#### コードレビュー


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


---

### 26.3 コンテキストの与え方

#### @ 参照を使ったファイル指定


```
# 関連ファイルを明示的に参照する
@src/models/User.ts と @src/controllers/authController.ts を読んで、
ログアウト処理でセッションが正しく破棄されているか確認してください
```


#### エラーメッセージをそのまま貼る


```
以下のエラーが発生しています。根本原因を特定して修正してください：

TypeError: Cannot read properties of undefined (reading 'userId')
    at AuthMiddleware.verify (/app/src/middleware/auth.ts:23:45)
    at Layer.handle [as handle_request] (/app/node_modules/express/lib/router/layer.js:95:5)

src/middleware/auth.ts の23行目付近を調べてください
```


#### スクリーンショットを貼り付ける

UI の問題はスクリーンショットを直接ペーストすることで、文章での説明よりも正確に伝えられる。


```
[スクリーンショットを貼り付け]
この画面のボタンが Safari でクリックできない問題を修正してください。
Chrome では正常に動作しています。
```


---

### 26.4 Plan Mode の活用

複雑なタスクは先に計画を立ててから実装することで、間違った方向への実装を防ぐことができる。

```bash
# Shift+Tab で Plan Mode に切り替え（Normal → Plan → Auto-Accept のサイクル）
# または /plan コマンドを使用
# Plan Mode 中は Claude はファイルを読むだけで変更しない
```


```
[Plan Mode]
> OAuth 2.0 によるGoogle ログインを追加したい。
> 現在の認証フロー（src/auth/ 配下）を調べて、どのファイルを変更する必要があるか、
> どのような順序で実装するかを計画してください。
> ライブラリは passport.js を使います。
```


Claude が計画を提示したら、`Ctrl+G` でエディタに計画を開いて修正できる。納得できたら Normal Mode に切り替えて実装を指示する。

---

### 26.5 Claude へのインタビュー手法

大きな機能追加の前に Claude に質問させることで、見落としを防ぐことができる。


```
決済機能を追加したいと思っています。
AskUserQuestion ツールを使って、実装に必要な情報を私にインタビューしてください。
技術的な実装方法、UI/UX、エッジケース、セキュリティ上の考慮事項について
詳しく質問してください。自明な質問は避け、難しい部分を掘り下げてください。
全ての情報が揃ったら、SPEC.md に完全な仕様書を書いてください。
```


インタビュー完了後、`/clear` で新しいセッションを開始し、`@SPEC.md` を参照して実装を依頼する。

---

### 26.6 段階的な指示の技法

#### 探索 → 計画 → 実装 の分離


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


#### チェックリストを与える


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


---

### 26.7 CLAUDE.md でプロンプトを省力化する

毎回同じ指示を書かなくていいように、プロジェクト共通のルールは `CLAUDE.md` に記載する。


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


#### API 経由の場合のコスト試算


```
シナリオ: Claude Code を API で使い、月間 10M 入力トークン + 2M 出力トークン

Claude Sonnet 4.6:
- 入力: 10M × $3/M = $30
- 出力: 2M × $15/M = $30
- 合計: $60/月

→ Max プラン ($100/月) と比較すると API の方が安い場合がある
→ ただし、Max プランは使用量の保証があり、高負荷時でも安定して使える
```


**注意**: API 経由のヘビーコーディングでは月間 $3,650 を超えることもある。Claude Code を大量に使うなら Max プランの $200/月 の方が大幅に安い。

---

### 27.5 プラン選択のフローチャート


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


---

## 28. Git 連携詳細 - ブランチ・マージ・PR レビュー

### 28.1 概要

Claude Code の Git 連携は、自然言語のインストラクションを Git コマンドに変換する機能である。ブランチ作成から PR のマージまでを、ターミナルで `git` コマンドを手動入力することなく実行できる。`gh` CLI がインストールされていると GitHub との連携が格段に便利になる。


```bash
# gh CLI のインストール（推奨）
# macOS
brew install gh

# Linux
sudo apt install gh

# 認証
gh auth login
```


---

### 28.2 ブランチ管理

#### ブランチの作成


```
# 機能ブランチを作成する
> 通知システムを追加するためのフィーチャーブランチを作成してください

# Claude が実行するコマンド（内部的に）
git checkout -b feature/add-notification-system
```


CLAUDE.md にブランチ命名規則を定義すると、Claude が規則に従ったブランチ名を自動生成する。


```markdown
# CLAUDE.md
## Git ルール
- ブランチ命名: feature/<説明>、fix/<説明>、hotfix/<説明>、chore/<説明>
- コミットメッセージ: Conventional Commits 形式（feat:, fix:, docs:, refactor: 等）
- main への直接プッシュは禁止
```


#### ブランチ間の移動と状態確認


```
> 現在のブランチとその変更状況を教えてください

> main ブランチに切り替えて最新状態に更新してください
```


---

### 28.3 コミット管理

#### コンベンショナルコミットの自動生成

```
> ここまでの変更をコミットしてください
```

Claude はステージングされた差分を分析し、以下のような Conventional Commits 形式のメッセージを自動生成する。


```
feat(auth): JWT トークンリフレッシュ機能を追加

- /api/auth/refresh エンドポイントを追加
- リフレッシュトークンの有効期限を 7 日間に設定
- 期限切れトークンの自動無効化処理を実装
```


#### 複数コミットへの分割


```
> この変更は論理的に 3 つのコミットに分けられます。
> それぞれのコミットとして適切にステージングしてコミットしてください：
> 1. データモデルの変更
> 2. API エンドポイントの追加
> 3. テストの追加
```


---

### 28.4 マージコンフリクトの解決

#### 基本的なコンフリクト解決


```
> main ブランチをマージしようとしたらコンフリクトが発生しました。
> コンフリクトを解決してください。
> 優先方針: 最新の main ブランチの変更を優先するが、
> src/auth/ 配下の変更は私のブランチのものを維持すること
```


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


```
> src/models/User.ts にコンフリクトがあります。
> 両方のブランチの変更内容を説明してから、最適な解決策を提案してください。
> 変更を適用する前に私が承認できるよう、差分を表示してください。
```


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


```bash
# worktree を使ったセッション起動
claude --worktree

# または手動で worktree を作成してから起動
git worktree add ../my-app-feature feature/new-auth
cd ../my-app-feature
claude
```


**活用場面**:
- 本番バグの緊急修正と機能開発を同時進行
- A/B で異なる実装アプローチを試す
- レビュー待ちの PR と次の機能開発を並行作業

---

### 28.7 CI/CD との連携

#### GitHub Actions での自動 PR レビュー

`.github/workflows/claude-review.yml` を設定すると、PR 作成時に Claude が自動でレビューを行う。


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
          anthropic_api_key: ${{% raw %}}{{ secrets.ANTHROPIC_API_KEY }}{{% endraw %}}
          prompt: |
            このPRをレビューしてください。
            - セキュリティの問題
            - パフォーマンスの問題
            - テストの漏れ
            - コーディング規約の違反
            問題がある場合はコメントで指摘し、修正案を提示してください。
```


#### コミット前のフック

`.claude/settings.json` で pre-commit フックを設定する。


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


---

### 29.3 TDD スキルの定義

`.claude/skills/tdd/SKILL.md` を作成して TDD を自動化する。


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


---

### 29.4 サブエージェントを使ったテスト隔離

「コンテキスト汚染」（実装を知っているとテストを甘く書く）を防ぐために、テスト作成と実装を別のサブエージェントに分担させる。


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


---

### 29.5 テストタイプ別の TDD アプローチ

#### ユニットテスト（Jest / Vitest）


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


#### E2E テスト（Playwright）


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


---

### 29.6 TDD フックの設定

`.claude/settings.json` でテスト実行を強制するフックを設定する。


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


このフックにより、テストファイルを書いた後に自動でそのテストが実行され、失敗しているかどうかを確認できる。

---

### 29.7 CLAUDE.md での TDD ルール定義


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


#### 複数ファイルにまたがるバグ


```
@src/hooks/useProducts.ts と @src/components/ProductList.tsx を両方確認して、
products が undefined になる可能性のある箇所を全て特定してください。

その後、最も可能性の高い根本原因から順に修正案を提示してください。
確実性の低い修正から始めないこと。
```


---

### 30.3 ログ分析ワークフロー

#### ターミナル出力のパイプ


```bash
# テスト出力を Claude に送る
npm test 2>&1 | claude -p "テスト失敗の根本原因を分析して修正方法を提示してください"

# ビルドエラーを送る
npm run build 2>&1 | claude -p "ビルドエラーを分析して修正してください"

# サーバーログを送る
cat server.log | claude -p "エラーパターンを分析し、最も緊急度の高い問題を報告してください"
```


#### ログに詳細情報を追加させる


```
現在のコードにデバッグログを追加してください。
以下の箇所に console.log を入れて、データの流れを追跡できるようにしてください：

1. src/services/paymentService.ts の processPayment 関数の入口
2. 各 API 呼び出しの前後
3. エラーハンドリングブロック内

ログフォーマット: [DEBUG][<関数名>] <メッセージ>: <値>

デバッグが完了したら、追加したログを削除することを忘れないでください
```


---

### 30.4 ノウハウ集: バグタイプ別デバッグ手順

#### 非同期処理のバグ


```
src/api/userApi.ts で Promise が正しく処理されていない可能性があります。

以下を確認してください：
1. async/await の使い忘れ
2. Promise のエラーハンドリングが漏れている箇所
3. 競合状態（race condition）が発生しうる非同期処理の並列実行

テストコードで再現するケースを作成してから修正してください
```


#### パフォーマンス問題


```
アプリのホームページの読み込みが遅くなりました（3秒以上）。

@src/pages/index.tsx を分析して：
1. 不必要な再レンダリングを引き起こしている箇所
2. データフェッチの最適化できる箇所
3. 大きなバンドルサイズを引き起こしているインポート

各問題の修正優先度と期待される改善幅を示してください
```


#### 環境依存バグ


```
本番環境でのみ発生するエラーです。ローカルでは再現しません。

エラー: DATABASE_URL environment variable is not set
スタック: src/config/database.ts:12

本番環境と開発環境の設定ファイルの違いを分析して、
環境変数の取り扱いに問題がないか確認してください。
@.env.example と @src/config/ を調べてください
```


---

### 30.5 /debug コマンドとデバッグセッション管理


```
# セッション中のデバッグ支援
/debug

# 長いデバッグセッションのコンテキスト圧縮
# （デバッグの結論を保持しつつコンテキストを節約）
/compact デバッグのまとめを保持して。バグの根本原因と修正内容を記録すること
```


#### バックグラウンドでのログ監視


```
# テストを実行しながらメインの作業を継続する
npm run test:watch > test-output.log 2>&1 &

# テスト結果が変わったときに Claude に分析させる
tail -f test-output.log | claude -p "新しいテスト失敗が検出されたらすぐに報告してください"
```


---

### 30.6 getDiagnostics ツールの活用

Claude Code には `getDiagnostics` ツールが組み込まれており、TypeScript や ESLint などの言語サーバーの診断情報を自動取得できる。


```
ファイルを編集した後、TypeScript の型エラーと ESLint の警告を全てチェックして、
エラーがあれば修正してください。
エラーがなくなるまで繰り返してください。
```


このような指示を与えると、Claude は `getDiagnostics` を使って自動的にエラーを確認し、全てのエラーが解消されるまでループして修正を続ける。

---

### 30.7 デバッグ記録の CLAUDE.md への反映

発見したバグや解決策を CLAUDE.md に記録することで、将来の同じ問題を回避できる。


```
今回発見した以下の問題を CLAUDE.md の「既知の問題」セクションに追記してください：

- React の useEffect で cleanup 関数を返さないとメモリリークが発生する
  （src/hooks/useWebSocket.ts を参照）
- Windows 環境でパスの区切り文字が / でなく \ になる問題
  （path.join を使うことで回避）
```


---

## 31. ツール比較 2026年版 - Cursor / Copilot / Aider / Windsurf / Cline

### 31.1 ツールの位置づけ

2026年現在、AI コーディングツールは大きく3つのカテゴリに分かれる。

| カテゴリ | ツール | 特徴 |
|---------|-------|------|
| **ターミナルエージェント** | Claude Code、Aider、OpenCode | コードベース全体を対象に自律的に動作 |
| **AI 統合 IDE** | Cursor、Windsurf | VS Code ベースで AI をエディタに深く統合 |
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

---

### 31.3 機能比較マトリクス

2026年版のツール比較マトリクスです（A=優秀、B=良好、C=基本的）。

| 機能 | Claude Code | Cursor | Copilot | Aider | Windsurf | Cline |
|------|:-----------:|:------:|:-------:|:-----:|:--------:|:-----:|
| 大規模リファクタリング（20+ ファイル） | A | B | C | B | C | B |
| インラインオートコンプリート | C | A | A | C | B | B |
| 自然言語でのコード生成 | A | A | B | A | A | A |
| Git 統合 | A | B | B | A | B | B |
| テスト生成 | A | B | B | A | B | B |
| コードベース質問応答 | A | B | C | B | B | B |
| デバッグ支援 | A | B | B | B | B | B |
| PR レビュー自動化 | A | C | B | C | C | C |
| カスタマイズ性 | A | B | C | A | B | A |
| コスト効率（重量ユーザー） | B | B | B | A | A | A |

（A=優秀、B=良好、C=基本的）

---

### 31.4 ツール選択ガイド


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


**ルート CLAUDE.md（共通ルール）**:


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


**フロントエンド固有 CLAUDE.md**:


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


---

### 32.3 コンテキスト制限への対策

#### 対策 1: 作業前にスコープを明示する


```
作業スコープを宣言してください：
- 作業対象: apps/backend/src/auth/ のみ
- 参照可能: packages/utils/src/crypto.ts
- 変更禁止: apps/frontend/, packages/ui/

このスコープを厳守して、JWT 認証の実装を行ってください
```


#### 対策 2: /clear を積極的に使う


```
# タスクとタスクの間には必ず /clear を使う
/clear

# 新しいタスクには必要なコンテキストを明示して再開する
> apps/backend の payment サービスを修正します。
> @apps/backend/src/services/payment.ts と
> @apps/backend/src/__tests__/payment.test.ts を読んでから始めてください
```


#### 対策 3: サブエージェントで調査を分離する


```
サブエージェントを使って以下を調査してください：
1. apps/backend で使われている全てのデータベース接続パターン
2. packages/utils に移動できそうな重複コード
3. TypeScript の型エラーが出ているファイル一覧

調査結果のサマリーだけを返してください（コードの中身は不要）
```


#### 対策 4: claudeMdExcludes を使う

`.claude/settings.json` で不要なディレクトリの CLAUDE.md を除外できる。


```json
{
  "claudeMdExcludes": [
    "legacy/**",
    "node_modules/**",
    "archived/**"
  ]
}
```


#### 対策 5: コンテキスト使用量の監視

ステータスラインでリアルタイムにコンテキスト使用量を監視する（15章参照）。


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


---

### 32.4 複数言語プロジェクトの設定

#### ポリグロットなモノレポの例


```
fullstack-app/
├── backend/          Python (FastAPI)
├── frontend/         TypeScript (React)
├── mobile/           Swift (iOS) + Kotlin (Android)
├── ml/               Python (PyTorch)
└── infra/            HCL (Terraform)
```


**ルート CLAUDE.md でポリシーを統一**:


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


---

### 32.5 大規模マイグレーションの実行

#### fan-out パターン（並列処理）


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


#### 段階的マイグレーション


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


---

### 32.6 MCP を使ったコードベース検索の強化

大規模コードベースでは MCP（Model Context Protocol）サーバーを使ったセマンティック検索が効果的である。


```bash
# Zilliz Claude Context MCP サーバーのインストール（コードベースのセマンティック検索）
claude mcp add zilliz-code-search

# 使用例
> MCP ツールを使って、エラーハンドリングが不足している箇所を
> コードベース全体から検索してください（grep ではなくセマンティック検索を使う）
```


---

### 32.7 大規模プロジェクトのベストプラクティスまとめ


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


---

[^25]: [Claude Code Setup - Anthropic 公式](https://code.claude.com/docs/ja/setup)
[^26]: [Prompt Engineering Best Practices - Anthropic 公式](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
[^27]: [Claude AI Pricing 2026 - Global GPT](https://www.glbgpt.com/hub/claude-ai-pricing-2026-the-ultimate-guide-to-plans-api-costs-and-limits/)
[^28]: [Git Integration - SFEIR Institute](https://institute.sfeir.com/en/claude-code/claude-code-git-integration/)
[^29]: [Forcing Claude Code to TDD - alexop.dev](https://alexop.dev/posts/custom-tdd-workflow-claude-code-vue/)
[^30]: [Cursor vs Windsurf vs Claude Code 2026 - DEV Community](https://dev.to/pockit_tools/cursor-vs-windsurf-vs-claude-code-in-2026-the-honest-comparison-after-using-all-three-3gof)
[^31]: [Claude Code Monorepo Best Practices - DEV Community](https://dev.to/anvodev/how-i-organized-my-claudemd-in-a-monorepo-with-too-many-contexts-37k7)
[^32]: [Manage Claude Context in Large Projects - Arsturn](https://www.arsturn.com/blog/how-to-actually-manage-context-in-large-coding-projects-with-claude)

---

[← 前: チーム編](team)
