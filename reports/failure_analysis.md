# Failure analysis — Flat RAG vs GraphRAG

## Flat RAG failure: G05 cross-document

Question G05 cần kết hợp hai quan hệ của Apple từ hai chunk khác nhau. Flat RAG chỉ đạt 2/5 comprehensiveness, 3/5 faithfulness và 2/5 multi-hop reasoning vì vector top-k không đảm bảo gom đủ hai evidence rời rạc. Hybrid GraphRAG traversal đưa hai edge có provenance vào cùng context, đạt 5/5 trên ba tiêu chí.

## GraphRAG limitation: G03 multi-hop

Ở G03, Flat và GraphRAG cùng đạt 4/5 cho comprehensiveness/multi-hop. Chuỗi Citi → Citi Token Services → blockchain technology đã có trong vector context, nên graph không tạo thêm quality gain. Để tránh mở rộng graph vô ích, bonus dùng sufficiency check: hop 2, tối đa hop 3, rồi mới vector fallback.

## Mitigations

- Provenance check của run: 46 nodes, 26 edges, `invalid_provenance_edges = 0`.
- Super-node cap được kiểm tra xác định tại boundary 100/101 dù graph mẫu có degree cao nhất chỉ là 3.
- `REJECT_GUARD` giữ `Samsung Electronics` tách khỏi `Samsung Semiconductor Electronics` dù similarity cao.
