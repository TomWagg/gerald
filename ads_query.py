import ads
import datetime


def get_ads_papers(query, astronomy_collection=True, past_week=False, allowed_types=["article", "eprint"]):
    """Get papers from NASA/ADS based on a query

    Parameters
    ----------
    query : `str`
        Query used for ADS searchs
    astronomy_collection : `bool`, optional
        Whether to restrict to the astronomy collection, by default True
    past_week : `bool`, optional
        Whether to restrict to papers from the past week, by default False
    allowed_types : `list`, optional
        List of allowed types of papers, by default ["article", "eprint"]
    """
    # append astronomy collection to query if wanted
    if astronomy_collection:
        query += " collection:astronomy"

    # if in the past week
    if past_week:
        # use datetime to work out the dates
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(weeks=1)

        # restrict the entdates to the date range of last week
        query += f" entdate:[{week_ago.strftime('%Y-%m-%d')} TO {today.strftime('%Y-%m-%d')}]"

    # get the papers
    papers = ads.SearchQuery(q=query, sort="date", fl=["abstract", "author", "citation_count", "doctype",
                                                       "first_author", "read_count", "title", "bibcode",
                                                       "pubdate"])

    papers_dict_list = []

    for paper in papers:
        if paper.doctype in allowed_types:
            year, month, _ = map(int, paper.pubdate.split("-"))
            papers_dict_list.append({
                "link": f"https://ui.adsabs.harvard.edu/abs/{paper.bibcode}/abstract",
                "title": paper.title[0],
                "abstract": paper.abstract,
                "authors": paper.author,
                "date": datetime.date(year=year, month=month, day=1),
                "citations": paper.citation_count,
                "reads": paper.read_count,
            })
    return papers_dict_list


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
    for author in author_string:
        split_author = list(reversed(author.split(", ")))

        # get their first initial and last name
        first_initial, last_name = split_author[0][0], split_author[-1]

        # NOTE: I assume if first initial and last name match then it is the right person
        if first_initial == split_name[0][0] and last_name == split_name[-1]:
            # add asterisks for bold in mrkdwn
            authors += f"*{' '.join(split_author)}*, "
        else:
            authors += f"{' '.join(split_author)}, "

    # add final underscore so the whole thing is italic
    authors = authors[:-2] + "_"
    return authors
