import xml.etree.ElementTree as ET
from urllib.request import urlopen
from datetime import date

namespace = "{http://www.w3.org/2005/Atom}"


def get_papers_by_orcid(orcid):
    """Get a list of papers from the arXiv matching an ORCID ID

    Parameters
    ----------
    orcid : `str`
        ORCID ID

    Returns
    -------
    papers : `list` of `dict`s
        Each paper contains a link, date, title, abstract and the authors
    """
    # get the data from the arXiv
    data = urlopen(f"https://arxiv.org/a/{orcid}.atom2")

    # parse the XML
    root = ET.fromstring(data.read())

    # go through each entry in the list
    papers = []
    for entry in root.iter(f"{namespace}entry"):
        # convert the *published* date to year/month/day
        year, month, day = map(int, entry.find(f"{namespace}published").text.split("T")[0].split("-"))

        # add the paper to the list
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
    """Get the most recently *published* paper associated with an ORCID id (they are sorted by latest
    updated which is not the same)

    Parameters
    ----------
    orcid : `str`
        ORCID ID

    Returns
    -------
    most_recent : `dict`
        Most recent paper in a dictionary

    most_recent_time : `int`
        How many days since it was published
    """
    # get today's date and all of the papers
    today = date.today()
    papers = get_papers_by_orcid(orcid)

    # track the most recent and its time from today
    most_recent = None
    most_recent_time = None

    # go through each and find the most recent
    for paper in papers:
        if most_recent is None or today - paper["date"] < most_recent_time:
            most_recent = paper
            most_recent_time = today - paper["date"]
    return most_recent, most_recent_time.days

# print(get_papers_by_orcid("0000-0001-6147-5761")[-1])
# print(get_most_recent_paper("0000-0001-6147-5761"))
