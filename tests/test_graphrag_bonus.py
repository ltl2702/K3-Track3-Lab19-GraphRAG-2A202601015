import unittest

import pandas as pd

from graphrag_bonus import (
    build_community_reports,
    find_near_duplicate_pairs,
    select_community_reports,
    traversal_edge_limit,
)


class GraphRAGBonusTests(unittest.TestCase):
    def test_near_duplicate_lsh_returns_similar_pair_but_not_unrelated_text(self):
        """A broken LSH candidate filter must not drop a clearly similar document."""
        texts = [
            "Apple introduced the iPhone 15 with a titanium design and USB C connector.",
            "Apple introduced iPhone 15 with titanium design and a USB C connector today.",
            "Citi launched a blockchain service for institutional payment workflows.",
        ]

        pairs = find_near_duplicate_pairs(texts, threshold=0.75)

        self.assertEqual([(row["left_index"], row["right_index"]) for row in pairs], [(0, 1)])
        self.assertGreaterEqual(pairs[0]["similarity"], 0.75)

    def test_community_reports_keep_provenance_and_global_routing_prefers_relevant_community(self):
        """A community report without source evidence or relevant routing is unusable for Global Search."""
        edges = pd.DataFrame(
            [
                {"source": "apple", "target": "iphone15", "source_name": "Apple", "relation": "DEVELOPED", "target_name": "iPhone 15", "source_chunk_id": "c-apple", "published_date": "2023-09-19", "evidence": "Apple developed iPhone 15."},
                {"source": "apple", "target": "streaming", "source_name": "Apple", "relation": "PARTNERED_WITH", "target_name": "video streaming services", "source_chunk_id": "c-stream", "published_date": "2023-06-01", "evidence": "Apple partnered with video streaming services."},
                {"source": "citi", "target": "token", "source_name": "Citi", "relation": "DEVELOPED", "target_name": "Citi Token Services", "source_chunk_id": "c-citi", "published_date": "2023-09-26", "evidence": "Citi developed Citi Token Services."},
            ]
        )
        membership = {"apple": 0, "iphone15": 0, "streaming": 0, "citi": 1, "token": 1}

        reports = build_community_reports(edges, membership)
        selected = select_community_reports("What is Apple's relationship to video streaming?", reports)

        self.assertIn("chunk=c-apple", reports.loc[reports.community_id.eq(0), "report"].iat[0])
        self.assertEqual(selected.iloc[0].community_id, 0)
        self.assertIn("Apple", selected.iloc[0].report)

    def test_supernode_limit_caps_only_nodes_above_threshold(self):
        """Changing the degree boundary must not accidentally truncate ordinary nodes."""
        self.assertEqual(traversal_edge_limit(degree=100, requested_limit=80), 80)
        self.assertEqual(traversal_edge_limit(degree=101, requested_limit=80), 50)


if __name__ == "__main__":
    unittest.main()
