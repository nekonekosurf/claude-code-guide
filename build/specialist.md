---
layout: default
title: "ローカルLLM構築ガイド - 専門技術編（章16〜19 + 付録）"
---

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---




汎用Embeddingモデルをドメイン固有データでファインチューニングすることで、専門分野での検索精度を大幅に改善できます。RAGシステムの精度向上に有効な手法です。

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


<details>
<summary>MultipleNegativesRankingLoss（推...（Python）</summary>

```python
# (anchor, positive) ペアのみでOK
# バッチ内の他サンプルが自動的に負例になる
pairs = [
    ("ホーマン遷移の計算", "ホーマン軌道遷移のデルタV"),
    ("比推力とは",          "Isp: Specific Impulse の定義"),
    ...
]
```

</details>


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


<details>
<summary>aerospace_pair_generator.py（Python）</summary>

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

</details>


#### ステップ2: sentence-transformers v3による公式Hard Negative Mining


<details>
<summary>hard_negative_mining_v3.py（Python）</summary>

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

</details>


---

### Fine-tuning実装コード


<details>
<summary>finetune_aerospace_embeddings.py（Python）</summary>

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

</details>


---

### 精度評価（Recall@K、MRR、NDCG）


<details>
<summary>evaluate_embeddings.py（Python）</summary>

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

</details>


---

### Fine-tuning済みEmbeddingのRAG統合


<details>
<summary>rag_with_finetuned_embedding.py（Python）</summary>

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

</details>


---

## 17. 学習 vs エージェント - 何をどこまでやるか


ファインチューニングとエージェント設計のどちらに注力すべきかは、ユースケースによって異なります。このセクションでは判断基準と実践的な使い分けを解説します。

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


AIエージェントを本番運用する際に人間の判断が必要なポイントを整理します。自動化と人間の監督のバランスが安全で信頼性の高いシステムの鍵となります。

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


ドメイン専門家のフィードバックを効率的に収集してモデル改善に活かすシステムの設計です。継続的な品質向上サイクル（フライホイール）を実現します。

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


<details>
<summary>セッション管理（SQL）</summary>

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

</details>


---

### StreamlitによるフィードバックUI実装


<details>
<summary>feedback_app.py（Python）</summary>

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

</details>


---

### フィードバックからDPOデータへの自動変換パイプライン


<details>
<summary>feedback_to_dpo_pipeline.py（Python）</summary>

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

</details>


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


<details>
<summary>フィードバック収集システム</summary>

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

</details>


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
> 最終更新: 2026-03-07

---

[← 前: 運用編](operations)
