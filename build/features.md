---
layout: default
title: "ローカルLLM構築ガイド - 高度な機能編A（章6〜8）"
---

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---



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
  {{% raw %}}{{
    "task_id": "task_1",
    "description": "サブタスクの説明",
    "depends_on": []
  }}{{% endraw %}},
  {{% raw %}}{{
    "task_id": "task_2",
    "description": "別のサブタスク",
    "depends_on": ["task_1"]
  }}{{% endraw %}}
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

---

[← 前: 基礎編](foundations) | [次: ファインチューニング →](finetuning)
