import socket

domains_to_test = [
    # IITBBS
    "new.iitbbs.ac.in", "iitbbs.ac.in", "www.iitbbs.ac.in",
    # IITM
    "iitm.ac.in", "www.iitm.ac.in",
    # NITS
    "nits.ac.in", "www.nits.ac.in",
    # TEZU
    "tezu.ernet.in", "tezu.ac.in", "www.tezu.ac.in",
    # Udaipur Development Authority / Udaipur MC
    "udajodhpur.org", "uitudaipur.org", "udaipurmc.org", "urban.rajasthan.gov.in",
    # Udagamandalam (Nilgiris)
    "udagamandalam.nic.in", "nilgiris.nic.in", "nilgiris.gov.in",
    # VADA / VUDA / VMRDA
    "vada.gov.in", "vuda.gov.in", "vuda.co.in", "vmrda.gov.in",
    # Vapi (Valsad)
    "vapi.nic.in", "valsad.nic.in",
    # Veraval (Gir Somnath)
    "veraval.nic.in", "girsomnath.nic.in", "gir-somnath.nic.in",
    # Vijayawada (NTR / Krishna)
    "vijayawada.nic.in", "ntr.ap.gov.in", "krishna.ap.gov.in",
    # Villupuram
    "villupuram.nic.in", "viluppuram.nic.in",
    # Vyara (Tapi)
    "vyara.nic.in", "tapi.nic.in",
    # Let's test the main Karnataka domain which timed out
    "karnataka.gov.in", "www.karnataka.gov.in",
    # Haveri
    "haveri.nic.in"
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
