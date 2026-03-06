---
layout: default
title: "ローカルLLM構築ガイド - 運用・最適化編（章12〜15）"
---
{% raw %}

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---




GPU購入・クラウドレンタル・API利用それぞれのコスト構造を比較します。プロジェクトの規模とフェーズに応じた最適な選択を判断するための情報を提供します。

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


AIエージェントがシェルコマンドを実行する際のセキュリティリスクと対策を解説します。本番環境では必ずサンドボックスを導入し、最小権限の原則を徹底してください。

### Bashツール実行のリスク

エージェントがBashツールを使ってシステムコマンドを実行する場合、以下のリスクがあります:

- 意図しないファイル削除（`rm -rf`等）
- ネットワークへの不正アクセス
- セキュリティ関連ファイルへのアクセス
- 無限ループによるリソース枯渇

### Docker サンドボックス実装


<details>
<summary>sandbox.py（Python）</summary>

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

</details>


### パーミッション管理


<details>
<summary>permissions.py（Python）</summary>

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

</details>


### 使用例: パーミッション付きエージェント


<details>
<summary>AgentCore 実装（Python）</summary>

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

</details>


---

## 14. セッション・メモリ管理


エージェントが長期にわたって文脈を保持するための仕組みです。短期メモリ（コンテキストウィンドウ）と長期メモリ（永続ストレージ）を組み合わせて実現します。

### セッションの保存・復元


<details>
<summary>session_manager.py（Python）</summary>

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

</details>


### 長期記憶システム（Auto Memory相当）


<details>
<summary>long_memory.py（Python）</summary>

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

</details>


---

## 15. 実装ロードマップ


ゼロからエージェントを構築する際の推奨順序と各フェーズの目安を示します。スモールスタートして段階的に機能を追加するアプローチが安全で管理しやすいです。

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


<details>
<summary>minimal_agent.py（Python）</summary>

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

</details>


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


<details>
<summary>セッション管理（Python）</summary>

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

</details>


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

---

[← 前: 機能編B](features2) | [次: 専門編 →](specialist)
{% endraw %}
