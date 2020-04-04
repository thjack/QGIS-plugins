#!/usr/bin/python3

import pywikibot
from pywikibot import pagegenerators as pg

with open('my_query.rq', 'r') as query_file:
    QUERY = query_file.read()

wikidata_site = pywikibot.Site("wikidata", "wikidata")
generator = pg.WikidataSPARQLPageGenerator(QUERY, site=wikidata_site)

for wd_property in generator:
    print(wd_property)