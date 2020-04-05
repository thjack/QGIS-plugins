#!/usr/bin/python3

import pywikibot
from pywikibot import pagegenerators as pg

site = pywikibot.Site('wikidata', 'wikidata')
repo = site.data_repository()
item = pywikibot.ItemPage(repo, 'Q42')
item.get()
sitelinks = item.sitelinks
aliases = item.aliases
if 'en' in item.labels:
    print('The label in English is: ' + item.labels['en'])
if item.claims:
    if 'P31' in item.claims: # instance of
        print(item.claims['P31'][0].getTarget())
        print(item.claims['P31'][0].sources[0])  # let's just assume it has sources.

with open('WD properties.rq', 'r') as query_file:
    QUERY = query_file.read()

print(QUERY)
wikidata_site = pywikibot.Site("wikidata", "wikidata")
generator = pg.WikidataSPARQLPageGenerator(QUERY, site=repo)

for wd_property in generator:
    print(wd_property)