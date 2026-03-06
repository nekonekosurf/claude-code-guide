---
layout: default
title: "ローカルLLM構築ガイド - 高度な機能編B（章10〜11）"
---

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---



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


基本的なベクトル検索を超えた高精度な検索手法を紹介します。BM25との融合、仮説文書生成（HyDE）、グラフベース検索など、ユースケースに応じた使い分けが重要です。

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
  {% raw %}{{"entity1": "衛星", "relation": "使用する", "entity2": "MLI"}}{% endraw %},
  {% raw %}{{"entity1": "MLI", "relation": "提供する", "entity2": "断熱性能"}}{% endraw %}
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

---

[← 前: ファインチューニング](finetuning) | [次: 運用編 →](operations)
