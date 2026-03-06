---
layout: default
title: "ローカルLLM構築ガイド - ファインチューニング（章9）"
---

[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)

---




**このセクションの内容:**
- [9.1 QLoRA/SFT基礎](#91-qlorasft基礎)
- [9.2 継続事前学習（CPT）](#92-継続事前学習cpt)
- [9.3 DPO/RLHF/ORPO（強化学習・選好最適化）](#93-dpoorlhforpo強化学習選好最適化)
- [9.4 学習の評価方法](#94-学習の評価方法)
- [9.5 フレームワーク比較](#95-フレームワーク比較)

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


<details markdown="1">
<summary>finetune.py（Python）</summary>

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

</details>


### 学習済みモデルのvLLMへのロード


<details markdown="1">
<summary>vLLM 起動コマンド（Bash）</summary>

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

</details>


### データ収集の自動化


<details markdown="1">
<summary>collect_training_data.py（Python）</summary>

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

</details>


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


<details markdown="1">
<summary>data_prep_cpt.py（Python）</summary>

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

</details>


#### 手順2: UnslothでCPT実行


<details markdown="1">
<summary>train_cpt.py（Python）</summary>

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

</details>


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


<details markdown="1">
<summary>catastrophic_forgetting_mitigation.py（Python）</summary>

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

</details>


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


<details markdown="1">
<summary>preference_data_human.py（Python）</summary>

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

</details>


#### 方法2: LLM-as-Judge で自動生成


<details markdown="1">
<summary>preference_data_llm_judge.py（Python）</summary>

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

</details>


---

### DPOの実装コード（Unsloth + TRL）


<details markdown="1">
<summary>train_dpo.py（Python）</summary>

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

</details>


---

### ORPOの実装コード


<details markdown="1">
<summary>train_orpo.py（Python）</summary>

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

</details>


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


<details markdown="1">
<summary>analyze_training_loss.py（Python）</summary>

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

</details>


---

### 自動評価指標の実装


<details markdown="1">
<summary>evaluation_metrics.py（Python）</summary>

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

</details>


---

### LLM-as-Judge による評価


<details markdown="1">
<summary>llm_judge_eval.py（Python）</summary>

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

</details>


---

### Wandb / MLflow でのトラッキング設定


<details markdown="1">
<summary>tracking_setup.py（Python）</summary>

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

</details>


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


<details markdown="1">
<summary>Unsloth 学習コード（Python）</summary>

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

</details>


#### TRL (Transformers Reinforcement Learning)

```
得意分野: DPO/ORPO/PPO/RewardModelなどのアラインメント手法全般
GPU要件: NVIDIA GPU（VRAM 16GB〜 推奨）
対応モデル: HuggingFaceのすべてのCausalLMモデル
主な用途: アラインメント段階（SFT後）
```


<details markdown="1">
<summary>DPO 実装（Python）</summary>

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

</details>


#### Axolotl

```
得意分野: 設定ファイルベースの学習パイプライン、初心者〜中級者
GPU要件: NVIDIA GPU（VRAM 8GB〜、マルチGPU対応）
対応モデル: Llama, Mistral, Falcon, MPT等 主要モデル
主な用途: SFT、LoRA、QLoRA全般
```


<details markdown="1">
<summary>Axolotl 設定ファイル（YAML）</summary>

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

</details>



<details markdown="1">
<summary>Axolotl 設定ファイル（Bash）</summary>

```bash
# Axolotlの実行
# インストール: uv pip install axolotl
axolotl train config.yml
```

</details>


#### torchtune (Meta公式)

```
得意分野: フルカスタマイズ、マルチノード大規模学習、研究目的
GPU要件: NVIDIA/AMD GPU、FSDP対応環境
対応モデル: Llama 3.x (Meta公式サポート)、一部他モデル
主な用途: フル精度SFT、LoRA、大規模分散学習
```


<details markdown="1">
<summary>Axolotl 設定ファイル（YAML）</summary>

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

</details>



<details markdown="1">
<summary>QLoRA 学習コード（Bash）</summary>

```bash
# torchtune の実行
# インストール: uv pip install torchtune
tune run lora_finetune_single_device --config llama3_2/3B_lora_single_device
```

</details>


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

---

[← 前: 機能編A](features) | [次: 機能編B →](features2)
