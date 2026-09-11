"""Werkend ketentje voor het doelbeeld directe lozing op een rijkswater.

De architectuur staat in `usecases/lozing.py` en op /lozing; dit pakket laat hem lopen op een
synthetische casus, met live bevraging van de KRW-service van RWS en de bestuurlijke gebieden
van PDOK. De gedeelde kern (objectbibliotheek, LHSO, motor) zit in `usecases/ketenkern`.
"""
