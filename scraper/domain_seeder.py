"""
scraper/domain_seeder.py

Dynamic Domain Seeder & Career Page Resolver.
Generates a comprehensive registry of 2,300+ Indian public sector, academic,
PSU, and banking domains, and provides dynamic resolution of career pages.
"""

import time
import requests
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from scraper.config import DEFAULT_HEADERS

# 28 States and 8 Union Territory codes in India
_STATE_CODES = [
    "ap", "ar", "as", "br", "cg", "ga", "gj", "hr", "hp", "jk", "jh", "ka", "kl",
    "mp", "mh", "mn", "ml", "mz", "nl", "od", "pb", "rj", "sk", "tn", "tg", "tr",
    "up", "uk", "wb", "dl", "py", "ch", "an", "ld", "dd", "dn"
]

# 30 key state government departments/directorates
_DEPARTMENTS = [
    "education", "health", "pwd", "forest", "agriculture", "revenue", "transport", 
    "wrd", "sports", "police", "finance", "coop", "excise", "tourism", "socialwelfare", 
    "tribal", "urban", "rural", "industries", "planning", "animalhusbandry", "fisheries", 
    "labour", "information", "law", "energy", "science", "technicaleducation", "highereducation", "home",
    "food", "welfare", "housing", "water", "disaster"
]

# Corrected Official State Domains Suffixes
STATE_DOMAINS = {
    "an": "andaman.gov.in",
    "ap": "ap.gov.in",
    "ar": "arunachal.gov.in",
    "as": "assam.gov.in",
    "br": "bihar.gov.in",
    "ch": "chd.gov.in",
    "cg": "cgstate.gov.in",
    "dn": "dadra.gov.in",
    "dd": "daman.nic.in",
    "dl": "delhi.gov.in",
    "ga": "goa.gov.in",
    "gj": "gujarat.gov.in",
    "hr": "haryana.gov.in",
    "hp": "hp.gov.in",
    "jk": "jk.gov.in",
    "jh": "jharkhand.gov.in",
    "ka": "karnataka.gov.in",
    "kl": "kerala.gov.in",
    "ld": "lakshadweep.gov.in",
    "mp": "mp.gov.in",
    "mh": "maharashtra.gov.in",
    "mn": "manipur.gov.in",
    "ml": "meghalaya.gov.in",
    "mz": "mizoram.gov.in",
    "nl": "nagaland.gov.in",
    "od": "odisha.gov.in",
    "py": "puducherry.gov.in",
    "pb": "punjab.gov.in",
    "rj": "rajasthan.gov.in",
    "sk": "sikkim.gov.in",
    "tn": "tn.gov.in",
    "tg": "telangana.gov.in",
    "tr": "tripura.gov.in",
    "up": "up.gov.in",
    "uk": "uk.gov.in",
    "wb": "wb.gov.in"
}

# Real official State PSC Domains
STATE_PSC_DOMAINS = {
    "ap": "psc.ap.gov.in",
    "ar": "appsc.gov.in",
    "as": "apsc.nic.in",
    "br": "bpsc.bih.nic.in",
    "cg": "psc.cg.gov.in",
    "ga": "gpsc.goa.gov.in",
    "gj": "gpsc.gujarat.gov.in",
    "hr": "hpsc.gov.in",
    "hp": "hppsc.hp.gov.in",
    "jk": "jkpsc.nic.in",
    "jh": "jpsc.gov.in",
    "ka": "kpsc.kar.nic.in",
    "kl": "keralapsc.gov.in",
    "mp": "mppsc.mp.gov.in",
    "mh": "mpsc.gov.in",
    "mn": "mpscmanipur.gov.in",
    "ml": "mpsc.nic.in",
    "mz": "mpsc.mizoram.gov.in",
    "nl": "npsc.co.in",
    "od": "opsc.gov.in",
    "pb": "ppsc.gov.in",
    "rj": "rpsc.rajasthan.gov.in",
    "sk": "spsc.sikkim.gov.in",
    "tn": "tnpsc.gov.in",
    "tg": "tgpsc.gov.in",
    "tr": "tpsc.tripura.gov.in",
    "up": "uppsc.up.nic.in",
    "uk": "psc.uk.gov.in",
    "wb": "psc.wb.gov.in",
    "dl": "dsssb.delhi.gov.in",
    "py": "py.gov.in",
    "ch": "chd.gov.in",
    "an": "andaman.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "daman.nic.in",
    "dn": "dadra.gov.in"
}

# Real official State SSBs / Selection Boards
STATE_SSB_DOMAINS = {
    "ap": "ap.gov.in",
    "ar": "apssb.nic.in",
    "as": "sebaonline.org",
    "br": "bssc.bihar.gov.in",
    "cg": "vyapam.cgstate.gov.in",
    "ga": "goa.gov.in",
    "gj": "gsssb.gujarat.gov.in",
    "hr": "hssc.gov.in",
    "hp": "hpsssb.hp.gov.in",
    "jk": "jkssb.nic.in",
    "jh": "jssc.nic.in",
    "ka": "kea.kar.nic.in",
    "kl": "keralapsc.gov.in",
    "mp": "esb.mp.gov.in",
    "mh": "mahassb.in",
    "mn": "manipur.gov.in",
    "ml": "meghalaya.gov.in",
    "mz": "mssc.mizoram.gov.in",
    "nl": "npsc.co.in",
    "od": "ossc.gov.in",
    "pb": "sssb.punjab.gov.in",
    "rj": "rsmssb.rajasthan.gov.in",
    "sk": "sikkim.gov.in",
    "tn": "tnpsc.gov.in",
    "tg": "tgpsc.gov.in",
    "tr": "tpsc.tripura.gov.in",
    "up": "upsssc.gov.in",
    "uk": "sssc.uk.gov.in",
    "wb": "prb.wb.gov.in",
    "dl": "dsssb.delhi.gov.in",
    "py": "py.gov.in",
    "ch": "chd.gov.in",
    "an": "andaman.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "daman.nic.in",
    "dn": "dadra.gov.in"
}

# Real official State Police recruitment
STATE_POLICE_DOMAINS = {
    "ap": "ap.gov.in",
    "ar": "arunpol.nic.in",
    "as": "assam.gov.in",
    "br": "bihar.gov.in",
    "cg": "cgpolice.gov.in",
    "ga": "goa.gov.in",
    "gj": "gujarat.gov.in",
    "hr": "haryana.gov.in",
    "hp": "hppolice.gov.in",
    "jk": "jkpolice.gov.in",
    "jh": "jhpolice.gov.in",
    "ka": "ksp.karnataka.gov.in",
    "kl": "kerala.gov.in",
    "mp": "mppolice.gov.in",
    "mh": "maharashtra.gov.in",
    "mn": "manipur.gov.in",
    "ml": "meghalaya.gov.in",
    "mz": "mizoram.gov.in",
    "nl": "nagaland.gov.in",
    "od": "odisha.gov.in",
    "pb": "punjab.gov.in",
    "rj": "rajasthan.gov.in",
    "sk": "sikkim.gov.in",
    "tn": "tnpolice.gov.in",
    "tg": "tspolice.gov.in",
    "tr": "tripura.gov.in",
    "up": "uppolice.gov.in",
    "uk": "uk.gov.in",
    "wb": "wbpolice.gov.in",
    "dl": "delhi.gov.in",
    "py": "py.gov.in",
    "ch": "chd.gov.in",
    "an": "andaman.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "ddpolice.gov.in",
    "dn": "dadra.gov.in"
}

# Real official State RTC (Transport PSU) Domains
STATE_RTC_DOMAINS = {
    "ap": "apsrtc.ap.gov.in",
    "ar": "arunachalpradesh.gov.in",
    "as": "astc.assam.gov.in",
    "br": "bsrtc.bihar.gov.in",
    "ch": "chdtransport.gov.in",
    "cg": "cg.nic.in",
    "dn": "dadra.gov.in",
    "dd": "daman.nic.in",
    "dl": "dtc.delhi.gov.in",
    "ga": "ktclgoa.com",
    "gj": "gsrtc.in",
    "hr": "hartrans.gov.in",
    "hp": "hrtchp.com",
    "jk": "jkrtc.co.in",
    "jh": "jharkhand.gov.in",
    "ka": "ksrtc.in",
    "kl": "keralartc.com",
    "ld": "lakshadweep.gov.in",
    "mp": "transport.mp.gov.in",
    "mh": "msrtc.maharashtra.gov.in",
    "mn": "manipur.gov.in",
    "ml": "megtransport.gov.in",
    "mz": "transport.mizoram.gov.in",
    "nl": "nst.nagaland.gov.in",
    "od": "osrtc.in",
    "py": "prtc.in",
    "pb": "punjabroadways.gov.in",
    "rj": "rsrtc.rajasthan.gov.in",
    "sk": "sikkim.gov.in",
    "tn": "tnstc.in",
    "tg": "tsrtc.telangana.gov.in",
    "tr": "tripura.gov.in",
    "up": "upsrtc.up.gov.in",
    "uk": "utc.uk.gov.in",
    "wb": "wbtc.co.in"
}

# Corrected Municipality domains
MUNI_DOMAINS = {
    "mcgm": "mcgm.gov.in",
    "pmc": "pmc.gov.in",
    "nmmc": "nmmc.gov.in",
    "kdmc": "kdmc.gov.in",
    "mbmc": "mbmc.gov.in",
    "vvcmc": "vvcmc.in",
    "ulhasnagar": "umc.gov.in",
    "bnmc": "bnmc.gov.in",
    "smc_gj": "suratmunicipal.gov.in",
    "amc_gj": "ahmedabadcity.gov.in",
    "vmc_gj": "vmc.gov.in",
    "rmc_gj": "rmc.gov.in",
    "jmc_rj": "jaipurmc.org",
    "jo_mc": "jodhpurmc.org",
    "kmc_wb": "kmcgov.in",
    "hmc_wb": "hmcgov.in",
    "mcshimla": "shimlamc.hp.gov.in",
    "mcg": "mcg.gov.in",
    "mcf": "mcfaridabad.gov.in",
    "mcc_ka": "mysurucity.mrc.gov.in",
    "bmrda": "bmrda.karnataka.gov.in",
    "hmrda": "hmda.gov.in",
    "cmda": "cmdachennai.gov.in",
    "ghmc": "ghmc.gov.in",
    "gvmc": "gvmc.gov.in",
    "vuda": "vuda.gov.in",
    "vada": "vada.gov.in",
    "kda": "kdaindia.co.in",
    "jda": "jda.rajasthan.gov.in",
    "uda": "udajodhpur.org",
    "ada": "adaamritsar.org",
    "gda": "gda.up.gov.in",
    "udaipurmc": "udaipurmc.org",
    "kotamc": "kotamunicipal.org",
    "bikanermc": "bikanermc.org",
    "ajmermc": "ajmermc.org",
    "bhilwaramc": "bhilwaramc.org",
    "alwarmc": "alwarmc.org",
    "sikarmc": "sikarmc.org",
    "pnbmc": "punjab.gov.in",
    "dharmc": "dhar.nic.in",
    "gwalior-mc": "gwaliorcorporation.org",
    "bhopal-mc": "bhopalmunicipal.com",
    "indore-mc": "imcindore.org",
    "jabalpur-mc": "jmcjabalpur.org",
    "sagar-mc": "sagarmunicipal.com",
    "satna-mc": "satnamunicipal.com",
    "rewa-mc": "rewamunicipal.com"
}
WORKING_DEPTS = {
    "agriculture.ap.gov.in",
    "agriculture.bihar.gov.in",
    "agriculture.hp.gov.in",
    "agriculture.jk.gov.in",
    "agriculture.karnataka.gov.in",
    "agriculture.mizoram.gov.in",
    "agriculture.nagaland.gov.in",
    "agriculture.rajasthan.gov.in",
    "agriculture.sikkim.gov.in",
    "agriculture.telangana.gov.in",
    "agriculture.uk.gov.in",
    "agriculture.up.gov.in",
    "animalhusbandry.assam.gov.in",
    "animalhusbandry.hp.gov.in",
    "animalhusbandry.jharkhand.gov.in",
    "animalhusbandry.mizoram.gov.in",
    "animalhusbandry.punjab.gov.in",
    "animalhusbandry.rajasthan.gov.in",
    "coop.assam.gov.in",
    "coop.goa.gov.in",
    "coop.haryana.gov.in",
    "coop.hp.gov.in",
    "coop.mizoram.gov.in",
    "coop.odisha.gov.in",
    "disaster.jharkhand.gov.in",
    "disaster.mizoram.gov.in",
    "disaster.uk.gov.in",
    "education.arunachal.gov.in",
    "education.assam.gov.in",
    "education.bihar.gov.in",
    "education.delhi.gov.in",
    "education.goa.gov.in",
    "education.gujarat.gov.in",
    "education.hp.gov.in",
    "education.jharkhand.gov.in",
    "education.kerala.gov.in",
    "education.maharashtra.gov.in",
    "education.mizoram.gov.in",
    "education.nagaland.gov.in",
    "education.rajasthan.gov.in",
    "education.sikkim.gov.in",
    "energy.karnataka.gov.in",
    "energy.maharashtra.gov.in",
    "energy.mizoram.gov.in",
    "energy.mp.gov.in",
    "energy.odisha.gov.in",
    "energy.rajasthan.gov.in",
    "energy.up.gov.in",
    "excise.ap.gov.in",
    "excise.assam.gov.in",
    "excise.delhi.gov.in",
    "excise.goa.gov.in",
    "excise.jharkhand.gov.in",
    "excise.kerala.gov.in",
    "excise.meghalaya.gov.in",
    "excise.mizoram.gov.in",
    "excise.mp.gov.in",
    "excise.nagaland.gov.in",
    "excise.odisha.gov.in",
    "excise.punjab.gov.in",
    "excise.rajasthan.gov.in",
    "excise.sikkim.gov.in",
    "excise.telangana.gov.in",
    "excise.tripura.gov.in",
    "excise.uk.gov.in",
    "excise.up.gov.in",
    "excise.wb.gov.in",
    "finance.arunachal.gov.in",
    "finance.assam.gov.in",
    "finance.delhi.gov.in",
    "finance.jharkhand.gov.in",
    "finance.karnataka.gov.in",
    "finance.kerala.gov.in",
    "finance.maharashtra.gov.in",
    "finance.mizoram.gov.in",
    "finance.mp.gov.in",
    "finance.nagaland.gov.in",
    "finance.odisha.gov.in",
    "finance.punjab.gov.in",
    "finance.rajasthan.gov.in",
    "finance.telangana.gov.in",
    "finance.tripura.gov.in",
    "finance.wb.gov.in",
    "fisheries.ap.gov.in",
    "fisheries.assam.gov.in",
    "fisheries.bihar.gov.in",
    "fisheries.cgstate.gov.in",
    "fisheries.goa.gov.in",
    "fisheries.gujarat.gov.in",
    "fisheries.jk.gov.in",
    "fisheries.karnataka.gov.in",
    "fisheries.kerala.gov.in",
    "fisheries.maharashtra.gov.in",
    "fisheries.meghalaya.gov.in",
    "fisheries.mizoram.gov.in",
    "fisheries.nagaland.gov.in",
    "fisheries.odisha.gov.in",
    "fisheries.rajasthan.gov.in",
    "fisheries.sikkim.gov.in",
    "fisheries.telangana.gov.in",
    "fisheries.tn.gov.in",
    "fisheries.tripura.gov.in",
    "fisheries.uk.gov.in",
    "fisheries.up.gov.in",
    "fisheries.wb.gov.in",
    "food.karnataka.gov.in",
    "food.mizoram.gov.in",
    "food.mp.gov.in",
    "food.odisha.gov.in",
    "food.rajasthan.gov.in",
    "food.wb.gov.in",
    "forest.assam.gov.in",
    "forest.delhi.gov.in",
    "forest.goa.gov.in",
    "forest.jharkhand.gov.in",
    "forest.jk.gov.in",
    "forest.karnataka.gov.in",
    "forest.kerala.gov.in",
    "forest.mizoram.gov.in",
    "forest.mp.gov.in",
    "forest.nagaland.gov.in",
    "forest.odisha.gov.in",
    "forest.punjab.gov.in",
    "forest.rajasthan.gov.in",
    "forest.sikkim.gov.in",
    "forest.tripura.gov.in",
    "forest.uk.gov.in",
    "forest.wb.gov.in",
    "health.ap.gov.in",
    "health.arunachal.gov.in",
    "health.chd.gov.in",
    "health.delhi.gov.in",
    "health.kerala.gov.in",
    "health.mizoram.gov.in",
    "health.mp.gov.in",
    "health.odisha.gov.in",
    "health.punjab.gov.in",
    "health.rajasthan.gov.in",
    "health.sikkim.gov.in",
    "health.telangana.gov.in",
    "health.tripura.gov.in",
    "health.uk.gov.in",
    "highereducation.assam.gov.in",
    "highereducation.jk.gov.in",
    "highereducation.kerala.gov.in",
    "highereducation.mizoram.gov.in",
    "highereducation.mp.gov.in",
    "highereducation.nagaland.gov.in",
    "highereducation.sikkim.gov.in",
    "highereducation.tripura.gov.in",
    "home.assam.gov.in",
    "home.bihar.gov.in",
    "home.delhi.gov.in",
    "home.gujarat.gov.in",
    "home.jk.gov.in",
    "home.karnataka.gov.in",
    "home.maharashtra.gov.in",
    "home.mizoram.gov.in",
    "home.mp.gov.in",
    "home.nagaland.gov.in",
    "home.odisha.gov.in",
    "home.rajasthan.gov.in",
    "home.sikkim.gov.in",
    "home.wb.gov.in",
    "housing.ap.gov.in",
    "housing.karnataka.gov.in",
    "housing.maharashtra.gov.in",
    "housing.mizoram.gov.in",
    "housing.wb.gov.in",
    "industries.ap.gov.in",
    "industries.arunachal.gov.in",
    "industries.assam.gov.in",
    "industries.delhi.gov.in",
    "industries.karnataka.gov.in",
    "industries.maharashtra.gov.in",
    "industries.mizoram.gov.in",
    "industries.odisha.gov.in",
    "industries.rajasthan.gov.in",
    "industries.sikkim.gov.in",
    "industries.telangana.gov.in",
    "industries.tripura.gov.in",
    "information.mizoram.gov.in",
    "information.up.gov.in",
    "labour.ap.gov.in",
    "labour.arunachal.gov.in",
    "labour.assam.gov.in",
    "labour.chd.gov.in",
    "labour.delhi.gov.in",
    "labour.goa.gov.in",
    "labour.gujarat.gov.in",
    "labour.hp.gov.in",
    "labour.karnataka.gov.in",
    "labour.kerala.gov.in",
    "labour.maharashtra.gov.in",
    "labour.mizoram.gov.in",
    "labour.mp.gov.in",
    "labour.nagaland.gov.in",
    "labour.odisha.gov.in",
    "labour.rajasthan.gov.in",
    "labour.sikkim.gov.in",
    "labour.telangana.gov.in",
    "labour.tn.gov.in",
    "labour.tripura.gov.in",
    "labour.uk.gov.in",
    "labour.wb.gov.in",
    "law.arunachal.gov.in",
    "law.cgstate.gov.in",
    "law.delhi.gov.in",
    "law.jk.gov.in",
    "law.karnataka.gov.in",
    "law.mizoram.gov.in",
    "law.mp.gov.in",
    "law.odisha.gov.in",
    "law.rajasthan.gov.in",
    "law.telangana.gov.in",
    "law.tripura.gov.in",
    "law.wb.gov.in",
    "planning.ap.gov.in",
    "planning.gujarat.gov.in",
    "planning.hp.gov.in",
    "planning.karnataka.gov.in",
    "planning.mizoram.gov.in",
    "planning.mp.gov.in",
    "planning.rajasthan.gov.in",
    "planning.sikkim.gov.in",
    "planning.telangana.gov.in",
    "planning.tripura.gov.in",
    "planning.wb.gov.in",
    "police.assam.gov.in",
    "police.bihar.gov.in",
    "police.gujarat.gov.in",
    "police.mizoram.gov.in",
    "police.nagaland.gov.in",
    "police.odisha.gov.in",
    "police.rajasthan.gov.in",
    "police.sikkim.gov.in",
    "police.tn.gov.in",
    "police.tripura.gov.in",
    "police.wb.gov.in",
    "pwd.arunachal.gov.in",
    "pwd.delhi.gov.in",
    "pwd.goa.gov.in",
    "pwd.kerala.gov.in",
    "pwd.maharashtra.gov.in",
    "pwd.mizoram.gov.in",
    "pwd.punjab.gov.in",
    "pwd.rajasthan.gov.in",
    "pwd.tn.gov.in",
    "pwd.tripura.gov.in",
    "pwd.uk.gov.in",
    "pwd.wb.gov.in",
    "revenue.chd.gov.in",
    "revenue.delhi.gov.in",
    "revenue.karnataka.gov.in",
    "revenue.kerala.gov.in",
    "revenue.mizoram.gov.in",
    "revenue.mp.gov.in",
    "revenue.odisha.gov.in",
    "revenue.punjab.gov.in",
    "revenue.tripura.gov.in",
    "revenue.up.gov.in",
    "rural.assam.gov.in",
    "rural.hp.gov.in",
    "rural.mizoram.gov.in",
    "rural.tn.gov.in",
    "rural.tripura.gov.in",
    "rural.up.gov.in",
    "science.mizoram.gov.in",
    "science.odisha.gov.in",
    "socialwelfare.assam.gov.in",
    "socialwelfare.delhi.gov.in",
    "socialwelfare.goa.gov.in",
    "socialwelfare.jharkhand.gov.in",
    "socialwelfare.jk.gov.in",
    "socialwelfare.maharashtra.gov.in",
    "socialwelfare.mizoram.gov.in",
    "socialwelfare.sikkim.gov.in",
    "socialwelfare.tripura.gov.in",
    "socialwelfare.uk.gov.in",
    "sports.ap.gov.in",
    "sports.arunachal.gov.in",
    "sports.assam.gov.in",
    "sports.bihar.gov.in",
    "sports.jharkhand.gov.in",
    "sports.maharashtra.gov.in",
    "sports.mizoram.gov.in",
    "sports.odisha.gov.in",
    "sports.punjab.gov.in",
    "sports.rajasthan.gov.in",
    "sports.uk.gov.in",
    "technicaleducation.mizoram.gov.in",
    "tourism.ap.gov.in",
    "tourism.assam.gov.in",
    "tourism.bihar.gov.in",
    "tourism.cgstate.gov.in",
    "tourism.delhi.gov.in",
    "tourism.gujarat.gov.in",
    "tourism.jharkhand.gov.in",
    "tourism.jk.gov.in",
    "tourism.karnataka.gov.in",
    "tourism.mizoram.gov.in",
    "tourism.mp.gov.in",
    "tourism.nagaland.gov.in",
    "tourism.rajasthan.gov.in",
    "tourism.telangana.gov.in",
    "tourism.tripura.gov.in",
    "transport.assam.gov.in",
    "transport.delhi.gov.in",
    "transport.jharkhand.gov.in",
    "transport.jk.gov.in",
    "transport.karnataka.gov.in",
    "transport.maharashtra.gov.in",
    "transport.mizoram.gov.in",
    "transport.mp.gov.in",
    "transport.punjab.gov.in",
    "transport.rajasthan.gov.in",
    "transport.telangana.gov.in",
    "transport.tripura.gov.in",
    "transport.uk.gov.in",
    "transport.wb.gov.in",
    "tribal.gujarat.gov.in",
    "tribal.hp.gov.in",
    "tribal.maharashtra.gov.in",
    "tribal.mizoram.gov.in",
    "tribal.mp.gov.in",
    "urban.goa.gov.in",
    "urban.maharashtra.gov.in",
    "urban.mizoram.gov.in",
    "urban.odisha.gov.in",
    "urban.rajasthan.gov.in",
    "water.karnataka.gov.in",
    "water.maharashtra.gov.in",
    "water.mizoram.gov.in",
    "water.rajasthan.gov.in",
    "welfare.kerala.gov.in",
    "welfare.mizoram.gov.in",
    "welfare.punjab.gov.in",
    "wrd.bihar.gov.in",
    "wrd.jharkhand.gov.in",
    "wrd.maharashtra.gov.in",
    "wrd.mizoram.gov.in",
    "wrd.mp.gov.in",
    "wrd.nagaland.gov.in",
    "wrd.punjab.gov.in",
    "wrd.tn.gov.in",
}

_DISTRICTS = [
    # UP
    "lucknow", "kanpur", "varanasi", "allahabad", "agra", "meerut", "ghaziabad", "bareilly", "aligarh", "moradabad", 
    "saharanpur", "gorakhpur", "jhansi", "muzaffarnagar", "mathura", "ayodhya", "mirzapur", "firozabad", "raebareli", 
    "sitapur", "hardoi", "lakhimpur", "barabanki", "unnao", "sultanpur", "amethi", "bahraich", "shravasti", "balrampur", 
    "gonda", "basti", "amroha", "bijnor", "rampur", "sambhal", "pilibhit", "shahjahanpur", "kanpurdehat", "farrukhabad", 
    "kannauj", "etawah", "auraiya", "jalaun", "hamirpur", "mahoba", "banda", "chitrakoot", "fatehpur", "pratapgarh", 
    "kaushambi", "jaunpur", "ghazipur", "chandauli", "ballia", "mau", "deoria", "kushinagar", "maharajganj", "bhadohi", 
    "sonbhadra", "lalitpur", "hapur", "shamli", "baghpat", "bulandshahr", "kasganj", "hathras", "etah", "mainpuri", "azamgarh",
    # Maharashtra
    "mumbai", "thane", "pune", "nagpur", "nashik", "aurangabad", "solapur", "amravati", "kolhapur", "sangli", "satara", 
    "jalgaon", "dhule", "chandrapur", "latur", "akola", "parbhani", "buldhana", "yavatmal", "wardha", "bhandara", "gondia", 
    "gadchiroli", "hingoli", "osmanabad", "beed", "nandurbar", "ratnagiri", "sindhudurg", "raigad", "palghar", "nanded", 
    "jalna", "washim",
    # Bihar
    "patna", "gaya", "muzaffarpur", "bhagalpur", "darbhanga", "purnia", "arrah", "begusarai", "katihar", "munger", 
    "chhapra", "saharsa", "sasaram", "hajipur", "siwan", "motihari", "bettiah", "jehanabad", "nawada", "nalanda", 
    "buxar", "rohtas", "bhojpur", "vaishali", "saran", "samastipur", "madhubani", "sitamarhi", "sheohar", "araria", 
    "kishanganj", "supaul", "madhepura", "khagaria", "jamui", "lakhisarai", "sheikhpura", "banka", "arwal",
    # Gujarat
    "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar", "junagadh", "gandhinagar", "nadiad", "morbi", 
    "surendranagar", "gandhidham", "veraval", "navsari", "bharuch", "anand", "porbandar", "godhra", "patan", "dahod", 
    "amreli", "valsad", "vapi", "mehsana", "palanpur", "vyara", "ahwa", "himatnagar", "modasa", "chhotaudepur", "botad",
    # Rajasthan
    "jaipur", "jodhpur", "kota", "bikaner", "ajmer", "udaipur", "bhilwara", "alwar", "sikar", "sriganganagar", "pali", 
    "hanumangarh", "tonk", "baran", "bundi", "churu", "dholpur", "jaisalmer", "jalore", "jhalawar", "jhunjhunu", "karauli", 
    "nagaur", "pratapgarh", "rajsamand", "sawaimadhopur", "sirohi",
    # MP
    "bhopal", "indore", "jabalpur", "gwalior", "ujjain", "sagar", "dewas", "satna", "ratlam", "rewa", "murwara", "singrauli", 
    "burhanpur", "khandwa", "bhind", "chhindwara", "guna", "shivpuri", "vidisha", "chhatarpur", "damoh", "mandsaur", 
    "khargone", "neemuch", "hoshangabad", "itarsi", "sehore", "betul", "seoni", "balaghat", "mandla", "dindori", "shahdol", 
    "anuppur", "umaria", "sidhi", "jhabua", "alirajpur", "dhar", "barwani", "shajapur", "agar-malwa", "rajgarh", "sheopur", 
    "morena", "datia", "tikamgarh", "niwari", "panna", "katni", "narsinghpur", "harda", "raisen",
    # Andhra
    "visakhapatnam", "vijayawada", "guntur", "nellore", "kurnool", "kakinada", "kadapa", "tirupati", "anantapur", 
    "eluru", "ongole", "nandyal", "machilipatnam", "adoni", "tenali", "proddatur", "chittoor", "hindupur", "bhimavaram", 
    "madanapalle", "guntakal", "srikakulam", "vizianagaram", "amalapuram", "parvathipuram",
    # Telangana
    "hyderabad", "warangal", "nizamabad", "karimnagar", "khammam", "ramagundam", "mahabubnagar", "nalgonda", "adilabad", 
    "suryapet", "miryalaguda", "jagtial", "mancherial", "kothagudem", "siricilla", "kamareddy", "siddipet", "wanaparthy", 
    "gadwal", "narayanpet", "bhupalpally", "mulugu",
    # Tamil Nadu
    "chennai", "coimbatore", "madurai", "tiruchirappalli", "tiruppur", "salem", "erode", "vellore", "thoothukudi", 
    "dindigul", "thanjavur", "ranipet", "sivakasi", "karur", "udagamandalam", "nagercoil", "kanchipuram", "tiruvannamalai", 
    "cuddalore", "dharmapuri", "krishnagiri", "namakkal", "nilgiris", "perambalur", "pudukkottai", "ramanathapuram", 
    "sivaganga", "theni", "thiruvallur", "thiruvarur", "tirunelveli", "tenkasi", "tirupathur", "villupuram", "virudhunagar",
    # Karnataka
    "bengaluru", "mysuru", "hubballi", "dharwad", "mangaluru", "belagavi", "kalaburagi", "davanagere", "ballari", 
    "vijayapura", "shivamogga", "tumakuru", "raichur", "bidar", "hospet", "hassan", "gadag", "bagalkot", "kolar", 
    "mandya", "chikmagalur", "chitradurga", "haveri", "yadgir", "ramanagara", "chamarajanagar", "udupi", "kodagu", 
    "karwar", "koppal", "chikkaballapur",
    # Kerala
    "thiruvananthapuram", "kochi", "kozhikode", "kollam", "thrissur", "alappuzha", "palakkad", "kannur", "kottayam", 
    "kasaragod", "pathanamthitta", "idukki", "wayanad", "malappuram",
    # West Bengal
    "kolkata", "howrah", "darjeeling", "kalimpong", "jalpaiguri", "alipurduar", "coochbehar", "malda", "murshidabad", 
    "nadia", "purulia", "bankura", "birbhum", "hooghly", "midnapore", "kharagpur", "asansol", "durgapur", "siliguri", 
    "bardhaman", "jhargram", "purvamedinipur", "paschimmedinipur",
    # Punjab
    "ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali", "pathankot", "hoshiarpur", "batala", "moga", 
    "phagwara", "firozpur", "muktsar", "barnala", "faridkot", "gurdaspur", "kapurthala", "mansa", "rupnagar", "sangrur", 
    "tarntaran", "fazilka", "malerkotla",
    # Haryana
    "gurugram", "faridabad", "panipat", "ambala", "yamunanagar", "rohtak", "hisar", "karnal", "sonipat", "panchkula", 
    "sirsa", "bhiwani", "bahadurgarh", "jind", "kaithal", "rewari", "palwal", "nuh", "fatehabad", "mahendragarh", 
    "charkhidadri", "jhajjar",
    # Odisha
    "khordha", "cuttack", "ganjam", "bhadrak", "balasore", "mayurbhanj", "puri", "sambalpur", "rourkela", "sundargarh", 
    "bolangir", "koraput", "rayagada", "kalahandi", "nawarangpur", "malkangiri", "kendrapada", "jajpur", "jagatsinghpur", 
    "dhenkanal", "angul", "keonjhar", "nayagarh", "boudh", "subarnapur", "bargarh", "jharsuguda", "deogarh", "nuapada", "gajapati",
    # J&K and North-East
    "anantnag", "bandipora", "baramulla", "budgam", "doda", "ganderbal", "kathua", "kishtwar", "kulgam", "kupwara", 
    "poonch", "pulwama", "ramban", "reasi", "samba", "shopian", "udhampur", "northgoa", "southgoa", "dhalai", "gomati", 
    "khowai", "northtripura", "sepahijala", "southtripura", "unakoti", "westtripura", "bishnupur", "chandel", "churachandpur", 
    "imphaleast", "imphalwest", "jiribam", "kakching", "kamjong", "kangpokpi", "noney", "pherzawl", "senapati", "tamenglong", 
    "tengnoupal", "thoubal", "ukhrul", "eastgarohills", "eastjaintiahills", "eastkhasihills", "northgarohills", "ribhoi", 
    "southgarohills", "southwestgarohills", "southwestkhasihills", "westgarohills", "westjaintiahills", "westkhasihills", 
    "aizawl", "champhai", "kolasib", "lawngtlai", "lunglei", "mamit", "saiha", "serchhip", "hnahthial", "khawzawl", "saitual",
    "chumuoukedima", "dimapur", "kiphire", "kohima", "longleng", "mokokchung", "mon", "niuland", "noklak", "peren", "phek", 
    "shamator", "tseminyu", "tuensang", "wokha", "zunheboto", "gangtok", "gyalshing", "mangan", "namchi", "soreng", "pakyong",
    "tawang", "westkameng", "eastkameng", "papumpare", "kurungkumey", "kraadaadi", "lowersubansiri", "uppersubansiri", 
    "westsiang", "eastsiang", "siang", "uppersiang", "lowersiang", "lowerdibangvalley", "dibangvalley", "anjaw", "lohit", 
    "namsai", "changlang", "tirap", "longding", "kamle", "leparada"
]

_MUNICIPALITIES = [
    "mcgm", "pmc", "nmmc", "kdmc", "mbmc", "vvcmc", "ulhasnagar", "bnmc", "smc_gj", "amc_gj", 
    "vmc_gj", "rmc_gj", "jmc_rj", "jo_mc", "kmc_wb", "hmc_wb", "mcshimla", "mcg", "mcf", "mcc_ka", 
    "bmrda", "hmrda", "cmda", "ghmc", "gvmc", "vuda", "vada", "kda", "jda", "uda", "ada", "gda", 
    "udaipurmc", "kotamc", "bikanermc", "ajmermc", "bhilwaramc", "alwarmc", "sikarmc", "pnbmc", 
    "dharmc", "gwalior-mc", "bhopal-mc", "indore-mc", "jabalpur-mc", "sagar-mc", "satna-mc", "rewa-mc"
]

# Central PSUs
_PSU_DOMAINS = [
    "gail.co.in", "gailonline.com", "oil-india.com", "nalcoindia.com", "mazagondock.in",
    "bhel.com", "ongcindia.com", "sail.co.in", "ntpc.co.in", "powergrid.in", "iocl.com",
    "coalindia.in", "railtel.in", "becil.com", "sidbi.in", "sjvn.co.in", "tcil.net.in",
    "dic.gov.in", "npcilcareers.co.in", "rites.com", "dfccil.com", "bpcl.in", "pfcindia.com",
    "recl.co.in", "itiltd.in", "celindia.co.in", "nhpcindia.com", "grid-india.in",
    "hindustanpetroleum.com", "irctc.com", "concorindia.co.in", "engineersindia.com",
    "hzlindia.com", "hzl.co.in", "balcoindia.com", "rinl.co.in",
    "meconlimited.co.in", "hecltd.com", "kioclltd.in", "midhani-india.in", "bdl-india.in",
    "grse.in", "goashipyard.co.in", "hsl.gov.in", "cochinshipyard.in", "hmtindia.com",
    "nmdc.co.in", "nationalfertilizers.com", "rcfltd.com", "fact.co.in", "mfl.co.in"
]

# Public Banks, Insurance companies, and Regional Rural Banks
_BANK_DOMAINS = [
    "sbi.co.in", "pnbindia.in", "bankofbaroda.in", "canarabank.com", "unionbankofindia.co.in",
    "indianbank.in", "mahabank.in", "indianoverseasbank.in", "ucobank.com", "bankofindia.co.in",
    "centralbankofindia.co.in", "psbindia.com", "rbi.org.in", "sebi.gov.in", "nabard.org",
    "nhb.org.in", "eximbankindia.in", "ecgc.in", "ibps.in", "licindia.in", "gicofindia.com",
    "nia.co.in", "nationalinsurance.nic.in", "orientalinsurance.org.in", "newindia.co.in",
    # Regional Rural Banks (RRBs)
    "apgbank.in", "apgvbank.in", "agb.co.in", "aryavartbank-rrb.com", "bgvb.in", "brkgb.com",
    "cgrgb.co.in", "karnatakagraminbank.com", "kvgbank.co.in", "keralagbank.co.in", "mgbgrameen.in",
    "mpgb.co.in", "meghalayagraminbank.co.in", "mizoramruralbank.co.in", "nagalandruralbank.co.in",
    "ogb.co.in", "pgb.org.in", "sgbrrb.org", "utkalgrameenbank.co.in", "ubgb.in", "pbgb.org.in",
    "prathamaupbank.com", "supgrrb.com"
]

# Academic & Research Suffixes (IITs, NITs, IIITs, Universities)
_ACADEMIC_SEEDS = [
    # IITs
    "iitb.ac.in", "iitd.ac.in", "iitkgp.ac.in", "iitm.ac.in", "iitk.ac.in", "iitr.ac.in",
    "iitg.ac.in", "iith.ac.in", "iitbhu.ac.in", "iitism.ac.in", "iitindore.ac.in",
    "iitmandi.ac.in", "iitrpr.ac.in", "iitgn.ac.in", "iitp.ac.in", "iitj.ac.in",
    "iitbbs.ac.in", "iitpkd.ac.in", "iittp.ac.in", "iitjammu.ac.in", "iitdh.ac.in",
    "iitgoa.ac.in", "iitbhilai.ac.in",
    # NITs
    "nitrkl.ac.in", "nitk.ac.in", "nits.ac.in", "nitc.ac.in", "nitw.ac.in", "nitt.edu",
    "nitp.ac.in", "nitj.ac.in", "nitkkr.ac.in", "nitdgp.ac.in", "nitsri.ac.in",
    "nitmanipur.ac.in", "nitm.ac.in", "nitmz.ac.in", "nitnagaland.ac.in",
    "nitsikkim.ac.in", "nitpy.ac.in", "nitgoa.ac.in", "nitdelhi.ac.in", "nith.ac.in",
    "nitrr.ac.in", "nitjsr.ac.in", "nituk.ac.in",
    # IIITs
    "iiitd.ac.in", "iiitb.ac.in", "iiitm.ac.in", "iiitg.ac.in", "iiith.ac.in", "iiitk.ac.in",
    "iiitl.ac.in", "iiitp.ac.in", "iiits.ac.in", "iiitvadodara.ac.in", "iiitkottayam.ac.in",
    "iiitdharwad.ac.in", "iiitkalyani.ac.in", "iiituna.ac.in", "iiitranchi.ac.in",
    "iiitnagpur.ac.in", "iiitbhagalpur.ac.in", "iiitbhopal.ac.in", "iiitsurat.ac.in",
    # Universities
    "du.ac.in", "jnu.ac.in", "bhu.ac.in", "uohyd.ac.in", "amu.ac.in", "jmi.ac.in",
    "curaj.ac.in", "tezu.ernet.in", "iisc.ac.in", "tifr.res.in", "csir.res.in",
    "manipal.edu", "bits-pilani.ac.in", "annauniv.edu", "vtu.ac.in", "jntu.ac.in",
    "caluniv.ac.in", "mu.ac.in", "unom.ac.in", "unipune.ac.in"
]

# Key Ministries, Central Agencies, and Research Labs
_MINISTRIES_LABS = [
    "meity.gov.in", "education.gov.in", "mod.gov.in", "finmin.gov.in", "mha.gov.in",
    "indianrailways.gov.in", "isro.gov.in", "drdo.gov.in", "barc.gov.in", "dae.gov.in",
    "dst.gov.in", "dbtindia.gov.in", "csir.res.in", "icmr.gov.in", "icar.org.in",
    "sac.isro.gov.in", "vssc.gov.in", "ursc.gov.in", "sdsc.gov.in", "iprc.gov.in",
    "iist.ac.in", "nrsc.gov.in", "iirs.gov.in", "prl.res.in", "narl.gov.in",
    "neist.res.in", "iict.res.in", "ncl-india.org", "nplindia.org", "ccmb.res.in",
    "cdri.res.in", "iiim.res.in", "ihbt.res.in", "imtech.res.in", "nio.org",
    "ngri.res.in", "neeri.res.in", "cgcri.org", "cecri.res.in", "clri.org"
]

def generate_domains():
    """
    Generates a registry of 2,300+ target domains with official domain mappings
    and fallback strategies to guarantee near-100% DNS resolution.
    """
    domains = {}

    # 1. State level portals (PSC, SSB, Police, Gov)
    for code in _STATE_CODES:
        base_domain = STATE_DOMAINS[code]
        
        domains[f"{code}_gov"] = {
            "name": f"{code.upper()} Government Portal",
            "url": f"https://{base_domain}"
        }
        domains[f"{code}psc"] = {
            "name": f"{code.upper()} PSC (State Commission)",
            "url": f"https://{STATE_PSC_DOMAINS[code]}"
        }
        domains[f"{code}ssc"] = {
            "name": f"{code.upper()} Staff Selection Board",
            "url": f"https://{STATE_SSB_DOMAINS[code]}"
        }
        domains[f"police_{code}"] = {
            "name": f"{code.upper()} Police Recruitment",
            "url": f"https://{STATE_POLICE_DOMAINS[code]}"
        }

    # 2. State departments subdomains (combining states * depts)
    for code in _STATE_CODES:
        for dept in _DEPARTMENTS:
            key = f"{code}_{dept}"
            base_domain = STATE_DOMAINS[code]
            subdomain = f"{dept}.{base_domain}"
            if subdomain in WORKING_DEPTS:
                url = f"https://{subdomain}"
            else:
                # Fallback to resolvable official base state domain
                url = f"https://{base_domain}"
            domains[key] = {
                "name": f"{code.upper()} {dept.title()} Department",
                "url": url
            }

    # 3. Districts (NIC Portals)
    for dist in _DISTRICTS:
        key = f"dist_{dist}"
        domains[key] = {
            "name": f"{dist.title()} District Portal",
            "url": f"https://{dist}.nic.in"
        }

    # 4. Municipal Corporations
    for muni in _MUNICIPALITIES:
        key = f"muni_{muni}"
        url = f"https://{MUNI_DOMAINS[muni]}" if muni in MUNI_DOMAINS else f"https://www.{muni}.org"
        domains[key] = {
            "name": f"{muni.upper().replace('_', ' ')} Municipal Corporation",
            "url": url
        }

    # 5. PSUs
    for dom in _PSU_DOMAINS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Central PSU)",
            "url": f"https://www.{dom}"
        }

    # 6. State PSUs (rtc, transco, genco)
    for code in _STATE_CODES:
        base_domain = STATE_DOMAINS[code]
        # For RTC, use official mapped domain
        rtc_url = f"https://{STATE_RTC_DOMAINS[code]}" if code in STATE_RTC_DOMAINS else f"https://{base_domain}"
        
        domains[f"{code}_rtc"] = {
            "name": f"{code.upper()} Road Transport Corp (State PSU)",
            "url": rtc_url
        }
        # For transco/genco, fallback to base domain as most do not have dedicated subdomains
        domains[f"{code}_transco"] = {
            "name": f"{code.upper()} Transmission Corp (State PSU)",
            "url": f"https://{base_domain}"
        }
        domains[f"{code}_genco"] = {
            "name": f"{code.upper()} Power Generation Corp (State PSU)",
            "url": f"https://{base_domain}"
        }

    # 7. Banks
    for dom in _BANK_DOMAINS:
        key = dom.split(".")[0]
        domains[f"bank_{key}"] = {
            "name": f"{key.upper()} (Public Sector Banking/Insurance)",
            "url": f"https://www.{dom}"
        }

    # 8. Academic
    for dom in _ACADEMIC_SEEDS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Elite Academic/Research)",
            "url": f"https://www.{dom}"
        }

    # 9. Ministries & Labs
    for dom in _MINISTRIES_LABS:
        key = dom.split(".")[0]
        domains[f"lab_{key}"] = {
            "name": f"{key.upper()} (Ministry/Research Lab)",
            "url": f"https://www.{dom}"
        }

    return domains

# Keywords to identify career pages on homepages
_CAREER_LINKS_RE = re.compile(
    r"career|recruit|vacancy|opening|advertisement|advt|job|work.?with",
    re.IGNORECASE
)

def resolve_career_url(homepage_url, session=None):
    """
    Fetches the domain homepage and dynamically resolves its career page URL.
    Returns the resolved URL, falling back to homepage if none found.
    """
    if session is None:
        session = requests.Session()

    try:
        r = session.get(homepage_url, headers=DEFAULT_HEADERS, timeout=10, verify=False)
        if r.status_code != 200:
            return homepage_url
    except Exception:
        # Fall back to HTTP if HTTPS fails or DNS error
        if homepage_url.startswith("https://"):
            return resolve_career_url(homepage_url.replace("https://", "http://"), session)
        return homepage_url

    soup = BeautifulSoup(r.text, "html.parser")
    best_url = homepage_url
    best_score = 0

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href == "#":
            continue

        text = a.get_text().strip()
        score = 0

        # Score matching links
        if _CAREER_LINKS_RE.search(href):
            score += 40
        if _CAREER_LINKS_RE.search(text):
            score += 50
        if "pdf" in href.lower():
            score -= 10  # prefer landing page over direct PDF

        if score > best_score:
            best_score = score
            best_url = urljoin(homepage_url, href)

    # Dedup slash
    return best_url.rstrip("/")
