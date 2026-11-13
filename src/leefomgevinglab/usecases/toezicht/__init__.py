"""Toezichtsignalen op de Atlas voor een Schone Maas.

Het register van vergunde lozingen (`/waterruimte`, `connectors/smwk_atlas.py`) wordt hier
omgezet in een signaaldossier voor een toezichthouder: niet "is dit een overtreding?" maar
"waar vraagt deze vergunning om een nadere blik?". Dat onderscheid loopt door de hele use-case:
een signaal is afgeleid uit de data, nooit een vaststelling.

`signalen.py` is de deterministische kern: tien regels, elk een gewone Python-functie zonder
netwerk en zonder taalmodel. Latere modules (dossier, graaf, agentrunner, pagina) bouwen daarop
voort, maar de signalen zelf blijven hier -- en blijven uitlegbaar zonder een van die lagen te
starten.
"""
