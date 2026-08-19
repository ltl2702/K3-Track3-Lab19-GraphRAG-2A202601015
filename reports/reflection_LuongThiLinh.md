# Reflection & Action Plan — Lương Thị Linh

Lab cho thấy GraphRAG không phải thay thế mặc định cho Flat RAG. Factoid đơn lẻ hưởng lợi ít, trong khi cross-document/multi-hop hưởng lợi rõ khi graph có edge quality và provenance tốt.

Khó khăn kỹ thuật đáng chú ý là output benchmark chạy trong Colab ở `/content/outputs` không tự xuất hiện trong repository. Bài học là cần kiểm tra artefact sau runtime, không chỉ nhìn log “Exported”.

Đề xuất đồ án: **Tech News Intelligence Assistant**. Node gồm Company, Person, Technology, Product, Event và Article; relation gồm `ACQUIRED`, `INVESTED_IN`, `DEVELOPED`, `FOUNDED`, `WORKED_AT`, `PARTNERED_WITH`, `MENTIONED_IN`. Hệ thống dùng Flat RAG cho factoid, Hybrid GraphRAG cho multi-hop/cross-doc, ANN + lexical guard cho entity resolution, degree/recency cap cho super-node và community reports cho global questions.
