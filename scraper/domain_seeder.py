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
    "an": "andamannicobar.gov.in",
    "ap": "ap.gov.in",
    "ar": "arunachalpradesh.gov.in",
    "as": "assam.gov.in",
    "br": "state.bihar.gov.in",
    "ch": "chandigarh.gov.in",
    "cg": "cgstate.gov.in",
    "dn": "dnh.gov.in",
    "dd": "daman.nic.in",
    "dl": "delhi.gov.in",
    "ga": "goa.gov.in",
    "gj": "gujaratindia.gov.in",
    "hr": "haryana.gov.in",
    "hp": "himachal.gov.in",
    "jk": "jk.nic.in",
    "jh": "jharkhand.gov.in",
    "ka": "karnataka.gov.in",
    "kl": "kerala.nic.in",
    "ld": "lakshadweep.gov.in",
    "mp": "mp.gov.in",
    "mh": "maharashtra.gov.in",
    "mn": "manipur.nic.in",
    "ml": "meghalaya.gov.in",
    "mz": "mizoram.gov.in",
    "nl": "nagaland.gov.in",
    "od": "odisha.gov.in",
    "py": "py.gov.in",
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
    "ch": "chandigarh.gov.in",
    "an": "erecruitment.andamannicobar.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "daman.nic.in",
    "dn": "dnh.gov.in"
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
    "hp": "hppsc.hp.gov.in",
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
    "ch": "chandigarh.gov.in",
    "an": "erecruitment.andamannicobar.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "daman.nic.in",
    "dn": "dnh.gov.in"
}

# Real official State Police recruitment
STATE_POLICE_DOMAINS = {
    "ap": "ap.gov.in",
    "ar": "arunpol.nic.in",
    "as": "assam.gov.in",
    "br": "state.bihar.gov.in",
    "cg": "cgpolice.gov.in",
    "ga": "goa.gov.in",
    "gj": "gujarat.gov.in",
    "hr": "haryana.gov.in",
    "hp": "citizenportal.hppolice.gov.in/citizen",
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
    "ch": "chandigarh.gov.in",
    "an": "police.andamannicobar.gov.in",
    "ld": "lakshadweep.gov.in",
    "dd": "ddpolice.gov.in",
    "dn": "dnh.gov.in"
}

# Real official State RTC (Transport PSU) Domains
STATE_RTC_DOMAINS = {
    "ap": "apsrtc.ap.gov.in",
    "ar": "arunachalpradesh.gov.in",
    "as": "astc.assam.gov.in",
    "br": "bsrtc.bihar.gov.in",
    "ch": "chdtransport.gov.in",
    "cg": "cgtransport.gov.in",
    "dn": "dnh.gov.in",
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
    "wb": "wbtconline.in"
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
    "bnmc": "bncmc.gov.in",
    "smc_gj": "suratmunicipal.gov.in",
    "amc_gj": "ahmedabadcity.gov.in",
    "vmc_gj": "vmc.gov.in",
    "rmc_gj": "rmc.gov.in",
    "jmc_rj": "jaipurmc.org",
    "jo_mc": "jodhpurmc.org",
    "kmc_wb": "www.kmcgov.in",
    "hmc_wb": "myhmc.in",
    "mcshimla": "shimlamc.hp.gov.in",
    "mcg": "mcg.gov.in",
    "mcf": "www.mcf.gov.in",
    "mcc_ka": "mysurucity.mrc.gov.in",
    "bmrda": "bmrda.karnataka.gov.in",
    "hmrda": "hmda.gov.in",
    "cmda": "cmdachennai.gov.in",
    "ghmc": "ghmc.gov.in",
    "gvmc": "gvmc.ap.gov.in",
    "vuda": "vuda.gov.in",
    "vada": "vada.gov.in",
    "kda": "kdaindia.co.in",
    "jda": "jda.rajasthan.gov.in",
    "uda": "udajodhpur.org",
    "ada": "adaamritsar.gov.in",
    "gda": "gdaghaziabad.in",
    "udaipurmc": "udaipurmc.org",
    "kotamc": "urban.rajasthan.gov.in",
    "bikanermc": "bikanermc.org",
    "ajmermc": "ajmermc.org",
    "bhilwaramc": "bhilwara.rajasthan.gov.in",
    "alwarmc": "alwar.rajasthan.gov.in",
    "sikarmc": "sikarmc.org",
    "pnbmc": "punjab.gov.in",
    "dharmc": "dhar.nic.in",
    "gwalior-mc": "gwalior.nic.in",
    "bhopal-mc": "bhopalmunicipal.com",
    "indore-mc": "imcindore.org",
    "jabalpur-mc": "jabalpur.nic.in",
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
    "www.gail.co.in", "www.gailonline.com", "www.oil-india.com", "www.nalcoindia.com", "www.mazagondock.in",
    "www.bhel.com", "www.ongcindia.com", "www.sail.co.in", "www.ntpc.co.in", "www.powergrid.in", "www.iocl.com",
    "www.coalindia.in", "www.railtel.in", "www.becil.com", "www.sidbi.in", "www.sjvn.co.in", "www.tcil.net.in",
    "www.dic.gov.in", "www.npcilcareers.co.in", "www.rites.com", "dfccil.com", "www.bharatpetroleum.in", "www.pfcindia.com",
    "www.recl.co.in", "www.itiltd.in", "www.celindia.co.in", "www.nhpcindia.com", "www.grid-india.in",
    "www.hindustanpetroleum.com", "www.irctc.com", "www.concorindia.co.in", "www.engineersindia.com",
    "www.hzlindia.com", "www.balcoindia.com", "www.rinl.co.in",
    "www.meconlimited.co.in", "www.hecltd.com", "www.kioclltd.in", "www.midhani-india.in", "www.bdl-india.in",
    "www.grse.in", "www.goashipyard.co.in", "www.hslvizag.in", "www.cochinshipyard.in", "www.hmtindia.com",
    "www.nmdc.co.in", "www.nationalfertilizers.com", "www.rcfltd.com", "www.fact.co.in", "www.mfl.co.in"
]

# Public Banks, Insurance companies, and Regional Rural Banks
_BANK_DOMAINS = [
    "www.sbi.co.in", "www.pnbindia.in", "www.bankofbaroda.in", "www.canarabank.com", "www.unionbankofindia.co.in",
    "www.indianbank.in", "mahabank.in", "www.iob.in", "www.ucobank.com", "www.bankofindia.co.in",
    "www.centralbankofindia.co.in", "www.psbindia.com", "www.rbi.org.in", "www.sebi.gov.in", "www.nabard.org",
    "www.nhb.org.in", "www.eximbankindia.in", "www.ecgc.in", "www.ibps.in", "www.licindia.in", "www.gicre.in",
    "www.niapune.org.in", "nationalinsurance.nic.co.in", "orientalinsurance.org.in", "www.newindia.co.in",
    # Regional Rural Banks (RRBs)
    "apgb.bank.in", "apgvbank.in", "agb.co.in", "aryavartbank-rrb.com", "bgvb.in", "brkgb.com",
    "cgbank.in", "karnatakagraminbank.com", "karnatakagrameenabank.com", "kgb.bank.in",
    "mpgb.bank.in", "meghalayaruralbank.bank.in", "mrb.bank.in", "www.nrb.bank.in",
    "ogb.co.in", "pgb.org.in", "sgbrrb.org", "ubgb.in", "wbgb.bank.in",
    "prathamaupbank.com"
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
    "www.meity.gov.in", "www.education.gov.in", "www.mod.gov.in", "www.finmin.gov.in", "www.mha.gov.in",
    "www.indianrailways.gov.in", "www.isro.gov.in", "www.drdo.gov.in", "www.barc.gov.in", "www.dae.gov.in",
    "www.dst.gov.in", "www.dbtindia.gov.in", "www.csir.res.in", "www.icmr.gov.in", "www.icar.org.in",
    "www.sac.gov.in", "www.vssc.gov.in", "www.ursc.gov.in", "www.shar.gov.in", "www.iprc.gov.in",
    "www.iist.ac.in", "www.nrsc.gov.in", "www.iirs.gov.in", "www.prl.res.in", "www.narl.gov.in",
    "www.neist.res.in", "www.iict.res.in", "www.ncl-india.org", "www.nplindia.org", "www.ccmb.res.in",
    "www.cdri.res.in", "www.iiim.res.in", "www.ihbt.res.in", "www.imtech.res.in", "www.nio.org",
    "www.ngri.res.in", "www.neeri.res.in", "www.cgcri.res.in", "www.cecri.res.in", "www.clri.org"
]

# Overrides for district domains that do not conform to standard {dist}.nic.in
# (due to spelling variations, state subdomain routing, or headquarters names)
DISTRICT_OVERRIDES = {
    # Rajasthan (subdomains of rajasthan.gov.in)
    "alwar": "alwar.rajasthan.gov.in",
    "ajmer": "ajmer.rajasthan.gov.in",
    "jaipur": "jaipur.rajasthan.gov.in",
    "jodhpur": "jodhpur.rajasthan.gov.in",
    "kota": "kota.rajasthan.gov.in",
    "bikaner": "bikaner.rajasthan.gov.in",
    "udaipur": "udaipur.rajasthan.gov.in",
    "bhilwara": "bhilwara.rajasthan.gov.in",
    "sikar": "sikar.rajasthan.gov.in",
    "sriganganagar": "sriganganagar.rajasthan.gov.in",
    "pali": "pali.rajasthan.gov.in",
    "hanumangarh": "hanumangarh.rajasthan.gov.in",
    "tonk": "tonk.rajasthan.gov.in",
    "baran": "baran.rajasthan.gov.in",
    "bundi": "bundi.rajasthan.gov.in",
    "churu": "churu.rajasthan.gov.in",
    "dholpur": "dholpur.rajasthan.gov.in",
    "jaisalmer": "jaisalmer.rajasthan.gov.in",
    "jalore": "jalore.rajasthan.gov.in",
    "jhalawar": "jhalawar.rajasthan.gov.in",
    "jhunjhunu": "jhunjhunu.rajasthan.gov.in",
    "karauli": "karauli.rajasthan.gov.in",
    "nagaur": "nagaur.rajasthan.gov.in",
    "rajsamand": "rajsamand.rajasthan.gov.in",
    "sawaimadhopur": "sawaimadhopur.rajasthan.gov.in",
    "sirohi": "sirohi.rajasthan.gov.in",
    
    # State/Spelling/HQ variations
    "agar-malwa": "agarmalwa.nic.in",
    "ahwa": "dangs.nic.in",
    "arrah": "bhojpur.nic.in",
    "batala": "gurdaspur.nic.in",
    "bengaluru": "bengaluruurban.nic.in",
    "bhimavaram": "westgodavari.ap.gov.in",
    "bolangir": "balangir.odisha.gov.in",
    "bulandshahr": "bulandshahar.nic.in",
    "chamarajanagar": "chamarajanagar.nic.in",
    "chhapra": "saran.nic.in",
    "chikmagalur": "chikkamagaluru.nic.in",
    "chumuoukedima": "chumoukedima.nic.in",
    "deogarh": "deogarh.odisha.gov.in",
    "eluru": "eluru.ap.gov.in",
    "anantapur": "ananthapuramu.ap.gov.in",
    "asansol": "paschimbardhaman.gov.in",
    "durgapur": "paschimbardhaman.gov.in",
    "adoni": "kurnool.ap.gov.in",
    "amalapuram": "eastgodavari.ap.gov.in",
    "alipurduar": "alipurduar.gov.in",
    "gajapati": "gajapati.odisha.gov.in",
    "gandhidham": "kutch.gov.in",
    "gangtok": "gangtok.nic.in",
    "ganjam": "ganjam.nic.in",
    "godhra": "panchmahal.nic.in",
    "guntakal": "ananthapuramu.ap.gov.in",
    "gurugram": "gurugram.gov.in",
    "boudh": "boudh.odisha.gov.in",
    "kapurthala": "kapurthala.gov.in",
    "lowerdibangvalley": "roing.nic.in",
    "khawzawl": "dckhawzawl.mizoram.gov.in",
    "kraadaadi": "kradaadi.nic.in",
    "leparada": "arunachalpradesh.gov.in",
    "lowersiang": "arunachalpradesh.gov.in",
    "hajipur": "vaishali.nic.in",
    "himatnagar": "sabarkantha.nic.in",
    "hindupur": "srisathyasai.ap.gov.in",
    "hnahthial": "hnahthial.mizoram.gov.in",
    "hoshangabad": "narmadapuram.nic.in",
    "hospet": "vijayanagara.nic.in",
    "hubballi": "dharwad.nic.in",
    "itarsi": "narmadapuram.nic.in",

    # Newly Resolved Districts
    "angul": "angul.odisha.gov.in",
    "aurangabad": "aurangabad.gov.in",
    "baghpat": "bagpat.nic.in",
    "bahadurgarh": "jhajjar.nic.in",
    "balasore": "balasore.odisha.gov.in",
    "bandipora": "bandipore.nic.in",
    "bankura": "bankura.gov.in",
    "bargarh": "bargarh.odisha.gov.in",
    "barnala": "barnala.gov.in",
    "bettiah": "westchamparan.nic.in",
    "bhadrak": "bhadrak.odisha.gov.in",
    "bhupalpally": "bhoopalapally.telangana.gov.in",
    "chandrapur": "chandrapur.gov.in",
    "cuttack": "cuttack.odisha.gov.in",
    "dhenkanal": "dhenkanal.odisha.gov.in",
    "eastgarohills": "eastgarohills.gov.in",
    "firozpur": "ferozepur.nic.in"
}

def generate_domains():
    """
    Generates a registry of 2,300+ target domains with official domain mappings
    and fallback strategies to guarantee near-100% DNS resolution.
    """
    # Department overrides for non-standard routing
    dept_overrides = {
        "dl_education": "http://www.edudel.nic.in",
        "up_rural": "https://ruraldevp.up.gov.in/"
    }

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
            if key in dept_overrides:
                url = dept_overrides[key]
            elif subdomain in WORKING_DEPTS:
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
        if dist in DISTRICT_OVERRIDES:
            url = f"https://{DISTRICT_OVERRIDES[dist]}"
        else:
            url = f"https://{dist}.nic.in"
        domains[key] = {
            "name": f"{dist.title()} District Portal",
            "url": url
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
        key = dom.replace("www.", "").split(".")[0]
        if key == "hslvizag":
            key = "hsl"
        domains[key] = {
            "name": f"{key.upper()} (Central PSU)",
            "url": f"https://{dom}"
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
        key = dom.replace("www.", "").split(".")[0]
        domains[f"bank_{key}"] = {
            "name": f"{key.upper()} (Public Sector Banking/Insurance)",
            "url": f"https://{dom}"
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
        key = dom.replace("www.", "").split(".")[0]
        domains[f"lab_{key}"] = {
            "name": f"{key.upper()} (Ministry/Research Lab)",
            "url": f"https://{dom}"
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
    Returns the resolved URL, falling back to homepage if none found or if dead.
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
            http_url = homepage_url.replace("https://", "http://")
            try:
                # Only use HTTP if we can successfully establish a connection to it
                r_http = session.get(http_url, headers=DEFAULT_HEADERS, timeout=5, verify=False)
                if r_http.status_code == 200:
                    return resolve_career_url(http_url, session)
            except Exception:
                pass
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
    resolved_url = best_url.rstrip("/")

    # Verification: If we resolved a different URL than the homepage,
    # verify it is alive (returns HTTP 2xx or 3xx). If not, fallback to homepage.
    if resolved_url != homepage_url:
        try:
            head_r = session.head(resolved_url, headers=DEFAULT_HEADERS, timeout=5, verify=False)
            status = head_r.status_code
            if status >= 400:
                # Some servers return 405 Method Not Allowed or 403 on HEAD, check with GET
                get_r = session.get(resolved_url, headers=DEFAULT_HEADERS, timeout=5, verify=False, stream=True)
                status = get_r.status_code
            if status >= 400:
                return homepage_url
        except Exception:
            return homepage_url

    return resolved_url
