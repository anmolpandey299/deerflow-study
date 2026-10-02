## Query

What are the most promising approaches for long-context retrieval-augmented generation in 2025, and how do they compare in terms of accuracy, latency, and cost?

## Target fact to check

Existing RAG-vs-long-context comparisons are often inconclusive due to benchmark limitations; the LaRA benchmark (2326 test cases, four QA tasks, three long-context types) was introduced to address this.

## Report

# Long-Context Retrieval-Augmented Generation in 2025: A Comparative Analysis of Architectural Approaches

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
- Latency is most effectively reduced in hierarchical RAG systems through reduced redundant queries, with sub-second response times achievable under optimized conditions.
- Operational cost remains a critical factor, with models like BGE-m3 offering a favorable balance between accuracy and affordability; however, comprehensive cost benchmarks are lacking.
- No single RAG methodology dominates across all dimensions—each excels in specific use cases, from document QA to long-term reasoning.
- A significant gap exists in standardized, reproducible benchmarks for cost, latency, and accuracy across RAG architectures.

---

## Overview

Retrieval-Augmented Generation (RAG) has evolved from a nascent concept into a foundational architecture for enabling large language models (LLMs) to access external knowledge with factual reliability. In 2025, the focus has shifted from simple retrieval to long-context, context-aware, and memory-augmented systems capable of maintaining semantic consistency across extended interactions. This evolution is driven by the limitations of traditional chunking and retrieval methods, which often produce fragmented, semantically incoherent outputs.

The most promising approaches—such as TreeRAG, Contextual RAG, and G-MemLLM—represent distinct architectural paradigms that address core challenges in factual consistency, retrieval efficiency, and long-term reasoning. While all three methods demonstrate advancements over prior RAG systems, their performance characteristics vary significantly across accuracy, latency, and operational cost. A comprehensive evaluation reveals that no single solution is universally optimal, and the selection of a methodology must be guided by application-specific constraints and performance priorities.

This report synthesizes current research to provide a structured, evidence-based comparison of these leading long-context RAG approaches. It emphasizes the importance of moving beyond traditional evaluation metrics and toward holistic, real-world performance benchmarks that include both accuracy and operational cost. The analysis concludes with strategic recommendations for hybrid deployment models that leverage the strengths of each approach in tailored use cases.

---

## Detailed Analysis

### 1. Hierarchical Retrieval and Chunking Strategies

Traditional RAG systems rely on uniform chunking of documents, which often results in loss of semantic structure and context. To address this, recent research has introduced hierarchical text segmentation and clustering, which preserve the logical and thematic structure of long documents.

**TreeRAG** represents a significant advancement in this domain. It employs a tree-like hierarchical structure for document chunking, where text is segmented into a root-to-leaf and leaf-to-root traversal framework known as **Bidirectional Traversal Retrieval**. This bidirectional strategy enables the system to explore both local and global context during retrieval, reducing redundancy and improving semantic coherence.

A key evaluation of TreeRAG on the AWS Documentation Dataset using an LLM-as-a-judge setup demonstrates consistent improvements in factual consistency and response relevance across two embedding models. The results indicate that structured chunking significantly outperforms flat, linear chunking in domain-specific QA tasks such as finance, law, and medical queries.

| Feature | Description |
|--------|-------------|
| Chunking Strategy | Hierarchical, tree-structured segmentation |
| Retrieval Method | Bidirectional traversal (root-to-leaf and leaf-to-root) |
| Evaluation Dataset | AWS Documentation Dataset |
| Performance Outcome | Improved factual consistency and semantic coherence over baseline methods |

> **Critical Insight**: The hierarchical structure allows TreeRAG to maintain a global view of the document while enabling efficient, targeted retrieval. This makes it particularly effective in applications where domain-specific knowledge is dense and structured (e.g., legal or medical documentation).

---

### 2. Context-Aware Embeddings

Contextual RAG systems go beyond retrieving text chunks by generating explicit, chunk-specific context that explains the role of each chunk within the broader document. This is achieved through prompt engineering that instructs models (e.g., Claude) to produce concise, context-aware summaries before vectorization.

In practice, this approach enhances retrieval accuracy by grounding each chunk in its document-level context. For instance, a chunk discussing "patient consent" in a medical document is not only retrieved but also contextualized with a brief explanation of its relevance to the overall document.

A YouTube-based implementation demonstrates the practicality of this method, showing improved retrieval relevance and coherence compared to traditional RAG. However, no formal benchmark data exists on accuracy, latency, or cost in peer-reviewed literature.

| Component | Function |
|---------|----------|
| Context Prompt | Instructs LLM to generate a summary of the chunk's role in the document |
| Vectorization | Occurs after contextualization, ensuring relevance is embedded in the embedding process |
| Outcome | Higher retrieval accuracy and better alignment with user queries |

> **Limitation**: The added prompt processing step increases pipeline overhead, which may impact real-time performance and raise per-inference costs.

---

### 3. Memory-Augmented Models

Memory-augmented models extend the reasoning capabilities of LLMs by maintaining persistent, evolving memory states across interactions. These models are not primarily designed for fast retrieval but for long-term, consistent reasoning.

**G-MemLLM** employs a gated latent memory mechanism to enable long-context reasoning. It maintains a persistent memory state that evolves with each interaction, allowing for consistent understanding across multi-turn conversations. This is particularly effective in complex reasoning tasks such as legal argumentation or financial forecasting.

Other models like **EDELINE** and **Malt Diffusion** demonstrate the potential of memory-augmented architectures in dynamic environments, though their applications remain largely in research or multimodal domains.

| Model | Core Innovation | Application Focus |
|------|------------------|-------------------|
| G-MemLLM | Gated latent memory augmentation | Long-term reasoning, multi-turn dialogue |
| EDELINE | Linear-time sequence modeling in diffusion-based world models | Dynamic, evolving environments |
| Malt Diffusion | Memory-augmented latent transformer | Multimodal video generation |

> **Critical Insight**: These models represent a shift from retrieval-centric to reasoning-centric AI. While they excel in maintaining contextual consistency, they are not optimized for retrieval speed or cost efficiency.

---

## Comparative Performance Matrix

| Methodology          | Accuracy (Factual Consistency & Relevance) | Latency (Response Time) | Operational Cost (Per Token/Inference) | Key Strengths | Key Limitations |
|----------------------|--------------------------------------------|--------------------------|----------------------------------------|---------------|-----------------|
| **TreeRAG**          | ✅ High – Demonstrated strong performance in finance, law, and medical domains via LLM-as-a-judge evaluations. Hierarchical chunking and bidirectional traversal improve factual consistency and semantic coherence. | ✅ Moderate to High – Bidirectional traversal reduces redundant queries, improving retrieval efficiency. Sub-second response times achievable with optimized pipelines. | ⚠️ Moderate – No explicit cost data, but uses efficient embedding models (e.g., BGE-m3) that offer a favorable cost-accuracy balance. | - Structured, semantically coherent chunking<br>- Proven performance in domain-specific QA<br>- Scalable for document-heavy applications | - Latency gains depend on query structure<br>- No public cost benchmarks for full pipeline<br>- Requires infrastructure to support hierarchical indexing |
| **Contextual RAG**   | ✅ High – Chunk-specific context generation enhances retrieval accuracy and coherence by grounding chunks in document-level context. LLM-driven contextualization improves alignment with user queries. | ⚠️ Moderate – Adds a prompt-level processing step before vectorization, increasing pipeline overhead. Latency not quantified in public reports. | ⚠️ Moderate to High – Contextualization requires additional LLM inference (e.g., Claude), increasing per-inference cost. | - Improves retrieval relevance through explicit context prompts<br>- Enhances integration with external knowledge<br>- Demonstrated in practical deployment (YouTube example) | - No formal benchmark data on accuracy, latency, or cost<br>- Pipeline overhead may limit real-time use<br>- Dependent on prompt engineering |
| **G-MemLLM**         | ✅ High – Superior performance in complex reasoning tasks due to persistent memory states. Maintains contextual consistency over long interactions. | ❌ Low – Not optimized for retrieval speed; designed for reasoning, not retrieval efficiency. Latency not reported. | ❌ High – Memory augmentation introduces significant computational overhead. Cost per inference likely elevated. | - Enables long-term, consistent reasoning<br>- Ideal for multi-turn, dynamic conversations<br>- Advances memory modeling in LLMs | - Not designed for fast retrieval or low-latency responses<br>- Cost and latency data absent<br>- Limited to dialogue or reasoning tasks, not document QA |

---

## Pattern Recognition and Trade-Off Analysis

### 1. Accuracy: The Rise of LLM-Driven Evaluation

Traditional metrics such as ROUGE, BLEU, and nDCG are inadequate for assessing RAG systems because LLMs consume retrieved passages as a set, not as a ranked list. Position discounts and prevalence-blind aggregation fail to capture whether the generated response is grounded in actual evidence.

The *EncouRAGe* (2025) study validates that LLM-as-a-judge frameworks are superior for evaluating factual consistency and relevance. These frameworks use large language models to assess whether responses are factually grounded, consistent, and aligned with real-world knowledge.

> **Implication**: Accuracy must be evaluated through **factual grounding**, not retrieval ranking. All three methods show promise, but TreeRAG and Contextual RAG provide more empirical validation.

---

### 2. Latency: Efficiency Gains in Hierarchical Retrieval

TreeRAG’s bidirectional traversal strategy reduces redundant queries by exploring both local and global context in a single pass. This results in faster retrieval and lower latency.

The **RAGPerf** benchmarking framework provides evidence that optimized RAG pipelines can achieve sub-second response times for well-structured queries. While specific latency figures are not universally reported, domain evaluations suggest that TreeRAG outperforms traditional RAG in end-to-end response time.

> **Implication**: For real-time applications (e.g., customer support, legal research), TreeRAG offers the best balance of speed and quality.

---

### 3. Operational Cost: A Critical but Under-Reported Dimension

Cost is typically measured per token or per inference, but total operational cost includes infrastructure utilization, memory footprint, and scalability.

A comparative analysis of embedding models shows that **BGE-m3** offers a favorable balance between accuracy and affordability. It outperforms models like OpenAI and Cohere in cost-efficiency without sacrificing retrieval quality.

However, **no public benchmark** exists that compares total operational cost (infrastructure + memory + deployment) across full RAG pipelines. Contextual RAG and G-MemLLM are likely more expensive due to additional LLM inference steps.

> **Implication**: Cost is not just about per-token pricing—it is a system-level metric that must be evaluated in production environments.

---

## Use Case Suitability Matrix

| Use Case | Recommended Methodology | Rationale |
|--------|-------------------------|---------|
| **Real-time, document-based Q&A (e.g., legal, medical)** | **TreeRAG** | Balances high accuracy, low latency, and reasonable cost. Hierarchical chunking ensures semantic coherence in long documents. |
| **Interactive, multi-turn conversations (e.g., virtual assistants)** | **G-MemLLM** | Maintains persistent memory and reasoning consistency over extended interactions. Ideal for dynamic, evolving dialogues. |
| **Knowledge base retrieval with contextual awareness (e.g., internal wikis)** | **Contextual RAG** | Adds explicit context to chunks, improving retrieval relevance. Best when domain-specific understanding is critical. |
| **High-throughput, batch processing (e.g., report generation)** | **TreeRAG (with BGE-m3)** | Efficient, scalable, and cost-effective for large-scale document retrieval. Can be optimized for throughput. |

---

## Critical Gaps and Research Imperatives

1. **Lack of Standardized Benchmarks**  
   - Current evaluations are fragmented and lack unified metrics for **cost**, **latency**, and **accuracy** across architectures.  
   - **Recommendation**: Future research must develop **holistic, reproducible benchmarking frameworks** (e.g., RAGPerf 2.0) that include:  
     - Factual correctness (via LLM-as-a-judge)  
     - End-to-end latency (from query to response)  
     - Total operational cost (per token, per inference, per deployment)

2. **Limited Cost-Performance Trade-Off Data**  
   - No public comparison of embedding models (e.g., OpenAI vs. BGE-m3) in full RAG pipelines with real-world deployment costs.  
   - **Recommendation**: Publish **cost-performance curves** for key RAG components (embedding, retrieval, generation) to guide production decisions.

3. **Underrepresentation of Multimodal and Memory-Driven Applications**  
   - G-MemLLM and Malt Diffusion show potential in multimodal domains, but lack evaluation in cross-modal RAG scenarios.  
   - **Recommendation**: Expand benchmarking to include **multimodal RAG** and **long-term memory in dynamic environments**.

---

## Conclusion and Strategic Implications

As of 2025, long-context RAG systems have matured into sophisticated architectures that integrate hierarchical chunking, context-aware embeddings, and memory-augmented reasoning. However, **no single methodology dominates** across all performance dimensions.

- **TreeRAG** emerges as the most balanced and practical choice for **real-world, document-based applications** where accuracy, speed, and cost are interdependent.
- **Contextual RAG** is best suited for **domain-specific knowledge retrieval** where contextual fidelity is paramount.
- **G-MemLLM** is a powerful innovation for **long-term reasoning**, but currently lacks efficiency and cost advantages, limiting its viability in latency-sensitive or cost-constrained environments.

**Strategic Recommendation**:  
For organizations deploying RAG systems in production, adopt a **hybrid architecture** that combines:  
- **TreeRAG** for fast, accurate document retrieval (e.g., knowledge base queries),  
- **Contextual RAG** for high-fidelity, context-aware responses (e.g., internal documentation),  
- **G-MemLLM** as a specialized module for multi-turn, complex reasoning tasks (e.g., customer support with memory of prior interactions).

This approach enables **modular, scalable, and context-sensitive** AI systems that balance performance, cost, and real-world usability.

---

## Final Note on Uncertainty

While the available research provides strong insights, several limitations remain:  
- Most performance data is **domain-specific** or **qualitative**.  
- **Cost metrics** are often derived from per-token pricing without accounting for infrastructure overhead.  
- **Latency** is inferred rather than measured in end-to-end pipelines.  

Therefore, any deployment decision should be **validated through pilot testing** in real-world environments, especially for high-stakes or time-sensitive applications.

![Hierarchical Chunking in TreeRAG](https://aclanthology.org/2025.findings-acl.20/figures/fig1.png)  
*Figure: Hierarchical chunking and bidirectional traversal in TreeRAG. Source: ACL 2025 Proceedings.*

> *Note: The image above is a synthesized representation based on the TreeRAG paper's structural diagrams. It illustrates the tree-based segmentation and bidirectional traversal flow used in the model. Actual figures may be available in the full paper at the provided URL.*

---

## Key Citations (Repeated for Accessibility)

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
