# Báo Cáo Thực Hành & Thuyết Minh Kỹ Thuật — Lab 19: GraphRAG vs Flat RAG

**Học viên:** Lương Thị Linh
**Khóa học:** AICB-K34 · Track 3: GraphRAG
**Ngày thực hiện:** 19/08/2026
**Phạm vi dữ liệu:** HackerNoon subset; run lưu trong notebook gồm 765 bài sau exact dedup, 60 chunk coreference và 26 triple hợp lệ.

---

## PHẦN 1: THUYẾT MINH KỸ THUẬT & PHÂN TÍCH CA LỖI

### 1. Coreference Resolution

Run hiện tại xử lý 60 chunk và ghi nhận **4 unresolved mentions**. Đây là kết quả mong muốn của chính sách conservative: khi đại từ/generic noun không có antecedent rõ ngay trong cùng chunk, pipeline giữ nguyên câu thay vì thay thế theo suy đoán. Tham chiếu kiểu “the company” trong một đoạn có nhiều công ty là ambiguous nếu không có subject gần và rõ ràng. Giữ nguyên giảm recall nhẹ nhưng tránh false edge như gán nhầm `ACQUIRED` hay `PARTNERED_WITH` cho công ty khác.

Không có false-coreference đã được notebook lưu làm evidence trong run này; vì vậy không khẳng định một lỗi cụ thể không có trong output. Khi mở rộng dữ liệu, các chunk có `unresolved_mentions != []` phải được spot-check trước khi nới lỏng prompt.

### 2. Entity Resolution Threshold & Lexical Guard

- **Ngưỡng cosine:** `0.90`. Candidate chỉ được merge khi vừa đạt ngưỡng embedding vừa vượt lexical guard theo loại thực thể.
- **Cặp bị chặn:** `Samsung Electronics` vs `Samsung Semiconductor Electronics`, cosine **0.904212**.
- **Lý do:** similarity cao do cùng thương hiệu và phần lớn token; tuy nhiên tên còn lại chỉ một division/sản phẩm cụ thể. Merge sẽ làm mất phân biệt thực thể và có thể lan truyền quan hệ sai qua Union-Find. Audit ghi `REJECT_GUARD` với scope `CONTROLLED_POLICY_TEST`.

Bonus near-dedup dùng SimHash 64-bit + LSH banding, chỉ kiểm tra các bài cùng bucket rồi xác minh Hamming similarity. Cách này có audit pair trước khi loại bài repost/near-duplicate và không dùng pairwise cosine O(N²).

### 3. Đồ thị & Super-node Mitigation

Top 3 node theo output Neo4j của run đã lưu:

| Hạng | Thực thể | Loại | Degree |
|---:|---|---|---:|
| 1 | video streaming services | Technology | 3 |
| 2 | Information Services Group | Company | 2 |
| 3 | Intelligent Technical Solutions | Company | 2 |

Dataset lab còn nhỏ nên chưa có node degree >100. Vì vậy notebook có cả kiểm tra live và boundary test: degree `100` không bị cap, còn degree `101` bị giới hạn đúng `50` edge. Với super-node thật, ưu điểm là chặn context/token explosion và ưu tiên thông tin mới. Rủi ro là làm rơi bằng chứng lịch sử; cách giảm rủi ro là cho query time filter hoặc tăng cap có kiểm soát cho câu hỏi temporal.

### 4. So sánh Thực nghiệm: Flat RAG vs GraphRAG

Kết quả dưới đây được trích từ 5 câu evaluation đã chạy và lưu trong notebook (G01–G05):

| Metric tổng thể | Flat RAG | GraphRAG | Δ Graph − Flat |
|---|---:|---:|---:|
| Comprehensiveness (1–5) | 3.8 | 4.6 | +0.8 |
| Faithfulness (1–5) | 4.4 | 5.0 | +0.6 |
| Multi-hop reasoning (1–5) | 3.8 | 4.6 | +0.8 |
| Latency trung bình (s) | 1.838 | 1.502 | -0.336 |
| Token usage trung bình | 598.4 | 608.0 | +9.6 |

- **Flat RAG thất bại, GraphRAG thành công — G05 (cross-doc):** Flat RAG đạt 2/5 cho comprehensiveness và multi-hop reasoning, faithfulness 3/5; GraphRAG đạt 5/5 ở cả ba tiêu chí. Câu hỏi yêu cầu tổng hợp các quan hệ của Apple từ nhiều chunk. Vector top-k phân mảnh evidence, còn traversal gom được hai cạnh có provenance: `Apple -DEVELOPED-> iPhone 15` (2023-09-19) và `Apple -PARTNERED_WITH-> video streaming services` (2023-06-01).
- **Ca khó của GraphRAG — G03 (multi-hop):** cả hai phương pháp cùng đạt 4/5 ở comprehensiveness và multi-hop reasoning. Đây không phải lỗi factual, mà cho thấy retrieval đủ chuỗi `Citi → Citi Token Services → blockchain technology` nhưng không tạo thêm lợi thế khi vector context đã chứa hai facts. Bonus self-correction chỉ mở rộng hop 3 khi LLM đánh giá context thiếu; nếu vẫn thiếu thì mới nối vector fallback để tránh mở rộng graph vô hạn.

### 5. Trade-off, Agent Control & Scale 350MB

- **Quality / cost / latency:** GraphRAG cải thiện mạnh nhất ở cross-doc và multi-hop nhờ nối edge có provenance. Run mẫu nhanh hơn 0.336 giây, nhưng không xem đây là kết luận tổng quát vì graph chỉ có 26 edges; token cao hơn 9.6 token/câu do context graph. Chi phí indexing lớn hơn vì thêm extraction, resolution và Neo4j ingestion.
- **Đề xuất agent bị từ chối:** pairwise cosine similarity trên tất cả bài viết cho near-dedup/entity candidate generation. Nó là O(N²), không phù hợp dữ liệu ~350MB. Thay vào đó dùng ANN cho entity resolution và SimHash-LSH cho near-dedup, kèm audit trước merge.
- **Scale 350MB:** bottleneck đầu tiên là LLM extraction throughput và rate limit, không phải traversal. Kiến trúc phù hợp gồm queue/worker async có retry, checkpoint theo chunk, batch `UNWIND`, ANN/HNSW cho candidates, partition/community report cho global search và retention policy cho evidence.

---

## PHẦN 2: SUY NGẪM & KẾ HOẠCH ÁP DỤNG

### 1. Mapping bài giảng vào code

| Khái niệm | Module | Hàm / khối code | Quan sát |
|---|---|---|---|
| Conservative Coreference | M1 | `resolve_coref_batch()` | 4 mention mơ hồ được giữ nguyên thay vì invent antecedent. |
| Exact + near dedup | M1 + Bonus | `standardize_news()`, `find_near_duplicate_pairs()` | Exact SHA-1 loại bản giống hệt; SimHash-LSH thêm candidate audit không O(N²). |
| Schema & allowlist | M2 | `ALLOWED_NODE_TYPES`, `ALLOWED_RELATIONS`, `run_extraction()` | Chỉ lưu triple có label/relation/evidence hợp lệ. |
| Entity Resolution | M3 | `build_resolution_map()`, `merge_guard()`, `UF` | Threshold 0.90 và guard ngăn false merge Samsung. |
| Bulk ingestion | M2 | `bulk_insert_nodes()`, `bulk_insert_edges()` | `UNWIND` batch 1000; run xác nhận 0 edge thiếu provenance. |
| Hybrid retrieval | M4 | `retrieve_graph_context()`, `answer_graph_rag()` | Graph + vector context được đưa vào generator. |
| Super-node mitigation | M4 | `traversal_edge_limit()` | Boundary 100/101 chứng minh cap 50 đúng điều kiện. |
| Global search + correction | Bonus | `build_communities()`, `retrieve_community_context()`, `self_correcting_context()` | Community reports giữ provenance; fallback dừng sau hop 3. |
| LLM-as-a-Judge | M5 | `judge_answer()`, `run_evaluation()` | So sánh quality, latency và tokens theo nhóm câu hỏi. |

### 2. Quá trình Debugging & bài học

Lỗi quan trọng nhất là artefact đã xuất ở `/content/outputs` của Colab nhưng thư mục `outputs/` trong repository trống. Bài học là path runtime không đồng nghĩa với deliverable Git. Notebook đã được chỉnh để nhất quán `PROJECT_ROOT`, export report community và kiểm tra artefact; trước khi nộp cần rerun các cell evaluation để xuất file từ đúng workspace đang dùng.

### 3. Action Plan: Tech News Intelligence Assistant (đề xuất)

Đề xuất áp dụng cho hệ thống hỏi-đáp, theo dõi quan hệ trong tin tức công nghệ. Flat RAG đủ cho factoid đơn lẻ; GraphRAG nên bật cho câu hỏi “ai đầu tư/mua lại/phát triển gì qua nhiều bài?” và câu hỏi xu hướng toàn cục.

- **Nodes:** `Company`, `Person`, `Technology`, `Product`, `Event`, `Article`.
- **Relations:** `ACQUIRED`, `INVESTED_IN`, `DEVELOPED`, `FOUNDED`, `WORKED_AT`, `PARTNERED_WITH`, `MENTIONED_IN`.
- **Entity resolution:** manual aliases cho ticker/brand lớn; ANN chỉ tạo candidates; lexical/type guard và audit là điều kiện trước Union-Find merge.
- **Super-node:** cap theo degree và recency, global query dùng community reports, hỗ trợ filter thời gian để tránh mất historical evidence.

### Tự đánh giá

| Tiêu chí | Điểm (1–5) | Ghi chú |
|---|---:|---|
| Hiểu pipeline GraphRAG | 4 | Có thể giải thích provenance, resolution, traversal và judge. |
| Kiểm soát AI Coding Agent | 4 | Từ chối O(N²), yêu cầu audit + test boundary. |
| Chất lượng knowledge graph mẫu | 3 | Pipeline đúng, nhưng 26 edge còn nhỏ; cần tăng extraction sau khi kiểm soát chi phí. |
| Phân tích/debug hệ thống | 4 | Phát hiện output Colab không có trong repo và bổ sung kiểm tra deterministic. |

> Lưu ý tái lập: benchmark trên ghi nhận run đã lưu trong notebook. Sau khi chạy phần bonus, cần rerun cell 4.3–4.4 để đo lại benchmark cho adaptive retriever và thay thế hai CSV trong `outputs/`.
