import socket

domains_to_test = [
    'kendrapada.odisha.gov.in',
    'kendrapara.odisha.gov.in',
    'kendrapara.nic.in',
    'keonjhar.odisha.gov.in',
    'khordha.odisha.gov.in',
    'khurda.nic.in',
    'khurda.odisha.gov.in',
    'koraput.odisha.gov.in',
    'kalimpong.nic.in',
    'kalimpong.gov.in',
    'kalimpongdistrict.in',
    'kanchipuram.nic.in',
    'kanchipuram.gov.in',
    'kanpur.nic.in',
    'kanpur.gov.in',
    'kanpurnagar.nic.in',
    'karwar.nic.in',
    'karwar.gov.in',
    'uttarakannada.nic.in',
    'kasaragod.nic.in',
    'kasaragod.gov.in',
    'kasargod.nic.in',
    'kolkata.nic.in',
    'kolkata.gov.in',
    'kolkata.wb.gov.in',
    'kolkatadistrict.gov.in'
]

print(f"{'Domain':<35} | {'Resolves':<10} | {'IP':<15}")
print("-" * 70)

for dom in domains_to_test:
    try:
        ip = socket.gethostbyname(dom)
        print(f"{dom:<35} | True       | {ip}")
    except Exception as e:
        print(f"{dom:<35} | False      | {str(e)[:25]}")
