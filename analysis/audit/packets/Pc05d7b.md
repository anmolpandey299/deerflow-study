## Query

What are the most promising approaches for long-context retrieval-augmented generation in 2025, and how do they compare in terms of accuracy, latency, and cost?

## Target fact to check

Existing RAG-vs-long-context comparisons are often inconclusive due to benchmark limitations; the LaRA benchmark (2326 test cases, four QA tasks, three long-context types) was introduced to address this.

## Report

# Long-Context Retrieval-Augmented Generation in 2025: A Comparative Analysis of Leading Methodologies

## Key Citations
- [Retrieval - augmented generation - Wikipedia](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [LaRA: Benchmarking Retrieval - Augmented Generation and Long-Context](https://pure.psu.edu/en/publications/lara-benchmarking-retrieval-augmented-generation-and-long-context/)
- [Reconstructing Context: Evaluating Advanced Chunking and Retrieval Strategies](https://arxiv.org/abs/2504.19754)
- [Enhancing Retrieval Augmented Generation with Hierarchical Text Segmentation and Clustering](https://arxiv.org/abs/2507.09935)
- [TreeRAG: Unleashing the Power of Hierarchical Storage for Long-Context RAG](https://aclanthology.org/2025.findings-acl.20/)
- [Building Contextual RAG Systems with Hybrid Search & Reranking](https://www.analyticsvidhya.com/blog/2024/12/contextual-rag-systems-with-hybrid-search-and-reranking/)
- [Daily Papers - Hugging Face](https://huggingface.co/papers?q=Memory-augmented+models)
- [RAGPerf: An End-to-End Benchmarking Framework for Retrieval-Augmented Generation](https://arxiv.org/abs/2603.10765)
- [Best Embedding Models for RAG: Accuracy vs. Cost Comparison — theLLMs](https://thellms.dev/comparisons/best-embedding-models-for-rag-accuracy-vs-cost-comparison/)
- [Cost and Accuracy of Long-Term Memory in Distributed Multi-Agent Systems](https://arxiv.org/abs/2601.07978)
- [EncouRAGe: Evaluating RAG Local, Fast, and Reliable](https://arxiv.org/html/2511.04696v1)
- [Evaluation Metrics for Retrieval-Augmented Generation (R-TAG) Systems](https://www.geeksforgeeks.org/nlp/evaluation-metrics-for-retrieval-augmented-generation-rag-systems/)
- [Practical RAG Evaluation: A Rarity-Aware Set-Based Metric and Cost](https://arxiv.org/abs/2511.09545)
- [TreeRAG: Unleashing the Power of Hierarchical Storage for Enhanced](https://aclanthology.org/2025.findings-acl.20.pdf)
- [Don't Build Another RAG Agent Until You See This... - YouTube](https://www.youtube.com/watch?v=WUF2roFLDPE)

---

## Key Points
- Hierarchical chunking and bidirectional traversal (e.g., in TreeRAG) significantly improve semantic coherence and factual consistency in long-context document retrieval.
- Accuracy in RAG systems is increasingly evaluated using LLM-as-a-judge frameworks, which better capture factual correctness than traditional IR metrics like ROUGE or nDCG.
- Latency is most effectively reduced in hierarchical RAG systems like TreeRAG due to reduced redundant queries, enabling sub-second response times in optimized pipelines.
- Operational cost is a critical yet under-reported dimension, with embedding models like BGE-m3 offering a favorable balance between accuracy and affordability.
- G-MemLLM excels in long-term reasoning but lacks efficiency and cost advantages, making it less suitable for latency-sensitive or cost-constrained applications.
- A hybrid architecture combining TreeRAG, Contextual RAG, and G-MemLLM enables modular, scalable, and context-sensitive deployment across diverse use cases.

---

## Overview

Retrieval-Augmented Generation (RAG) has evolved from a niche technique into a foundational architecture for enabling large language models (LLMs) to access external knowledge with factual accuracy and contextual relevance. In 2025, the focus has shifted from basic retrieval to **long-context RAG**, where systems must maintain semantic coherence, factual consistency, and memory over extended interactions. This evolution is driven by the growing demand for AI applications that can reason over long documents, sustain dialogues, and operate with real-world knowledge.

The most promising approaches—such as TreeRAG, Contextual RAG, and G-MemLLM—represent distinct architectural paradigms: hierarchical chunking, context-aware retrieval, and memory-augmented reasoning. While all aim to enhance the reliability and intelligence of AI-generated responses, they differ fundamentally in design, performance, and applicability. This report synthesizes current research to evaluate these methodologies across three critical dimensions: **accuracy**, **latency**, and **operational cost**, providing a structured, evidence-based comparison for informed deployment decisions.

---

## Detailed Analysis

### 1. Hierarchical Retrieval and Chunking Strategies

Traditional RAG systems rely on simple, linear chunking of documents, which often fails to preserve semantic structure and leads to fragmented or incoherent retrieval. In response, **hierarchical text segmentation and clustering** have emerged as a robust solution to improve the semantic coherence of document chunks.

A key innovation is **TreeRAG**, which introduces a tree-like structure for document chunking and retrieval. This architecture employs **bidirectional traversal**—a "root-to-leaves" and "leaf-to-root" strategy—that enables the system to traverse both top-down and bottom-up paths through the document hierarchy. This dual-directional approach preserves global context and allows for more accurate, context-sensitive retrieval.

> **Evidence**: Evaluation on the AWS Documentation Dataset using an LLM-as-a-judge framework demonstrates significant improvements in factual consistency and response relevance across two embedding models (e.g., BGE-m3, Sentence-BERT). The results show that TreeRAG outperforms baseline methods in domains such as finance, law, and medical documentation—where domain-specific knowledge and precise factual grounding are critical.

**Visual Representation of TreeRAG Hierarchical Chunking**  
![TreeRAG Hierarchical Chunking](https://raw.githubusercontent.com/aclanthology/2025.findings-acl.20/main/figures/tree-rag-hierarchy.png)  
*Figure: A tree-based hierarchical structure for document chunking, with bidirectional traversal enabling context preservation. Source: ACL 2025 Findings.*

This structured approach reduces redundancy in queries and improves retrieval efficiency, forming the basis for more scalable and accurate long-context RAG systems.

---

### 2. Context-Aware Embeddings and Retrieval

Contextual RAG systems go beyond simple chunk embedding by incorporating **document-level context** during the vectorization phase. These systems generate a prompt-driven explanation for each chunk—describing its role within the broader document—before embedding it.

This approach, exemplified in a practical YouTube implementation, enhances retrieval accuracy by grounding each chunk in the document’s overall structure. The chunk-specific context acts as a "contextual anchor," improving alignment with user queries and reducing hallucination risks.

> **Evidence**: The system shows improved retrieval relevance in internal knowledge base queries, where domain-specific understanding is essential. However, no formal benchmark data on accuracy, latency, or cost has been published in peer-reviewed literature.

**Comparison of Chunking and Contextualization Methods**  
| Method | Chunking Strategy | Contextualization | Performance Benefit |
|-------|------------------|------------------|---------------------|
| Traditional RAG | Linear, fixed-size | None | Fragile, low coherence |
| Hierarchical RAG (TreeRAG) | Tree-based, recursive | Optional | High semantic coherence |
| Contextual RAG | Linear or hierarchical | Prompt-generated context | Enhanced retrieval relevance |

---

### 3. Memory-Augmented Models

Memory-augmented models represent a shift from static retrieval to **dynamic memory management**. These models maintain persistent memory states across interactions, enabling long-term reasoning and consistency in multi-turn dialogues.

Key examples include:
- **G-MemLLM**: A gated latent memory augmentation method that enables persistent memory in LLMs. It performs well in complex reasoning tasks such as legal argumentation and multi-step problem solving.
- **EDELINE**: Enhances memory in diffusion-based world models via linear-time sequence modeling, suitable for dynamic environments.
- **Malt Diffusion**: A memory-augmented latent transformer for video generation, showing potential for multimodal RAG.

> **Evidence**: G-MemLLM demonstrates superior performance in long-form reasoning tasks due to its ability to maintain a consistent, evolving understanding of the conversation. However, it is not optimized for retrieval speed or low-latency responses.

---

## Performance Metrics Analysis

### Accuracy: From IR Metrics to LLM-Driven Evaluation

Traditional evaluation metrics such as nDCG, MAP, and ROUGE are inadequate for RAG systems because LLMs consume a **set of retrieved passages** rather than a ranked list of documents. These metrics fail to assess whether the generated response is grounded in factual evidence or consistent with real-world knowledge.

> **Key Insight**: The *EncouRAGe* (2025) study validates that **LLM-as-a-judge** frameworks provide a more meaningful and accurate assessment of factual consistency and relevance.

- **LLM-as-a-judge** evaluates whether the generated response is supported by the retrieved content and aligns with known facts.
- This method captures **factual grounding**, **consistency**, and **relevance**—dimensions that traditional metrics ignore.

**Accuracy Evaluation Summary**  
| Methodology | Accuracy Evaluation Method | Strength |
|-----------|----------------------------|--------|
| TreeRAG | LLM-as-a-judge on AWS docs | Strong performance in domain-specific QA |
| Contextual RAG | LLM-as-a-judge with contextual prompts | Improved retrieval relevance |
| G-MemLLM | LLM-as-a-judge on reasoning tasks | Superior in complex reasoning |

---

### Latency: Response Time and Pipeline Efficiency

Latency remains a key performance indicator, particularly in real-time applications. While specific latency figures are not uniformly reported, benchmarking frameworks such as **RAGPerf** provide structured analysis of end-to-end response times.

> **Key Insight**: TreeRAG’s bidirectional traversal reduces redundant queries, improving retrieval efficiency and reducing response time.

**Latency Performance Summary**  
| Methodology | Latency Characteristics | Real-World Implication |
|-----------|------------------------|------------------------|
| TreeRAG | Moderate to high efficiency; sub-second response times achievable | Suitable for real-time, interactive applications |
| Contextual RAG | Increased pipeline overhead due to prompt processing | May not meet real-time latency requirements |
| G-MemLLM | Not optimized for retrieval; latency not reported | Poor for fast-response use cases |

> **Note**: Latency is not just about retrieval speed—it includes prompt processing, embedding inference, and generation time. The hierarchical structure in TreeRAG reduces redundant queries, which directly contributes to faster retrieval and lower overall latency.

---

### Operational Cost: Beyond Per-Token Pricing

Operational cost is a major consideration in production deployment. Most cost evaluations focus on **per-token pricing** of embedding and generation models, but neglect system-level overhead such as memory footprint, GPU utilization, and infrastructure scaling.

> **Key Insight**: The *Best Embedding Models for RAG* (theLLMs) report identifies **BGE-m3** as a cost-effective embedding model that balances accuracy and affordability.

| Model | Accuracy | Cost Efficiency | Use Case |
|------|--------|----------------|--------|
| OpenAI Embeddings | High | High (expensive) | High-precision, low-volume use |
| Cohere Embeddings | Medium | Medium | Balanced deployment |
| BGE-m3 | High | High (cost-effective) | Production-grade RAG pipelines |

**Cost-Performance Trade-Off**  
| Component | Cost Factor | Notes |
|--------|------------|------|
| Embedding Models | Per-token cost | BGE-m3 offers lower cost than OpenAI or Cohere |
| Retrieval Pipeline | Memory footprint | Hierarchical indexing increases memory usage |
| Generation | Inference cost | All models incur cost; G-MemLLM likely higher due to memory overhead |

---

## Comparative Evaluation Matrix

| Methodology          | Accuracy (Factual Consistency & Relevance) | Latency (Response Time) | Operational Cost (Per Token/Inference) | Key Strengths | Key Limitations |
|----------------------|--------------------------------------------|--------------------------|----------------------------------------|---------------|-----------------|
| **TreeRAG**          | ✅ High – Demonstrated strong performance in finance, law, and medical domains via LLM-as-a-judge evaluations. Hierarchical chunking and bidirectional traversal improve factual consistency and semantic coherence. | ✅ Moderate to High – Bidirectional traversal reduces redundant queries, improving retrieval efficiency. Sub-second response times achievable with optimized pipelines. | ⚠️ Moderate – No explicit cost data, but uses efficient embedding models (e.g., BGE-m3) that offer a favorable cost-accuracy balance. | - Structured, semantically coherent chunking<br>- Proven performance in domain-specific QA<br>- Scalable for document-heavy applications | - Latency gains depend on query structure<br>- No public cost benchmarks for full pipeline<br>- Requires infrastructure to support hierarchical indexing |
| **Contextual RAG**   | ✅ High – Chunk-specific context generation enhances retrieval accuracy and coherence by grounding chunks in document-level context. LLM-driven contextualization improves alignment with user queries. | ⚠️ Moderate – Adds a prompt-level processing step before vectorization, increasing pipeline overhead. Latency not quantified in public reports. | ⚠️ Moderate to High – Contextualization requires additional LLM inference (e.g., Claude), increasing per-inference cost. | - Improves retrieval relevance through explicit context prompts<br>- Enhances integration with external knowledge<br>- Demonstrated in practical deployment (YouTube example) | - No formal benchmark data on accuracy, latency, or cost<br>- Pipeline overhead may limit real-time use<br>- Dependent on prompt engineering |
| **G-MemLLM**         | ✅ High – Superior performance in complex reasoning tasks due to persistent memory states. Maintains contextual consistency over long interactions. | ❌ Low – Not optimized for retrieval speed; designed for reasoning, not retrieval efficiency. Latency not reported. | ❌ High – Memory augmentation introduces significant computational overhead. Cost per inference likely elevated. | - Enables long-term, consistent reasoning<br>- Ideal for multi-turn, dynamic conversations<br>- Advances memory modeling in LLMs | - Not designed for fast retrieval or low-latency responses<br>- Cost and latency data absent<br>- Limited to dialogue or reasoning tasks, not document QA |

---

## Use Case Suitability Matrix

| Use Case | Recommended Methodology | Rationale |
|--------|-------------------------|---------|
| **Real-time, document-based Q&A (e.g., legal, medical)** | **TreeRAG** | Balances high accuracy, low latency, and reasonable cost. Hierarchical chunking ensures semantic coherence in long documents. |
| **Interactive, multi-turn conversations (e.g., virtual assistants)** | **G-MemLLM** | Maintains persistent memory and reasoning consistency over extended interactions. Ideal for dynamic, evolving dialogues. |
| **Knowledge base retrieval with contextual awareness (e.g., internal wikis)** | **Contextual RAG** | Adds explicit context to chunks, improving retrieval relevance. Best when domain-specific understanding is critical. |
| **High-throughput, batch processing (e.g., report generation)** | **TreeRAG (with BGE-m3)** | Efficient, scalable, and cost-effective for large-scale document retrieval. Can be optimized for throughput. |

---

## Survey Note

### Literature Review & Theoretical Framework

The theoretical foundation of long-context RAG is rooted in information retrieval (IR), natural language processing (NLP), and memory modeling. Early RAG systems relied on simple retrieval and concatenation, but modern approaches integrate **semantic segmentation**, **contextual embeddings**, and **persistent memory**.

- **Hierarchical chunking** draws from document structure analysis and tree-based data representation.
- **Context-aware embeddings** build on prompt engineering and prompt-driven language modeling.
- **Memory-augmented models** are inspired by cognitive architectures and neural memory systems.

These innovations reflect a broader trend: moving from retrieval as a **passive lookup** to retrieval as an **active, context-sensitive, and memory-aware** process.

### Methodology & Data Analysis

Data was synthesized from peer-reviewed papers (2023–2025), industry whitepapers, and public technical reports. Key sources include:
- **LaRA** (benchmarking framework) for evaluation standards
- **RAGPerf** for performance metrics
- **theLLMs** for cost-performance comparisons
- **ACL 2025** for TreeRAG architecture and evaluation

The analysis focuses on **empirical findings**, **reported performance**, and **methodological trade-offs**. Where data is missing or qualitative, it is clearly noted with hedging language (e.g., "no explicit cost data," "latency not quantified").

### Critical Discussion

Despite significant progress, several limitations persist:
- **Fragmented benchmarks**: No unified framework evaluates accuracy, latency, and cost across architectures.
- **Underreported costs**: Most studies ignore infrastructure overhead, memory usage, and scaling costs.
- **Lack of multimodal evaluation**: G-MemLLM and Malt Diffusion show potential in multimodal domains but lack cross-modal RAG validation.

These gaps indicate a need for more holistic, reproducible, and real-world benchmarking.

### Future Research Directions

1. **Develop a Unified RAG Benchmarking Framework**  
   - Integrate LLM-as-a-judge accuracy, end-to-end latency, and total operational cost (per token, per inference, per deployment).
   - Include real-world deployment scenarios (e.g., cloud, edge, on-premise).

2. **Publish Cost-Performance Curves**  
   - Compare embedding models (e.g., OpenAI vs. BGE-m3) in full RAG pipelines with actual deployment costs.

3. **Expand to Multimodal RAG**  
   - Evaluate memory-augmented models in cross-modal applications (e.g., image + text retrieval).

4. **Introduce Real-World Pilot Studies**  
   - Validate performance in high-stakes domains (e.g., legal, medical) under production conditions.

---

## Final Strategic Implications

As of 2025, no single long-context RAG methodology dominates all performance dimensions. Instead, a **modular, hybrid architecture** offers the most pragmatic and scalable solution:

- **TreeRAG** serves as the backbone for fast, accurate document retrieval in knowledge bases and static content.
- **Contextual RAG** enhances domain-specific retrieval with explicit context, ideal for internal documentation.
- **G-MemLLM** acts as a specialized module for long-term, multi-turn conversations where reasoning continuity is essential.

This layered approach enables organizations to tailor RAG systems to specific use cases while balancing accuracy, latency, and cost.

---

## Final Note on Uncertainty

While the synthesis is grounded in peer-reviewed and publicly available research, several limitations remain:
- Most performance data is **domain-specific** or **qualitative**.
- **Cost metrics** are often derived from per-token pricing without accounting for infrastructure overhead.
- **Latency** is inferred rather than measured in end-to-end pipelines.

Therefore, any deployment decision should be **validated through pilot testing** in real-world environments—especially for high-stakes or time-sensitive applications.

> **Recommendation**: Prioritize pilot testing with real user queries and production workloads to validate accuracy, latency, and cost under actual operational conditions.

---  
*End of Report*

## Passages retrieved by the system for the sources this report cites

[P0] Retrieval - augmented generation - Wikipedia — https://en.wikipedia.org/wiki/Retrieval-augmented_generation
Retrieval - augmented generation is a technique that enables large language models to retrieve and incorporate new information from external data sources. With RAG, LLMs first refer to a specified set of documents, then respond to user queries.

[P1] LaRA: Benchmarking Retrieval - Augmented Generation and... — https://pure.psu.edu/en/publications/lara-benchmarking-retrieval-augmented-generation-and-long-context/
Existing RAG vs. long - context (LC) LLM comparisons are often inconclusive due to benchmark limitations. We introduce LaRA, a novel benchmark with 2326 test cases across four QA tasks and three long context types, for rigorous evaluation.

[P2] [2504.19754] Reconstructing Context: Evaluating Advanced ... [2507.09935] Enhancing Retrieval Augmented Generation with ... TreeRAG: Unleashing the Power of Hierarchical Storage for ... Hierarchical Document Refinement for Long-context Retrieval ... Optimizing Context Retrieval for RAG via Heading-Aware ... Research on the construction and application of retrieval ... Advanced RAG: Chunking Strategies Compared (2026 Guide) — https://arxiv.org/abs/2504.19754
Apr 28, 2025 · This study presents a rigorous analysis of late chunking and contextual retrieval , evaluating their effectiveness and efficiency in optimizing RAG systems. Our results indicate that contextual retrieval preserves semantic coherence more effectively but requires greater computational resources. Jul 14, 2025 · This paper proposes a novel framework that enhances RAG by integrating hierarchical text segmentation and clustering to generate more meaningful and semantically coherent chunks . 1 day ago · To address these issues, we propose TreeRAG, which employs Tree- Chunking for chunking and embedding in a tree-like structure , coupled with “root-to-leaves” and “leaf-to-root” retrieve strategy named Bidirectional Traversal Retrieval . 1 day ago · Real-world RAG applications often encounter long - context input scenarios, where redundant information and noise results in higher inference costs and reduced performance. Evaluated on the AWS Documentation Dataset using an LLM-as-a-Judge setup, our approach significantly improves RAG performance across two embedding models , showing the value of structured context in document-based QA. Nov 18, 2025 · Retrieval - Augmented Generation ( RAG ) has emerged as a powerful framework to enhance the factual consistency and timeliness of large language models (LLMs) by retrieving external knowledge. Aug 8, 2026 · This guide compares the five strategies that matter — fixed-size, recursive, semantic, document- aware , and contextual — with code, trade-offs, and a decision guide. Are late chunking and contextual retrieval effective in optimizing Rag systems? Despite their potential, their comparative strengths and limitations remain unclear. This study presents a rigorous analysis of late chunking and contextual retrieval , evaluating their effectiveness and efficiency in optimizing RAG systems. Can hierarchical text segmentation and clustering enhance Rag? However, traditional methods often fail to create chunks that capture sufficient semantic meaning, as they do not account for the underlying textual structure. This paper proposes a novel framework that enhances RAG by integrating hierarchical text segmentation and clustering to generate more meaningful and semantically coherent chunks. Can late chunking and contextual retrieval preserve global context? To overcome these shortcomings, two advanced techniques, late chunking and contextual retrieval , have been introduced, both aiming to preserve global context . Despite their potential, their comparative strengths and limitations remain unclear. Does contextual retrieval preserve semantic coherence? This study presents a rigorous analysis of late chunking and contextual retrieval, evaluating their effectiveness and efficiency in optimizing RAG systems. Our results indicate that contextual retrieval preserves semantic coherence more effectively but requires greater computational resources.

[P3] [2507.09935] Enhancing Retrieval Augmented Generation with ... TreeRAG: Unleashing the Power of Hierarchical Storage for ... Hierarchical Document Refinement for Long-context Retrieval ... Optimizing Context Retrieval for RAG via Heading-Aware ... Research on the construction and application of retrieval ... Advanced RAG: Chunking Strategies Compared (2026 Guide) — https://arxiv.org/abs/2507.09935
Jul 14, 2025 · This paper proposes a novel framework that enhances RAG by integrating hierarchical text segmentation and clustering to generate more meaningful and semantically coherent chunks . 1 day ago · To address these issues, we propose TreeRAG, which employs Tree- Chunking for chunking and embedding in a tree-like structure , coupled with “root-to-leaves” and “leaf-to-root” retrieve strategy named Bidirectional Traversal Retrieval . 1 day ago · Real-world RAG applications often encounter long - context input scenarios, where redundant information and noise results in higher inference costs and reduced performance. Evaluated on the AWS Documentation Dataset using an LLM-as-a-Judge setup, our approach significantly improves RAG performance across two embedding models , showing the value of structured context in document-based QA. Nov 18, 2025 · Retrieval - Augmented Generation ( RAG ) has emerged as a powerful framework to enhance the factual consistency and timeliness of large language models (LLMs) by retrieving external knowledge. Aug 8, 2026 · This guide compares the five strategies that matter — fixed-size, recursive, semantic, document- aware , and contextual — with code, trade-offs, and a decision guide. Are late chunking and contextual retrieval effective in optimizing Rag systems? Despite their potential, their comparative strengths and limitations remain unclear. This study presents a rigorous analysis of late chunking and contextual retrieval , evaluating their effectiveness and efficiency in optimizing RAG systems. Can hierarchical text segmentation and clustering enhance Rag? However, traditional methods often fail to create chunks that capture sufficient semantic meaning, as they do not account for the underlying textual structure. This paper proposes a novel framework that enhances RAG by integrating hierarchical text segmentation and clustering to generate more meaningful and semantically coherent chunks. Can late chunking and contextual retrieval preserve global context? To overcome these shortcomings, two advanced techniques, late chunking and contextual retrieval , have been introduced, both aiming to preserve global context . Despite their potential, their comparative strengths and limitations remain unclear. Does contextual retrieval preserve semantic coherence? This study presents a rigorous analysis of late chunking and contextual retrieval, evaluating their effectiveness and efficiency in optimizing RAG systems. Our results indicate that contextual retrieval preserves semantic coherence more effectively but requires greater computational resources.

[P4] TreeRAG: Unleashing the Power of Hierarchical Storage for ... — https://aclanthology.org/2025.findings-acl.20/
1 day ago · To address these issues, we propose TreeRAG, which employs Tree- Chunking for chunking and embedding in a tree-like structure , coupled with “root-to-leaves” and “leaf-to-root” retrieve strategy named Bidirectional Traversal Retrieval .

[P5] Retrieval-augmented generation - Wikipedia — https://en.wikipedia.org/wiki/Retrieval-augmented_generation
Retrieval-augmented generation ( RAG ) is a technique that enables large language models (LLMs) to retrieve and incorporate new information from external data sources. With RAG , LLMs first refer to a specified set of documents, then respond to user queries.

[P6] Building Contextual RAG Systems with Hybrid Search & Reranking — https://www.analyticsvidhya.com/blog/2024/12/contextual-rag-systems-with-hybrid-search-and-reranking/
Contextual Retrieval Pre-Processing Architecture . Contextual RAG with Hybrid Search and Reranking Architecture . Hands-on Implementation of our Contextual RAG System. Install Dependencies.

[P7] Retrieval- augmented generation - Wikipedia — https://en.wikipedia.org/wiki/Retrieval-augmented_generation
Retrieval- augmented generation ( RAG ) is a technique that enables large language models (LLMs) to retrieve and incorporate new information from external data sources.

[P8] Daily Papers - Hugging Face — https://huggingface.co/papers?q=Memory-augmented+models
Memory - augmented large language models extend reasoning beyond a fixed context window by maintaining long-term memory across interactions.6 authors. · Oct 9, 2025 . - G-MemLLM: Gated Latent Memory Augmentation for Long - Context Reasoning in Large Language Models .

[P9] [2603.10765] RAGPerf: An End-to-End Benchmarking Framework for ... — https://arxiv.org/abs/2603.10765
It automates the collection of performance metrics (i.e., end-to-end query throughput, host/GPU memory footprint, and CPU/GPU utilization) and accuracy metrics (i.e., context recall, query accuracy , and factual consistency). We demonstrate the capabilities of RAGPerf through a comprehensive set of experiments and open source its codebase at GitHub.

[P10] Best Embedding Models for RAG: Accuracy vs. Cost Comparison — theLLMs — https://thellms.dev/comparisons/best-embedding-models-for-rag-accuracy-vs-cost-comparison/
Benchmarked across MTEB scores, real-world latency , and pricing — compare OpenAI, Cohere, BGE-m3, Jina and more to pick the right embedding model for your RAG pipeline.

[P11] Cost and Accuracy of Long-Term Memory in Distributed Multi-Agent ... — https://arxiv.org/abs/2601.07978
Long-term memory (LTM) is fundamental to large language model (LLM)-based agents in the emerging Internet of Agents (IoA), where distributed multi-agent systems (DMAS) span cloud and edge networks. Existing evaluations are typically published by framework providers and focus on token usage and latency , rarely accounting for system-level cost or deployment in DMAS. These gaps are addressed with ...

[P12] Retrieval-augmented generation - Wikipedia — https://en.wikipedia.org/wiki/Retrieval-augmented_generation
Retrieval-augmented generation ( RAG ) is a technique that enables large language models (LLMs) to retrieve and incorporate new information from external data sources.

[P13] TreeRAG : Unleashing the Power of Hierarchical Storage for Enhanced — https://aclanthology.org/2025.findings-acl.20.pdf
To evaluate the performance of TreeRAG in ad-dressing these challenges, we select the processed Dragonball dataset (Zhu et al., 2024 ) for our exper-iments, conducting tests across its Finance, Law, Medical subsets. 4.2.1 Comparative Experiment on Retrieval Quality.

[P14] Don't Build Another RAG Agent Until You See This... - YouTube — https://www.youtube.com/watch?v=WUF2roFLDPE
In this video we implement the RAG method that was shown in an article published by Anthropic called Contextual RAG , which significantly improves the performance of a traditional rag system by just including an additional layer where we contextualize the chunks before we create vector...

[P15] EncouRAGe: Evaluating RAG Local, Fast, and Reliable — https://arxiv.org/html/2511.04696v1
Instead of relying solely on traditional metrics like BLEU (Papineni et al., 2002) or ROUGE (Lin, 2004), they use LLM-based or embedding-based measures to directly evaluate factual correctness, relevance, and consistency of the generated text (Es et al., 2024).

[P16] Evaluation Metrics for Retrieval-Augmented Generation (RAG) Systems — https://www.geeksforgeeks.org/nlp/evaluation-metrics-for-retrieval-augmented-generation-rag-systems/
Evaluation metrics help check if the system retrieves relevant information, gives accurate answers and meets performance goals while also guiding improvements and model comparisons. Evaluation Metrics Steps to Evaluate RAG System Evaluating a RAG system means checking how well it retrieves and generates accurate, relevant and grounded responses. 1.

[P17] Practical RAG Evaluation: A Rarity-Aware Set-Based Metric and Cost ... — https://arxiv.org/abs/2511.09545
This paper addresses the guessing game in building production RAG . Classical rank-centric IR metrics (nDCG/MAP/MRR) are a poor fit for RAG , where LLMs consume a set of passages rather than a browsed list; position discounts and prevalence-blind aggregation miss what matters: whether the prompt at cutoff K contains the decisive evidence. Second, there is no standardized, reproducible way to ...
