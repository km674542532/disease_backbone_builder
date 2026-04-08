from app.services.packetizer import Packetizer


def test_packetizer_generates_source_packets():
    docs = [
        {
            "source_type": "ReviewArticle",
            "source_name": "Rev",
            "source_title": "PD",
            "sections": [
                {"section_label": "Pathogenesis", "text": "Para1"},
                {
                    "section_label": "Mechanism",
                    "subsections": [
                        {"label": "M1", "text": "A"},
                        {"label": "M2", "text": "B"},
                    ],
                },
            ],
        }
    ]
    packets = Packetizer().packetize("Parkinson disease", docs)
    assert len(packets) == 3
    assert packets[1].section_label.startswith("Mechanism / M1")
