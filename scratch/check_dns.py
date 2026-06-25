import socket
import urllib.request
import json

domains_to_test = [
    # Godhra (Panchmahal)
    "panchmahal.nic.in", "panchmahals.nic.in",
    # Kanpur
    "kanpur.nic.in", "kanpurnagar.nic.in", "kanpurdehat.nic.in",
    # Machilipatnam
    "machilipatnam.nic.in", "krishna.ap.gov.in",
    # Madanapalle
    "madanapalle.nic.in", "chittoor.ap.gov.in", "annamayya.ap.gov.in",
    # Mangaluru
    "mangaluru.nic.in", "dk.nic.in", "dakshinahannada.nic.in", "dakshinakannada.nic.in",
    # Miryalaguda
    "miryalaguda.nic.in", "nalgonda.telangana.gov.in",
    # Modasa
    "modasa.nic.in", "aravalli.gujarat.gov.in", "aravalli.nic.in",
    # Mohali
    "mohali.nic.in", "sasnagar.gov.in", "sasnagar.nic.in",
    # Motihari
    "motihari.nic.in", "eastchamparan.nic.in",
    # Mumbai
    "mumbai.nic.in", "mumbai.gov.in", "mumbaisuburban.gov.in",
    # Murwara
    "murwara.nic.in", "katni.nic.in",
    # Nadiad
    "nadiad.nic.in", "kheda.nic.in",
    # Nagercoil
    "nagercoil.nic.in", "kanniyakumari.nic.in", "kanyakumari.nic.in",
    # Nawarangpur
    "nawarangpur.nic.in", "nabarangpur.nic.in",
    # Nellore
    "nellore.nic.in", "spsnellore.ap.gov.in",
    # Ongole
    "ongole.nic.in", "prakasam.ap.gov.in",
    # Pakyong
    "pakyong.nic.in", "pakyongdistrict.nic.in",
    # Palanpur
    "palanpur.nic.in", "banaskantha.nic.in",
    # Parvathipuram
    "parvathipuram.nic.in", "parvathipurammanyam.ap.gov.in",
    # Peren
    "peren.nic.in", "peren-dist.nagaland.gov.in",
    # Phagwara
    "phagwara.nic.in", "kapurthala.gov.in", "kapurthala.nic.in",
    # Proddatur
    "proddatur.nic.in", "kadapa.ap.gov.in", "ysrkadapa.ap.gov.in",
    # Purnia
    "purnia.nic.in", "purnea.nic.in",
    # Ramagundam
    "ramagundam.nic.in", "peddapalli.telangana.gov.in",
    # Rourkela
    "rourkela.nic.in", "sundargarh.nic.in", "sundargarh.gov.in",
    # Sasaram
    "sasaram.nic.in", "rohtas.nic.in",
    # Tumakuru
    "tumakuru.nic.in", "tumkur.nic.in",
    # Academic/RTC/Muni
    "nitdgp.ac.in", "www.nitdgp.ac.in",
    "punjabroadways.gov.in", "punjabroadways.in",
    "rsrtc.rajasthan.gov.in", "rsrtconline.rajasthan.gov.in",
    "rewamunicipal.com", "rewamunicipalcorporation.com", "rewa.nic.in",
    "sagarmunicipal.com", "sagar.nic.in",
    "satnamunicipal.com", "satna.nic.in",
    "sikarmc.org", "sikar.rajasthan.gov.in",
    # Delhi Education & TN WRONG_VERSION_NUMBER targets
    "www.edudel.nic.in", "www.tn.gov.in"
]

def resolve(host):
    try:
        ips = socket.gethostbyname(host)
        return ips
    except Exception as e:
        return f"Fail: {e}"

for host in domains_to_test:
    res = resolve(host)
    print(f"{host:<40} -> {res}")
