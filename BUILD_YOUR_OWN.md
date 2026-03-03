# Claude Codeクローン構築ガイド - ローカルLLMでAIコーディングエージェントを作る

> 作成日: 2026-03-03
> 対象: GPU搭載Linux環境でClaude Code同等のAIエージェントをゼロから構築したい開発者

---

## 目次

1. [はじめに](#1-はじめに)
2. [アーキテクチャ概要](#2-アーキテクチャ概要)
3. [技術スタック選択](#3-技術スタック選択)
4. [vLLMセットアップ](#4-vllmセットアップ)
5. [コアエージェント実装](#5-コアエージェント実装)
6. [Extended Thinking（深い推論）](#6-extended-thinking深い推論)
7. [マルチモデルルーティング](#7-マルチモデルルーティング)
8. [サブエージェント・Agent Teams](#8-サブエージェントagent-teams)
9. [ファインチューニングと学習（専門知識の習得）](#9-ファインチューニングと学習専門知識の習得)
   - 9.1 QLoRA/SFT基礎
   - 9.2 継続事前学習（CPT）
   - 9.3 DPO/RLHF/ORPO（強化学習・選好最適化）
   - 9.4 学習の評価方法
   - 9.5 フレームワーク比較
10. [RAG（検索拡張生成）](#10-rag検索拡張生成)
11. [高度な検索技法](#11-高度な検索技法)
12. [費用・コスト](#12-費用コスト)
13. [セキュリティ・サンドボックス](#13-セキュリティサンドボックス)
14. [セッション・メモリ管理](#14-セッションメモリ管理)
15. [実装ロードマップ](#15-実装ロードマップ)
16. [Embedding Fine-tuning（検索精度の向上）](#16-embedding-fine-tuning検索精度の向上)
17. [学習 vs エージェント - 何をどこまでやるか](#17-学習-vs-エージェント---何をどこまでやるか)
18. [Human-in-the-Loop（人間が関与すべきポイント）](#18-human-in-the-loop人間が関与すべきポイント)
19. [エキスパートフィードバック収集システム](#19-エキスパートフィードバック収集システム)
- [付録A: ライセンス一覧](#付録a-ライセンス一覧)
- [付録B: 参考リンク](#付録b-参考リンク)

---

## 1. はじめに

### このガイドの目的

Claude Codeは、Anthropicが提供するAIコーディングエージェントです。このガイドでは、**ローカルLLMを使ってClaude Codeと同等の機能を持つエージェントをゼロから構築する方法**を解説します。

構築するシステムの主な機能:
- ファイルの読み書き・編集
- シェルコマンドの実行（永続セッション）
- Web検索・ページ取得
- サブエージェントによる並列タスク処理
- コードの検索・解析（ripgrep統合）
- 長期メモリ管理

### 前提条件

| 項目 | 最低要件 | 推奨 |
|------|---------|------|
| GPU | RTX 3090 (24GB VRAM) | A100/H100 80GB |
| RAM | 32GB | 64GB以上 |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Python | 3.11 | 3.12 |
| CUDA | 12.1 | 12.3以上 |
| ストレージ | 200GB SSD | 1TB NVMe SSD |

### 使用モデルのポリシー

このガイドでは**中国系モデルは一切使用しません**。使用するモデル:
- OpenAI GPT-OSS (gpt-oss-20b / gpt-oss-120b) ※ Cerebras API経由のみ、vLLMローカル起動不可
- Google Gemma 2/3シリーズ
- Meta Llama 3.1/3.2シリーズ
- Mistral / Codestral ※ Codestralは**非商用利用のみ**（Codestral License）
- StarCoder2

---

## 2. アーキテクチャ概要

### Claude Codeの内部構造（推測）

公開情報と既存OSSの分析から、Claude Codeは以下の構造を持つと推測されます:

```
┌─────────────────────────────────────────────┐
│                  Claude Code                │
│                                             │
│  ┌──────────┐    ┌──────────────────────┐   │
│  │  CLI/TUI │───▶│   AgentCore          │   │
│  │ (Ink/    │    │   - ReActループ       │   │
│  │  React)  │    │   - ツールディスパッチ │   │
│  └──────────┘    │   - コンテキスト管理  │   │
│                  └──────────┬─────────────┘  │
│                             │               │
│         ┌───────────────────┼───────────┐   │
│         ▼                   ▼           ▼   │
│  ┌────────────┐  ┌────────────┐  ┌────────┐ │
│  │ Tool Layer │  │  Context   │  │Memory  │ │
│  │ 23ツール   │  │  Manager   │  │System  │ │
│  └────────────┘  └────────────┘  └────────┘ │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────────────────────┐ │
│  │      vLLM / ローカルLLM API           │ │
│  │   (Llama 3.x / Gemma 2 / Mistral)     │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### エージェントループ（ReAct パターン）

ReActとは「Reasoning + Acting」の略で、思考→行動→観察を繰り返すループです:

```
┌─────────────────────────────────────────┐
│             ReAct ループ                 │
│                                         │
│  ユーザー入力                            │
│       │                                 │
│       ▼                                 │
│  ┌─────────┐                            │
│  │  Think  │ ← LLMが次のアクションを考える │
│  └────┬────┘                            │
│       │ tool_use レスポンス              │
│       ▼                                 │
│  ┌─────────┐                            │
│  │  Act    │ ← ツールを実行する           │
│  └────┬────┘                            │
│       │ ツール実行結果                   │
│       ▼                                 │
│  ┌─────────┐                            │
│  │ Observe │ ← 結果をコンテキストに追加   │
│  └────┬────┘                            │
│       │                                 │
│       ├── ツール呼び出しが必要 → Think へ  │
│       └── 完了 → ユーザーに返答          │
└─────────────────────────────────────────┘
```

### 既存OSSの設計パターン比較

| ツール | 言語 | 主な特徴 | 設計パターン |
|--------|------|---------|------------|
| **Aider** | Python | tree-sitterリポマップ、git統合 | whole/diff/udiff 3種editフォーマット |
| **OpenHands** | Python | イベントソーシング | Action-Observation パターン |
| **SWE-agent** | Python | ACI (Agent-Computer Interface) | 2階層アクションスペース |
| **Cline** | TypeScript | VSCode Extension | Plan/Actモード分離、MCP対応 |
| **Goose** | Rust | MCPをExtensionsと呼ぶ | Interface/Agent/Extensions 3層 |
| **Continue.dev** | TypeScript | @メンションコンテキスト | BaseContextProvider interface |

#### Aider: RepoMap（コード理解）

Aiderの最大の特徴は**tree-sitter + PageRank によるリポジトリマップ**です。

```python
# Aiderのリポマップ概念（簡略版）
# 実際のAiderのコードはもっと複雑ですが、核心はここ
import networkx as nx
from tree_sitter import Language, Parser

class RepoMap:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()  # 関数・クラス間の参照グラフ

    def build_graph(self, files):
        """全ファイルを解析して参照グラフを構築"""
        for file in files:
            symbols = self.extract_symbols(file)  # tree-sitterで解析
            for sym in symbols:
                self.graph.add_node(sym.name, file=file)
                for ref in sym.references:
                    self.graph.add_edge(sym.name, ref)

    def get_ranked_files(self, chat_files, max_tokens=2000):
        """PageRankで重要ファイルをランキングして返す"""
        scores = nx.pagerank(self.graph)
        # チャット中のファイルに関連するものを優先
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:max_tokens]
```

#### OpenHands: イベントソーシング

```python
# OpenHandsのAction-Observationパターン（概念）
from dataclasses import dataclass
from typing import Union

@dataclass
class CmdRunAction:
    """コマンド実行アクション"""
    command: str
    background: bool = False

@dataclass
class FileWriteAction:
    """ファイル書き込みアクション"""
    path: str
    content: str

@dataclass
class CmdOutputObservation:
    """コマンド実行結果"""
    output: str
    exit_code: int
    command: str

# 全てのアクション・オブザベーションをイベントストリームに記録
# → リプレイ可能、デバッグしやすい
```

#### SWE-agent: ACI（Agent-Computer Interface）

```
SWE-agentの2階層アクションスペース:

Search/Navigation層:
  - find_file <ファイル名>
  - search_file <パターン> [ファイル]
  - open <ファイル> [行番号]
  - scroll_down / scroll_up

Edit層:
  - edit <開始行>:<終了行>
    <新しい内容>
  end_of_edit
```

---

## 3. 技術スタック選択

### 言語選択: TypeScript vs Python vs Rust

| 項目 | TypeScript | Python | Rust |
|------|-----------|--------|------|
| 開発速度 | 速い | 最速 | 遅い |
| AI/MLライブラリ | 少ない | 豊富 | 少ない |
| 実行速度 | 中 | 遅い | 最速 |
| メモリ効率 | 中 | 低 | 最高 |
| 型安全性 | 高い | 中(型ヒント) | 最高 |
| コミュニティ | 大 | 最大 | 中 |
| CLI適性 | 高(Ink) | 高(Rich/Typer) | 高 |
| vLLM統合 | 可(REST) | ネイティブ | 可(REST) |
| 推奨用途 | Claude Code自体 | AIエージェント | 高速ツール |

**推奨: Python**
- vLLM、transformers、unsloth等との連携が最もスムーズ
- asyncio による並列処理が強力
- RAG・ファインチューニング等のAI周辺ライブラリが充実

### CLIフレームワーク

```bash
# Python推奨の組み合わせ
uv pip install typer rich openai
```

```python
# Typer + Rich によるCLI例
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer()
console = Console()

@app.command()
def chat(
    query: str = typer.Argument(..., help="質問・指示"),
    model: str = typer.Option("gpt-oss-120b", "--model", "-m"),
    plan: bool = typer.Option(False, "--plan", help="計画モード"),
    show_thinking: bool = typer.Option(False, "--show-thinking"),
):
    """AIコーディングエージェントと対話する"""
    console.print(Panel(f"[bold cyan]クエリ:[/] {query}", expand=False))
    # エージェント処理...

if __name__ == "__main__":
    app()
```

---

## 4. vLLMセットアップ

### インストール

```bash
# Python 3.12環境のセットアップ
uv venv --python 3.12
source .venv/bin/activate

# vLLMインストール（CUDA 12.1以上が必要）
uv pip install vllm

# 確認
python -c "import vllm; print(vllm.__version__)"
```

### 推奨モデル一覧（中国系除外）

| カテゴリ | モデル | VRAM | 特徴 | 入手方法 |
|---------|--------|------|------|----------|
| **コーディング** | Codestral 22B | 24GB | Mistral製、コード専門（非商用のみ） | `mistralai/Codestral-22B-v0.1` (HuggingFace) |
| | StarCoder2 15B | 16GB | BigCode製、多言語対応 | `bigcode/starcoder2-15b` (HuggingFace) |
| | CodeGemma 7B | 8GB | Google製、軽量 | `google/codegemma-7b-it` (HuggingFace) |
| **汎用（大）** | GPT-OSS 120B | 60GB+ | Cerebras API経由で利用、HuggingFaceからDL不可 | [Cerebras API](https://api.cerebras.ai) 経由のみ |
| | Llama 3.1 70B | 40GB | Meta製、バランス良 | `meta-llama/Llama-3.1-70B-Instruct` (HuggingFace) |
| | Gemma 2 27B | 28GB | Google製、高品質 | `google/gemma-2-27b-it` (HuggingFace) |
| **汎用（中）** | GPT-OSS 20B | 16GB | Cerebras API経由で利用、HuggingFaceからDL不可 | [Cerebras API](https://api.cerebras.ai) 経由のみ |
| | Llama 3.1 8B | 10GB | Meta製、高速 | `meta-llama/Llama-3.1-8B-Instruct` (HuggingFace) |
| **軽量** | Gemma 2 9B | 10GB | Google製、軽量高性能 | `google/gemma-2-9b-it` (HuggingFace) |
| | Phi-3 Mini 3.8B | 4GB | Microsoft製、超軽量 | `microsoft/Phi-3-mini-4k-instruct` (HuggingFace) |

> **注意:** GPT-OSS（gpt-oss-20b / gpt-oss-120b）は OpenAI が Cerebras のインフラ上で提供するサービスです。HuggingFace からの直接ダウンロードはできません。ローカル環境でのvLLM起動も不可能です。GPT-OSSを使用する場合は Cerebras API（OpenAI互換）経由でアクセスしてください。ローカルvLLMサーバーで使いたい場合は Llama / Gemma / Mistral 系モデルを選択してください。

### Tool Use（Function Calling）対応状況

ローカルモデルのツール呼び出し対応はモデルによって異なります:

| モデル | Tool Use対応 | vLLMパーサー名 | 備考 |
|--------|-------------|--------------|------|
| Llama 3.1/3.2 | ネイティブ対応 | `llama3_json` | 公式Function Calling対応 |
| Mistral/Codestral | ネイティブ対応 | `mistral` | Mistral Tool Use形式 |
| Hermes系 | ネイティブ対応 | `hermes` | NousResearch Hermes形式 |
| Granite | ネイティブ対応 | `granite` | IBM Granite形式 |
| GPT-OSS | 対応確認中 | `pythonic` | OpenAI形式で試行 |
| Gemma 2/3 | 部分対応 | テキスト解析 | JSON出力プロンプトで代替 |
| CodeGemma | 非対応 | テキスト解析 | XMLタグ形式で代替 |
| StarCoder2 | 非対応 | テキスト解析 | ReAct形式で代替 |

#### 非対応モデルのWorkaround

```python
# テキストからツール呼び出しを解析する実装
import re, json

def parse_tool_call_from_text(text: str) -> dict | None:
    """LLMのテキスト出力からツール呼び出しを解析する"""

    # パターン1: JSONブロック形式
    # ```json
    # {"tool": "Read", "input": {"file_path": "/path/to/file"}}
    # ```
    json_pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # パターン2: XMLタグ形式（Gemma等）
    # <tool_call>Read</tool_call>
    # <tool_input>{"file_path": "/path/to/file"}</tool_input>
    tool_name = re.search(r'<tool_call>(.*?)</tool_call>', text)
    tool_input = re.search(r'<tool_input>(.*?)</tool_input>', text, re.DOTALL)
    if tool_name and tool_input:
        try:
            return {
                "tool": tool_name.group(1).strip(),
                "input": json.loads(tool_input.group(1).strip())
            }
        except json.JSONDecodeError:
            pass

    # パターン3: ReAct形式（汎用）
    # Action: Read
    # Action Input: {"file_path": "/path/to/file"}
    action = re.search(r'Action:\s*(\w+)', text)
    action_input = re.search(r'Action Input:\s*(\{.*?\})', text, re.DOTALL)
    if action and action_input:
        try:
            return {
                "tool": action.group(1).strip(),
                "input": json.loads(action_input.group(1).strip())
            }
        except json.JSONDecodeError:
            pass

    return None  # ツール呼び出しなし（最終回答）
```

### vLLM 起動コマンド例

```bash
# =============================================
# 基本起動（OpenAI互換APIサーバー）
# =============================================

# CodeGemma 7B（コーディング専用、軽量）
vllm serve google/codegemma-7b-it \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype bfloat16

# Llama 3.1 70B（汎用、Tool Use対応）
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype bfloat16 \
    --tensor-parallel-size 2 \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json

# Codestral 22B（コーディング専用、Tool Use対応）
vllm serve mistralai/Codestral-22B-v0.1 \
    --host 0.0.0.0 \
    --port 8002 \
    --dtype bfloat16 \
    --enable-auto-tool-choice \
    --tool-call-parser mistral

# NOTE: GPT-OSS (gpt-oss-20b / gpt-oss-120b) はローカルvLLMでは起動できません。
# GPT-OSS を使う場合は Cerebras API（OpenAI互換）に接続してください:
#   from openai import OpenAI
#   client = OpenAI(base_url="https://api.cerebras.ai/v1", api_key="YOUR_KEY")
#   # model="gpt-oss-120b" で使用

# 代替: Llama 3.1 8B（汎用、コスト効率・ローカル実行可能）
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8003 \
    --dtype bfloat16 \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json

# Gemma 2 27B（高品質汎用）
vllm serve google/gemma-2-27b-it \
    --host 0.0.0.0 \
    --port 8004 \
    --dtype bfloat16 \
    --tensor-parallel-size 2

# =============================================
# 量子化オプション（VRAM削減）
# =============================================

# AWQ量子化（4bit、精度維持しやすい）
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --quantization awq \
    --port 8001

# GPTQ量子化
vllm serve mistralai/Codestral-22B-v0.1 \
    --quantization gptq \
    --port 8002

# FP8量子化（H100推奨）
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --quantization fp8 \
    --tensor-parallel-size 4 \
    --port 8005

# =============================================
# 高速化オプション
# =============================================

# Prefix Caching有効（同じシステムプロンプトを再利用）
vllm serve google/gemma-2-27b-it \
    --enable-prefix-caching \
    --port 8004

# Speculative Decoding（小モデルで先読み生成）
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --speculative-model meta-llama/Llama-3.2-1B-Instruct \
    --num-speculative-tokens 5 \
    --port 8001
```

### 接続確認

```python
# vLLMへの接続確認スクリプト
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # vLLMはAPIキー不要（ローカル）
)

# モデル一覧
models = client.models.list()
print("利用可能なモデル:")
for m in models.data:
    print(f"  - {m.id}")

# テスト生成
response = client.chat.completions.create(
    model="google/codegemma-7b-it",
    messages=[{"role": "user", "content": "Hello, 日本語で挨拶して"}],
    max_tokens=100
)
print(response.choices[0].message.content)
```

---

## 5. コアエージェント実装

### ディレクトリ構成

```
coding_agent/
├── __init__.py
├── main.py              # CLIエントリポイント
├── agent_core.py        # メインエージェントループ
├── tools.py             # 全ツール実装
├── context_manager.py   # コンテキストウィンドウ管理
├── sub_agent.py         # サブエージェント（並列実行）
└── config.py            # 設定・定数
```

### config.py: 設定

```python
# coding_agent/config.py
from dataclasses import dataclass, field
from typing import Optional
import os

@dataclass
class LLMConfig:
    """LLM接続設定"""
    base_url: str = field(
        default_factory=lambda: os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
    )
    model: str = field(
        default_factory=lambda: os.getenv("VLLM_MODEL", "google/codegemma-7b-it")
    )
    api_key: str = "dummy"  # ローカルvLLMはAPIキー不要
    max_tokens: int = 4096
    temperature: float = 0.1  # コーディングは低温度で確実性重視
    timeout: float = 120.0    # ツール実行タイムアウト

@dataclass
class AgentConfig:
    """エージェント動作設定"""
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "50"))
    max_context_tokens: int = 100_000    # コンテキスト上限
    compress_threshold: int = 80_000     # この閾値を超えたら圧縮
    use_native_tool_call: bool = (
        os.getenv("USE_NATIVE_TOOL_CALL", "true").lower() == "true"
    )
    force_cot: bool = (
        os.getenv("FORCE_COT", "false").lower() == "true"
    )
    show_thinking: bool = False

# システムプロンプト
SYSTEM_PROMPT = """あなたは優秀なAIコーディングエージェントです。
ユーザーの指示に従い、提供されたツールを使ってタスクを実行してください。

# 基本的な動作方針
- まずタスクを理解し、必要なツールを特定する
- ツールを使って情報を収集し、コードを書く・編集する
- エラーが発生した場合は原因を分析して修正する
- 作業完了後は結果を簡潔に報告する

# 注意事項
- find/grep コマンドは直接使わず、GlobツールやGrepツールを使う
- 大きなファイルを丸ごと表示するのではなく、必要な部分だけ読む
- コードを変更する前に必ずReadツールで現在の内容を確認する
"""
```

### tools.py: 全ツール実装

```python
# coding_agent/tools.py
import os
import re
import json
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import httpx

class ToolExecutor:
    """全ツールの実装と実行"""

    def __init__(self):
        # 永続シェルセッション（Bashツール用）
        self._shell_process: subprocess.Popen | None = None
        self._shell_lock = asyncio.Lock()

    # =============================================
    # ファイル操作ツール
    # =============================================

    async def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """ファイルを読み込む（cat -n形式で行番号付き）"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"エラー: ファイルが見つかりません: {file_path}"
            if not path.is_file():
                return f"エラー: ディレクトリです（ファイルを指定してください）: {file_path}"

            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            # offset/limitでスライス
            target_lines = lines[offset:offset + limit]
            result = []
            for i, line in enumerate(target_lines, start=offset + 1):
                result.append(f"{i:6}\t{line.rstrip()}")

            if len(lines) > offset + limit:
                result.append(f"\n... 残り {len(lines) - offset - limit} 行 ...")

            return '\n'.join(result)
        except Exception as e:
            return f"エラー: {e}"

    async def write(self, file_path: str, content: str) -> str:
        """ファイルを新規作成または上書き"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"書き込み完了: {file_path} ({len(content)} 文字)"
        except Exception as e:
            return f"エラー: {e}"

    async def edit(self, file_path: str, old_string: str, new_string: str) -> str:
        """ファイルの特定文字列を置換（完全一致、1箇所のみ）"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"エラー: ファイルが見つかりません: {file_path}"

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            count = content.count(old_string)
            if count == 0:
                return f"エラー: 置換対象の文字列が見つかりません"
            if count > 1:
                return f"エラー: 置換対象が{count}箇所あります。より具体的な文字列を指定してください"

            new_content = content.replace(old_string, new_string, 1)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return f"編集完了: {file_path}"
        except Exception as e:
            return f"エラー: {e}"

    async def glob(self, pattern: str, path: str = ".") -> str:
        """glob パターンでファイルを検索"""
        try:
            import glob as glob_module
            base = Path(path).resolve()
            full_pattern = str(base / pattern)
            matches = glob_module.glob(full_pattern, recursive=True)
            matches.sort()
            if not matches:
                return "マッチするファイルが見つかりませんでした"
            # 絶対パスを相対パスに変換して返す
            relative = [str(Path(m).relative_to(base)) for m in matches]
            return '\n'.join(relative)
        except Exception as e:
            return f"エラー: {e}"

    async def grep(self, pattern: str, path: str = ".", glob_pattern: str = None) -> str:
        """正規表現でファイル内容を検索（ripgrep使用）"""
        try:
            # ripgrep が使える場合はそちらを優先
            cmd = ["rg", "--line-number", "--no-heading", pattern, path]
            if glob_pattern:
                cmd.extend(["--glob", glob_pattern])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout[:30000]  # 出力上限
            elif result.returncode == 1:
                return "マッチする内容が見つかりませんでした"
            else:
                raise Exception("ripgrep not available")
        except (FileNotFoundError, Exception):
            # Pythonフォールバック実装
            return await self._grep_python(pattern, path, glob_pattern)

    async def _grep_python(self, pattern: str, path: str, glob_pattern: str = None) -> str:
        """Python実装のgrep（ripgrep非対応環境用）"""
        import glob as glob_module
        results = []
        base = Path(path)

        if glob_pattern:
            search_pattern = str(base / "**" / glob_pattern)
            files = glob_module.glob(search_pattern, recursive=True)
        else:
            if base.is_file():
                files = [str(base)]
            else:
                files = glob_module.glob(str(base / "**" / "*"), recursive=True)
                files = [f for f in files if Path(f).is_file()]

        regex = re.compile(pattern)
        for file_path in sorted(files)[:100]:  # 最大100ファイル
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for lineno, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{lineno}:{line.rstrip()}")
                            if len(results) > 1000:
                                break
            except Exception:
                pass

        if not results:
            return "マッチする内容が見つかりませんでした"
        return '\n'.join(results[:1000])

    # =============================================
    # Bash実行ツール
    # =============================================
    # 注意: この実装は毎回新しいサブプロセスを生成します。
    # そのため cd 等のシェル状態（カレントディレクトリ、環境変数）は
    # コマンド間で引き継がれません。
    # 状態を維持したい場合は1つのコマンド文字列内で完結させてください。
    # 例: "cd /path && python script.py"
    #
    # 真の永続セッション（状態引き継ぎ）を実装するには、
    # subprocess.Popen で shell プロセスを保持し、stdin/stdout を
    # 専用のパターン（例: "echo __DONE__" を終端として使用）で
    # ストリーミングする方式が必要です。

    async def bash(self, command: str, timeout: int = 120000) -> str:
        """
        シェルコマンドを実行する。
        毎回新しいプロセスを生成するため、cd等の状態は引き継がれない。
        状態を維持したい場合は "cd /path && your_command" の形式で記述する。
        timeout: ミリ秒（デフォルト120秒）
        """
        async with self._shell_lock:
            try:
                # タイムアウトを秒に変換
                timeout_sec = min(timeout / 1000, 600)

                # 出力を制限するラッパー
                wrapped = f"""
{{
{command}
}} 2>&1 | head -c 30000
echo "___EXIT_CODE_$?___"
"""
                proc = await asyncio.create_subprocess_shell(
                    wrapped,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout_sec
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return f"タイムアウト: {timeout_sec}秒を超えました"

                output = stdout.decode('utf-8', errors='replace')

                # 終了コードを抽出
                exit_match = re.search(r'___EXIT_CODE_(\d+)___\s*$', output)
                if exit_match:
                    exit_code = int(exit_match.group(1))
                    output = output[:exit_match.start()].rstrip()
                else:
                    exit_code = proc.returncode

                if exit_code != 0:
                    return f"[終了コード {exit_code}]\n{output}"
                return output

            except Exception as e:
                return f"実行エラー: {e}"

    # =============================================
    # Web ツール
    # =============================================

    async def web_search(self, query: str) -> str:
        """DuckDuckGo Instant Answer APIで検索（無料・APIキー不要）"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    }
                )
                data = resp.json()

                results = []
                # AbstractText（要約）
                if data.get("AbstractText"):
                    results.append(f"概要: {data['AbstractText']}")
                    if data.get("AbstractURL"):
                        results.append(f"出典: {data['AbstractURL']}")

                # RelatedTopics（関連トピック）
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(f"- {topic['Text']}")
                        if topic.get("FirstURL"):
                            results.append(f"  URL: {topic['FirstURL']}")

                if not results:
                    return f"検索結果が見つかりませんでした: {query}"
                return '\n'.join(results)

        except Exception as e:
            return f"検索エラー: {e}"

    async def web_fetch(self, url: str, prompt: str = "") -> str:
        """URLからコンテンツを取得してMarkdownに変換"""
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AIAgent/1.0)"}
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            # HTMLをMarkdownに変換
            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                return self._html_to_markdown(resp.text, url)
            else:
                return resp.text[:30000]

        except Exception as e:
            return f"取得エラー: {e}"

    def _html_to_markdown(self, html: str, url: str) -> str:
        """HTMLをMarkdown形式に変換（簡易実装）"""
        try:
            # markdownify が使える場合
            from markdownify import markdownify as md
            text = md(html, heading_style="ATX", strip=['script', 'style'])
        except ImportError:
            # フォールバック: タグを除去
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()

        return text[:30000]

    # =============================================
    # ツール定義（OpenAI Tool Use形式）
    # =============================================

    def get_tool_definitions(self) -> list[dict]:
        """OpenAI互換のツール定義を返す"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "ファイルを読み込む。行番号付きで表示する。offsetとlimitで範囲指定可能。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "読み込むファイルの絶対パス"},
                            "offset": {"type": "integer", "description": "読み込み開始行（0始まり）", "default": 0},
                            "limit": {"type": "integer", "description": "読み込む最大行数", "default": 2000},
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "ファイルを新規作成または完全上書きする。必ず先にReadで内容を確認してから使うこと。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "書き込むファイルの絶対パス"},
                            "content": {"type": "string", "description": "書き込む内容"},
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Edit",
                    "description": "ファイルの特定の文字列を別の文字列に置換する。old_stringはファイル内で一意である必要がある。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "編集するファイルの絶対パス"},
                            "old_string": {"type": "string", "description": "置換前の文字列（完全一致）"},
                            "new_string": {"type": "string", "description": "置換後の文字列"},
                        },
                        "required": ["file_path", "old_string", "new_string"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Glob",
                    "description": "globパターンでファイルを検索する。例: **/*.py, src/**/*.ts",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "globパターン"},
                            "path": {"type": "string", "description": "検索ベースディレクトリ", "default": "."},
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Grep",
                    "description": "正規表現でファイル内容を検索する。ripgrepを使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "正規表現パターン"},
                            "path": {"type": "string", "description": "検索対象ディレクトリ/ファイル", "default": "."},
                            "glob_pattern": {"type": "string", "description": "ファイルフィルタ（例: *.py）"},
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "シェルコマンドを実行する。find/grepの代わりにGlob/Grepを使うこと。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "実行するシェルコマンド"},
                            "timeout": {"type": "integer", "description": "タイムアウト（ミリ秒）", "default": 120000},
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "WebSearch",
                    "description": "Webを検索する",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ"},
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "WebFetch",
                    "description": "URLからコンテンツを取得してMarkdownに変換する",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "取得するURL"},
                            "prompt": {"type": "string", "description": "取得後に注目すべき点", "default": ""},
                        },
                        "required": ["url"]
                    }
                }
            },
        ]

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:
        """ツール名と引数からツールを実行"""
        handlers = {
            "Read": lambda i: self.read(**i),
            "Write": lambda i: self.write(**i),
            "Edit": lambda i: self.edit(**i),
            "Glob": lambda i: self.glob(**i),
            "Grep": lambda i: self.grep(**i),
            "Bash": lambda i: self.bash(**i),
            "WebSearch": lambda i: self.web_search(**i),
            "WebFetch": lambda i: self.web_fetch(**i),
        }

        handler = handlers.get(tool_name)
        if not handler:
            return f"エラー: 不明なツール: {tool_name}"

        try:
            return await handler(tool_input)
        except TypeError as e:
            return f"エラー: ツール引数が正しくありません: {e}"
        except Exception as e:
            return f"ツール実行エラー ({tool_name}): {e}"
```

### context_manager.py: コンテキスト管理

```python
# coding_agent/context_manager.py
import json
import tiktoken
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI

class TokenCounter:
    """トークン数カウンター（tiktoken使用）"""

    def __init__(self):
        # cl100k_base はGPT-4系のエンコーダ
        # ローカルモデルでは近似値として使用
        try:
            self.enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.enc = None

    def count(self, text: str) -> int:
        if self.enc:
            return len(self.enc.encode(text))
        # フォールバック: 文字数 / 3.5 で近似
        return len(text) // 4

    def count_messages(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        total += self.count(json.dumps(item))
            else:
                total += self.count(str(content))
        return total


class ContextManager:
    """コンテキストウィンドウ管理"""

    def __init__(self, client: AsyncOpenAI, model: str, config):
        self.client = client
        self.model = model
        self.config = config
        self.counter = TokenCounter()
        self.messages: list[dict] = []
        self.system_prompt: str = ""

    def add_message(self, role: str, content: str | list):
        """メッセージを追加"""
        self.messages.append({"role": role, "content": content})

    def get_token_count(self) -> int:
        """現在のコンテキストのトークン数"""
        total = self.counter.count(self.system_prompt)
        total += self.counter.count_messages(self.messages)
        return total

    async def compress_if_needed(self):
        """閾値を超えたらコンテキストを圧縮"""
        if self.get_token_count() < self.config.compress_threshold:
            return  # 圧縮不要

        # 古いメッセージを要約
        # 最近の5往復（10メッセージ）は保持
        keep_recent = 10
        if len(self.messages) <= keep_recent:
            return

        old_messages = self.messages[:-keep_recent]
        recent_messages = self.messages[-keep_recent:]

        # LLMに要約させる
        summary_prompt = "以下の会話を200字程度で要約してください:\n\n"
        for msg in old_messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)[:500]
            summary_prompt += f"[{msg['role']}]: {str(content)[:500]}\n"

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=500,
                temperature=0
            )
            summary = resp.choices[0].message.content

            # 圧縮: 要約 + 最近のメッセージ
            self.messages = [
                {"role": "system", "content": f"[過去の作業要約]\n{summary}"},
                *recent_messages
            ]
        except Exception:
            # 要約失敗時は古いメッセージを削除するだけ
            self.messages = recent_messages

    def save_session(self, session_dir: str = "sessions"):
        """セッションをJSONで保存"""
        Path(session_dir).mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path(session_dir) / f"session_{ts}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": ts,
                "system_prompt": self.system_prompt,
                "messages": self.messages
            }, f, ensure_ascii=False, indent=2)
        return str(path)

    def load_session(self, path: str):
        """保存したセッションを復元"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.system_prompt = data.get("system_prompt", "")
        self.messages = data.get("messages", [])
```

### agent_core.py: メインエージェントループ

```python
# coding_agent/agent_core.py
import json
import asyncio
from openai import AsyncOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .config import LLMConfig, AgentConfig, SYSTEM_PROMPT
from .tools import ToolExecutor
from .context_manager import ContextManager

console = Console()


class AgentCore:
    """
    メインエージェントループ
    ReAct (Reasoning + Acting) パターンで実装
    """

    def __init__(self, llm_config: LLMConfig = None, agent_config: AgentConfig = None):
        self.llm_config = llm_config or LLMConfig()
        self.agent_config = agent_config or AgentConfig()

        # OpenAI互換クライアント（vLLMに接続）
        self.client = AsyncOpenAI(
            base_url=self.llm_config.base_url,
            api_key=self.llm_config.api_key
        )

        self.tools = ToolExecutor()
        self.context = ContextManager(
            self.client,
            self.llm_config.model,
            self.agent_config
        )
        self.context.system_prompt = SYSTEM_PROMPT

    async def run(self, user_input: str) -> str:
        """
        エージェントのメインループ
        ユーザーの入力を受けて、ツールを使いながら回答を生成する
        """
        # ユーザーメッセージをコンテキストに追加
        self.context.add_message("user", user_input)

        iteration = 0
        final_response = ""

        while iteration < self.agent_config.max_iterations:
            iteration += 1

            # コンテキスト圧縮チェック
            await self.context.compress_if_needed()

            # LLMに問い合わせ（Think フェーズ）
            response = await self._call_llm()

            if response is None:
                final_response = "エラー: LLMからの応答がありません"
                break

            # ツール呼び出しがある場合（Act フェーズ）
            if response.tool_calls:
                # ツール呼び出しをコンテキストに追加
                self.context.add_message("assistant", response.content or "")

                # 全ツールを並列実行（Observe フェーズ）
                tool_results = await self._execute_tools(response.tool_calls)

                # ツール結果をコンテキストに追加
                for result in tool_results:
                    self.context.messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"]
                    })

            else:
                # ツール呼び出しなし = 最終回答
                final_response = response.content or ""
                self.context.add_message("assistant", final_response)
                break

        if iteration >= self.agent_config.max_iterations:
            final_response = f"最大反復回数({self.agent_config.max_iterations})に達しました"

        return final_response

    async def _call_llm(self):
        """LLMを呼び出す"""
        messages = [
            {"role": "system", "content": self.context.system_prompt},
            *self.context.messages
        ]

        kwargs = {
            "model": self.llm_config.model,
            "messages": messages,
            "max_tokens": self.llm_config.max_tokens,
            "temperature": self.llm_config.temperature,
        }

        # Chain-of-Thought強制（非Tool Use対応モデル向け）
        if self.agent_config.force_cot:
            kwargs["extra_body"] = {"stop_sequences": ["</thinking>"]}

        # ネイティブTool Use対応モデルの場合
        if self.agent_config.use_native_tool_call:
            kwargs["tools"] = self.tools.get_tool_definitions()
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            # 思考プロセスの表示
            if self.agent_config.show_thinking and choice.message.content:
                content = choice.message.content
                if "<thinking>" in content:
                    thinking_match = __import__('re').search(
                        r'<thinking>(.*?)</thinking>', content, __import__('re').DOTALL
                    )
                    if thinking_match:
                        console.print(Panel(
                            thinking_match.group(1).strip(),
                            title="[dim]思考プロセス[/dim]",
                            style="dim"
                        ))

            return choice.message

        except Exception as e:
            console.print(f"[red]LLMエラー: {e}[/red]")
            return None

    async def _execute_tools(self, tool_calls) -> list[dict]:
        """複数のツール呼び出しを並列実行"""

        async def execute_one(tc) -> dict:
            tool_name = tc.function.name
            try:
                tool_input = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                return {
                    "tool_call_id": tc.id,
                    "content": "エラー: ツール引数のJSONパースに失敗しました"
                }

            # ツール実行前の表示
            console.print(f"[cyan]ツール実行:[/cyan] {tool_name}")
            if tool_input:
                first_key = next(iter(tool_input))
                console.print(f"  {first_key}: {str(tool_input[first_key])[:100]}")

            result = await self.tools.dispatch(tool_name, tool_input)

            # 結果の表示（短縮）
            result_preview = str(result)[:200]
            console.print(f"[green]結果:[/green] {result_preview}...")

            return {"tool_call_id": tc.id, "content": result}

        # 全ツールを並列実行
        results = await asyncio.gather(*[execute_one(tc) for tc in tool_calls])
        return list(results)
```

### main.py: CLIエントリポイント

```python
# coding_agent/main.py
import asyncio
import typer
from rich.console import Console
from rich.panel import Panel

from .config import LLMConfig, AgentConfig
from .agent_core import AgentCore

app = typer.Typer(help="AIコーディングエージェント")
console = Console()


@app.command()
def main(
    query: str = typer.Option(None, "--query", "-q", help="シングルクエリモード"),
    model: str = typer.Option(None, "--model", "-m", help="使用モデル"),
    base_url: str = typer.Option(None, "--base-url", help="vLLMエンドポイント"),
    show_thinking: bool = typer.Option(False, "--show-thinking", help="思考プロセスを表示"),
    no_native_tools: bool = typer.Option(False, "--no-native-tools", help="テキスト解析フォールバック"),
    max_iter: int = typer.Option(50, "--max-iter", help="最大反復回数"),
):
    """AIコーディングエージェントを起動する"""

    llm_config = LLMConfig()
    if model:
        llm_config.model = model
    if base_url:
        llm_config.base_url = base_url

    agent_config = AgentConfig()
    agent_config.show_thinking = show_thinking
    agent_config.use_native_tool_call = not no_native_tools
    agent_config.max_iterations = max_iter

    agent = AgentCore(llm_config, agent_config)

    if query:
        # シングルクエリモード
        asyncio.run(_single_query(agent, query))
    else:
        # 対話モード
        asyncio.run(_interactive(agent))


async def _single_query(agent: AgentCore, query: str):
    console.print(Panel(f"[bold]クエリ:[/] {query}", expand=False))
    result = await agent.run(query)
    console.print(Panel(result, title="[bold green]回答[/bold green]"))


async def _interactive(agent: AgentCore):
    console.print(Panel(
        "[bold cyan]AIコーディングエージェント[/bold cyan]\n"
        "終了するには 'exit' または Ctrl+C",
        expand=False
    ))

    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("終了します")
                break

            result = await agent.run(user_input)
            console.print(Panel(result, title="[bold green]回答[/bold green]"))

        except KeyboardInterrupt:
            console.print("\n終了します")
            break
        except Exception as e:
            console.print(f"[red]エラー: {e}[/red]")


if __name__ == "__main__":
    app()
```

### 起動方法

```bash
# パッケージとして起動
uv run python -m coding_agent.main

# シングルクエリ
uv run python -m coding_agent.main -q "src/以下のPythonファイルを一覧して"

# 思考プロセス表示
uv run python -m coding_agent.main -q "バグを修正して" --show-thinking

# テキスト解析フォールバック（Tool Use非対応モデル）
uv run python -m coding_agent.main --no-native-tools

# カスタムエンドポイント
uv run python -m coding_agent.main \
    --base-url http://localhost:8001/v1 \
    --model mistralai/Codestral-22B-v0.1
```

---

## 6. Extended Thinking（深い推論）

Claude CodeはClaude Opus 4.6の「Extended Thinking」機能を使って複雑な問題を深く考えます。ローカルモデルで同等の機能を実現する4つの手法を紹介します。

### 手法1: Chain-of-Thought（CoT）強制

最も基本的な手法。システムプロンプトで`<thinking>`タグを強制します。

```python
# thinking.py - Chain-of-Thought実装
from openai import AsyncOpenAI
import re

async def chain_of_thought(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    max_thinking_tokens: int = 2000
) -> tuple[str, str]:
    """
    CoTプロンプトで思考を強制する
    Returns: (thinking, answer)
    """

    cot_system = """あなたは段階的に思考するAIアシスタントです。
回答する前に必ず以下の形式で思考プロセスを示してください:

<thinking>
1. 問題の理解: ...
2. 必要な情報: ...
3. 解決アプローチ: ...
4. 実行計画: ...
</thinking>

<answer>
最終回答をここに書く
</answer>"""

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": cot_system},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_thinking_tokens + 1000,
        temperature=0.3
    )

    content = response.choices[0].message.content

    # thinkingとanswerを抽出
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
    answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)

    thinking = thinking_match.group(1).strip() if thinking_match else ""
    answer = answer_match.group(1).strip() if answer_match else content

    return thinking, answer
```

### 手法2: Self-Reflection（自己批判）

生成→批判→修正の3段階で精度を高めます。

```python
async def self_reflection(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    max_iterations: int = 2
) -> str:
    """
    自己批判による品質改善
    生成 → 批判 → 修正 を繰り返す
    """

    # 初回生成
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7
    )
    current_answer = response.choices[0].message.content

    for i in range(max_iterations):
        # 批判プロンプト
        critic_prompt = f"""以下の回答を批判的に評価してください。
問題点、不正確な点、改善できる点を指摘してください。

元の質問: {prompt}

回答:
{current_answer}

批判的評価（問題点を箇条書きで）:"""

        critic_resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": critic_prompt}],
            max_tokens=500,
            temperature=0.3
        )
        criticism = critic_resp.choices[0].message.content

        # 修正プロンプト
        refine_prompt = f"""元の質問に対する回答を改善してください。

元の質問: {prompt}

前の回答:
{current_answer}

指摘された問題点:
{criticism}

改善された回答:"""

        refine_resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": refine_prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        current_answer = refine_resp.choices[0].message.content

    return current_answer
```

### 手法3: Tree-of-Thought（複数候補探索）

N個の候補を生成してスコアリングし、最良を選びます。

```python
async def tree_of_thought(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    num_branches: int = 3,
    depth: int = 2
) -> str:
    """
    Tree-of-Thoughtで複数の思考パスを探索
    num_branches: 各ステップで生成する候補数
    depth: 探索の深さ
    """

    async def generate_candidates(context: str, n: int) -> list[str]:
        """複数の次のステップ候補を生成"""
        tasks = []
        for _ in range(n):
            task = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": context}],
                max_tokens=500,
                temperature=0.8  # 多様性のため高め
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return [r.choices[0].message.content for r in responses]

    async def score_candidate(context: str, candidate: str) -> float:
        """候補の品質をスコアリング"""
        score_prompt = f"""以下の思考ステップを0.0〜1.0でスコアリングしてください。
数字のみを回答してください。

元の問題: {prompt}
思考ステップ: {candidate}

スコア（0.0-1.0）:"""

        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": score_prompt}],
            max_tokens=10,
            temperature=0
        )
        try:
            return float(resp.choices[0].message.content.strip())
        except ValueError:
            return 0.5

    # 初期候補を生成
    initial_prompt = f"次の問題を解く最初のステップを示してください:\n{prompt}"
    candidates = await generate_candidates(initial_prompt, num_branches)

    # 各深さでベスト候補を選択して展開
    best_path = []
    for d in range(depth):
        # 候補をスコアリング
        scores = await asyncio.gather(*[
            score_candidate(prompt, c) for c in candidates
        ])

        # ベスト候補を選択
        best_idx = scores.index(max(scores))
        best_candidate = candidates[best_idx]
        best_path.append(best_candidate)

        if d < depth - 1:
            # 次のステップの候補を生成
            context = f"問題: {prompt}\n\n前のステップ:\n" + "\n".join(best_path)
            next_prompt = f"{context}\n\n次のステップ:"
            candidates = await generate_candidates(next_prompt, num_branches)

    # 最終回答の生成
    final_context = f"問題: {prompt}\n\n思考過程:\n" + "\n".join(best_path)
    final_prompt = f"{final_context}\n\n最終回答:"

    final_resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": final_prompt}],
        max_tokens=1000,
        temperature=0.3
    )

    return final_resp.choices[0].message.content
```

### 手法4: Best-of-N（並列生成して最良を選択）

```python
async def best_of_n(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    n: int = 5,
    judge_model: str = None
) -> str:
    """
    N個の回答を並列生成してベストを選ぶ
    judge_model: 評価に別モデルを使う場合（None=同じモデル）
    """

    # N個の回答を並列生成
    tasks = [
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        for _ in range(n)
    ]

    responses = await asyncio.gather(*tasks)
    candidates = [r.choices[0].message.content for r in responses]

    # ジャッジモデルで評価
    judge = judge_model or model
    numbered_candidates = "\n\n".join([
        f"回答{i+1}:\n{c}" for i, c in enumerate(candidates)
    ])

    judge_prompt = f"""以下の{n}個の回答を評価し、最も正確・有用・完全な回答の番号のみを答えてください。

質問: {prompt}

{numbered_candidates}

最も良い回答の番号（1〜{n}）:"""

    judge_resp = await client.chat.completions.create(
        model=judge,
        messages=[{"role": "user", "content": judge_prompt}],
        max_tokens=5,
        temperature=0
    )

    try:
        best_num = int(judge_resp.choices[0].message.content.strip()) - 1
        best_num = max(0, min(n-1, best_num))  # 範囲チェック
    except ValueError:
        best_num = 0  # パース失敗時は最初の回答

    return candidates[best_num]
```

### 自動モード選択

```python
from enum import Enum

class ThinkingMode(Enum):
    AUTO = "auto"
    COT = "cot"              # Chain-of-Thought
    SELF_REFLECTION = "sr"   # Self-Reflection
    TREE_OF_THOUGHT = "tot"  # Tree-of-Thought
    BEST_OF_N = "bon"        # Best-of-N

async def think(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    mode: ThinkingMode = ThinkingMode.AUTO
) -> str:
    """タスクに応じて最適な思考手法を自動選択"""

    if mode == ThinkingMode.AUTO:
        # タスクの複雑さで自動判定
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["デバッグ", "バグ", "エラー", "修正"]):
            # デバッグ系: Self-Reflectionが有効
            mode = ThinkingMode.SELF_REFLECTION
        elif any(kw in prompt_lower for kw in ["設計", "アーキテクチャ", "計画"]):
            # 設計系: Tree-of-Thoughtが有効
            mode = ThinkingMode.TREE_OF_THOUGHT
        elif len(prompt) > 500:
            # 長いプロンプト: CoTが基本
            mode = ThinkingMode.COT
        else:
            # 短いプロンプト: Best-of-Nで品質向上
            mode = ThinkingMode.BEST_OF_N

    if mode == ThinkingMode.COT:
        _, answer = await chain_of_thought(client, model, prompt)
        return answer
    elif mode == ThinkingMode.SELF_REFLECTION:
        return await self_reflection(client, model, prompt)
    elif mode == ThinkingMode.TREE_OF_THOUGHT:
        return await tree_of_thought(client, model, prompt)
    elif mode == ThinkingMode.BEST_OF_N:
        return await best_of_n(client, model, prompt)
    else:
        raise ValueError(f"不明なThinkingMode: {mode}")
```


---

## 7. マルチモデルルーティング

タスクの種類に応じて最適なモデルに振り分けることで、コスト効率と品質を両立できます。

### モデルロールの定義

```python
# router.py
from enum import Enum
from dataclasses import dataclass

class ModelRole(Enum):
    CODING = "coding"           # コーディング専用
    REASONING = "reasoning"     # 汎用推論
    LIGHTWEIGHT = "lightweight" # 軽量・高速
    SPECIALIZED = "specialized" # 専門分野（ファインチューニング済み）
    ULTRALIGHT = "ultralight"   # 超軽量（分類等）

@dataclass
class ModelEndpoint:
    role: ModelRole
    model_id: str
    base_url: str
    description: str
    vram_gb: float

# モデル設定（自分の環境に合わせて変更）
MODEL_REGISTRY = [
    ModelEndpoint(
        role=ModelRole.CODING,
        model_id="mistralai/Codestral-22B-v0.1",
        base_url="http://localhost:8001/v1",
        description="コーディング専用モデル",
        vram_gb=24.0
    ),
    ModelEndpoint(
        role=ModelRole.REASONING,
        model_id="meta-llama/Llama-3.1-70B-Instruct",
        base_url="http://localhost:8002/v1",
        description="汎用推論モデル",
        vram_gb=40.0
    ),
    ModelEndpoint(
        role=ModelRole.LIGHTWEIGHT,
        model_id="google/gemma-2-9b-it",
        base_url="http://localhost:8003/v1",
        description="軽量・高速モデル",
        vram_gb=10.0
    ),
    ModelEndpoint(
        role=ModelRole.ULTRALIGHT,
        model_id="microsoft/Phi-3-mini-4k-instruct",
        base_url="http://localhost:8004/v1",
        description="超軽量モデル（分類・要約）",
        vram_gb=4.0
    ),
]
```

### ルーティングロジック

```python
import re
from openai import AsyncOpenAI

# タスク分類キーワード
CODING_KEYWORDS = [
    r'\bコード\b', r'\bプログラム\b', r'\b実装\b', r'\bデバッグ\b',
    r'\bバグ\b', r'\bテスト\b', r'\bリファクタ\b', r'\bAPI\b',
    r'\bclass\b', r'\bdef\b', r'\bfunction\b', r'\bimport\b',
    r'\.py\b', r'\.ts\b', r'\.js\b', r'\.go\b', r'\.rs\b',
]

LIGHTWEIGHT_KEYWORDS = [
    r'\b要約\b', r'\b分類\b', r'\b翻訳\b', r'\byes/no\b',
    r'\bTrue/False\b', r'^.{0,50}$',  # 短いプロンプト
]

SPECIALIZED_KEYWORDS_SPACE = [
    r'\b宇宙\b', r'\b衛星\b', r'\b軌道\b', r'\bJERG\b', r'\bNASA\b',
    r'\bJAXA\b', r'\b推進\b', r'\b熱制御\b', r'\bMLI\b',
]


class ModelRouter:
    """タスクを分析して最適なモデルを選択"""

    def __init__(self, registry: list[ModelEndpoint] = None):
        self.registry = registry or MODEL_REGISTRY
        self._health_cache: dict[str, bool] = {}

    def classify_task(self, prompt: str) -> ModelRole:
        """プロンプトを分析してタスク種別を判定"""
        # キーワードスコアリング
        scores = {role: 0 for role in ModelRole}

        for pattern in CODING_KEYWORDS:
            if re.search(pattern, prompt, re.IGNORECASE):
                scores[ModelRole.CODING] += 1

        for pattern in LIGHTWEIGHT_KEYWORDS:
            if re.search(pattern, prompt, re.IGNORECASE):
                scores[ModelRole.LIGHTWEIGHT] += 1

        for pattern in SPECIALIZED_KEYWORDS_SPACE:
            if re.search(pattern, prompt, re.IGNORECASE):
                scores[ModelRole.SPECIALIZED] += 2  # 専門語は重み2倍

        # プロンプトの長さで調整
        if len(prompt) > 1000:
            scores[ModelRole.REASONING] += 2
        elif len(prompt) < 100:
            scores[ModelRole.LIGHTWEIGHT] += 1

        # 最高スコアのロールを返す
        best_role = max(scores, key=scores.get)

        # 全て0の場合はデフォルト
        if scores[best_role] == 0:
            return ModelRole.REASONING

        return best_role

    def get_endpoint(self, role: ModelRole) -> ModelEndpoint | None:
        """ロールに対応するエンドポイントを取得"""
        for ep in self.registry:
            if ep.role == role:
                return ep
        # フォールバック: REASONINGを返す
        for ep in self.registry:
            if ep.role == ModelRole.REASONING:
                return ep
        return self.registry[0] if self.registry else None

    async def check_health(self, endpoint: ModelEndpoint) -> bool:
        """エンドポイントの死活確認"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{endpoint.base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False

    async def route(self, prompt: str) -> tuple[AsyncOpenAI, str]:
        """
        プロンプトを分析してクライアントとモデルIDを返す
        Returns: (client, model_id)
        """
        role = self.classify_task(prompt)
        endpoint = self.get_endpoint(role)

        if endpoint is None:
            raise RuntimeError("利用可能なモデルエンドポイントがありません")

        # ヘルスチェック（失敗したらREASONINGにフォールバック）
        if not await self.check_health(endpoint):
            fallback = self.get_endpoint(ModelRole.REASONING)
            if fallback and await self.check_health(fallback):
                endpoint = fallback
            else:
                raise RuntimeError(f"モデルエンドポイントに接続できません: {endpoint.base_url}")

        client = AsyncOpenAI(
            base_url=endpoint.base_url,
            api_key="dummy"
        )
        return client, endpoint.model_id


# 使用例
async def routed_query(router: ModelRouter, prompt: str) -> str:
    client, model_id = await router.route(prompt)

    response = await client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content
```

### ルーティング統計の収集

```python
from collections import defaultdict
from datetime import datetime

class RoutingStats:
    """ルーティング統計を収集して最適化に活用"""

    def __init__(self):
        self.records = []
        self.role_counts = defaultdict(int)
        self.role_latencies = defaultdict(list)

    def record(self, role: ModelRole, latency_ms: float, success: bool):
        self.records.append({
            "timestamp": datetime.now().isoformat(),
            "role": role.value,
            "latency_ms": latency_ms,
            "success": success
        })
        self.role_counts[role] += 1
        if success:
            self.role_latencies[role].append(latency_ms)

    def summary(self) -> dict:
        return {
            role.value: {
                "count": self.role_counts[role],
                "avg_latency_ms": (
                    sum(self.role_latencies[role]) / len(self.role_latencies[role])
                    if self.role_latencies[role] else 0
                )
            }
            for role in ModelRole
        }
```

---

## 8. サブエージェント・Agent Teams

複雑なタスクを複数のサブエージェントに分割して並列実行することで、処理を高速化できます。

### サブエージェントの設計

```python
# sub_agent.py
import asyncio
import json
from dataclasses import dataclass
from openai import AsyncOpenAI


@dataclass
class SubTask:
    """サブタスクの定義"""
    task_id: str
    description: str
    context: str = ""             # 追加コンテキスト
    depends_on: list[str] = None  # 依存タスクID

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class SubTaskResult:
    """サブタスクの実行結果"""
    task_id: str
    result: str
    success: bool
    error: str = ""


class SubAgent:
    """独立したコンテキストで動作するサブエージェント"""

    def __init__(self, client: AsyncOpenAI, model: str, system_prompt: str = ""):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt or "あなたは指示されたタスクを実行するエージェントです。"

    async def execute(self, task: SubTask) -> SubTaskResult:
        """タスクを実行して結果を返す"""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # コンテキストがあれば追加
        user_content = task.description
        if task.context:
            user_content = f"コンテキスト:\n{task.context}\n\nタスク:\n{task.description}"

        messages.append({"role": "user", "content": user_content})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.3
            )
            result = response.choices[0].message.content
            return SubTaskResult(task_id=task.task_id, result=result, success=True)

        except Exception as e:
            return SubTaskResult(
                task_id=task.task_id, result="", success=False, error=str(e)
            )


class SubAgentManager:
    """複数のサブエージェントをオーケストレート"""

    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model
        self.agent = SubAgent(client, model)

    async def decompose_task(self, main_task: str) -> list[SubTask]:
        """
        オーケストレーターLLMがタスクを分割する
        Returns: 並列実行可能なサブタスクのリスト
        """
        decompose_prompt = f"""以下のタスクを並列実行可能なサブタスクに分割してください。
依存関係がある場合はdepends_onで指定してください。

タスク: {main_task}

以下のJSON形式で回答してください:
```json
[
  {{
    "task_id": "task_1",
    "description": "サブタスクの説明",
    "depends_on": []
  }},
  {{
    "task_id": "task_2",
    "description": "別のサブタスク",
    "depends_on": ["task_1"]
  }}
]
```"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": decompose_prompt}],
            max_tokens=1000,
            temperature=0
        )

        content = response.choices[0].message.content

        # JSONを抽出
        json_match = __import__('re').search(r'```json\s*(.*?)\s*```', content, __import__('re').DOTALL)
        if json_match:
            try:
                tasks_data = json.loads(json_match.group(1))
                return [SubTask(**t) for t in tasks_data]
            except (json.JSONDecodeError, TypeError):
                pass

        # フォールバック: 単一タスクとして実行
        return [SubTask(task_id="main", description=main_task)]

    async def execute_parallel(
        self,
        tasks: list[SubTask],
        completed: dict[str, str] = None
    ) -> dict[str, str]:
        """
        依存関係を考慮しながら並列実行
        Returns: {task_id: result}
        """
        if completed is None:
            completed = {}

        remaining = [t for t in tasks if t.task_id not in completed]

        while remaining:
            # 依存関係が全て完了しているタスクを抽出
            ready = [
                t for t in remaining
                if all(dep in completed for dep in t.depends_on)
            ]

            if not ready:
                # デッドロック防止
                break

            # 準備できたタスクを並列実行
            results = await asyncio.gather(*[
                self._run_with_context(task, completed)
                for task in ready
            ])

            for result in results:
                if result.success:
                    completed[result.task_id] = result.result
                else:
                    completed[result.task_id] = f"エラー: {result.error}"

            remaining = [t for t in remaining if t.task_id not in completed]

        return completed

    async def _run_with_context(
        self,
        task: SubTask,
        completed: dict[str, str]
    ) -> SubTaskResult:
        """依存タスクの結果をコンテキストとして注入して実行"""
        if task.depends_on:
            context_parts = []
            for dep_id in task.depends_on:
                if dep_id in completed:
                    context_parts.append(f"[{dep_id}の結果]\n{completed[dep_id]}")
            task.context = "\n\n".join(context_parts)

        return await self.agent.execute(task)

    async def summarize_results(
        self,
        main_task: str,
        results: dict[str, str]
    ) -> str:
        """全サブタスクの結果を統合して最終回答を生成"""
        results_text = "\n\n".join([
            f"[{task_id}]\n{result}"
            for task_id, result in results.items()
        ])

        summary_prompt = f"""以下のサブタスクの結果を統合して、最終的な回答を生成してください。

元のタスク: {main_task}

各サブタスクの結果:
{results_text}

統合された最終回答:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        return response.choices[0].message.content

    async def run(self, main_task: str) -> str:
        """
        メインのオーケストレーションフロー:
        1. タスク分解
        2. 並列実行
        3. 結果統合
        """
        # 1. タスク分解
        tasks = await self.decompose_task(main_task)

        # 2. 並列実行
        results = await self.execute_parallel(tasks)

        # 3. 統合
        if len(results) == 1:
            return list(results.values())[0]

        return await self.summarize_results(main_task, results)


# 使用例
async def demo_parallel():
    client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
    manager = SubAgentManager(client, "google/gemma-2-27b-it")

    result = await manager.run(
        "Pythonプロジェクトのsrc/ディレクトリを分析して、"
        "各ファイルの役割と改善点をまとめてください"
    )
    print(result)
```

### Anthropic Agent SDK との比較

| 機能 | Anthropic Agent SDK | 自作実装 |
|------|-------------------|---------|
| サブエージェント起動 | `Task` ツール経由 | `SubAgentManager.run()` |
| 並列実行 | 自動（内部管理） | `asyncio.gather()` |
| コンテキスト共有 | 独立（Task隔離） | `completed`辞書で受け渡し |
| モデル選択 | 同一モデルのみ | ロール別モデル切り替え可 |
| フック | PreToolUse/PostToolUse | カスタム実装 |
| セッション継続 | `resume=session_id` | JSON保存・復元 |

---

## 9. ファインチューニングと学習（専門知識の習得）

### 9.1 QLoRA/SFT基礎

### QLoRA とは

QLoRA（Quantized LoRA）は、モデルを4bit量子化した状態でLoRA（Low-Rank Adaptation）ファインチューニングを行う手法です。

```
通常のファインチューニング:
  全パラメータを更新 → 70Bモデルで280GB VRAM必要

LoRA:
  低ランク行列のみ更新 → 70Bモデルで40GB VRAM

QLoRA:
  4bit量子化 + LoRA → 70Bモデルで24GB VRAMで可能
```

### 必要なデータ量と形式

| データ量 | 期待できる効果 |
|---------|-------------|
| 500件 | 用語・スタイルの基礎習得 |
| 2,000〜5,000件 | 実用レベルの専門知識 |
| 10,000件以上 | 高品質な専門家レベル |

データフォーマット（Alpaca形式）:

```jsonl
{"instruction": "MLI（多層断熱材）の基本原理を説明してください", "input": "", "output": "MLI（Multi-Layer Insulation）は、真空中での放射熱制御に使用される断熱材です。複数の反射シート（通常はAlやMylar）とスペーサーシートを交互に積層した構造を持ちます..."}
{"instruction": "低軌道衛星のMLI設計における注意点は何ですか？", "input": "軌道高度: 500km、軌道傾斜角: 51.6度", "output": "低軌道（LEO）でのMLI設計では以下の点に注意が必要です:\n1. アウトガスリスク: 有機系接着剤..."}
```

### Unslothによるファインチューニング

```python
# finetune.py
# unsloth: https://github.com/unslothai/unsloth
# インストール: uv pip install unsloth[cu121] trl

from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset, Dataset
import json

# =============================================
# 1. モデルのロード（QLoRA設定）
# =============================================

# 4bitで量子化してロード（VRAM大幅削減）
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
    max_seq_length=4096,
    dtype=None,  # 自動検出
    load_in_4bit=True,
)

# LoRAアダプタを追加
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                     # LoRAランク（大きいほど精度↑、VRAM↑）
    target_modules=[          # 更新するモジュール
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_alpha=16,            # LoRAスケール
    lora_dropout=0.05,        # ドロップアウト
    bias="none",
    use_gradient_checkpointing="unsloth",  # VRAM30%節約
    random_state=42,
)

# =============================================
# 2. データセット準備
# =============================================

def load_jsonl_dataset(path: str) -> Dataset:
    """JSONLファイルをデータセットとして読み込む"""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return Dataset.from_list(records)

def format_alpaca(examples):
    """Alpaca形式をChatML形式に変換"""
    texts = []
    for instruction, input_text, output in zip(
        examples["instruction"],
        examples.get("input", [""] * len(examples["instruction"])),
        examples["output"]
    ):
        if input_text:
            user_msg = f"{instruction}\n\n入力: {input_text}"
        else:
            user_msg = instruction

        # ChatML形式
        text = tokenizer.apply_chat_template(
            [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": output}
            ],
            tokenize=False,
            add_generation_prompt=False
        )
        texts.append(text)
    return {"text": texts}

# データセットをロードして変換
dataset = load_jsonl_dataset("data/space_training_data.jsonl")
dataset = dataset.map(format_alpaca, batched=True)

# train/validation分割
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
eval_dataset = split["test"]

print(f"訓練データ: {len(train_dataset)}件")
print(f"検証データ: {len(eval_dataset)}件")

# =============================================
# 3. 学習の実行
# =============================================

training_args = TrainingArguments(
    output_dir="./outputs/space-llm-lora",
    num_train_epochs=3,              # エポック数（多いほど過学習リスク↑）
    per_device_train_batch_size=4,   # バッチサイズ（VRAM次第）
    gradient_accumulation_steps=4,  # 実質バッチサイズ = 4*4 = 16
    warmup_ratio=0.03,               # ウォームアップ割合
    learning_rate=2e-4,              # 学習率
    fp16=True,                       # FP16混合精度（A100ならbf16推奨）
    logging_steps=10,
    evaluation_strategy="steps",
    eval_steps=100,
    save_steps=200,
    save_total_limit=3,
    load_best_model_at_end=True,
    report_to="none",                # wandb等を使う場合は変更
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    dataset_text_field="text",
    max_seq_length=4096,
    args=training_args,
)

# 学習開始
trainer.train()

# =============================================
# 4. モデルの保存
# =============================================

# LoRAアダプタのみ保存（軽量）
model.save_pretrained("./outputs/space-llm-lora/adapter")
tokenizer.save_pretrained("./outputs/space-llm-lora/adapter")
print("LoRAアダプタを保存しました: ./outputs/space-llm-lora/adapter")

# ベースモデルにマージして保存（vLLMで使う場合）
model.save_pretrained_merged(
    "./outputs/space-llm-merged",
    tokenizer,
    save_method="merged_16bit"  # "merged_4bit_forced" でさらに軽量化可能
)
print("マージ済みモデルを保存しました: ./outputs/space-llm-merged")
```

### 学習済みモデルのvLLMへのロード

```bash
# 方法1: マージ済みモデルをそのまま起動
vllm serve ./outputs/space-llm-merged \
    --host 0.0.0.0 \
    --port 8005 \
    --dtype float16

# 方法2: LoRAアダプタを動的ロード
# （ベースモデルとアダプタを別々に管理できる）
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8005 \
    --enable-lora \
    --lora-modules space-expert=./outputs/space-llm-lora/adapter

# LoRAアダプタのモデルIDは "space-expert" として使う
# curl http://localhost:8005/v1/completions \
#   -d '{"model": "space-expert", "prompt": "..."}'
```

### データ収集の自動化

```python
# collect_training_data.py
# NASAの技術報告書からファインチューニングデータを自動収集

import httpx
import json
import asyncio
from pathlib import Path

async def collect_nasa_ntrs(
    query: str,
    max_results: int = 100,
    output_path: str = "data/nasa_collected.jsonl"
) -> int:
    """NASA NTRS（技術報告書サーバー）からデータを収集"""

    base_url = "https://ntrs.nasa.gov/api/citations/search"
    collected = []

    async with httpx.AsyncClient(timeout=30) as client:
        # 検索
        resp = await client.get(base_url, params={
            "q": query,
            "rows": max_results,
            "start": 0
        })
        data = resp.json()

        for item in data.get("hits", {}).get("hits", []):
            source = item.get("_source", {})
            abstract = source.get("abstract", "")
            title = source.get("title", "")

            if abstract and len(abstract) > 200:
                # Q&A形式に変換
                record = {
                    "instruction": f"{title}について教えてください",
                    "input": "",
                    "output": abstract
                }
                collected.append(record)

                # APIに負荷をかけないよう間隔を空ける
                await asyncio.sleep(1.0)

    # 保存
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in collected:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f"収集完了: {len(collected)}件 → {output_path}")
    return len(collected)


# 実行
asyncio.run(collect_nasa_ntrs(
    query="satellite thermal control MLI",
    max_results=200
))
```

---

### 9.2 継続事前学習（Continued Pre-Training / CPT）

### CPTとは何か

継続事前学習（CPT: Continued Pre-Training）とは、すでに汎用データで事前学習済みのモデルに対して、特定ドメインの生テキストをさらに学習させる手法です。

**SFTとの根本的な違い：**

| 項目 | SFT（Supervised Fine-Tuning） | CPT（Continued Pre-Training） |
|---|---|---|
| データ形式 | instruction/response ペア | 生テキスト（ラベルなし） |
| 目的 | 応答スタイルの習得 | ドメイン知識・語彙の習得 |
| 学習シグナル | 教師あり | 次トークン予測（自己教師あり） |
| 典型エポック数 | 1〜3 | 1〜2 |
| 学習率 | 2e-4 前後 | 5e-5 前後（低め） |

### いつCPTが必要か

以下の状況ではSFT単独では限界があり、CPTが有効です：

- 宇宙工学・航空宇宙の専門用語が大量にある（例: "ΔV", "ISP", "GEO/LEO", "TRL"）
- ベースモデルが学習していない文書形式（JERG仕様書、NASAの技術報告書など）
- 既存の語彙にない略語・造語が頻出する
- 特定言語（日本語の技術文書など）の比率がベースモデルで低い

**判断の目安:** CPTなしでSFTしたモデルが専門用語を "hallucination" するようなら、CPTを先行させる。

---

### Unslothを使ったCPT実装

#### 手順1: データ準備

生テキスト（宇宙/航空宇宙ドメインの例）を準備し、チャンク分割します。

```python
# data_prep_cpt.py
# 宇宙・航空宇宙ドメインのテキストデータ準備

from datasets import Dataset
from transformers import AutoTokenizer

# ========================================
# ステップ1: 生テキストの収集例
# ========================================
# 想定ソース:
# - JAXA技術報告書（公開PDF）
# - NASA Technical Reports Server
# - JERG（JAXA Engineering Review Guidelines）
# - arXiv宇宙工学論文

raw_texts = [
    """
    軌道力学の基本概念として、デルタV（ΔV）は軌道変換に必要な速度変化量を表す。
    ホーマン遷移軌道を用いた低軌道（LEO）から静止軌道（GEO）への遷移では、
    2回のΔVバーンが必要となる。比推力（Isp）はロケットエンジンの効率を示す指標で、
    高いIspほど推進剤消費が少ない。...
    """,
    """
    TRL（Technology Readiness Level）は技術成熟度を9段階で評価する指標である。
    TRL 1は基礎的な原理観察段階、TRL 9は実証済みシステムを意味する。
    JAXAおよびNASAの開発プログラムでは、フライトモデル移行前にTRL 6以上が要求される。
    ...
    """,
    # 実際には数百〜数千件のドキュメントを使用
]

# ========================================
# ステップ2: テキストのチャンク分割
# ========================================

def chunk_texts(texts: list[str], chunk_size: int = 2048, overlap: int = 128) -> list[str]:
    """
    長いテキストをオーバーラップ付きでチャンク分割する。
    chunk_size: トークン数ベースのチャンクサイズ
    overlap: チャンク間のオーバーラップトークン数（文脈の連続性維持）
    """
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B")

    chunks = []
    for text in texts:
        tokens = tokenizer.encode(text, add_special_tokens=False)

        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            chunks.append({"text": chunk_text})

            if end == len(tokens):
                break
            start += chunk_size - overlap  # オーバーラップ分だけ戻る

    return chunks


# ========================================
# ステップ3: Datasetオブジェクトへ変換
# ========================================

chunks = chunk_texts(raw_texts, chunk_size=2048, overlap=128)
dataset = Dataset.from_list(chunks)

# train/eval 分割（90/10）
dataset = dataset.train_test_split(test_size=0.1, seed=42)

print(f"訓練データ: {len(dataset['train'])} チャンク")
print(f"評価データ: {len(dataset['test'])} チャンク")

dataset.save_to_disk("./aerospace_cpt_dataset")
```

#### 手順2: UnslothでCPT実行

```python
# train_cpt.py
# UnslothTrainer を使った継続事前学習（CPT）

from unsloth import FastLanguageModel, UnslothTrainer, UnslothTrainingArguments
from datasets import load_from_disk
import torch

# ========================================
# ステップ1: モデルロード
# ========================================

MAX_SEQ_LENGTH = 2048
DTYPE = torch.bfloat16  # Ampere以降のGPUはbfloat16推奨
LOAD_IN_4BIT = True     # VRAM節約のためQLoRA使用

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="meta-llama/Llama-3.2-3B",  # ベースモデル（Instructなし）
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=DTYPE,
    load_in_4bit=LOAD_IN_4BIT,
)

# ========================================
# ステップ2: LoRAアダプター設定（CPT向け）
# ========================================
# CPTではembed_tokensとlm_headも学習対象に含める（新語彙習得のため）

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=[
        # 通常のアテンション・FFN
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
        # CPT専用: 埋め込み層と出力層も含める
        "embed_tokens",
        "lm_head",
    ],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ========================================
# ステップ3: データセット準備
# ========================================

dataset = load_from_disk("./aerospace_cpt_dataset")

def format_for_cpt(examples):
    """CPTはシンプルに生テキストをそのまま使う"""
    return {"text": examples["text"]}

# ========================================
# ステップ4: UnslothTrainer でCPT実行
# ========================================
# UnslothTrainer の特徴:
#   - embedding_learning_rate で埋め込み層の学習率を分離できる
#   - embed_tokens/lm_head はメイン学習率の 1/10 程度に抑えるのが推奨

trainer = UnslothTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    dataset_num_proc=4,
    args=UnslothTrainingArguments(
        # --- 基本設定 ---
        output_dir="./aerospace_cpt_output",
        num_train_epochs=1,           # CPTは1〜2エポックが標準
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=8,

        # --- 学習率 (CPTの重要設定) ---
        learning_rate=5e-5,           # SFTより低め（通常SFTの約1/4）
        embedding_learning_rate=5e-6, # embed_tokens/lm_headはさらに低く（1/10）
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,

        # --- 精度・最適化 ---
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        optim="adamw_8bit",
        weight_decay=0.01,

        # --- 評価・保存 ---
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        logging_steps=20,
        load_best_model_at_end=True,

        # --- シード ---
        seed=42,
    ),
)

print("CPT開始...")
trainer_stats = trainer.train()
print(f"CPT完了: {trainer_stats.metrics}")

# CPTアダプターを保存（後でSFTに使用）
model.save_pretrained("./aerospace_cpt_adapter")
tokenizer.save_pretrained("./aerospace_cpt_adapter")
print("CPTアダプター保存完了")
```

---

### ハイパーパラメータの選び方

| パラメータ | CPT推奨値 | 理由 |
|---|---|---|
| `learning_rate` | 5e-5 〜 1e-4 | 高すぎるとCatastrophic Forgettingが悪化 |
| `embedding_learning_rate` | 学習率の1/10 | 埋め込みの急激な変化を防ぐ |
| `num_train_epochs` | 1〜2 | 3エポック以上は過学習・知識消失リスク |
| `warmup_ratio` | 0.03〜0.1 | 学習初期の不安定さを緩和 |
| `weight_decay` | 0.01〜0.1 | 過学習防止 |
| `r` (LoRA rank) | 16〜64 | CPTはSFTより高rankが有効なことが多い |

---

### Catastrophic Forgetting への対策

CPTの最大リスクは、新ドメインを学習する過程で汎用能力が劣化することです。

```python
# catastrophic_forgetting_mitigation.py

# 対策1: リプレイバッファ（元の汎用データを一定割合混ぜる）
from datasets import concatenate_datasets, load_dataset

# 宇宙ドメインデータ
domain_dataset = load_from_disk("./aerospace_cpt_dataset")["train"]

# 汎用テキスト（WikipediaやC4から少量サンプル）
# 比率は domain : general = 80 : 20 程度が目安
general_dataset = load_dataset("wikipedia", "20220301.en", split="train[:5000]")
general_dataset = general_dataset.select_columns(["text"])

# 混合データセット作成
from datasets import Dataset
mixed_samples = (
    domain_dataset.shuffle(seed=42).select(range(min(len(domain_dataset), 8000)))
)
general_samples = general_dataset.shuffle(seed=42).select(range(2000))

mixed_dataset = concatenate_datasets([mixed_samples, general_samples]).shuffle(seed=42)
print(f"混合データセット: {len(mixed_dataset)} 件 (domain 80% + general 20%)")


# 対策2: LoRA rank を抑える（元のウェイトへの影響を最小化）
# r=8〜16 で済む場合はそちらを優先

# 対策3: CPT後に汎用タスクで評価して劣化を確認
def check_catastrophic_forgetting(model, tokenizer):
    """
    CPT前後で一般的な質問応答タスクの品質を比較する簡易チェック
    """
    test_prompts = [
        "What is the capital of France?",
        "Explain Newton's first law of motion.",
        "Write a simple Python function to reverse a string.",
    ]

    from unsloth import FastLanguageModel
    FastLanguageModel.for_inference(model)

    for prompt in test_prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=100, temperature=0.7)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"Q: {prompt}")
        print(f"A: {response[len(prompt):]}")
        print("---")
```

---

### 9.3 DPO/RLHF/ORPO（強化学習・選好最適化）

### RLHF vs DPO vs ORPO 比較

| 項目 | RLHF (PPO) | DPO | ORPO |
|---|---|---|---|
| **アルゴリズム** | 強化学習（PPO） | 直接選好最適化 | オッズ比選好最適化 |
| **必要データ** | 選好ペア + ランキング | chosen/rejected ペア | chosen/rejected ペア |
| **参照モデル** | 必要（SFTモデル） | 必要（SFTモデル） | **不要** |
| **報酬モデル** | 別途学習が必要 | 不要 | 不要 |
| **計算コスト** | 非常に高い（モデル4つ分） | 中程度（モデル2つ分） | **低い（モデル1つ分）** |
| **実装難易度** | 高い | 中程度 | 低い |
| **安定性** | 不安定になりやすい | 比較的安定 | 安定 |
| **学習段階** | CPT → SFT → RM学習 → PPO | CPT → SFT → DPO | CPT → SFT+ORPO（同時） |
| **主な用途** | ChatGPT, InstructGPT | モデルのアラインメント全般 | SFTとアラインメントの効率化 |

---

### DPOの仕組み

DPO（Direct Preference Optimization）は、人間の選好データから直接ポリシーを最適化する手法です。従来のRLHFが「報酬モデルを学習 → PPOで強化学習」という2段階を必要とするのに対し、DPOは数学的に同値な目的関数を導出し、単純な分類損失として解きます。

**損失関数の直感的な意味:**
- chosenの回答をrejectedより高い確率で生成するよう学習
- ただし参照モデル（SFT済みモデル）から大きく外れないよう制約

---

### ORPOの仕組み

ORPO（Odds Ratio Preference Optimization）は参照モデルを必要とせず、SFTとアラインメントを1つの目的関数で同時最適化します。

**オッズ比による直感:**
- `odds(y|x) = P(y|x) / (1 - P(y|x))`
- chosenのオッズとrejectedのオッズの比を大きくするよう学習
- 参照モデルとの比較ではなく「現在のモデルが生成する2つの応答間の相対的確率」を最適化

---

### 選好データの作り方

#### 方法1: 人手アノテーション

```python
# preference_data_human.py
# 宇宙/航空宇宙ドメインでの選好データ作成例

import json

# 選好ペアの例（宇宙工学ドメイン）
preference_examples = [
    {
        "prompt": [
            {"role": "user", "content": "ホーマン遷移軌道のΔVを計算する方法を教えてください。"}
        ],
        "chosen": [
            {"role": "assistant", "content": (
                "ホーマン遷移軌道のΔVは2段階で計算します。\n\n"
                "**第1バーン（LEO → 遷移軌道）:**\n"
                "ΔV₁ = √(μ/r₁) × (√(2r₂/(r₁+r₂)) - 1)\n\n"
                "**第2バーン（遷移軌道 → GEO）:**\n"
                "ΔV₂ = √(μ/r₂) × (1 - √(2r₁/(r₁+r₂)))\n\n"
                "ここで μ = 3.986×10¹⁴ m³/s²（地球の重力定数）、"
                "r₁は初期軌道半径、r₂は目標軌道半径です。\n\n"
                "LEO(400km)からGEO(35786km)への遷移では合計ΔV ≈ 3.9 km/s が必要です。"
            )}
        ],
        "rejected": [
            {"role": "assistant", "content": (
                "ホーマン遷移軌道は楕円軌道を使った軌道変換手法です。"
                "ΔVを計算するには速度の差を求めます。"
                "詳細な計算式は教科書を参照してください。"
            )}
        ]
    },
    {
        "prompt": [
            {"role": "user", "content": "比推力（Isp）とは何ですか？"}
        ],
        "chosen": [
            {"role": "assistant", "content": (
                "比推力（Isp: Specific Impulse）は推進剤1単位あたりの推力の継続時間を示す指標で、"
                "エンジン効率を表します。\n\n"
                "**定義:** Isp = F / (ṁ × g₀)\n"
                "- F: 推力 [N]\n"
                "- ṁ: 推進剤質量流量 [kg/s]\n"
                "- g₀: 標準重力加速度 (9.80665 m/s²)\n\n"
                "**典型値:**\n"
                "- 固体燃料ロケット: 250〜300 s\n"
                "- 液体水素/液体酸素: 450〜460 s（H-IIAのLE-7Aなど）\n"
                "- イオンエンジン: 1000〜10000 s\n\n"
                "Ispが高いほど同じ推進剤でより多くのΔVを得られます（ツィオルコフスキーの公式）。"
            )}
        ],
        "rejected": [
            {"role": "assistant", "content": (
                "比推力はロケットエンジンの効率を表す指標です。"
                "値が大きいほど効率が良いエンジンです。"
            )}
        ]
    },
]

# JSONL形式で保存
with open("./aerospace_preference_data.jsonl", "w", encoding="utf-8") as f:
    for example in preference_examples:
        f.write(json.dumps(example, ensure_ascii=False) + "\n")

print(f"選好データ作成完了: {len(preference_examples)} ペア")
```

#### 方法2: LLM-as-Judge で自動生成

```python
# preference_data_llm_judge.py
# 強力なLLM（Claude等）を使って自動的にchosen/rejectedを生成・評価

import json
import random
from openai import OpenAI  # Cerebras API（OpenAI互換）を使用

client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key="YOUR_CEREBRAS_API_KEY",
)

# ========================================
# ステップ1: 複数の応答を生成
# ========================================

def generate_multiple_responses(prompt: str, model: str, n: int = 4) -> list[str]:
    """同じプロンプトに対して複数の応答を生成"""
    responses = []
    for _ in range(n):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # 多様性のために高めに設定
            max_tokens=512,
        )
        responses.append(response.choices[0].message.content)
    return responses


# ========================================
# ステップ2: LLM-as-Judge で品質評価
# ========================================

JUDGE_PROMPT_TEMPLATE = """あなたは宇宙工学・航空宇宙分野の専門家として、以下の2つの回答を評価してください。

**質問:**
{question}

**回答A:**
{response_a}

**回答B:**
{response_b}

以下の基準で評価し、JSONで回答してください：
1. 技術的正確性（専門用語・数式・数値の正確さ）
2. 情報の完全性（重要な情報の網羅度）
3. 実用性（実際の宇宙開発業務で使えるか）
4. 明確さ（説明の論理性・わかりやすさ）

回答形式:
{{
  "winner": "A" または "B",
  "reason": "選択理由（50字以内）",
  "score_a": 1〜10,
  "score_b": 1〜10
}}"""


def judge_responses(question: str, response_a: str, response_b: str) -> dict:
    """LLMを使って2つの応答を比較評価"""
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        response_a=response_a,
        response_b=response_b,
    )

    result = client.chat.completions.create(
        model="gpt-oss-120b",  # Cerebras API経由で利用
        messages=[{"role": "user", "content": judge_prompt}],
        temperature=0.1,  # 判定は低温で安定させる
        max_tokens=256,
    )

    try:
        return json.loads(result.choices[0].message.content)
    except json.JSONDecodeError:
        return None


# ========================================
# ステップ3: データセット自動生成
# ========================================

def create_preference_dataset(
    questions: list[str],
    target_model: str,
    output_path: str,
):
    """質問リストから選好データセットを自動生成"""
    preference_pairs = []

    for question in questions:
        print(f"処理中: {question[:50]}...")

        # 複数応答を生成
        responses = generate_multiple_responses(question, target_model, n=4)

        # ランダムに2つ選んでjudge
        a, b = random.sample(responses, 2)
        judgment = judge_responses(question, a, b)

        if judgment is None:
            continue

        if judgment["winner"] == "A":
            chosen, rejected = a, b
        else:
            chosen, rejected = b, a

        # スコア差が小さいペアはノイズになるのでスキップ
        score_diff = abs(judgment.get("score_a", 5) - judgment.get("score_b", 5))
        if score_diff < 2:
            continue

        preference_pairs.append({
            "prompt": [{"role": "user", "content": question}],
            "chosen": [{"role": "assistant", "content": chosen}],
            "rejected": [{"role": "assistant", "content": rejected}],
        })

    # JSONL保存
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in preference_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"生成完了: {len(preference_pairs)} ペア → {output_path}")
    return preference_pairs


# 使用例
aerospace_questions = [
    "ツィオルコフスキーのロケット方程式を導出してください。",
    "再突入カプセルの熱シールドに使われる材料の特性を説明してください。",
    "GEO衛星とLEO衛星のメリット・デメリットを比較してください。",
    "姿勢制御にリアクションホイールが使われる理由を説明してください。",
]

# create_preference_dataset(
#     questions=aerospace_questions,
#     target_model="YOUR_FINE_TUNED_MODEL",
#     output_path="./aerospace_preference_auto.jsonl",
# )
```

---

### DPOの実装コード（Unsloth + TRL）

```python
# train_dpo.py
# Unsloth + trl.DPOTrainer を使ったDPO学習

from unsloth import FastLanguageModel
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig
from datasets import load_dataset, Dataset
import json
import torch

# ========================================
# ステップ1: SFT済みモデルをロード
# ========================================
# DPOはSFT後のモデルを出発点とする（CPT → SFT → DPO の順）

MAX_SEQ_LENGTH = 2048

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="./aerospace_sft_adapter",  # SFT済みモデル
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=torch.bfloat16,
    load_in_4bit=True,
)

# DPO用のLoRAアダプター設定
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ========================================
# ステップ2: 選好データセットの準備
# ========================================

def load_preference_jsonl(path: str) -> Dataset:
    """JSONL形式の選好データをDatasetに変換"""
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return Dataset.from_list(data)

preference_dataset = load_preference_jsonl("./aerospace_preference_data.jsonl")
split = preference_dataset.train_test_split(test_size=0.1, seed=42)

# ========================================
# ステップ3: DPOTrainer の設定
# ========================================

dpo_config = DPOConfig(
    output_dir="./aerospace_dpo_output",

    # --- 学習設定 ---
    num_train_epochs=1,              # DPOは1〜2エポックが標準
    per_device_train_batch_size=2,   # DPOはchosenとrejectedを同時処理するためVRAM多い
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,

    # --- 学習率 ---
    learning_rate=5e-6,              # DPOはSFTよりさらに低め
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,

    # --- DPO固有パラメータ ---
    beta=0.1,                        # KLダイバージェンスの強さ（0.1〜0.5）
    loss_type="sigmoid",             # デフォルト（IPO使いたい場合は "ipo"）

    # --- 精度 ---
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    optim="adamw_8bit",

    # --- 評価・保存 ---
    eval_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=100,
    logging_steps=10,

    # --- シーケンス長 ---
    max_length=MAX_SEQ_LENGTH,
    max_prompt_length=1024,
)

trainer = DPOTrainer(
    model=model,
    ref_model=None,  # Noneの場合、初期モデルが参照モデルとして使用される
    args=dpo_config,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    processing_class=tokenizer,
)

print("DPO学習開始...")
trainer_stats = trainer.train()
print(f"DPO完了: {trainer_stats.metrics}")

model.save_pretrained("./aerospace_dpo_adapter")
tokenizer.save_pretrained("./aerospace_dpo_adapter")
```

---

### ORPOの実装コード

```python
# train_orpo.py
# trl.ORPOTrainer を使った学習（SFTとアラインメント同時最適化）

from unsloth import FastLanguageModel
from trl import ORPOConfig, ORPOTrainer
from datasets import Dataset
import json
import torch

# ========================================
# ORPOの特徴:
# - 参照モデル不要（メモリ効率◎）
# - SFTとアラインメントを1ステップで実行
# - DPO比で計算コスト約50%削減
# ========================================

MAX_SEQ_LENGTH = 2048

# ベースモデルをロード（ORPOはSFT済みモデルでも可、ベースモデルでも可）
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="./aerospace_cpt_adapter",  # CPT後のアダプター
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=torch.bfloat16,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# データセット
def load_preference_jsonl(path: str) -> Dataset:
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return Dataset.from_list(data)

preference_dataset = load_preference_jsonl("./aerospace_preference_data.jsonl")
split = preference_dataset.train_test_split(test_size=0.1, seed=42)

# ORPO設定
orpo_config = ORPOConfig(
    output_dir="./aerospace_orpo_output",

    # --- 学習設定 ---
    num_train_epochs=2,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,

    # --- 学習率 ---
    learning_rate=8e-6,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,

    # --- ORPO固有パラメータ ---
    lambda_=0.1,   # SFT損失とORPO損失のバランス係数

    # --- 精度 ---
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    optim="adamw_8bit",

    # --- 評価 ---
    eval_strategy="steps",
    eval_steps=50,
    logging_steps=10,

    max_length=MAX_SEQ_LENGTH,
    max_prompt_length=1024,
)

trainer = ORPOTrainer(
    model=model,
    args=orpo_config,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    processing_class=tokenizer,
)

print("ORPO学習開始...")
trainer_stats = trainer.train()
print(f"ORPO完了: {trainer_stats.metrics}")

model.save_pretrained("./aerospace_orpo_adapter")
tokenizer.save_pretrained("./aerospace_orpo_adapter")
```

---

### 学習段階の順序が重要な理由

```
CPT → SFT → DPO の順序（推奨）

CPT（継続事前学習）
  ↓ ドメイン知識・専門語彙を習得
SFT（教師あり学習）
  ↓ instruction/response形式の応答スタイルを習得
DPO/ORPO（選好最適化）
  ↓ 回答品質の向上・有害応答の抑制
最終モデル
```

**なぜこの順序か:**
1. CPTなしでSFTすると、専門用語をハルシネーションしやすい
2. SFTなしでDPOすると、そもそも適切な応答形式を学べていない
3. DPOはSFT済みモデルを参照モデルとして使うため、SFTの品質がDPOの上限を決める

---

### 9.4 学習の評価方法

### Loss曲線の読み方

```python
# analyze_training_loss.py
# 学習ログからLoss曲線を分析する

import json
import matplotlib.pyplot as plt
import numpy as np

def load_trainer_logs(log_path: str) -> list[dict]:
    """trainer_state.jsonからログを読み込む"""
    with open(log_path) as f:
        state = json.load(f)
    return state["log_history"]

def plot_loss_curves(log_path: str, output_path: str = "loss_curves.png"):
    """Train/Eval Loss曲線をプロット"""
    logs = load_trainer_logs(log_path)

    train_steps, train_losses = [], []
    eval_steps, eval_losses = [], []

    for entry in logs:
        if "loss" in entry:
            train_steps.append(entry["step"])
            train_losses.append(entry["loss"])
        if "eval_loss" in entry:
            eval_steps.append(entry["step"])
            eval_losses.append(entry["eval_loss"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # --- Loss曲線 ---
    ax = axes[0]
    ax.plot(train_steps, train_losses, label="Train Loss", color="blue", alpha=0.7)
    if eval_losses:
        ax.plot(eval_steps, eval_losses, label="Eval Loss", color="red", linewidth=2)
    ax.set_xlabel("Steps")
    ax.set_ylabel("Loss")
    ax.set_title("Training & Evaluation Loss")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # --- 過学習検出 ---
    # Eval LossがTrain Lossを大きく上回り始めた時点が過学習の開始
    if len(eval_losses) > 5:
        # 後半20%でのeval lossの傾き
        recent_eval = eval_losses[-len(eval_losses)//5:]
        slope = np.polyfit(range(len(recent_eval)), recent_eval, 1)[0]

        ax2 = axes[1]
        ax2.plot(eval_steps, eval_losses, color="red", label="Eval Loss")
        ax2.axhline(y=min(eval_losses), color="green", linestyle="--",
                    label=f"Best Eval Loss: {min(eval_losses):.4f}")
        if slope > 0:
            ax2.set_title(f"Overfitting detected (eval loss increasing, slope={slope:.4f})")
        else:
            ax2.set_title(f"Learning normally (slope={slope:.4f})")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Loss曲線を保存: {output_path}")


# 使用例
# plot_loss_curves("./aerospace_sft_output/trainer_state.json")

"""
Loss曲線の読み方チートシート:

[正常な学習]
- Train Loss: 単調に減少
- Eval Loss: Train Lossと近い値で減少
- 両者のギャップが小さい

[過学習の兆候]
- Train Loss: 減少し続ける
- Eval Loss: ある時点から増加に転じる（U字型）
- 対策: 早期停止、learning_rate低下、weight_decay増加

[学習不足]
- Train Loss, Eval Loss ともに高止まり
- 対策: learning_rate増加、エポック数増加、データ量確認

[DPO固有の指標]
- rewards/margins: 増加傾向が望ましい（chosenとrejectedの差が拡大）
- rewards/accuracies: 0.5以上（理想的には0.7以上）
"""
```

---

### 自動評価指標の実装

```python
# evaluation_metrics.py
# Perplexity, ROUGE, BERTScore の計算

import torch
import math
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import Dataset
from typing import Optional


# ========================================
# 1. Perplexity（困惑度）
# ========================================

def calculate_perplexity(
    model,
    tokenizer,
    texts: list[str],
    max_length: int = 512,
    batch_size: int = 4,
) -> float:
    """
    モデルのPerplexityを計算する。
    低いほど良い（モデルがテキストを予測しやすい）。

    宇宙/航空宇宙ドメインのテキストで計算することで
    ドメイン適応度を定量評価できる。
    """
    from unsloth import FastLanguageModel
    FastLanguageModel.for_inference(model)

    model.eval()
    total_loss = 0.0
    total_tokens = 0

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        encodings = tokenizer(
            batch,
            return_tensors="pt",
            max_length=max_length,
            truncation=True,
            padding=True,
        ).to(model.device)

        with torch.no_grad():
            outputs = model(**encodings, labels=encodings["input_ids"])

        # 有効トークン数で重み付け
        non_pad = (encodings["input_ids"] != tokenizer.pad_token_id).sum().item()
        total_loss += outputs.loss.item() * non_pad
        total_tokens += non_pad

    avg_loss = total_loss / total_tokens if total_tokens > 0 else float("inf")
    perplexity = math.exp(avg_loss)
    return perplexity


# ========================================
# 2. ROUGE スコア
# ========================================

def calculate_rouge(
    predictions: list[str],
    references: list[str],
) -> dict:
    """
    ROUGE-1, ROUGE-2, ROUGE-L を計算。
    テキスト生成タスクの自動評価に使用。
    """
    try:
        from rouge_score import rouge_scorer
    except ImportError:
        print("インストール: uv pip install rouge-score")
        return {}

    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"],
        use_stemmer=False,  # 日本語の場合はFalse
    )

    scores = {"rouge1": [], "rouge2": [], "rougeL": []}
    for pred, ref in zip(predictions, references):
        result = scorer.score(ref, pred)
        scores["rouge1"].append(result["rouge1"].fmeasure)
        scores["rouge2"].append(result["rouge2"].fmeasure)
        scores["rougeL"].append(result["rougeL"].fmeasure)

    return {k: sum(v) / len(v) for k, v in scores.items() if v}


# ========================================
# 3. BERTScore（意味的類似度）
# ========================================

def calculate_bertscore(
    predictions: list[str],
    references: list[str],
    lang: str = "ja",  # 日本語の場合は "ja"
) -> dict:
    """
    BERTScoreで意味的類似度を評価。
    ROUGEより表現の揺れに頑健。
    """
    try:
        from bert_score import score as bert_score
    except ImportError:
        print("インストール: uv pip install bert-score")
        return {}

    P, R, F1 = bert_score(
        predictions,
        references,
        lang=lang,
        rescale_with_baseline=True,  # ベースラインで正規化（0〜1スケール）
    )

    return {
        "bertscore_precision": P.mean().item(),
        "bertscore_recall": R.mean().item(),
        "bertscore_f1": F1.mean().item(),
    }


# ========================================
# 4. ドメイン固有ベンチマーク（宇宙/航空宇宙）
# ========================================

# 宇宙工学ドメインのテストセット設計例
AEROSPACE_BENCHMARK = [
    {
        "id": "orbital_mech_001",
        "category": "orbital_mechanics",
        "prompt": "第1宇宙速度（低軌道速度）を計算してください（地球半径6371km、重力加速度9.8m/s²）。",
        "expected_keywords": ["7.9", "7.9km/s", "7900", "√(gR)"],
        "reference": "第1宇宙速度 v₁ = √(gR) = √(9.8 × 6,371,000) ≈ 7.9 km/s",
    },
    {
        "id": "propulsion_001",
        "category": "propulsion",
        "prompt": "H-IIAロケットの第1段エンジン LE-7A の比推力（真空中）はおよそ何秒ですか？",
        "expected_keywords": ["440", "442", "LE-7A"],
        "reference": "LE-7A の真空中比推力は約 440〜442 秒です。",
    },
    {
        "id": "satellite_001",
        "category": "satellite_systems",
        "prompt": "静止軌道（GEO）の高度と周期を答えてください。",
        "expected_keywords": ["35786", "35,786", "36000", "24時間", "23時間56分"],
        "reference": "GEO高度は約35,786km、周期は約24時間（正確には23時間56分4秒）。",
    },
]


def evaluate_domain_benchmark(
    model,
    tokenizer,
    benchmark: list[dict],
    max_new_tokens: int = 256,
) -> dict:
    """ドメイン固有ベンチマークでの評価"""
    from unsloth import FastLanguageModel
    FastLanguageModel.for_inference(model)

    results = []
    keyword_hits = 0

    for item in benchmark:
        # 生成
        inputs = tokenizer(
            item["prompt"],
            return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.1,
                do_sample=True,
            )

        generated = tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        # キーワードヒット率チェック
        hits = sum(1 for kw in item["expected_keywords"] if kw in generated)
        hit_rate = hits / len(item["expected_keywords"])
        keyword_hits += hit_rate

        results.append({
            "id": item["id"],
            "category": item["category"],
            "generated": generated,
            "keyword_hit_rate": hit_rate,
        })

    avg_hit_rate = keyword_hits / len(benchmark) if benchmark else 0

    return {
        "avg_keyword_hit_rate": avg_hit_rate,
        "details": results,
    }
```

---

### LLM-as-Judge による評価

```python
# llm_judge_eval.py
# 別のLLMにモデル出力を採点させる

import json
from openai import OpenAI

client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key="YOUR_API_KEY",
)

# ========================================
# 評価プロンプトテンプレート
# ========================================

EVALUATION_PROMPT = """あなたは宇宙工学・航空宇宙分野の専門家です。
以下のAIアシスタントの回答を5段階で評価してください。

**質問:**
{question}

**回答:**
{response}

**評価基準:**
- 5点: 技術的に完全正確、専門家レベルの詳細、実務で直接使用可能
- 4点: 概ね正確、主要な技術情報を網羅、わずかな補足が必要
- 3点: 基本的に正確だが、重要な技術詳細が欠けている
- 2点: 部分的に正確だが、誤りや重大な欠落がある
- 1点: 技術的に不正確、または回答拒否

回答形式（JSON）:
{{
  "score": 1〜5,
  "technical_accuracy": "技術的正確性のコメント",
  "completeness": "情報の完全性のコメント",
  "suggestions": "改善点（あれば）"
}}"""


def llm_judge_evaluate(
    questions: list[str],
    responses: list[str],
    judge_model: str = "gpt-oss-120b",
) -> list[dict]:
    """LLMによる一括評価"""
    evaluations = []

    for q, r in zip(questions, responses):
        prompt = EVALUATION_PROMPT.format(question=q, response=r)

        result = client.chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
        )

        try:
            eval_data = json.loads(result.choices[0].message.content)
        except json.JSONDecodeError:
            eval_data = {"score": None, "error": "parse_error"}

        evaluations.append({
            "question": q[:50] + "...",
            "response_preview": r[:100] + "...",
            **eval_data,
        })

    # 統計サマリー
    valid_scores = [e["score"] for e in evaluations if isinstance(e.get("score"), (int, float))]
    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
        print(f"平均スコア: {avg_score:.2f} / 5.0 ({len(valid_scores)} 件評価)")

    return evaluations
```

---

### Wandb / MLflow でのトラッキング設定

```python
# tracking_setup.py
# 学習メトリクスのトラッキング設定

# ========================================
# オプション1: Weights & Biases (wandb)
# ========================================

import wandb
from transformers import TrainingArguments

def setup_wandb_tracking(project_name: str, run_name: str):
    """wandbの初期化"""
    # インストール: uv pip install wandb
    wandb.init(
        project=project_name,
        name=run_name,
        config={
            "model": "Llama-3.2-3B",
            "domain": "aerospace",
            "training_type": "CPT+SFT+DPO",
        },
        tags=["aerospace", "llm", "fine-tuning"],
    )

# TrainingArgumentsにwandb設定を追加
training_args_with_wandb = {
    "report_to": "wandb",
    "run_name": "aerospace-llm-sft-v1",
    "logging_steps": 10,
    # wandbが自動的にloss, learning_rate等を記録する
}


# ========================================
# オプション2: MLflow（ローカルでの利用に最適）
# ========================================

def setup_mlflow_tracking(
    tracking_uri: str = "./mlruns",  # ローカル保存
    experiment_name: str = "aerospace-llm",
):
    """MLflowの初期化"""
    # インストール: uv pip install mlflow
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    return mlflow

# MLflowを使ったトラッキング例
def train_with_mlflow_tracking(trainer, training_args):
    import mlflow

    with mlflow.start_run(run_name=training_args.run_name):
        # パラメータを記録
        mlflow.log_params({
            "learning_rate": training_args.learning_rate,
            "num_epochs": training_args.num_train_epochs,
            "batch_size": training_args.per_device_train_batch_size,
        })

        # 学習実行
        trainer_stats = trainer.train()

        # 最終メトリクスを記録
        mlflow.log_metrics({
            "final_train_loss": trainer_stats.metrics["train_loss"],
            "train_runtime_sec": trainer_stats.metrics["train_runtime"],
        })

        # モデルアーティファクトを保存
        mlflow.log_artifacts(training_args.output_dir, artifact_path="model")

    return trainer_stats


# ========================================
# オプション3: カスタムコールバック（外部依存なし）
# ========================================

from transformers import TrainerCallback
import csv
from datetime import datetime

class AerospaceTrainingLogger(TrainerCallback):
    """学習ログをCSVとJSONLに記録するカスタムコールバック"""

    def __init__(self, log_dir: str = "./training_logs"):
        self.log_dir = log_dir
        self.csv_path = f"{log_dir}/metrics_{datetime.now():%Y%m%d_%H%M%S}.csv"
        self.fieldnames = ["step", "epoch", "loss", "eval_loss", "learning_rate"]

        import os
        os.makedirs(log_dir, exist_ok=True)

        with open(self.csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is None:
            return

        row = {k: logs.get(k, "") for k in self.fieldnames}
        row["step"] = state.global_step
        row["epoch"] = state.epoch

        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerow(row)

# トレーナーへの追加方法
# trainer = UnslothTrainer(
#     ...
#     callbacks=[AerospaceTrainingLogger("./logs")],
# )
```

---

### 9.5 フレームワーク比較

### 主要フレームワーク比較表

| フレームワーク | 開発元 | 特徴 | 速度 | VRAM効率 | マルチGPU | 難易度 |
|---|---|---|---|---|---|---|
| **Unsloth** | Unsloth AI | カスタムTritonカーネル、QLoRA最適化 | 最速（2〜5x） | 最高（80%削減） | 有料版のみ | 低〜中 |
| **TRL** | HuggingFace | DPO/PPO/ORPO公式実装、エコシステム統合 | 標準 | 標準 | FSDP/DeepSpeed対応 | 中 |
| **Axolotl** | OpenAccess AI | YAML設定ベース、豊富なテンプレート | 良好 | 良好 | DeepSpeed/FSDP対応 | 低 |
| **torchtune** | Meta | PyTorch native、カスタマイズ性最高 | 良好（compile時） | 中程度 | FSDP対応 | 高 |

> **注意:** LLaMA-Factory（hiyouga製）は中国の開発者によるプロジェクトです。コードの監査が困難な環境や機密データを扱う場合は上記の選択肢を使用してください。

---

### 各フレームワーク詳解

#### Unsloth

```
得意分野: 単一GPU環境でのQLoRA/LoRA学習、高速プロトタイピング
GPU要件: NVIDIA GPU（VRAM 8GB〜）、CUDA 11.8以上
対応モデル: Llama 3.x, Gemma 2/3, Mistral, Phi-3/4（このガイドでは中国系モデルは使用しない）
主な用途: CPT、SFT、DPO（単一GPU）
```

```python
# Unsloth の典型的な使い方
from unsloth import FastLanguageModel, UnslothTrainer, UnslothTrainingArguments

model, tokenizer = FastLanguageModel.from_pretrained(
    "meta-llama/Llama-3.2-3B",
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(model, r=16, ...)
trainer = UnslothTrainer(model=model, ...)
trainer.train()
```

#### TRL (Transformers Reinforcement Learning)

```
得意分野: DPO/ORPO/PPO/RewardModelなどのアラインメント手法全般
GPU要件: NVIDIA GPU（VRAM 16GB〜 推奨）
対応モデル: HuggingFaceのすべてのCausalLMモデル
主な用途: アラインメント段階（SFT後）
```

```python
# TRL の典型的な使い方（DPO）
from trl import DPOTrainer, DPOConfig

trainer = DPOTrainer(
    model="./my_sft_model",
    args=DPOConfig(
        beta=0.1,
        learning_rate=5e-6,
        output_dir="./dpo_output",
    ),
    train_dataset=preference_dataset,
)
trainer.train()
```

#### Axolotl

```
得意分野: 設定ファイルベースの学習パイプライン、初心者〜中級者
GPU要件: NVIDIA GPU（VRAM 8GB〜、マルチGPU対応）
対応モデル: Llama, Mistral, Falcon, MPT等 主要モデル
主な用途: SFT、LoRA、QLoRA全般
```

```yaml
# Axolotl の設定ファイル例 (config.yml)
base_model: meta-llama/Llama-3.2-3B
model_type: LlamaForCausalLM
tokenizer_type: AutoTokenizer

load_in_4bit: true
adapter: lora
lora_r: 16
lora_alpha: 16
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj

datasets:
  - path: ./aerospace_sft_data.jsonl
    type: alpaca

dataset_prepared_path: ./axolotl_prepared
output_dir: ./axolotl_output

sequence_len: 2048
train_on_inputs: false

num_epochs: 2
learning_rate: 2e-4
optimizer: adamw_bnb_8bit
```

```bash
# Axolotlの実行
# インストール: uv pip install axolotl
axolotl train config.yml
```

#### torchtune (Meta公式)

```
得意分野: フルカスタマイズ、マルチノード大規模学習、研究目的
GPU要件: NVIDIA/AMD GPU、FSDP対応環境
対応モデル: Llama 3.x (Meta公式サポート)、一部他モデル
主な用途: フル精度SFT、LoRA、大規模分散学習
```

```yaml
# torchtune config 例
model:
  _component_: torchtune.models.llama3_2.lora_llama3_2_3b
  lora_attn_modules: ['q_proj', 'v_proj']
  apply_lora_to_mlp: False
  lora_rank: 8
  lora_alpha: 16

tokenizer:
  _component_: torchtune.models.llama3_2.llama3_2_tokenizer
  path: /path/to/tokenizer.model

dataset:
  _component_: torchtune.datasets.alpaca_dataset
  source: ./aerospace_data

output_dir: ./torchtune_output

optimizer:
  _component_: torch.optim.AdamW
  lr: 2e-4

lr_scheduler:
  _component_: torchtune.training.lr_schedulers.get_cosine_schedule_with_warmup
  num_warmup_steps: 100
```

```bash
# torchtune の実行
# インストール: uv pip install torchtune
tune run lora_finetune_single_device --config llama3_2/3B_lora_single_device
```

---

### フレームワーク選定ガイド

```
【状況別推奨フレームワーク】

単一GPU (VRAM 8〜24GB) でとにかく速く学習したい
  → Unsloth + TRL

DPO/ORPOなどのアラインメント手法を使いたい
  → Unsloth (CPT/SFT) + TRL (DPO/ORPO)

設定ファイルベースで簡単に始めたい
  → Axolotl

マルチGPU (4〜8枚以上) でフル精度学習したい
  → torchtune または Axolotl (DeepSpeed)

研究目的でアルゴリズムを細かくカスタマイズしたい
  → torchtune または TRL (直接)

本番モデル開発で信頼性・監査性を重視
  → torchtune (Meta公式) または Axolotl

【このガイドで採用している構成】
  CPT → Unsloth (UnslothTrainer)
  SFT → Unsloth (SFTTrainer/UnslothTrainer)
  DPO → Unsloth + TRL (DPOTrainer)
  ORPO → TRL (ORPOTrainer) with Unsloth model
```

---

## 10. RAG（検索拡張生成）

RAG（Retrieval-Augmented Generation）は、LLMが回答する際に関連文書を検索してコンテキストに注入する手法です。ファインチューニングと組み合わせることで、最新情報・正確な数値・特定文書への参照が可能になります。

### 基本アーキテクチャ

```
文書登録フロー:
  文書ファイル → チャンキング → Embedding → Vector DB保存

検索フロー:
  クエリ → Embedding → Vector DB検索 → 類似文書取得
        → BM25検索 → キーワードマッチ取得
        → スコア統合（RRF） → 上位N件をプロンプトに注入 → LLM
```

### Embedding モデルの選択

| モデル | 次元数 | サイズ | 日本語 | 特徴 |
|--------|-------|--------|--------|------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 470MB | 対応 | バランス良、ラズパイでも動作 |
| `BAAI/bge-m3` | 1024 | 1.1GB | 対応 | Dense+Sparse+Colbert、最高精度 |
| `BAAI/bge-small-en-v1.5` | 384 | 134MB | 非対応 | 英語専用、超軽量 |
| `intfloat/multilingual-e5-small` | 384 | 470MB | 対応 | 多言語、E5形式 |

### Vector DB の選択

| DB | 特徴 | 推奨規模 | インストール |
|----|------|---------|------------|
| NumPy flat | ファイルのみ、依存なし | ~10万件 | 不要 |
| **ChromaDB** | Python純正、簡単 | ~100万件 | `uv pip install chromadb` |
| FAISS | Meta製、高速 | ~1000万件 | `uv pip install faiss-cpu` |
| Qdrant | Rust製、本番向け | 無制限 | Docker: `docker run qdrant/qdrant` |

### RAGエンジンの実装

```python
# rag_engine.py
import json
import numpy as np
from pathlib import Path
from typing import NamedTuple
from fastembed import TextEmbedding  # pip install fastembed

class RetrievedChunk(NamedTuple):
    chunk_id: str
    text: str
    score: float
    metadata: dict


class RAGEngine:
    """ハイブリッド検索RAGエンジン（Vector + BM25）"""

    def __init__(
        self,
        db_path: str = "./rag_db",
        embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        top_k: int = 5
    ):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k
        self.embed_model = TextEmbedding(embed_model)

        # インデックスデータ
        self.chunks: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self._load_index()

    def add_documents(self, documents: list[dict]) -> int:
        """
        文書をインデックスに追加
        documents: [{"text": "...", "metadata": {...}}, ...]
        """
        # チャンキング（500文字ごと、50文字オーバーラップ）
        new_chunks = []
        for doc in documents:
            text = doc["text"]
            metadata = doc.get("metadata", {})
            chunks = self._chunk_text(text, chunk_size=500, overlap=50)
            for i, chunk in enumerate(chunks):
                new_chunks.append({
                    "chunk_id": f"chunk_{len(self.chunks) + i}",
                    "text": chunk,
                    "metadata": metadata
                })

        if not new_chunks:
            return 0

        # Embeddingを生成
        texts = [c["text"] for c in new_chunks]
        new_embeddings = np.array(list(self.embed_model.embed(texts)))

        # インデックスに追加
        self.chunks.extend(new_chunks)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        self._save_index()
        return len(new_chunks)

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """テキストをチャンクに分割"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def search(self, query: str) -> list[RetrievedChunk]:
        """ハイブリッド検索（Vector + BM25）"""
        if not self.chunks or self.embeddings is None:
            return []

        # Vector検索
        vector_results = self._vector_search(query)

        # BM25検索
        bm25_results = self._bm25_search(query)

        # RRF（Reciprocal Rank Fusion）で統合
        return self._rrf_merge(vector_results, bm25_results)

    def _vector_search(self, query: str, k: int = 20) -> list[tuple[int, float]]:
        """コサイン類似度によるベクトル検索"""
        query_emb = np.array(list(self.embed_model.embed([query]))[0])

        # コサイン類似度計算
        norms = np.linalg.norm(self.embeddings, axis=1)
        query_norm = np.linalg.norm(query_emb)
        scores = self.embeddings @ query_emb / (norms * query_norm + 1e-9)

        # 上位k件のインデックスを取得
        top_k_idx = np.argpartition(scores, -min(k, len(scores)))[-min(k, len(scores)):]
        top_k_idx = top_k_idx[np.argsort(scores[top_k_idx])[::-1]]

        return [(int(idx), float(scores[idx])) for idx in top_k_idx]

    def _bm25_search(self, query: str, k: int = 20) -> list[tuple[int, float]]:
        """BM25キーワード検索（簡易実装）"""
        query_terms = query.lower().split()
        scores = []

        # DF（文書頻度）を計算
        df = {}
        for term in query_terms:
            df[term] = sum(1 for c in self.chunks if term in c["text"].lower())

        N = len(self.chunks)
        k1, b = 1.5, 0.75  # BM25パラメータ
        avg_dl = sum(len(c["text"]) for c in self.chunks) / max(N, 1)

        for i, chunk in enumerate(self.chunks):
            text_lower = chunk["text"].lower()
            dl = len(text_lower)
            score = 0.0

            for term in query_terms:
                if term not in text_lower:
                    continue
                tf = text_lower.count(term)
                idf = np.log((N - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
                tf_norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avg_dl))
                score += idf * tf_norm

            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def _rrf_merge(
        self,
        vector_results: list[tuple[int, float]],
        bm25_results: list[tuple[int, float]],
        k: int = 60
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusionでスコアを統合"""
        rrf_scores: dict[int, float] = {}

        for rank, (idx, _) in enumerate(vector_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

        # 上位top_k件を返す
        sorted_idx = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in sorted_idx[:self.top_k]:
            chunk = self.chunks[idx]
            results.append(RetrievedChunk(
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                score=score,
                metadata=chunk["metadata"]
            ))

        return results

    def build_context(self, query: str, max_tokens: int = 3000) -> str:
        """検索結果からプロンプト注入用コンテキストを生成"""
        chunks = self.search(query)
        if not chunks:
            return ""

        context_parts = ["# 参照文書\n"]
        total_chars = 0
        char_limit = max_tokens * 3  # トークン→文字数の近似

        for i, chunk in enumerate(chunks, 1):
            chunk_text = f"[文書{i}]\n{chunk.text}\n"
            if total_chars + len(chunk_text) > char_limit:
                break
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return '\n'.join(context_parts)

    def _save_index(self):
        """インデックスをファイルに保存"""
        # チャンクデータ
        with open(self.db_path / "chunks.json", 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False)

        # Embeddingベクトル
        if self.embeddings is not None:
            np.save(self.db_path / "embeddings.npy", self.embeddings)

    def _load_index(self):
        """保存されたインデックスをロード"""
        chunks_path = self.db_path / "chunks.json"
        emb_path = self.db_path / "embeddings.npy"

        if chunks_path.exists():
            with open(chunks_path, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)

        if emb_path.exists():
            self.embeddings = np.load(emb_path)


# エージェントへの統合
class RAGAgent:
    """RAGを統合したエージェント"""

    def __init__(self, agent, rag: RAGEngine):
        self.agent = agent  # AgentCoreインスタンス
        self.rag = rag

    async def ask(self, query: str) -> str:
        """RAGコンテキストを注入してエージェントに問い合わせ"""
        # 関連文書を検索
        context = self.rag.build_context(query)

        if context:
            enhanced_query = f"{context}\n\n# 質問\n{query}"
        else:
            enhanced_query = query

        return await self.agent.run(enhanced_query)
```

---

## 11. 高度な検索技法

### HyDE（Hypothetical Document Embeddings）

クエリそのものではなく、「こんな文書がある」という仮想文書を埋め込んで検索精度を高める手法。

```python
# hyde_search.py
from openai import AsyncOpenAI
import numpy as np

async def hyde_search(
    client: AsyncOpenAI,
    model: str,
    rag: RAGEngine,
    query: str
) -> list[RetrievedChunk]:
    """
    HyDE: 仮想文書を生成してから検索する
    精度が低い場合の改善手法として有効
    """

    # 仮想文書の生成プロンプト
    hyde_prompt = f"""以下の質問に対する理想的な回答文書を100字程度で生成してください。
実際の知識がなくても構いません。形式・スタイルが重要です。

質問: {query}

回答文書:"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": hyde_prompt}],
        max_tokens=200,
        temperature=0.7
    )
    hypothetical_doc = response.choices[0].message.content

    # 仮想文書を使って検索
    # （クエリの代わりに仮想文書のEmbeddingで検索）
    results = rag.search(hypothetical_doc)  # クエリの代わりに仮想文書を使う
    return results
```

### Query Expansion（クエリ拡張）

```python
async def expand_query(
    client: AsyncOpenAI,
    model: str,
    query: str,
    n_expansions: int = 3
) -> list[str]:
    """
    クエリを複数の言い換えに展開して検索精度を向上
    """
    expand_prompt = f"""以下のクエリを{n_expansions}個の異なる言い換えに変換してください。
同じ意味を異なる表現で表してください。
1行に1つ、番号なしで答えてください。

クエリ: {query}

言い換え:"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": expand_prompt}],
        max_tokens=200,
        temperature=0.7
    )

    expansions = response.choices[0].message.content.strip().split('\n')
    # 元のクエリも含める
    return [query] + [e.strip() for e in expansions if e.strip()]


async def multi_query_search(
    client: AsyncOpenAI,
    model: str,
    rag: RAGEngine,
    query: str
) -> list[RetrievedChunk]:
    """拡張クエリで複数検索してRRFで統合"""
    expanded_queries = await expand_query(client, model, query)

    all_results: dict[str, tuple[RetrievedChunk, list[int]]] = {}

    for q_idx, q in enumerate(expanded_queries):
        results = rag.search(q)
        for rank, chunk in enumerate(results):
            if chunk.chunk_id not in all_results:
                all_results[chunk.chunk_id] = (chunk, [])
            all_results[chunk.chunk_id][1].append(rank)

    # RRFスコアで再ランキング
    k = 60
    scored = []
    for chunk_id, (chunk, ranks) in all_results.items():
        rrf_score = sum(1.0 / (k + r + 1) for r in ranks)
        scored.append((chunk, rrf_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in scored[:rag.top_k]]
```

### GraphRAG（知識グラフ拡張検索）

```python
# graph_rag.py
# エンティティ・関係を抽出してグラフ構造で検索
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class GraphNode:
    node_id: str
    text: str
    node_type: str  # "entity" | "chunk" | "document"
    metadata: dict = field(default_factory=dict)

@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0


class SimpleKnowledgeGraph:
    """networkx不要の軽量知識グラフ"""

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adj: dict[str, list[str]] = defaultdict(list)  # 隣接リスト

    def add_node(self, node: GraphNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge):
        self.edges.append(edge)
        self._adj[edge.source_id].append(edge.target_id)
        self._adj[edge.target_id].append(edge.source_id)

    def bfs_neighbors(self, start_id: str, depth: int = 2) -> list[str]:
        """BFSで近傍ノードを探索"""
        visited = {start_id}
        queue = [(start_id, 0)]
        result = []

        while queue:
            node_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            for neighbor in self._adj.get(node_id, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    queue.append((neighbor, current_depth + 1))

        return result

    def get_hub_nodes(self, top_n: int = 10) -> list[tuple[str, int]]:
        """次数中心性の高いハブノードを返す"""
        degree = {node_id: len(neighbors)
                  for node_id, neighbors in self._adj.items()}
        sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]


async def extract_entities(
    client: AsyncOpenAI,
    model: str,
    text: str
) -> list[dict]:
    """テキストからエンティティと関係を抽出"""
    extract_prompt = f"""以下のテキストからエンティティ（人物・組織・概念・技術）と
それらの関係をJSON配列で抽出してください。

テキスト: {text[:500]}

形式:
```json
[
  {{"entity1": "衛星", "relation": "使用する", "entity2": "MLI"}},
  {{"entity1": "MLI", "relation": "提供する", "entity2": "断熱性能"}}
]
```"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": extract_prompt}],
        max_tokens=500,
        temperature=0
    )

    import re, json
    content = response.choices[0].message.content
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    return []
```

### Contextual Retrieval（Anthropic方式）

各チャンクに文書全体の文脈プレフィックスを付与することで検索精度を49%改善。

```python
# contextual_retrieval.py
async def generate_chunk_context(
    client: AsyncOpenAI,
    model: str,
    document_text: str,
    chunk_text: str
) -> str:
    """
    チャンクに文書全体の文脈を付与する（Anthropicの手法）
    参考: https://www.anthropic.com/news/contextual-retrieval
    """
    context_prompt = f"""以下の文書全体の文脈を考慮して、
特定のチャンクがどのような位置づけにあるかを50字以内で説明してください。

文書全体（先頭500字）:
{document_text[:500]}

...（中略）...

文書末尾（最後200字）:
{document_text[-200:]}

このチャンク:
{chunk_text[:200]}

文脈説明（50字以内）:"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": context_prompt}],
        max_tokens=100,
        temperature=0
    )
    return response.choices[0].message.content.strip()


async def build_contextual_index(
    client: AsyncOpenAI,
    model: str,
    rag: RAGEngine,
    document: dict,
    batch_size: int = 10
) -> int:
    """
    文書を文脈付きチャンクとしてインデックス化
    バッチ処理で効率化
    """
    text = document["text"]
    chunks = rag._chunk_text(text, chunk_size=500, overlap=50)

    # バッチでコンテキストを生成
    contextual_chunks = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # 並列でコンテキスト生成
        contexts = await asyncio.gather(*[
            generate_chunk_context(client, model, text, chunk)
            for chunk in batch
        ])

        for chunk, context in zip(batch, contexts):
            # コンテキストプレフィックスを付けたチャンク
            contextual_text = f"{context}\n\n{chunk}"
            contextual_chunks.append({
                "text": contextual_text,
                "metadata": {
                    **document.get("metadata", {}),
                    "original_chunk": chunk,
                    "context": context
                }
            })

    return rag.add_documents(contextual_chunks)


import asyncio  # 上で使用
```

### 階層的チャンキング（Parent-Child Retrieval）

```python
# hierarchical_chunker.py
import re
from dataclasses import dataclass, field

@dataclass
class HierarchicalChunk:
    chunk_id: str
    text: str
    level: int            # 0=ルート, 1=章, 2=節, 3=項
    parent_id: str | None
    children_ids: list[str] = field(default_factory=list)
    section_number: str = ""  # "1.2.3" 形式


def build_hierarchy(text: str, doc_id: str = "doc") -> list[HierarchicalChunk]:
    """
    セクション番号パターンで文書から階層構造を構築
    例: "1. 概要", "1.1 背景", "1.1.1 詳細"
    """
    # セクション番号パターン
    section_pattern = re.compile(
        r'^(\d+(?:\.\d+)*)\s+(.+?)$',
        re.MULTILINE
    )

    chunks = []
    matches = list(section_pattern.finditer(text))

    for i, match in enumerate(matches):
        section_num = match.group(1)
        title = match.group(2)
        level = section_num.count('.') + 1  # "1.2.3" → level 3

        # セクションのテキスト範囲
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        # 親セクション番号を計算
        parent_num = '.'.join(section_num.split('.')[:-1]) if '.' in section_num else None

        chunk = HierarchicalChunk(
            chunk_id=f"{doc_id}_{section_num.replace('.', '_')}",
            text=section_text,
            level=level,
            parent_id=f"{doc_id}_{parent_num.replace('.', '_')}" if parent_num else None,
            section_number=section_num
        )
        chunks.append(chunk)

    # 親子関係を設定
    chunk_map = {c.chunk_id: c for c in chunks}
    for chunk in chunks:
        if chunk.parent_id and chunk.parent_id in chunk_map:
            chunk_map[chunk.parent_id].children_ids.append(chunk.chunk_id)

    return chunks


def parent_child_search(
    rag: RAGEngine,
    chunks: list[HierarchicalChunk],
    query: str
) -> list[HierarchicalChunk]:
    """
    子チャンクで精確に検索し、親チャンクのコンテキストで回答
    """
    chunk_map = {c.chunk_id: c for c in chunks}

    # 子チャンク（最小単位）のみ検索対象
    leaf_chunks = [c for c in chunks if not c.children_ids]

    # 検索用の簡易インデックスを構築
    search_docs = [{"text": c.text, "metadata": {"chunk_id": c.chunk_id}}
                   for c in leaf_chunks]

    results = rag.search(query)

    # 親チャンクのテキストも追加
    enriched = []
    for result in results:
        chunk_id = result.metadata.get("chunk_id", "")
        if chunk_id in chunk_map:
            chunk = chunk_map[chunk_id]
            # 親チャンクのコンテキストを付与
            if chunk.parent_id and chunk.parent_id in chunk_map:
                parent = chunk_map[chunk.parent_id]
                enriched.append(parent)  # 親チャンクで文脈を提供
            else:
                enriched.append(chunk)

    return enriched
```

### RRF リランキング

```python
# reranker.py
def rrf_rerank(
    result_lists: list[list[RetrievedChunk]],
    k: int = 60
) -> list[RetrievedChunk]:
    """
    複数の検索結果リストをRRFで統合
    各結果のランクから最終スコアを計算
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, RetrievedChunk] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list):
            chunk_map[chunk.chunk_id] = chunk
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1.0 / (k + rank + 1)

    # スコア降順でソート
    sorted_chunks = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            text=chunk_map[chunk_id].text,
            score=score,
            metadata=chunk_map[chunk_id].metadata
        )
        for chunk_id, score in sorted_chunks
    ]


async def llm_rerank(
    client: AsyncOpenAI,
    model: str,
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int = 5
) -> list[RetrievedChunk]:
    """
    LLMによる最終リランキング（精度最優先）
    上位chunks件をLLMが評価して最終順位を決定
    """
    if len(chunks) <= top_k:
        return chunks

    # 候補を番号付きで提示
    candidates_text = "\n\n".join([
        f"[候補{i+1}]\n{chunk.text[:300]}"
        for i, chunk in enumerate(chunks[:top_k * 3])  # 候補は多めに
    ])

    rerank_prompt = f"""以下の候補を質問への関連度の高い順に番号で並べ替えてください。
上位{top_k}件のみ回答してください。

質問: {query}

{candidates_text}

関連度の高い順（番号のみ、カンマ区切り）:"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": rerank_prompt}],
        max_tokens=50,
        temperature=0
    )

    # 番号を解析
    import re
    numbers = re.findall(r'\d+', response.choices[0].message.content)
    reranked = []
    for num_str in numbers[:top_k]:
        idx = int(num_str) - 1
        if 0 <= idx < len(chunks):
            reranked.append(chunks[idx])

    # 不足分を元のリストで補完
    existing_ids = {c.chunk_id for c in reranked}
    for chunk in chunks:
        if len(reranked) >= top_k:
            break
        if chunk.chunk_id not in existing_ids:
            reranked.append(chunk)

    return reranked
```


---

## 12. 費用・コスト

### APIクラウドサービスのコスト比較（2026年3月時点）

| サービス | モデル | 入力(1Mトークン) | 出力(1Mトークン) | 備考 |
|---------|-------|--------------|--------------|------|
| **Anthropic** | Claude Opus 4.6 | $15.00 | $75.00 | 最高品質 |
| | Claude Sonnet 4.6 | $3.00 | $15.00 | バランス |
| | Claude Haiku 3.5 | $0.80 | $4.00 | 軽量 |
| **OpenAI** | GPT-4o | $2.50 | $10.00 | 汎用高性能 |
| | GPT-4o mini | $0.15 | $0.60 | 軽量 |
| | o3 | $10.00 | $40.00 | 深い推論 |
| **Google** | Gemini 2.0 Pro | $1.25 | $5.00 | マルチモーダル |
| | Gemini 2.0 Flash | $0.10 | $0.40 | 超高速 |
| **OSS API** | Cerebras (gpt-oss-120b) | $0.60 | $0.60 | 超高速推論 |
| | Together.ai (Llama 70B) | $0.90 | $0.90 | オープンモデル |
| | Groq (Llama 70B) | $0.59 | $0.79 | 超高速 |

### ローカルLLMのコスト（初期投資）

| GPU | VRAM | 価格目安 | 動かせるモデル |
|-----|------|--------|-------------|
| RTX 3090 | 24GB | 約15万円 | CodeGemma 7B, Codestral 22B |
| RTX 4090 | 24GB | 約25万円 | Llama 3.1 70B (量子化) |
| A6000 Ada | 48GB | 約60万円 | Llama 3.1 70B, Gemma 2 27B |
| A100 80GB | 80GB | 約150万円 | GPT-OSS 120B (量子化) |
| H100 SXM | 80GB | 約400万円 | GPT-OSS 120B (フル) |

### 月間コスト試算

#### APIを使う場合

```
ライトユーザー（1日30回程度）:
  平均リクエスト: 5,000トークン入力 + 2,000トークン出力
  月間: 30 × 30 = 900リクエスト

  Claude Opus 4.6:
    入力: 900 × 5,000 / 1,000,000 × $15 = $67.5
    出力: 900 × 2,000 / 1,000,000 × $75 = $135
    合計: 約 $202/月 （約3万円）

  Claude Sonnet 4.6:
    入力: $13.5 + 出力: $27 = 約 $40/月 （約6,000円）

ヘビーユーザー（1日200回程度）:
  月間: 200 × 30 = 6,000リクエスト

  Claude Opus 4.6: 約 $1,350/月 （約20万円）
  Claude Sonnet 4.6: 約 $270/月 （約4万円）
  Cerebras OSS API: 約 $78/月 （約1.2万円）
```

#### ローカルLLMの場合（電気代のみ）

```
RTX 4090 (350W TDP) を1日8時間使用:
  1日: 0.35kW × 8h = 2.8kWh
  月間: 2.8 × 30 = 84kWh
  電気代: 84 × 35円（業務用） = 約2,940円/月

RTX 3090で Codestral 22B を常時稼働:
  月間電気代: 約3,000〜5,000円
  初期投資（RTX 3090）: 150,000円
  → 損益分岐点: Claude Sonnet比較で約3年
  → Opus比較なら4〜5ヶ月で回収可能
```

---

## 13. セキュリティ・サンドボックス

### Bashツール実行のリスク

エージェントがBashツールを使ってシステムコマンドを実行する場合、以下のリスクがあります:

- 意図しないファイル削除（`rm -rf`等）
- ネットワークへの不正アクセス
- セキュリティ関連ファイルへのアクセス
- 無限ループによるリソース枯渇

### Docker サンドボックス実装

```python
# sandbox.py
import docker
import asyncio
from typing import NamedTuple

class SandboxResult(NamedTuple):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


class DockerSandbox:
    """Dockerコンテナ内でコマンドを安全に実行"""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "512m",  # メモリ上限
        cpu_quota: int = 50000,       # CPU上限（50%）
        network_disabled: bool = True  # ネットワーク無効化
    ):
        self.client = docker.from_env()
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled

        # イメージが存在しない場合はプル
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"イメージをプルしています: {image}")
            self.client.images.pull(image)

    async def execute(
        self,
        command: str,
        workdir: str = "/workspace",
        timeout_sec: int = 30
    ) -> SandboxResult:
        """コマンドをサンドボックス内で実行"""

        container = None
        try:
            # コンテナを作成（起動しない）
            container = self.client.containers.create(
                self.image,
                command=["sh", "-c", command],
                working_dir=workdir,
                network_disabled=self.network_disabled,
                mem_limit=self.memory_limit,
                cpu_quota=self.cpu_quota,
                # 読み取り専用ルートFS（書き込みはtmpfsのみ）
                read_only=False,  # 実用的にはFalseにしておく
                tmpfs={"/tmp": "size=100m"},
                # セキュリティオプション
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],  # 全Linux権限を削除
                cap_add=["CHOWN", "SETUID", "SETGID"],  # 必要最小限
            )

            # コンテナを起動
            container.start()

            # タイムアウト付きで待機
            try:
                exit_code = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: container.wait()
                    ),
                    timeout=timeout_sec
                )
                timed_out = False
            except asyncio.TimeoutError:
                container.kill()
                timed_out = True
                exit_code = {"StatusCode": -1}

            # ログ取得
            logs = container.logs(stdout=True, stderr=True)
            output = logs.decode('utf-8', errors='replace')[:30000]

            return SandboxResult(
                stdout=output,
                stderr="",
                exit_code=exit_code.get("StatusCode", -1) if not timed_out else -1,
                timed_out=timed_out
            )

        except Exception as e:
            return SandboxResult(
                stdout="", stderr=str(e), exit_code=-1, timed_out=False
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass


# gVisor によるさらに強固なサンドボックス（オプション）
# gVisorはLinuxカーネルのユーザースペース実装
# インストール: https://gvisor.dev/docs/user_guide/install/

class GVisorSandbox(DockerSandbox):
    """gVisor (runsc) を使ったカーネルレベルの隔離"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Dockerデーモンにgvisorランタイムが設定されている必要がある
        # /etc/docker/daemon.json に "runtimes": {"runsc": {"path": "/usr/local/bin/runsc"}}

    async def execute(self, command: str, **kwargs) -> SandboxResult:
        # runtime="runsc" を指定してgVisorで実行
        # （コンテナ作成時にruntime="runsc"オプションを追加）
        return await super().execute(command, **kwargs)
```

### パーミッション管理

```python
# permissions.py
from enum import Flag, auto
from pathlib import Path


class Permission(Flag):
    """エージェントに付与する権限"""
    NONE = 0
    READ_FILES = auto()        # ファイル読み取り
    WRITE_FILES = auto()       # ファイル書き込み
    EXECUTE_BASH = auto()      # シェル実行
    WEB_ACCESS = auto()        # Web検索・取得
    SYSTEM_COMMANDS = auto()   # システムコマンド（apt, systemctl等）

    # プリセット
    READONLY = READ_FILES | WEB_ACCESS
    STANDARD = READ_FILES | WRITE_FILES | EXECUTE_BASH | WEB_ACCESS
    FULL = READ_FILES | WRITE_FILES | EXECUTE_BASH | WEB_ACCESS | SYSTEM_COMMANDS


class PermissionGuard:
    """ツール実行前に権限チェック"""

    # ツール名 → 必要な権限のマッピング
    TOOL_PERMISSIONS = {
        "Read": Permission.READ_FILES,
        "Glob": Permission.READ_FILES,
        "Grep": Permission.READ_FILES,
        "Write": Permission.WRITE_FILES,
        "Edit": Permission.WRITE_FILES,
        "Bash": Permission.EXECUTE_BASH,
        "WebSearch": Permission.WEB_ACCESS,
        "WebFetch": Permission.WEB_ACCESS,
    }

    # 危険なコマンドパターン
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/',     # ルートからの再帰削除
        r'dd\s+if=',         # ディスクの直接操作
        r'mkfs',             # ファイルシステムフォーマット
        r':(){ :|:& };:',    # Fork爆弾
        r'>\s*/dev/s',       # デバイスへの直接書き込み
        r'chmod\s+-R\s+777', # 全ファイルへの権限付与
    ]

    def __init__(self, granted: Permission = Permission.STANDARD):
        self.granted = granted

    def check(self, tool_name: str, tool_input: dict) -> tuple[bool, str]:
        """
        ツール実行を許可するか確認
        Returns: (allowed, reason)
        """
        required = self.TOOL_PERMISSIONS.get(tool_name)
        if required is None:
            return False, f"不明なツール: {tool_name}"

        if not (required in self.granted):
            return False, f"権限不足: {tool_name}には{required.name}が必要です"

        # Bashコマンドの危険性チェック
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                import re
                if re.search(pattern, command):
                    return False, f"危険なコマンドパターンを検出: {pattern}"

        # 書き込み先のパスチェック
        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")
            if self._is_protected_path(file_path):
                return False, f"保護されたパスへの書き込みは禁止: {file_path}"

        return True, ""

    def _is_protected_path(self, path: str) -> bool:
        """保護されたパスへの書き込みを拒否"""
        protected_prefixes = [
            "/etc/", "/boot/", "/sys/", "/proc/",
            "/usr/bin/", "/usr/sbin/", "/bin/", "/sbin/",
            "~/.ssh/", "~/.gnupg/"
        ]
        path = Path(path).resolve().as_posix()
        for prefix in protected_prefixes:
            expanded = Path(prefix).expanduser().as_posix()
            if path.startswith(expanded):
                return True
        return False
```

### 使用例: パーミッション付きエージェント

```python
# 読み取り専用モード
guard = PermissionGuard(Permission.READONLY)
agent = AgentCore()

# ツール実行前にチェック
async def safe_dispatch(tool_name: str, tool_input: dict) -> str:
    allowed, reason = guard.check(tool_name, tool_input)
    if not allowed:
        return f"[権限エラー] {reason}"
    return await agent.tools.dispatch(tool_name, tool_input)
```

---

## 14. セッション・メモリ管理

### セッションの保存・復元

```python
# session_manager.py
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from openai import AsyncOpenAI


class SessionManager:
    """会話セッションの保存・復元・管理"""

    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.sessions_dir / "index.json"
        self._load_index()

    def _load_index(self):
        """セッションインデックスをロード"""
        if self.index_path.exists():
            with open(self.index_path) as f:
                self.index = json.load(f)
        else:
            self.index = {"sessions": []}

    def _save_index(self):
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def save(self, messages: list[dict], title: str = "", tags: list[str] = None) -> str:
        """セッションを保存してセッションIDを返す"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.sessions_dir / f"{session_id}.json"

        # タイトル自動生成（未指定の場合）
        if not title and messages:
            first_user = next(
                (m["content"] for m in messages if m["role"] == "user"), ""
            )
            title = str(first_user)[:50]

        data = {
            "session_id": session_id,
            "title": title,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": messages
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # インデックスに追加
        self.index["sessions"].append({
            "session_id": session_id,
            "title": title,
            "tags": tags or [],
            "created_at": data["created_at"],
            "message_count": len(messages),
            "path": str(path)
        })
        self._save_index()

        return session_id

    def load(self, session_id: str) -> list[dict]:
        """セッションIDからメッセージを復元"""
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"セッションが見つかりません: {session_id}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data["messages"]

    def list_sessions(self, days: int = 7) -> list[dict]:
        """最近のセッション一覧"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for s in self.index["sessions"]:
            created = datetime.fromisoformat(s["created_at"])
            if created > cutoff:
                recent.append(s)
        return sorted(recent, key=lambda x: x["created_at"], reverse=True)

    def export_markdown(self, session_id: str) -> str:
        """セッションをMarkdownに変換"""
        messages = self.load(session_id)
        lines = [f"# セッション: {session_id}\n"]
        for msg in messages:
            role = "ユーザー" if msg["role"] == "user" else "アシスタント"
            content = msg.get("content", "")
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)
            lines.append(f"## {role}\n\n{content}\n")
        return '\n'.join(lines)

    def auto_archive(self, max_age_days: int = 7, max_sessions: int = 50):
        """古いセッションを自動アーカイブ"""
        sessions = self.index["sessions"]
        cutoff = datetime.now() - timedelta(days=max_age_days)

        active = []
        archived = []
        for s in sessions:
            created = datetime.fromisoformat(s["created_at"])
            if created < cutoff or len(active) >= max_sessions:
                archived.append(s)
            else:
                active.append(s)

        if archived:
            archive_dir = self.sessions_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            # アーカイブファイルを移動
            for s in archived:
                src = Path(s["path"])
                if src.exists():
                    src.rename(archive_dir / src.name)

            self.index["sessions"] = active
            self._save_index()
            print(f"{len(archived)}件のセッションをアーカイブしました")
```

### 長期記憶システム（Auto Memory相当）

```python
# long_memory.py
# Claude CodeのAuto Memory（memory/MEMORY.md）相当の実装

import json
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI
from enum import Enum


class MemoryType(Enum):
    WORKING = "working"       # 現在のタスクに関連
    EPISODIC = "episodic"     # 過去の作業エピソード
    SEMANTIC = "semantic"     # 一般知識・事実
    PROCEDURAL = "procedural" # 手順・方法論


class MemoryRecord:
    def __init__(self, content: str, memory_type: MemoryType, importance: float = 0.5):
        self.memory_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.content = content
        self.memory_type = memory_type
        self.importance = importance  # 0.0〜1.0
        self.created_at = datetime.now().isoformat()
        self.access_count = 0


class MemorySystem:
    """4層記憶システム"""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[MemoryRecord] = []
        self._load()

        # 初期知識シード（プロジェクト固有の情報）
        if not self.records:
            self._seed_initial_knowledge()

    def _seed_initial_knowledge(self):
        """初期知識をシード"""
        seeds = [
            ("このプロジェクトのパッケージマネージャーはuvです（pipは使わない）",
             MemoryType.PROCEDURAL, 0.9),
            ("コードはPython 3.12で書く",
             MemoryType.SEMANTIC, 0.8),
            ("LLMバックエンドはvLLM（http://localhost:8000/v1）",
             MemoryType.SEMANTIC, 0.8),
        ]
        for content, mtype, importance in seeds:
            self.add(content, mtype, importance)

    def add(self, content: str, memory_type: MemoryType, importance: float = 0.5):
        """記憶を追加"""
        record = MemoryRecord(content, memory_type, importance)
        self.records.append(record)
        self._save()

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """クエリに関連する記憶を検索（簡易キーワードマッチ）"""
        query_terms = query.lower().split()
        scored = []

        for record in self.records:
            content_lower = record.content.lower()
            # キーワードマッチスコア
            match_score = sum(1 for term in query_terms if term in content_lower)
            if match_score > 0:
                # 重要度とアクセス頻度も考慮
                final_score = match_score * record.importance * (1 + record.access_count * 0.1)
                scored.append((record, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [r for r, _ in scored[:top_k]]

        # アクセスカウント更新
        for r in results:
            r.access_count += 1

        self._save()
        return results

    def get_context(self, query: str = "") -> str:
        """エージェントのシステムプロンプトに注入するコンテキスト"""
        if query:
            memories = self.search(query)
        else:
            # 重要度の高いものを上位10件
            memories = sorted(
                self.records, key=lambda r: r.importance, reverse=True
            )[:10]

        if not memories:
            return ""

        lines = ["# 記憶（過去の作業・知識）"]
        for m in memories:
            lines.append(f"- [{m.memory_type.value}] {m.content}")

        return '\n'.join(lines)

    async def auto_memorize(
        self,
        client: AsyncOpenAI,
        model: str,
        conversation: list[dict]
    ):
        """会話から重要な情報を自動抽出して記憶に追加"""
        conv_text = '\n'.join([
            f"{m['role']}: {str(m.get('content', ''))[:500]}"
            for m in conversation[-10:]  # 最新10件
        ])

        extract_prompt = f"""以下の会話から、将来の作業に役立つ重要な情報を抽出してください。
決定事項、学んだこと、注意点、手順などを3件以内のJSON配列で返してください。

会話:
{conv_text}

形式:
```json
[
  {{"content": "重要な情報", "type": "procedural|semantic|episodic", "importance": 0.8}}
]
```"""

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": extract_prompt}],
                max_tokens=500,
                temperature=0
            )

            content = response.choices[0].message.content
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                memories = json.loads(json_match.group(1))
                for m in memories:
                    mem_type = MemoryType(m.get("type", "semantic"))
                    self.add(m["content"], mem_type, m.get("importance", 0.5))
        except Exception:
            pass  # 自動記憶は失敗しても継続

    def save_to_markdown(self, path: str = "memory/MEMORY.md"):
        """Claude Code互換のMEMORY.mdフォーマットで保存"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# Memory\n", f"更新日時: {datetime.now().isoformat()}\n"]

        for mem_type in MemoryType:
            type_records = [r for r in self.records if r.memory_type == mem_type]
            if not type_records:
                continue
            lines.append(f"\n## {mem_type.value.capitalize()}\n")
            for r in sorted(type_records, key=lambda x: x.importance, reverse=True):
                lines.append(f"- {r.content}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _save(self):
        path = self.memory_dir / "memories.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([
                {
                    "memory_id": r.memory_id,
                    "content": r.content,
                    "memory_type": r.memory_type.value,
                    "importance": r.importance,
                    "created_at": r.created_at,
                    "access_count": r.access_count
                }
                for r in self.records
            ], f, ensure_ascii=False, indent=2)

    def _load(self):
        path = self.memory_dir / "memories.json"
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        self.records = []
        for d in data:
            r = MemoryRecord(d["content"], MemoryType(d["memory_type"]), d["importance"])
            r.memory_id = d["memory_id"]
            r.created_at = d["created_at"]
            r.access_count = d["access_count"]
            self.records.append(r)
```

---

## 15. 実装ロードマップ

### Phase 1: 最小MVP（1週間）

最初の1週間で動作する最小限のエージェントを完成させます。

```
Week 1 チェックリスト:
□ vLLMのセットアップ（1日目）
  - GPU環境の確認
  - CodeGemma 7B または Llama 3.1 8B を起動
  - 接続テスト

□ 基本ツールの実装（2-3日目）
  - Read / Write / Edit の3ツール
  - Bash（タイムアウト付き）
  - Glob（ファイル検索）

□ シンプルなエージェントループ（4-5日目）
  - ReAct ループ（Think → Tool → Observe）
  - ネイティブTool Useが使えない場合はテキスト解析

□ 動作確認（6-7日目）
  - "このファイルの内容を読んで" → Readツール
  - "新しいファイルを作って" → Writeツール
  - "このディレクトリのPyファイルを一覧して" → Globツール
```

```python
# Phase 1 の最小実装（全部で100行以内）
# minimal_agent.py

import asyncio
import json
import re
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
MODEL = "google/codegemma-7b-it"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "ファイルを読む",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "ファイルを書く",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "シェルコマンドを実行する",
            "parameters": {
                "type": "object",
                "properties": {"cmd": {"type": "string"}},
                "required": ["cmd"]
            }
        }
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """ツールを実行"""
    import subprocess
    from pathlib import Path

    if name == "read_file":
        try:
            return Path(args["path"]).read_text(encoding='utf-8')
        except Exception as e:
            return f"エラー: {e}"
    elif name == "write_file":
        try:
            p = Path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"], encoding='utf-8')
            return "書き込み完了"
        except Exception as e:
            return f"エラー: {e}"
    elif name == "bash":
        try:
            result = subprocess.run(
                args["cmd"], shell=True, capture_output=True,
                text=True, timeout=30
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"エラー: {e}"
    return f"不明なツール: {name}"

async def run(user_input: str):
    """最小エージェントループ"""
    messages = [
        {"role": "system", "content": "あなたはコーディングアシスタントです。"},
        {"role": "user", "content": user_input}
    ]

    for _ in range(20):  # 最大20回
        response = await client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS,
            tool_choice="auto", max_tokens=1000
        )
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            messages.append({"role": "assistant", "content": choice.message.content or ""})
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, args)
                print(f"[{tc.function.name}] → {result[:100]}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            print(choice.message.content)
            return

if __name__ == "__main__":
    import sys
    asyncio.run(run(" ".join(sys.argv[1:])))
```

### Phase 2: ツール充実（2週間）

```
Week 2-3 チェックリスト:
□ Grep ツール（ripgrep統合）
□ WebSearch（DuckDuckGo API）
□ WebFetch（HTMLをMarkdown変換）
□ コンテキスト圧縮（閾値超過で要約）
□ ストリーミング出力（リアルタイム表示）
□ エラーリカバリー（ツール失敗時の再試行）
□ セッション保存・復元
□ Rich TUI（進捗表示、カラー出力）
```

```python
# ストリーミング出力の実装
async def run_with_streaming(user_input: str):
    """ストリーミングでリアルタイムに出力"""
    messages = [{"role": "user", "content": user_input}]

    async with client.chat.completions.stream(
        model=MODEL,
        messages=messages,
        max_tokens=2000
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
    print()  # 改行
```

### Phase 3: マルチモデル（1ヶ月）

```
Week 4-6 チェックリスト:
□ ModelRouter の実装
  - タスク分類ロジック
  - ヘルスチェック
□ 複数vLLMサーバーの起動スクリプト
□ Extended Thinking
  - Chain-of-Thought
  - Self-Reflection
□ サブエージェント（並列タスク実行）
□ パーミッション管理
□ Dockerサンドボックス
□ 長期記憶システム
□ マルチモデルルーティング統計
```

### Phase 4: ファインチューニング・RAG（以降）

```
Month 2+ チェックリスト:
□ 訓練データの収集
  - NASA NTRS API
  - ドメイン固有文書
□ QLoRAファインチューニング（Unsloth）
□ RAGエンジン実装
  - ChromaDB セットアップ
  - Embeddingモデル選択
  - ハイブリッド検索（BM25+Vector）
□ Contextual Retrieval
□ GraphRAG（エンティティ抽出）
□ HyDE・Query Expansion
□ 評価システム（精度測定）
□ CI/CD パイプライン
```

---

## 16. Embedding Fine-tuning（検索精度の向上）

### なぜEmbedding Fine-tuningが必要か

汎用Embeddingモデル（`all-MiniLM-L6-v2` など）は、一般的なテキスト類似度では良い性能を発揮します。しかし専門ドメインでは致命的な問題が生じます。

**具体例（宇宙ドメイン）:**

```
汎用モデルでの類似度:
"スラスタの比推力" ↔ "エンジンの燃費" → 0.82  ← 高すぎる（別概念）
"LEO軌道"         ↔ "低軌道"           → 0.41  ← 低すぎる（同概念）
"デルタV"         ↔ "速度変化量"       → 0.38  ← 低すぎる（同概念）
```

Fine-tuning後:
```
"スラスタの比推力" ↔ "エンジンの燃費"  → 0.31  ← 適切に区別
"LEO軌道"         ↔ "低軌道"           → 0.94  ← 正しく類似
"デルタV"         ↔ "速度変化量"       → 0.91  ← 正しく類似
```

**問題の本質:**
- 汎用モデルは「ロケット」「エンジン」を日常語として学習している
- 専門用語の階層関係（`Isp` > `比推力` > `エンジン効率指標`）を知らない
- 略語展開（`GTO` = `Geostationary Transfer Orbit`）ができない

---

### 損失関数の選択

#### Triplet Loss（三つ組み損失）

```
アンカー: "ホーマン遷移軌道の計算方法"
正例(Positive): "ホーマン軌道遷移のデルタV算出"
負例(Negative): "静止軌道の定義"
```

目標: `distance(anchor, positive) + margin < distance(anchor, negative)`

**特徴:**
- 明示的に正例・負例を指定できる
- Hard negative（境界付近の難しい負例）が有効
- データ準備が少し手間

#### Contrastive Loss（対照損失）

```
ペア例:
("LEO軌道", "低地球軌道", label=1)   # 類似
("LEO軌道", "静止軌道",   label=0)   # 非類似
```

**特徴:**
- ラベル付きペアデータで使いやすい
- 二値分類的な学習
- 専門家アノテーションとの相性が良い

#### CosineSimilarityLoss（コサイン類似度損失）

```
ペア例:
("比推力の計算", "Ispの求め方", score=0.95)   # 類似度スコア付き
("比推力の計算", "軌道傾斜角", score=0.12)    # 類似度スコア付き
```

**特徴:**
- 連続値スコアを直接学習できる
- 人間の直感的な類似度を反映しやすい
- 評価データから自然にスコアを生成できる

#### MultipleNegativesRankingLoss（推奨）

```python
# (anchor, positive) ペアのみでOK
# バッチ内の他サンプルが自動的に負例になる
pairs = [
    ("ホーマン遷移の計算", "ホーマン軌道遷移のデルタV"),
    ("比推力とは",          "Isp: Specific Impulse の定義"),
    ...
]
```

**特徴:**
- データ準備が最も簡単（ペアのみ）
- 大バッチサイズで効果大
- 高性能モデルの標準的な手法

---

### Matryoshka Representation Learning（MRL）

通常のEmbeddingモデルは固定次元のベクトルを出力します。MRLでは、**一つのモデルで複数の次元サイズのEmbeddingを生成**できます。

**仕組み:**

```
通常の学習:
入力テキスト → [768次元ベクトル] → 損失計算

MRLの学習:
入力テキスト → [768次元ベクトル]
                ├── 最初の768次元 → 損失1
                ├── 最初の512次元 → 損失2
                ├── 最初の256次元 → 損失3
                ├── 最初の128次元 → 損失4
                └── 最初の 64次元 → 損失5
                         ↓
                合計損失 = 損失1 + 損失2 + ... + 損失5
```

**実用的なメリット:**

```
用途別の次元選択:
64次元  → 初期フィルタリング（超高速、大量文書）
128次元 → バランス型（速度と精度の両立）
256次元 → 品質重視（最終的な順位付け）
768次元 → 最高精度（重要な判断のみ）
```

---

### 学習データの作り方

#### ステップ1: ドメインコーパスからペア生成

```python
# aerospace_pair_generator.py

import random
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

# 宇宙ドメインの用語辞書（同義語グループ）
AEROSPACE_SYNONYMS = {
    "比推力": ["Isp", "Specific Impulse", "エンジン効率指標", "比推力Isp"],
    "LEO": ["低地球軌道", "Low Earth Orbit", "低軌道", "近地球軌道"],
    "デルタV": ["ΔV", "速度変化量", "軌道変更速度", "推進力要件"],
    "GTO": ["静止遷移軌道", "Geostationary Transfer Orbit", "GEO遷移軌道"],
    "ホーマン遷移": ["Hohmann Transfer", "楕円軌道遷移", "最小エネルギー軌道変換"],
    "ペイロード質量比": ["質量比", "マスフラクション", "推進剤質量比"],
}

def generate_positive_pairs(
    synonyms: dict,
    qa_pairs: List[Tuple[str, str]]
) -> List[Tuple[str, str]]:
    """
    正例ペアを生成する。

    Returns:
        List of (anchor, positive) tuples
    """
    pairs = []

    # 同義語からペア生成
    for term, synonyms_list in synonyms.items():
        all_terms = [term] + synonyms_list
        for i in range(len(all_terms)):
            for j in range(i + 1, len(all_terms)):
                pairs.append((all_terms[i], all_terms[j]))

    # QAペアから生成（質問→回答を正例として扱う）
    for question, answer in qa_pairs:
        pairs.append((question, answer))
        # 回答の先頭100文字を要約として追加
        pairs.append((question, answer[:100]))

    return pairs


def generate_triplets_with_hard_negatives(
    corpus: List[str],
    model: SentenceTransformer,
    positive_pairs: List[Tuple[str, str]],
    num_negatives: int = 3,
    hard_negative_margin: float = 0.05
) -> List[Tuple[str, str, str]]:
    """
    Hard negative miningでtripletを生成する。

    Args:
        corpus: 検索対象の文書リスト
        model: 現在のEmbeddingモデル
        positive_pairs: (anchor, positive)のリスト
        num_negatives: 各アンカーに対する負例の数
        hard_negative_margin: positiveとの類似度差の許容範囲

    Returns:
        List of (anchor, positive, negative) tuples
    """
    print("コーパスのEmbeddingを計算中...")
    corpus_embeddings = model.encode(corpus, show_progress_bar=True)

    triplets = []
    for anchor, positive in positive_pairs:
        anchor_emb = model.encode([anchor])[0]
        positive_emb = model.encode([positive])[0]

        # positiveとの類似度
        positive_sim = np.dot(anchor_emb, positive_emb) / (
            np.linalg.norm(anchor_emb) * np.linalg.norm(positive_emb)
        )

        # コーパス全体との類似度を計算
        similarities = np.dot(corpus_embeddings, anchor_emb) / (
            np.linalg.norm(corpus_embeddings, axis=1) * np.linalg.norm(anchor_emb)
        )

        # Hard negativeを選択:
        # - positiveよりも(margin分)類似度が低い
        # - ランダムな負例よりも類似度が高い
        threshold_high = positive_sim - hard_negative_margin
        threshold_low = positive_sim - 0.4

        candidate_indices = np.where(
            (similarities < threshold_high) & (similarities > threshold_low)
        )[0]

        if len(candidate_indices) >= num_negatives:
            # 最も難しい（類似度が高い）ものを選択
            top_hard_negatives = candidate_indices[
                np.argsort(similarities[candidate_indices])[::-1][:num_negatives]
            ]
            for neg_idx in top_hard_negatives:
                triplets.append((anchor, positive, corpus[neg_idx]))

    return triplets


# 使用例
if __name__ == "__main__":
    # 宇宙ドメインのQAペア（ドキュメントから抽出）
    qa_pairs = [
        (
            "ホーマン遷移軌道でLEOからGTOへ移動するのに必要なデルタVは？",
            "LEOからGTOへのホーマン遷移には約2.5 km/sのΔVが必要です。"
            "第一バーンで約2.46 km/s、第二バーンで約1.47 km/sを使用します。"
        ),
        (
            "比推力（Isp）の単位は何ですか？",
            "比推力の単位は秒（s）です。IspはF/(ṁ×g₀)で定義され、"
            "エンジンが1秒間に1Nの推力を発生させるのに必要な推進剤質量フローを表します。"
        ),
        (
            "ツィオルコフスキーのロケット方程式を教えてください",
            "ツィオルコフスキー方程式: ΔV = Isp × g₀ × ln(m₀/mf)\n"
            "m₀=初期質量、mf=最終質量、g₀=標準重力加速度(9.80665 m/s²)"
        ),
    ]

    pairs = generate_positive_pairs(AEROSPACE_SYNONYMS, qa_pairs)
    print(f"生成された正例ペア数: {len(pairs)}")
```

#### ステップ2: sentence-transformers v3による公式Hard Negative Mining

```python
# hard_negative_mining_v3.py
# sentence-transformers v3.1以降の公式APIを使用

from datasets import Dataset
from sentence_transformers.util import mine_hard_negatives
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-base")

# (anchor, positive)ペアのデータセット
data = {
    "anchor": [
        "比推力の計算方法",
        "LEO軌道の高度",
        "ホーマン遷移に必要なΔV",
    ],
    "positive": [
        "IspはF/(ṁ×g₀)で計算される推進効率指標",
        "低地球軌道は高度200〜2000kmの範囲",
        "ホーマン軌道遷移の速度変化量の算出",
    ],
}
dataset = Dataset.from_dict(data)

# コーパス（検索対象文書）
corpus = [
    "IspはF/(ṁ×g₀)で計算される推進効率指標",
    "低地球軌道は高度200〜2000kmの範囲",
    "ホーマン軌道遷移の速度変化量の算出",
    "静止軌道の高度は約35,786km",
    "ツィオルコフスキー方程式による燃料計算",
    "打ち上げウィンドウの計算方法",
    "軌道傾斜角の変更コスト",
    "太陽同期軌道の特性",
    # ... 実際には数千件のドキュメント
]

# Hard negative miningを実行
dataset_with_negatives = mine_hard_negatives(
    dataset=dataset,
    model=model,
    corpus=corpus,
    num_negatives=5,          # 各アンカーに対する負例数
    relative_margin=0.05,     # positive類似度の95%以下を負例とする
    sampling_strategy="top",  # 最も難しいものを優先
    batch_size=64,
    use_faiss=True,           # FAISS使用で高速化（大規模コーパス向け）
)

print(dataset_with_negatives)
# 出力例:
# Dataset({
#     features: ['anchor', 'positive', 'negative_0', ..., 'negative_4'],
#     num_rows: 3
# })
```

---

### Fine-tuning実装コード

```python
# finetune_aerospace_embeddings.py

import os
from datetime import datetime
from datasets import Dataset, load_dataset
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
)
from sentence_transformers.losses import (
    MultipleNegativesRankingLoss,
    MatryoshkaLoss,
)
from sentence_transformers.evaluation import (
    InformationRetrievalEvaluator,
    TripletEvaluator,
)

# ========== 設定 ==========
BASE_MODEL = "intfloat/multilingual-e5-base"  # 多言語対応
OUTPUT_DIR = "./aerospace-embedding-v1"
MATRYOSHKA_DIMS = [768, 512, 256, 128, 64]

# ========== データ準備 ==========

def prepare_training_data() -> Dataset:
    """学習データを準備する"""
    # ここに実際の宇宙ドメインデータを入れる
    data = {
        "anchor": [
            "ホーマン遷移軌道の計算",
            "比推力Ispの定義",
            "LEO軌道の特性",
            "ツィオルコフスキー方程式",
            "軌道傾斜角変更のコスト",
            # ... 実際には1000件以上
        ],
        "positive": [
            "Hohmann Transfer Orbit: 最小エネルギーで2つの円軌道間を移動する楕円軌道",
            "Specific Impulse: 推力を推進剤質量フロー(g₀乗算)で割った推進効率の指標",
            "Low Earth Orbit: 高度200〜2000kmの地球周回軌道、国際宇宙ステーションが位置する",
            "Tsiolkovsky Rocket Equation: ΔV = Isp×g₀×ln(m₀/mf)",
            "軌道面変更はコストが高く、傾斜角変更に必要なΔV = 2v×sin(Δi/2)",
        ],
    }
    return Dataset.from_dict(data)


def prepare_eval_data():
    """評価データを準備する（Information Retrieval形式）"""
    queries = {
        "q1": "比推力の計算方法を教えてください",
        "q2": "LEO軌道からGEOへの遷移",
        "q3": "ロケットの質量比計算",
    }

    corpus = {
        "d1": "比推力（Isp）はF/(ṁ×g₀)で計算。単位は秒。",
        "d2": "低地球軌道（LEO）は高度200〜2000km。ISS軌道高度約400km。",
        "d3": "静止軌道（GEO）は高度35,786km。ホーマン遷移でLEOから到達可能。",
        "d4": "ツィオルコフスキー方程式: ΔV = Isp × g₀ × ln(m₀/mf)",
        "d5": "ホーマン遷移軌道は最小エネルギー軌道変換。2回のバーンが必要。",
    }

    relevant_docs = {
        "q1": {"d1"},
        "q2": {"d2", "d3", "d5"},
        "q3": {"d4"},
    }

    return queries, corpus, relevant_docs


# ========== Fine-tuning実行 ==========

def main():
    print(f"ベースモデル: {BASE_MODEL}")
    print(f"Matryoshka次元: {MATRYOSHKA_DIMS}")

    # モデルロード
    model = SentenceTransformer(BASE_MODEL)

    # 学習データ
    train_dataset = prepare_training_data()

    # 損失関数: MNR Loss + Matryoshka Loss の組み合わせ
    base_loss = MultipleNegativesRankingLoss(model=model)
    loss = MatryoshkaLoss(
        model=model,
        loss=base_loss,
        matryoshka_dims=MATRYOSHKA_DIMS,
    )

    # 評価器
    queries, corpus, relevant_docs = prepare_eval_data()
    evaluator = InformationRetrievalEvaluator(
        queries=queries,
        corpus=corpus,
        relevant_docs=relevant_docs,
        name="aerospace-ir-eval",
    )

    # 学習設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args = SentenceTransformerTrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=32,  # GPUメモリに応じて調整
        learning_rate=2e-5,
        warmup_ratio=0.1,
        fp16=False,
        bf16=False,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
        load_best_model_at_end=True,
        logging_steps=10,
        run_name=f"aerospace-embedding-{timestamp}",
    )

    # 学習実行
    trainer = SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        loss=loss,
        evaluator=evaluator,
    )

    print("Fine-tuning開始...")
    trainer.train()

    # 最終評価
    results = evaluator(model)
    print(f"\n=== 最終評価結果 ===")
    for metric, value in results.items():
        print(f"  {metric}: {value:.4f}")

    # 保存
    model.save_pretrained(OUTPUT_DIR)
    print(f"\nモデルを保存しました: {OUTPUT_DIR}")
    return model


if __name__ == "__main__":
    model = main()
```

---

### 精度評価（Recall@K、MRR、NDCG）

```python
# evaluate_embeddings.py

import numpy as np
from typing import Dict, List, Set
from sentence_transformers import SentenceTransformer


def evaluate_retrieval(
    model: SentenceTransformer,
    queries: Dict[str, str],
    corpus: Dict[str, str],
    relevant_docs: Dict[str, Set[str]],
    k_values: List[int] = [1, 5, 10],
    embedding_dim: int = None,  # Matryoshka次元指定（Noneで全次元）
) -> Dict[str, float]:
    """
    情報検索精度を評価する。

    指標:
    - Recall@K: 上位K件に正解が含まれる割合
    - MRR (Mean Reciprocal Rank): 最初の正解の順位の逆数の平均
    - NDCG@K (Normalized Discounted Cumulative Gain): 順位を考慮した精度
    """
    if embedding_dim:
        query_embeddings = model.encode(
            list(queries.values()), normalize_embeddings=True
        )[:, :embedding_dim]
        corpus_embeddings = model.encode(
            list(corpus.values()), normalize_embeddings=True
        )[:, :embedding_dim]
        # 再正規化
        query_embeddings /= np.linalg.norm(query_embeddings, axis=1, keepdims=True)
        corpus_embeddings /= np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
    else:
        query_embeddings = model.encode(
            list(queries.values()), normalize_embeddings=True
        )
        corpus_embeddings = model.encode(
            list(corpus.values()), normalize_embeddings=True
        )

    query_ids = list(queries.keys())
    corpus_ids = list(corpus.keys())

    # コサイン類似度行列（内積で計算、normalize済みなので同等）
    similarity_matrix = np.dot(query_embeddings, corpus_embeddings.T)

    metrics = {}
    recalls = {k: [] for k in k_values}
    mrr_scores = []
    ndcg_scores = {k: [] for k in k_values}

    for i, q_id in enumerate(query_ids):
        ranked_indices = np.argsort(similarity_matrix[i])[::-1]
        ranked_corpus_ids = [corpus_ids[idx] for idx in ranked_indices]

        gold_docs = relevant_docs.get(q_id, set())

        # Recall@K
        for k in k_values:
            top_k = set(ranked_corpus_ids[:k])
            recall = len(top_k & gold_docs) / len(gold_docs) if gold_docs else 0
            recalls[k].append(recall)

        # MRR
        mrr = 0.0
        for rank, doc_id in enumerate(ranked_corpus_ids, start=1):
            if doc_id in gold_docs:
                mrr = 1.0 / rank
                break
        mrr_scores.append(mrr)

        # NDCG@K
        for k in k_values:
            dcg = 0.0
            idcg = sum(1.0 / np.log2(r + 2) for r in range(min(len(gold_docs), k)))
            for rank, doc_id in enumerate(ranked_corpus_ids[:k], start=1):
                if doc_id in gold_docs:
                    dcg += 1.0 / np.log2(rank + 1)
            ndcg = dcg / idcg if idcg > 0 else 0
            ndcg_scores[k].append(ndcg)

    # 集計
    for k in k_values:
        metrics[f"Recall@{k}"] = np.mean(recalls[k])
        metrics[f"NDCG@{k}"] = np.mean(ndcg_scores[k])
    metrics["MRR"] = np.mean(mrr_scores)

    return metrics


# 使用例・比較評価
def compare_models():
    queries = {
        "q1": "比推力の計算方法",
        "q2": "ホーマン遷移のデルタV",
        "q3": "LEO軌道の高度範囲",
    }
    corpus = {
        "d1": "比推力（Isp）= F / (ṁ × g₀)  単位: 秒",
        "d2": "ホーマン遷移のΔV第一バーン: √(μ/r₁)×(√(2r₂/(r₁+r₂)) - 1)",
        "d3": "低地球軌道（LEO）: 高度200〜2000km",
        "d4": "静止軌道（GEO）: 高度35,786km",
        "d5": "比推力と推力の関係: F = Isp × g₀ × ṁ",
    }
    relevant_docs = {
        "q1": {"d1", "d5"},
        "q2": {"d2"},
        "q3": {"d3"},
    }

    print("=== モデル比較評価 ===\n")

    # 汎用モデル
    base_model = SentenceTransformer("intfloat/multilingual-e5-base")
    base_metrics = evaluate_retrieval(base_model, queries, corpus, relevant_docs)

    # Fine-tuningモデル
    fine_tuned = SentenceTransformer("./aerospace-embedding-v1")
    ft_metrics = evaluate_retrieval(fine_tuned, queries, corpus, relevant_docs)

    # 結果比較
    print(f"{'指標':<15} {'汎用モデル':>12} {'Fine-tuned':>12} {'改善':>10}")
    print("-" * 55)
    for metric in ["Recall@1", "Recall@5", "MRR", "NDCG@5"]:
        base_val = base_metrics.get(metric, 0)
        ft_val = ft_metrics.get(metric, 0)
        improvement = (ft_val - base_val) / base_val * 100 if base_val > 0 else 0
        print(f"{metric:<15} {base_val:>12.4f} {ft_val:>12.4f} {improvement:>+9.1f}%")

    # Matryoshka次元別評価
    print("\n=== Matryoshka次元別のMRR ===")
    for dim in [64, 128, 256, 512, 768]:
        metrics = evaluate_retrieval(
            fine_tuned, queries, corpus, relevant_docs, embedding_dim=dim
        )
        print(f"  {dim}次元: MRR={metrics['MRR']:.4f}")


if __name__ == "__main__":
    compare_models()
```

---

### Fine-tuning済みEmbeddingのRAG統合

```python
# rag_with_finetuned_embedding.py

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

class AerospaceRAG:
    """Fine-tuning済みEmbeddingを使ったRAGシステム"""

    def __init__(
        self,
        embedding_model_path: str = "./aerospace-embedding-v1",
        embedding_dim: int = 256,  # Matryoshkaで最適な次元を選択
        collection_name: str = "aerospace_docs",
    ):
        # Fine-tuning済みモデルをロード
        self.model = SentenceTransformer(
            embedding_model_path,
            truncate_dim=embedding_dim,  # Matryoshka次元指定
        )
        self.dim = embedding_dim

        # ChromaDBクライアント
        self.client = chromadb.PersistentClient(path="./chroma_aerospace")

        # カスタムEmbedding関数
        class AerospaceEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, model):
                self.model = model
            def __call__(self, input):
                return self.model.encode(
                    input, normalize_embeddings=True
                ).tolist()

        self.ef = AerospaceEmbeddingFunction(self.model)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"RAGシステム初期化完了: {embedding_dim}次元Embedding使用")

    def add_documents(self, documents: list, ids: list, metadatas: list = None):
        """ドキュメントをインデックスに追加"""
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas or [{}] * len(documents),
        )
        print(f"{len(documents)}件のドキュメントを追加しました")

    def search(self, query: str, n_results: int = 5) -> list:
        """類似ドキュメントを検索"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        docs = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        return [
            {
                "document": doc,
                "similarity": 1 - dist,  # cosine distanceを類似度に変換
                "metadata": meta,
            }
            for doc, dist, meta in zip(docs, distances, metadatas)
        ]


# 使用例
if __name__ == "__main__":
    rag = AerospaceRAG(embedding_dim=256)

    # ドキュメント追加
    rag.add_documents(
        documents=[
            "ホーマン遷移軌道は2つの円軌道間を最小燃料で移動する楕円軌道。",
            "比推力（Isp）はエンジン効率の指標。単位は秒。値が大きいほど燃費が良い。",
            "LEO（低地球軌道）は高度200〜2000kmの軌道。ISS（国際宇宙ステーション）は高度約400km。",
        ],
        ids=["doc1", "doc2", "doc3"],
        metadatas=[
            {"category": "orbital_mechanics"},
            {"category": "propulsion"},
            {"category": "orbits"},
        ],
    )

    # 検索テスト
    results = rag.search("ホーマン軌道でデルタVを節約する方法")
    for r in results:
        print(f"類似度: {r['similarity']:.3f} | {r['document'][:50]}...")
```

---

## 17. 学習 vs エージェント - 何をどこまでやるか

### LLM単体の限界

LLMはテキスト生成機械です。学習データに含まれる知識を確率的に再現しますが、以下のことは**できません**:

```
LLM単体でできないこと:
  × ファイルを読み書きする
  × コマンドを実行する
  × 最新情報を取得する（学習データのカットオフ以降）
  × 計算を正確に行う（確率的生成のため誤差が出る）
  × 外部APIを呼び出す
  × 自分の回答を覚えておく（ステートレス）
```

これらを実現するために「エージェント」と「RAG」が必要になります。

---

### 3層構造の理解

```
┌─────────────────────────────────────────────────────────────┐
│                     システム全体像                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 3: エージェントフレームワーク                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ファイル操作 / コマンド実行 / Web検索 / API呼び出し    │  │
│  │ ツール使用 / 計画・実行・検証ループ                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                  │
│  Layer 2: RAGシステム                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 最新ドキュメント / 大量データ / 正確な引用             │  │
│  │ ベクトルDB / Embedding検索 / コンテキスト注入           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                  │
│  Layer 1: LLMコア（学習で改善）                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 専門知識 / 推論力 / コード品質 / 文体・指示への従順性  │  │
│  │ Fine-tuning / LoRA / DPO                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**各レイヤーの役割分担:**

| やりたいこと | 適切な手段 | 理由 |
|---|---|---|
| 宇宙工学の専門用語を正しく使う | 学習（Fine-tuning） | 知識自体をモデルに埋め込む |
| 計算ミスを減らす | 学習（CoT + RLHF） | 推論パターンを改善する |
| 最新のJAXA発表を参照する | RAG | 学習データに含まれない |
| 軌道計算ツールを使う | エージェント | 外部ツールの呼び出し |
| ファイルを生成・保存する | エージェント | ファイルシステムアクセス |
| 過去の会話を記憶する | エージェント + DB | ステート管理が必要 |
| 回答の語調を調整する | 学習（DPO/RLHF） | 嗜好・スタイルの最適化 |

---

### 判断フローチャート（何を実装するか）

```
ユーザーが「やりたいこと」を伝える
                |
                v
    ┌───────────────────────┐
    │  外部ツールや操作が   │
    │  必要か？             │
    │  (ファイル、コマンド、│
    │   API、Web検索...)    │
    └───────────────────────┘
          |           |
         YES          NO
          |           |
          v           v
    [エージェント]  ┌───────────────────────┐
    実装を追加      │  最新情報や大量の      │
                   │  ドキュメントを        │
                   │  参照する必要があるか？│
                   └───────────────────────┘
                         |           |
                        YES          NO
                         |           |
                         v           v
                      [RAG]    ┌───────────────────────┐
                    実装を追加  │  現在の回答品質は     │
                               │  許容できるか？        │
                               └───────────────────────┘
                                     |           |
                                    NO          YES
                                     |           |
                                     v           v
                               ┌──────────┐  [完成]
                               │どこが悪い│  そのまま運用
                               │      か？│
                               └──────────┘
                                  |     |
                    専門知識が足りない   語調・スタイルが
                        |               合わない
                        v                   |
                [SFT Fine-tuning]            v
                 専門データで追加学習    [DPO Fine-tuning]
                                        好みのデータで調整
```

---

### 構築フェーズの推奨順序

#### Phase 1: エージェントフレームワーク（必須・最初に構築）

**なぜ最初か:** エージェントがなければLLMはテキスト生成しかできない。コードの読み書き・実行がClaude Codeクローンの核心。

```
所要時間: 1〜2週間
コスト:   開発者の時間のみ（ライブラリはOSS）
成果物:
  - ツール定義（read_file, write_file, execute_command, web_search）
  - ツール選択ループ（ReActパターン）
  - 安全機構（実行前の確認、サンドボックス）
  - コンテキスト管理（会話履歴の管理）

参考ライブラリ:
  - LangGraph（複雑なフロー制御）
  - smolagents（HuggingFace、軽量）
  - 独自実装（最大の制御性）
```

#### Phase 2: RAGシステム（次に重要）

**なぜ2番目か:** 専門ドキュメントを参照できるようにすることで、回答品質が劇的に向上する。Fine-tuningよりコストが低い。

```
所要時間: 1〜2週間
コスト:   ベクトルDB（無料〜$50/月）
成果物:
  - ドキュメントの分割・Embedding化
  - ベクトルDB（ChromaDB / Qdrant）
  - 検索・コンテキスト注入パイプライン
  - Embedding品質評価

推奨構成:
  Embedding: intfloat/multilingual-e5-base（日本語対応）
  VectorDB:  ChromaDB（ローカル）/ Qdrant（本番）
```

#### Phase 3: Fine-tuning（品質向上）

**なぜ3番目か:** エージェントとRAGが動いた後、具体的な品質問題が見えてから対処する。むやみに先行させない。

```
所要時間: 2〜4週間
コスト:   GPU時間（$20〜$200）/ Embedding Fine-tuning（安価）

段階的アプローチ:
  Step 1: Embedding Fine-tuning（検索精度向上、低コスト）
           → セクション16参照
  Step 2: SFT（専門知識の補強）
           → 宇宙工学QAデータセット1000〜5000件
  Step 3: DPO（回答スタイルの最適化）
           → エキスパートフィードバックから生成
           → セクション19参照
```

#### Phase 4: 高度機能（任意・余裕があれば）

```
所要時間: 状況による
コスト:   状況による

選択肢:
  - マルチエージェント（複数のAIが協調）
  - 継続学習（新ドキュメントで自動更新）
  - モデルの蒸留（大モデル→小モデルに知識転送）
  - 特定タスク専用LoRA（軌道計算専用など）
```

---

### 各フェーズのコスト・時間の目安

| フェーズ | 作業 | 所要時間 | 計算コスト | 優先度 |
|---|---|---|---|---|
| Phase 1 | エージェント実装 | 1〜2週間 | $0 | 必須 |
| Phase 2 | RAG構築 | 1〜2週間 | $0〜$10 | 高 |
| Phase 2+ | Embedding Fine-tuning | 2〜3日 | $5〜$20 | 中 |
| Phase 3 | SFT (7B, LoRA) | 3〜5日 | $30〜$100 | 中 |
| Phase 3 | DPO | 2〜3日 | $20〜$80 | 低〜中 |
| Phase 4 | マルチエージェント | 2〜4週間 | $0〜$50 | 任意 |

> コスト試算: RTX 3090相当のGPUをクラウドでレンタルした場合の目安
> Raspberry Pi での学習は現実的でないため、クラウドGPUを推奨

---

## 18. Human-in-the-Loop（人間が関与すべきポイント）

### 構築フェーズでの人間のタスク

| タスク | 内容 | 所要時間目安 | 自動化可否 |
|---|---|---|---|
| **モデル選択** | ベースモデルの評価・選定 | 1〜3日 | 補助可能、判断は人間 |
| **プロンプト設計** | システムプロンプトの策定 | 2〜5日 | 生成補助可能、評価は人間 |
| **学習データ収集** | ドメイン文書の収集・選別 | 1〜4週間 | 収集は自動化可、選別は人間 |
| **アノテーション** | QAペアの正解付け | 1〜2週間 | 部分的に自動化可能 |
| **DPOデータ評価** | 回答AvsB の優劣判断 | 2〜5日 | 専門家が必要 |
| **ツール定義** | エージェントのツール設計 | 3〜7日 | 設計は人間 |
| **安全基準策定** | 拒否すべき操作の定義 | 1〜3日 | 人間必須 |
| **品質評価指標** | 何を「良い回答」とするか | 1〜2日 | 人間必須 |

### 運用フェーズでの人間のタスク

| タスク | 推奨頻度 | 内容 | 優先度 |
|---|---|---|---|
| **品質チェック** | 週1回以上 | ランダムサンプリングで回答確認 | 高 |
| **フィードバック確認** | 週2〜3回 | ユーザーからの報告のトリアージ | 高 |
| **異常検知確認** | 毎日 | 低評価率・エラー率の監視 | 高 |
| **新データ評価** | 月1〜2回 | 追加学習データの品質確認 | 中 |
| **再学習判断** | 月1回 | モデル更新が必要かの判断 | 中 |
| **セキュリティ審査** | 四半期 | 悪用パターンの確認と対策 | 中 |
| **ベンチマーク** | 月1回 | 最新モデルとの比較 | 低 |

---

### 自動化できることvs人間が判断すべきこと

```
自動化できること:
  ✓ ログ収集と集計
  ✓ エラー率・低評価率の監視アラート
  ✓ A/Bテストの統計的有意差の計算
  ✓ 学習データの形式チェック
  ✓ モデルのベンチマーク実行
  ✓ Embeddingのインデックス更新
  ✓ ルーティング（軽微な質問 vs 重要な質問の分類）
  ✓ フィードバックの一次分類

人間が必ず判断すべきこと:
  ✗ 「これは正しい専門知識か」の判断（特に安全性に関わる領域）
  ✗ モデルのリリース判断
  ✗ 倫理的に問題ある出力の定義
  ✗ Fine-tuningデータの品質（代表性・偏り）
  ✗ DPOの優劣判断（chosen vs rejected）
  ✗ 重大なバグやハルシネーション発見時の対応
  ✗ ユーザーへの謝罪・説明が必要な事象
```

---

### 継続的改善サイクル（PDCA）

```
┌──────────────────────────────────────────────────────────┐
│                   継続的改善サイクル                      │
│                                                          │
│   ┌─────────────┐          ┌─────────────┐              │
│   │   PLAN      │ ──────→ │    DO       │              │
│   │             │          │             │              │
│   │ 目標設定    │          │ モデル運用  │              │
│   │ 改善仮説    │          │ フィードバック│             │
│   │ データ計画  │          │ 収集・蓄積  │              │
│   └─────────────┘          └─────────────┘              │
│          ↑                        ↓                      │
│   ┌─────────────┐          ┌─────────────┐              │
│   │   ACT       │ ←────── │   CHECK     │              │
│   │             │          │             │              │
│   │ 再学習実行  │          │ 品質評価    │              │
│   │ プロンプト  │          │ エラー分析  │              │
│   │ 改善        │          │ A/Bテスト   │              │
│   └─────────────┘          └─────────────┘              │
│                                                          │
└──────────────────────────────────────────────────────────┘

具体的な運用スケジュール例:

月曜: 週次品質レポート確認（自動生成）
火曜: フィードバックのトリアージと優先付け
水木: データ作成・ラベリング作業
金曜: 小規模な改善のデプロイ・効果確認

月次: ベンチマーク実行、再学習判断、ロードマップ更新
```

---

### 失敗パターンと回避策

| 失敗パターン | 症状 | 原因 | 回避策 |
|---|---|---|---|
| **学習しても賢くならない** | Fine-tuning後も改善なし | 学習データが少ない・品質が低い | 最低1000件、人間がチェックしたデータで学習 |
| **一般能力が下がった** | 専門知識は増えたが基本タスクが劣化 | 過学習・Catastrophic Forgetting | LoRAを使う、汎用データを混ぜて学習 |
| **RAGが不正確** | 参照文書が的外れ | Embeddingモデルが不適切 | ドメインFine-tuning（セクション16参照） |
| **ハルシネーションが増加** | もっともらしい嘘をつく | 学習データに誤情報が含まれる | データクレンジング、専門家によるレビュー |
| **回答が長くなりすぎた** | 冗長な回答 | SFT学習データが長文ばかり | 短文の正例をDPOデータに含める |
| **特定トピックで崩壊** | 一部のトピックで壊滅的な回答 | カバレッジの偏り | データの分布を確認し、不足トピックを補充 |
| **フィードバックが集まらない** | 品質改善のデータが不足 | UIが複雑 / インセンティブなし | セクション19のUI設計を参照 |
| **改善サイクルが止まる** | 最初の学習で満足して放置 | 担当者不在 / 目標不明確 | 定期的なPDCAを組織に組み込む |

---

## 19. エキスパートフィードバック収集システム

### フィードバック収集のUI/UX設計原則

専門家からのフィードバックは**貴重だが時間が限られる**。UIは以下を意識します:

```
設計原則:
1. 最小摩擦: 1クリックで最低限のフィードバックを完了できる
2. 段階的詳細: 詳しく伝えたい場合の入力欄も用意する
3. 文脈を保持: フィードバックする回答が常に見えている
4. 即時フィードバック: 送信後に「ありがとう」の反応を返す
5. 重複なし: 同じ回答に複数回フィードバックしないよう管理
```

---

### SQLiteフィードバックDB設計

```sql
-- feedback_schema.sql

-- セッション管理
CREATE TABLE sessions (
    session_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    user_role    TEXT NOT NULL,  -- 'expert', 'user', 'admin'
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会話ログ
CREATE TABLE conversations (
    conv_id      TEXT PRIMARY KEY,
    session_id   TEXT REFERENCES sessions(session_id),
    query        TEXT NOT NULL,
    response     TEXT NOT NULL,
    model_name   TEXT NOT NULL,
    prompt_tokens    INTEGER,
    response_tokens  INTEGER,
    latency_ms       INTEGER,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- フィードバック（1レコード = 1回の評価）
CREATE TABLE feedback (
    feedback_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    conv_id      TEXT REFERENCES conversations(conv_id),
    user_id      TEXT NOT NULL,

    -- 即時評価（必須）
    rating       INTEGER CHECK(rating IN (-1, 0, 1)),  -- -1:Bad, 0:Neutral, 1:Good

    -- 詳細タグ（複数選択可、カンマ区切り）
    error_tags   TEXT,  -- 'factual_error,missing_knowledge,wrong_term,calc_error'

    -- 自由記述（任意）
    comment      TEXT,

    -- 正解情報（知識ギャップ報告用）
    correct_answer  TEXT,      -- 正しい回答があれば記入
    missing_info    TEXT,      -- 足りなかった情報
    reference_url   TEXT,      -- 参考文献URL

    -- メタデータ
    is_dpo_candidate  BOOLEAN DEFAULT FALSE,  -- DPOデータ化の候補
    reviewed_by       TEXT,    -- レビュアーのID
    reviewed_at       TIMESTAMP,

    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DPOデータセット（フィードバックから自動生成）
CREATE TABLE dpo_dataset (
    dpo_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt       TEXT NOT NULL,
    chosen       TEXT NOT NULL,  -- 良い回答
    rejected     TEXT NOT NULL,  -- 悪い回答
    source_conv_id_chosen   TEXT,  -- 元の会話ID
    source_conv_id_rejected TEXT,
    source_feedback_id      INTEGER,
    quality_score  REAL,   -- 0.0〜1.0
    approved_by    TEXT,   -- 承認者
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知識ギャップ追跡
CREATE TABLE knowledge_gaps (
    gap_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    topic        TEXT NOT NULL,   -- 「ホーマン遷移の計算」など
    description  TEXT NOT NULL,
    frequency    INTEGER DEFAULT 1,   -- 同じギャップが何回報告されたか
    priority     TEXT DEFAULT 'medium',  -- 'high', 'medium', 'low'
    status       TEXT DEFAULT 'open',    -- 'open', 'in_progress', 'resolved'
    resolved_by  TEXT,   -- 学習データ追加、RAG更新など
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_feedback_conv_id ON feedback(conv_id);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_conversations_created ON conversations(created_at);
CREATE INDEX idx_knowledge_gaps_topic ON knowledge_gaps(topic);
```

---

### StreamlitによるフィードバックUI実装

```python
# feedback_app.py
# 実行: streamlit run feedback_app.py

import sqlite3
import uuid
import json
import os
from datetime import datetime
from typing import Optional
import streamlit as st
import pandas as pd

# ========== DB操作クラス ==========

class FeedbackDB:
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """スキーマを初期化する"""
        with self._get_conn() as conn:
            with open("feedback_schema.sql") as f:
                conn.executescript(f.read())

    def save_conversation(
        self, query: str, response: str, model_name: str = "local-llm"
    ) -> str:
        """会話を保存してconversation IDを返す"""
        conv_id = str(uuid.uuid4())
        session_id = st.session_state.get("session_id", str(uuid.uuid4()))

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions (session_id, user_id, user_role)
                VALUES (?, ?, ?)
                """,
                (session_id, st.session_state.get("user_id", "anonymous"), "expert"),
            )
            conn.execute(
                """
                INSERT INTO conversations
                (conv_id, session_id, query, response, model_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conv_id, session_id, query, response, model_name),
            )
        return conv_id

    def save_feedback(
        self,
        conv_id: str,
        rating: int,
        error_tags: list,
        comment: str = "",
        correct_answer: str = "",
        missing_info: str = "",
        reference_url: str = "",
    ) -> int:
        """フィードバックを保存"""
        user_id = st.session_state.get("user_id", "anonymous")
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO feedback
                (conv_id, user_id, rating, error_tags, comment,
                 correct_answer, missing_info, reference_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conv_id, user_id, rating,
                    ",".join(error_tags) if error_tags else "",
                    comment, correct_answer, missing_info, reference_url,
                ),
            )
            return cursor.lastrowid

    def get_feedback_stats(self) -> dict:
        """フィードバックの集計を返す"""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            good = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE rating=1"
            ).fetchone()[0]
            bad = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE rating=-1"
            ).fetchone()[0]

            tags_raw = conn.execute(
                "SELECT error_tags FROM feedback WHERE error_tags != ''"
            ).fetchall()
            tag_counts = {}
            for (tags_str,) in tags_raw:
                for tag in tags_str.split(","):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total": total,
            "good": good,
            "bad": bad,
            "neutral": total - good - bad,
            "satisfaction_rate": good / total if total > 0 else 0,
            "tag_counts": tag_counts,
        }

    def get_recent_feedback(self, limit: int = 50) -> pd.DataFrame:
        """最近のフィードバックをDataFrameで返す"""
        with self._get_conn() as conn:
            df = pd.read_sql_query(
                """
                SELECT
                    f.feedback_id,
                    c.query,
                    c.response,
                    f.rating,
                    f.error_tags,
                    f.comment,
                    f.correct_answer,
                    f.created_at
                FROM feedback f
                JOIN conversations c ON f.conv_id = c.conv_id
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                conn,
                params=(limit,),
            )
        return df


# ========== Streamlitアプリ ==========

db = FeedbackDB()

ERROR_TAGS = {
    "factual_error": "事実誤認",
    "missing_knowledge": "知識不足",
    "wrong_term": "用語の誤用",
    "calc_error": "計算ミス",
    "outdated_info": "情報が古い",
    "off_topic": "的外れな回答",
    "too_vague": "回答が曖昧",
    "too_verbose": "回答が冗長",
}


def render_chat_interface():
    """メインのチャット + インラインフィードバックUI"""
    st.title("宇宙ドメインAI - エキスパート評価版")

    # ユーザーID設定（サイドバー）
    with st.sidebar:
        st.header("評価者設定")
        user_name = st.text_input("お名前 / ID", value="expert_01")
        st.session_state["user_id"] = user_name
        st.session_state["session_id"] = st.session_state.get(
            "session_id", str(uuid.uuid4())
        )
        st.info(f"Session: {st.session_state['session_id'][:8]}...")

        st.markdown("---")
        st.markdown("**評価の目的**")
        st.markdown("- 事実誤認の検出\n- 知識ギャップの発見\n- 用語の正確性確認")

    # 会話履歴の表示
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # AIの回答にフィードバックボタンを追加
            if msg["role"] == "assistant" and "conv_id" in msg:
                render_inline_feedback(msg["conv_id"], msg.get("feedback_given", False))

    # 入力欄
    if prompt := st.chat_input("宇宙工学について質問してください"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AIの回答を生成（実際はLLM APIを呼び出す）
        response = generate_response(prompt)
        conv_id = db.save_conversation(prompt, response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "conv_id": conv_id,
            "feedback_given": False,
        })

        with st.chat_message("assistant"):
            st.markdown(response)
            render_inline_feedback(conv_id, False)

        st.rerun()


def render_inline_feedback(conv_id: str, already_submitted: bool):
    """回答の直下に表示するインラインフィードバック"""
    if already_submitted:
        st.caption("フィードバック済み")
        return

    col1, col2, col3, col_space = st.columns([1, 1, 1, 6])

    with col1:
        if st.button("Good", key=f"good_{conv_id}", help="良い回答"):
            _submit_quick_feedback(conv_id, 1)
    with col2:
        if st.button("Bad", key=f"bad_{conv_id}", help="改善が必要"):
            st.session_state[f"show_detail_{conv_id}"] = True
    with col3:
        if st.button("詳細", key=f"detail_{conv_id}", help="詳細フィードバック"):
            st.session_state[f"show_detail_{conv_id}"] = True

    # 詳細フィードバックフォーム
    if st.session_state.get(f"show_detail_{conv_id}", False):
        render_detailed_feedback_form(conv_id)


def render_detailed_feedback_form(conv_id: str):
    """詳細フィードバック入力フォーム"""
    with st.expander("詳細フィードバック", expanded=True):
        rating = st.radio(
            "総合評価",
            options=[1, 0, -1],
            format_func=lambda x: {1: "良い", 0: "普通", -1: "問題あり"}[x],
            horizontal=True,
            key=f"rating_{conv_id}",
        )

        selected_tags = st.multiselect(
            "問題のカテゴリ（複数選択可）",
            options=list(ERROR_TAGS.keys()),
            format_func=lambda x: ERROR_TAGS[x],
            key=f"tags_{conv_id}",
        )

        comment = st.text_area(
            "コメント（何が問題でしたか？）",
            key=f"comment_{conv_id}",
            placeholder="例: ホーマン遷移の第二バーンの計算式が間違っています",
            height=80,
        )

        correct_answer = st.text_area(
            "正しい回答（わかる場合）",
            key=f"correct_{conv_id}",
            placeholder="例: 正しくは ΔV₂ = √(μ/r₂) × (1 - √(2r₁/(r₁+r₂))) です",
            height=80,
        )

        reference_url = st.text_input(
            "参考文献URL",
            key=f"ref_{conv_id}",
            placeholder="https://www.isas.jaxa.jp/...",
        )

        col_submit, col_cancel = st.columns(2)
        with col_submit:
            if st.button("送信", key=f"submit_{conv_id}", type="primary"):
                feedback_id = db.save_feedback(
                    conv_id=conv_id,
                    rating=rating,
                    error_tags=selected_tags,
                    comment=comment,
                    correct_answer=correct_answer,
                    reference_url=reference_url,
                )
                st.success(f"フィードバックを受け付けました（ID: {feedback_id}）")
                st.session_state[f"show_detail_{conv_id}"] = False
                st.rerun()
        with col_cancel:
            if st.button("キャンセル", key=f"cancel_{conv_id}"):
                st.session_state[f"show_detail_{conv_id}"] = False
                st.rerun()


def _submit_quick_feedback(conv_id: str, rating: int):
    """クイックフィードバックを送信"""
    db.save_feedback(conv_id=conv_id, rating=rating, error_tags=[])
    for msg in st.session_state.messages:
        if msg.get("conv_id") == conv_id:
            msg["feedback_given"] = True
    st.toast("フィードバックありがとうございます！")
    st.rerun()


def generate_response(query: str) -> str:
    """LLM APIを呼び出して回答を生成（実装は各自のLLMに合わせる）"""
    # Cerebras APIを使う場合の例
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ.get("CEREBRAS_API_KEY"),
            base_url="https://api.cerebras.ai/v1",
        )
        response = client.chat.completions.create(
            model="llama3.1-70b",
            messages=[
                {"role": "system", "content": "あなたは宇宙工学の専門家AIです。"},
                {"role": "user", "content": query},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return f"（デモ）「{query}」に対する回答です。実際はLLM APIを呼び出します。"


# ========== ダッシュボード ==========

def render_dashboard():
    """フィードバック集計ダッシュボード"""
    st.title("フィードバック分析ダッシュボード")

    stats = db.get_feedback_stats()

    # KPIカード
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総フィードバック数", stats["total"])
    with col2:
        st.metric("良い回答", stats["good"], delta=None)
    with col3:
        st.metric("問題あり", stats["bad"])
    with col4:
        satisfaction = stats["satisfaction_rate"] * 100
        st.metric("満足度", f"{satisfaction:.1f}%")

    st.markdown("---")

    # エラータグの分布
    if stats["tag_counts"]:
        st.subheader("問題カテゴリの分布")
        tag_df = pd.DataFrame(
            [
                {"カテゴリ": ERROR_TAGS.get(k, k), "件数": v}
                for k, v in sorted(stats["tag_counts"].items(), key=lambda x: -x[1])
            ]
        )
        st.bar_chart(tag_df.set_index("カテゴリ"))

    # 最近のフィードバック一覧
    st.subheader("最近のフィードバック")
    df = db.get_recent_feedback(limit=20)
    if not df.empty:
        df["評価"] = df["rating"].map({1: "Good", 0: "Neutral", -1: "Bad"})
        st.dataframe(
            df[["評価", "query", "error_tags", "comment", "created_at"]].rename(
                columns={
                    "query": "質問",
                    "error_tags": "タグ",
                    "comment": "コメント",
                    "created_at": "日時",
                }
            ),
            use_container_width=True,
        )
    else:
        st.info("まだフィードバックがありません")

    # DPOデータへのエクスポートボタン
    st.subheader("DPOデータ生成")
    if st.button("フィードバックからDPOデータを生成", type="primary"):
        pipeline = FeedbackToDPOPipeline()
        dpo_count = pipeline.run()
        st.success(f"{dpo_count}件のDPOデータを生成しました")

        dpo_df = load_dpo_dataset()
        if not dpo_df.empty:
            csv = dpo_df.to_csv(index=False)
            st.download_button(
                "DPOデータをCSVでダウンロード",
                data=csv,
                file_name=f"dpo_dataset_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )


# ========== メインナビゲーション ==========

def main():
    st.set_page_config(
        page_title="宇宙AI フィードバックシステム",
        layout="wide",
    )

    page = st.sidebar.radio(
        "ページ選択",
        ["チャット & 評価", "ダッシュボード"],
    )

    if page == "チャット & 評価":
        render_chat_interface()
    elif page == "ダッシュボード":
        render_dashboard()


if __name__ == "__main__":
    main()
```

---

### フィードバックからDPOデータへの自動変換パイプライン

```python
# feedback_to_dpo_pipeline.py

import sqlite3
import json
from datetime import datetime
from typing import Optional
import pandas as pd


class FeedbackToDPOPipeline:
    """
    フィードバックデータをDPO学習データに変換するパイプライン

    DPOデータ形式:
    {
        "prompt":   "ユーザーの質問",
        "chosen":   "良い回答（エキスパートが承認）",
        "rejected": "悪い回答（エキスパートが否定）"
    }
    """

    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def generate_dpo_pairs(
        self,
        min_rating_diff: int = 2,
        min_feedback_count: int = 2,
    ) -> list:
        """
        フィードバックからDPOペアを生成する。

        戦略1: 同じクエリに対して良い回答と悪い回答が存在する場合
        戦略2: 悪い回答 + エキスパートが提供した「正しい回答」の組み合わせ
        """
        dpo_pairs = []

        with self._get_conn() as conn:
            # 戦略2: 正しい回答が提供されたケース（最も信頼性が高い）
            rows = conn.execute(
                """
                SELECT
                    c.query,
                    c.response as bad_response,
                    f.correct_answer,
                    f.comment,
                    f.error_tags,
                    f.feedback_id
                FROM feedback f
                JOIN conversations c ON f.conv_id = c.conv_id
                WHERE f.rating = -1
                  AND f.correct_answer IS NOT NULL
                  AND f.correct_answer != ''
                ORDER BY f.created_at DESC
                """
            ).fetchall()

            for row in rows:
                query, bad_resp, correct_answer, comment, tags, fb_id = row
                dpo_pairs.append({
                    "prompt": query,
                    "chosen": correct_answer,
                    "rejected": bad_resp,
                    "source": "expert_correction",
                    "feedback_id": fb_id,
                    "error_tags": tags,
                    "quality_score": 0.9,
                })

            # 戦略1: 同じトピックの良い回答と悪い回答のペアリング
            good_rows = conn.execute(
                """
                SELECT c.query, c.response, f.feedback_id
                FROM feedback f
                JOIN conversations c ON f.conv_id = c.conv_id
                WHERE f.rating = 1
                """
            ).fetchall()

            bad_rows = conn.execute(
                """
                SELECT c.query, c.response, f.feedback_id, f.error_tags
                FROM feedback f
                JOIN conversations c ON f.conv_id = c.conv_id
                WHERE f.rating = -1
                  AND (f.correct_answer IS NULL OR f.correct_answer = '')
                """
            ).fetchall()

            good_by_query = {r[0]: r for r in good_rows}
            for bad_query, bad_resp, bad_fb_id, tags in bad_rows:
                if bad_query in good_by_query:
                    _, good_resp, good_fb_id = good_by_query[bad_query]
                    dpo_pairs.append({
                        "prompt": bad_query,
                        "chosen": good_resp,
                        "rejected": bad_resp,
                        "source": "feedback_comparison",
                        "feedback_id": f"{good_fb_id}_vs_{bad_fb_id}",
                        "error_tags": tags,
                        "quality_score": 0.7,
                    })

        return dpo_pairs

    def save_dpo_dataset(self, dpo_pairs: list, output_path: str = "dpo_dataset.jsonl"):
        """
        DPOデータをJSONL形式で保存する。

        HuggingFace TRLのDPOTrainerが読み込める形式:
        {"prompt": "...", "chosen": "...", "rejected": "..."}
        """
        saved = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for pair in dpo_pairs:
                if pair["quality_score"] < 0.6:
                    continue
                if len(pair["chosen"]) < 20 or len(pair["rejected"]) < 20:
                    continue

                record = {
                    "prompt": pair["prompt"],
                    "chosen": pair["chosen"],
                    "rejected": pair["rejected"],
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                saved += 1

        print(f"DPOデータ保存完了: {saved}件 → {output_path}")
        return saved

    def run(self, output_path: str = "dpo_dataset.jsonl") -> int:
        """パイプラインを実行"""
        print("Step 1: フィードバックデータを収集中...")
        dpo_pairs = self.generate_dpo_pairs()
        print(f"  候補ペア数: {len(dpo_pairs)}")

        print("Step 2: 品質フィルタリングと保存...")
        count = self.save_dpo_dataset(dpo_pairs, output_path)

        print("Step 3: DBに記録...")
        with sqlite3.connect(self.db_path) as conn:
            for pair in dpo_pairs[:count]:
                conn.execute(
                    """
                    INSERT INTO dpo_dataset
                    (prompt, chosen, rejected, quality_score, source_feedback_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        pair["prompt"],
                        pair["chosen"],
                        pair["rejected"],
                        pair["quality_score"],
                        str(pair.get("feedback_id", "")),
                    ),
                )

        return count


def load_dpo_dataset(db_path: str = "feedback.db") -> pd.DataFrame:
    """DPOデータセットをDataFrameで読み込む"""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM dpo_dataset ORDER BY created_at DESC", conn
        )


if __name__ == "__main__":
    pipeline = FeedbackToDPOPipeline()
    count = pipeline.run()
    print(f"\n生成されたDPOペア数: {count}")
```

---

### フィードバックバイアスへの対処

```
よくあるバイアスと対策:

1. 選択バイアス（Sampling Bias）
   問題: 使いやすいユーザーしかフィードバックしない
   対策: ランダムサンプリングで評価を依頼する仕組みを追加
         例: 10回に1回、評価を強制表示する

2. 好意的バイアス（Acquiescence Bias）
   問題: 専門家が遠慮して厳しいフィードバックをしない
   対策: 匿名フィードバックオプションを提供する
         「厳しい意見を歓迎する」とUIに明示する

3. 最新性バイアス（Recency Bias）
   問題: 最近の回答ばかりフィードバックされる
   対策: 古い会話のランダムサンプリングレビューを定期実施

4. タスク難易度バイアス
   問題: 簡単な質問は高評価、難しい質問は低評価になりがち
   対策: 難易度別に分析する。難しいタスクで低評価は許容すべき場合も
```

---

### 実運用時の注意点（自動化パイプライン）

```
自動化のリスクと対策:

リスク1: フィードバックループの暴走
  症状: 誤ったフィードバックが大量に学習データに入り品質が劣化
  対策:
    - 自動学習の前に必ず人間のレビューフェーズを挟む
    - 品質スコアのしきい値を設ける（quality_score >= 0.8のみ）
    - 前回モデルとのベンチマーク比較を自動実行

リスク2: エキスパートの燃え尽き
  症状: フィードバックの量・質が徐々に低下
  対策:
    - フィードバックにかかる時間を最小化（1クリック評価）
    - 自分のフィードバックが改善に繋がったことを通知する
    - フィードバック数に応じた gamification（ランキング等）

リスク3: ドメイン外の質問への過適応
  症状: 宇宙ドメイン専門になりすぎて汎用能力が低下
  対策:
    - DPOデータに汎用QAを一定割合（20〜30%）混ぜる
    - 定期的に汎用ベンチマーク（MMLU等）でも評価する
```

---

## 付録A: ライセンス一覧

本ガイドで使用するOSSライブラリのライセンス:

| ライブラリ | ライセンス | 商用利用 |
|---------|----------|--------|
| vLLM | Apache 2.0 | 可 |
| Unsloth | Apache 2.0 | 可 |
| TRL (transformers reinforcement learning) | Apache 2.0 | 可 |
| fastembed | MIT | 可 |
| ChromaDB | Apache 2.0 | 可 |
| FAISS | MIT | 可 |
| Qdrant | Apache 2.0 | 可 |
| tiktoken | MIT | 可 |
| Rich | MIT | 可 |
| Typer | MIT | 可 |
| httpx | BSD | 可 |
| docker-py | Apache 2.0 | 可 |
| markdownify | MIT | 可 |

モデルのライセンス（商用利用の注意点）:

| モデル | ライセンス | 商用利用 |
|-------|----------|--------|
| Llama 3.1/3.2 | Meta Llama 3 License | MAU 7億未満は可 |
| Gemma 2/3 | Gemma Terms of Use | 可（条件あり） |
| Codestral | Codestral License | 非商用のみ |
| StarCoder2 | BigCode Open RAIL-M | 制限あり（確認要） |
| GPT-OSS | OpenAI License | 要確認 |
| Mistral | Apache 2.0 | 可 |

> 重要: 商用利用の場合は必ず各モデルの最新ライセンスを確認してください。

---

## 付録B: 参考リンク

### 公式ドキュメント

- [vLLM 公式ドキュメント](https://docs.vllm.ai/)
- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Anthropic Claude Code](https://claude.ai/code)
- [OpenAI Tool Use API](https://platform.openai.com/docs/guides/function-calling)
- [GPT-OSS 公式ガイド](https://developers.openai.com/cookbook/articles/gpt-oss/run-vllm)

### OSSエージェント実装

- [Aider](https://github.com/paul-gauthier/aider) - tree-sitterリポマップ
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) - イベントソーシング
- [SWE-agent](https://github.com/princeton-nlp/SWE-agent) - ACI
- [Cline](https://github.com/cline/cline) - TypeScript/VSCode
- [Goose](https://github.com/block/goose) - Rust/MCP
- [Continue.dev](https://github.com/continuedev/continue) - IDE統合

### RAG・検索技術

- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [HyDE 論文](https://arxiv.org/abs/2212.10496)
- [RRF (Reciprocal Rank Fusion)](https://dl.acm.org/doi/10.1145/1571941.1572114)
- [FAISS](https://github.com/facebookresearch/faiss)
- [ChromaDB](https://www.trychroma.com/)
- [Qdrant](https://qdrant.tech/)

### サンドボックス

- [E2B](https://e2b.dev/) - Firecracker microVM
- [Microsandbox](https://github.com/microsandbox/microsandbox)
- [gVisor](https://gvisor.dev/)

### ファインチューニング

- [QLoRA 論文](https://arxiv.org/abs/2305.14314)
- [LoRA 論文](https://arxiv.org/abs/2106.09685)
- [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer)
- [NASA NTRS API](https://ntrs.nasa.gov/api/citations/search)

### パフォーマンス最適化

- [vLLM Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode.html)
- [vLLM Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html)
- [AWQ量子化](https://github.com/mit-han-lab/llm-awq)

---

> このガイドは `/home/neko/projects/claude-code-guide/BUILD_YOUR_OWN.md` に保存されています。
> 最終更新: 2026-03-03
