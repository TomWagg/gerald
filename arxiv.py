import xml.etree.ElementTree as ET
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import date
import numpy as np

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
        Each paper contains a link, date, title, abstract and the authors. Returns None if ORCID is invalid/
        isn't linked to arXiv account.
    """
    # get the data from the arXiv
    try:
        data = urlopen(f"https://arxiv.org/a/{orcid}.atom2")
    except HTTPError:
        return None

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


def get_n_most_recent_papers(orcid, n):
    """Get the n most recently *published* papers associated with an ORCID id (they are sorted by latest
    updated which is not the same)

    Parameters
    ----------
    orcid : `str`
        ORCID ID
    n : `int`
        How many papers

    Returns
    -------
    most_recent : `list` of `dict`
        Most recent n papers in a dictionary. None if ORCID invalid/not linked to arXiv.

    most_recent_time : `list` of `int`
        How many days since each was published. None if ORCID invalid/not linked to arXiv.
    """
    # get today's date and all of the papers
    today = date.today()
    papers = get_papers_by_orcid(orcid)
    if papers is None:
        return None, None

    # go through each and find how long it's been since they've been published
    time_since_published = [(today - paper["date"]).days for paper in papers]

    sort_order = np.argsort(time_since_published)
    sorted_papers = np.array(papers)[sort_order]
    sorted_times = np.array(time_since_published)[sort_order]

    return sorted_papers[:n], sorted_times[:n]


def bold_grad_author(author_string, name):
    """Bold the grad author in the list of authors

    Parameters
    ----------
    author_string : `str`
        Initial author string
    name : `str`
        Name of grad

    Returns
    -------
    authors: `str`
        Author string but with asterisks around the grad
    """
    authors = "_Authors: "
    split_name = name.split(" ")

    # go through each author in the list
    for author in author_string.split(", "):
        split_author = author.split(" ")

        # get their first initial and last name
        first_initial, last_name = split_author[0][0], split_author[-1]

        # NOTE: I assume if first initial and last name match then it is the right person
        if first_initial == split_name[0][0] and last_name == split_name[-1]:
            # add asterisks for bold in mrkdwn
            authors += f"*{author}*, "
        else:
            authors += f"{author}, "

    # add final underscore so the whole thing is italic
    authors = authors[:-2] + "_"
    return authors
