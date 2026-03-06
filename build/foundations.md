---
layout: default
title: "ローカルLLM構築ガイド - 基礎・設計編（章1〜5）"
---
{% raw %}

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---



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


実装言語とCLIフレームワークの選択は、後のAI/MLライブラリ統合のしやすさに大きく影響します。このセクションでは各選択肢のトレードオフを比較し、推奨構成を示します。

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


vLLMはローカルLLMをOpenAI互換APIとして提供する高速推論エンジンです。インストールからモデルの起動、接続確認まで順を追って解説します。

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


エージェントの中核となるファイル群の実装です。設定（config.py）・ツール（tools.py）・コンテキスト管理・メインループの4モジュールで構成されます。各ファイルは独立して理解・改変できるよう設計されています。

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

---

[次: 機能編A →](features)
{% endraw %}
