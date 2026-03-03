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
9. [ファインチューニング（専門知識の学習）](#9-ファインチューニング専門知識の学習)
10. [RAG（検索拡張生成）](#10-rag検索拡張生成)
11. [高度な検索技法](#11-高度な検索技法)
12. [費用・コスト](#12-費用コスト)
13. [セキュリティ・サンドボックス](#13-セキュリティサンドボックス)
14. [セッション・メモリ管理](#14-セッションメモリ管理)
15. [実装ロードマップ](#15-実装ロードマップ)
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
- OpenAI GPT-OSS (gpt-oss-20b / gpt-oss-120b)
- Google Gemma 2/3シリーズ
- Meta Llama 3.1/3.2シリーズ
- Mistral / Codestral
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
│  │         Anthropic Claude API           │ │
│  │    (claude-opus-4-6 / claude-sonnet)   │ │
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

| カテゴリ | モデル | VRAM | 特徴 | HuggingFace ID |
|---------|--------|------|------|----------------|
| **コーディング** | Codestral 22B | 24GB | Mistral製、コード専門 | `mistralai/Codestral-22B-v0.1` |
| | StarCoder2 15B | 16GB | BigCode製、多言語対応 | `bigcode/starcoder2-15b` |
| | CodeGemma 7B | 8GB | Google製、軽量 | `google/codegemma-7b-it` |
| **汎用（大）** | GPT-OSS 120B | 60GB+ | OpenAI公開、最高精度 | `openai/gpt-oss-120b` |
| | Llama 3.1 70B | 40GB | Meta製、バランス良 | `meta-llama/Llama-3.1-70B-Instruct` |
| | Gemma 2 27B | 28GB | Google製、高品質 | `google/gemma-2-27b-it` |
| **汎用（中）** | GPT-OSS 20B | 16GB | OpenAI公開、コスト効率 | `openai/gpt-oss-20b` |
| | Llama 3.1 8B | 10GB | Meta製、高速 | `meta-llama/Llama-3.1-8B-Instruct` |
| **軽量** | Gemma 2 9B | 10GB | Google製、軽量高性能 | `google/gemma-2-9b-it` |
| | Phi-3 Mini 3.8B | 4GB | Microsoft製、超軽量 | `microsoft/Phi-3-mini-4k-instruct` |

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

# GPT-OSS 20B（汎用、コスト効率）
vllm serve openai/gpt-oss-20b \
    --host 0.0.0.0 \
    --port 8003 \
    --dtype bfloat16

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
vllm serve openai/gpt-oss-120b \
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
    # Bash実行ツール（永続セッション）
    # =============================================

    async def bash(self, command: str, timeout: int = 120000) -> str:
        """
        シェルコマンドを実行する。
        永続セッションを使うため、cd等の状態が次のコマンドにも引き継がれる。
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


import asyncio  # tree_of_thought内で使用
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

## 9. ファインチューニング（専門知識の学習）

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
