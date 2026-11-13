# Streamlit panelaren hobekuntza-proposamenak

## Segurtasuna eta sendotasuna

4. **API kredentzialak:** tokena `st.session_state`-n gordetzen da, hau da, saio bakoitzeko bat, eta erabiltzaile bakoitzak token berri bat eskatzen du. `@st.cache_resource`-rekin bakarra partekatuko litzateke.
5. **Berrintentuak eta akatsak:** Elasticsearch-erako eta API-rako deiek ez dute berrintentuik. Hutsegite puntual batek `except Exception` batera eramaten du, eta horrek arrazoia ezkutatzen du eta Dashboard-a "Daturik ez" egoeran uzten du. "Elasticsearch erorita" eta "indize hutsa" bereiziko nituzke.
6. **Sarreraren balidazioa:** `machine_id`-k edozein testu onartzen du, hutsik ere bai. Gainera, sentsoreen tarteak kodean finkatuta daude (280–330 K, etab.). Komeni da API-ren eskemarekin bat etortzea, edo endpoint-ari eskatzea.

## Mantentzea

7. **Fitxategi bakarra, 827 lerrokoa, ~380 CSS txertatua:** `styles.css`, `api.py`, `eu.py` eta orri bakoitzeko modulu bat bereiziko nituzke. Horrela probatzeko eta ulertzeko errazagoa da.
8. **Proba eta motarik gabe Streamlit zatian:** datuen logika (multzokatzeak, iragazkiak) erraza da funtzio puruetara ateratzea eta probatzea.
9. **Dockerfile:** Python 3.10 erabiltzen du, euskarriaren amaieratik gertu dagoena. 3.12ra aldatuko nuke, `altair` `requirements.txt`-n finkatuko nuke (orain mendekotasun iragankor gisa sartzen da) eta edukiontzia root ez den erabiltzaile batekin exekutatuko nuke.

## Erabilgarritasuna (UX)

10. **Eguneratze automatikoa:** orain eskuz eguneratzen da botoi batekin. Monitorizazio-panel baterako, `st.fragment(run_every=10)` zentzuzkoagoa da.
11. **Eskuzko iragarpenen historia:** Iragarpenak orriak ez ditu aurreko emaitzak gordetzen ez erakusten. Saioko azken kontsultekin taula bat erabilgarria litzateke.
12. **Hizkuntzen nahasketa:** barne-izenak eta mailak euskaraz daude (KONTUZ, LARRIA, iragarri) eta interfazea gaztelaniaz. Proiektu osoa euskaraz egon behar denez, interfazea euskaraz bateratu behar da.
