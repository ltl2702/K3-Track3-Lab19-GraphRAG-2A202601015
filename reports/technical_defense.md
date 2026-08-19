# Thuyết minh kỹ thuật — Lương Thị Linh

1. **Coreference:** 60 chunk được xử lý và có 4 unresolved mention. Chính sách giữ nguyên mention mơ hồ ngăn false edge; không có false-resolution cụ thể được lưu trong output này.
2. **Entity threshold:** cosine `0.90`, sau ANN candidate còn lexical guard theo loại entity.
3. **Guard case:** `Samsung Electronics` và `Samsung Semiconductor Electronics` có cosine `0.904212` nhưng bị `REJECT_GUARD`, vì division/sản phẩm không được gộp với company.
4. **Top degree:** video streaming services (3), Information Services Group (2), Intelligent Technical Solutions (2).
5. **Temporal cap:** lấy 50 edge mới nhất giúp giữ context gọn; rủi ro là mất historical evidence, nên query temporal cần filter/cap riêng.
6. **Flat RAG thắng:** factoid G01–G02 không có lợi thế rõ rệt cho graph; Flat thường rẻ hơn về token.
7. **GraphRAG thắng:** cross-doc G05; scores quality tăng từ 2/3/2 lên 5/5/5 (comprehensiveness/faithfulness/multi-hop).
8. **Trade-off:** overall GraphRAG 4.6 vs 3.8 comprehensiveness; latency 1.502s vs 1.838s trong graph nhỏ; token 608 vs 598.4.
9. **Agent control:** từ chối pairwise cosine O(N²); dùng ANN và SimHash-LSH có audit.
10. **Scale 350MB:** LLM extraction throughput/rate limit là bottleneck trước; dùng queue, checkpoint, async batching, `UNWIND`, ANN/HNSW và community partitioning.
