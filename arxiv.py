import xml.etree.ElementTree as ET
from urllib.request import urlopen
from datetime import date

namespace = "{http://www.w3.org/2005/Atom}"


def get_papers_by_orcid(orcid):
    data = urlopen(f"https://arxiv.org/a/{orcid}.atom2")
    root = ET.fromstring(data.read())
    print(root.tag)
    papers = []
    for entry in root.iter(f"{namespace}entry"):
        year, month, day = map(int, entry.find(f"{namespace}published").text.split("T")[0].split("-"))
        paper = {
            "link": entry.find(f"{namespace}id").text,
            "date": date(year=year, month=month, day=day),
            "title": entry.find(f"{namespace}title").text,
            "abstract": entry.find(f"{namespace}summary").text,
            "authors": entry.find(f"{namespace}author").find(f"{namespace}name").text,
        }
        papers.append(paper)
    return papers


def get_most_recent_paper(orcid):
    today = date.today()
    papers = get_papers_by_orcid(orcid)
    most_recent = None
    most_recent_time = None
    for paper in papers:
        if most_recent is None or today - paper["date"] < most_recent_time:
            most_recent = paper
            most_recent_time = today - paper["date"]
    return most_recent, most_recent_time.days

# print(get_papers_by_orcid("0000-0001-6147-5761")[-1])
# print(get_most_recent_paper("0000-0001-6147-5761"))
