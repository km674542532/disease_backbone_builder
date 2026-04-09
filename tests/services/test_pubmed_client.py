from app.services.pubmed_client import PubMedClient


def test_parse_pubmed_xml_handles_nested_abstract_text_nodes():
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>123</PMID>
          <Article>
            <ArticleTitle>Sample Title</ArticleTitle>
            <Abstract>
              <AbstractText Label=\"Background\">Alpha <i>beta</i> gamma.</AbstractText>
              <AbstractText>Second part.</AbstractText>
            </Abstract>
            <Journal>
              <Title>Journal A</Title>
              <JournalIssue>
                <PubDate><Year>2024</Year></PubDate>
              </JournalIssue>
            </Journal>
            <PublicationTypeList>
              <PublicationType>Review</PublicationType>
            </PublicationTypeList>
          </Article>
          <MeshHeadingList>
            <MeshHeading><DescriptorName>Parkinson Disease</DescriptorName></MeshHeading>
          </MeshHeadingList>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType=\"doi\">10.1000/test</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>
    """

    records = PubMedClient._parse_pubmed_xml(xml, "q1")

    assert len(records) == 1
    assert records[0].pmid == "123"
    assert records[0].abstract == "Alpha beta gamma.\nSecond part."
