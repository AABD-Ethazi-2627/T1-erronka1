
# CNC Guard - Hutsegiteen ereduaren entrenamendua

Random Forest bat entrenatzen dugu, CNC makina batek 6 sentsore irakurketatik aurrera huts egingo duen iragartzen duena. 0,15eko atalasearekin, balidazioko 54 akatsetatik 48 detektatzen ditu (recall 0,89), eta kalkulatutako kostua 55.800 €-tan uzten du; eredurik gabe, berriz, 270.000 €-tan.


## Barne egitura
```text
T1-erronka1/
├── 
│   
├── notebooks/
│   └── 02_training_ML.ipynb        # Modeloaren entrenamendua
├── models/
│   ├── cnc_failure_model.pkl       # Model producction (pipeline sklearn osoa)
│   └── backups/                    # Modeloaren aurreko bertsioak
|
├── scoring/                        # Prediction API  (FastAPI)
│   ├── cnc_ml/                     # notebook eta API artean partekatutako ML-a
│   │   ├── columns.py              # Datu-multzoen zutabe izenak
│   │   ├── features.py             # Feature engineering. Hutsegite-mota bakoitzaren arrazoi fisikoan oinarrituta:
│   │   └── pipeline.py             # sklearn Pipeline osoa: feature engineering + kodeketa + eredua.
│   ├── app/


```
## Random Forest modeloa aukeratzeko justifikazioa

Random Forest eredua aukeratu dugu, CNC makinen sentsoreetatik jasotako datuak aztertzeko eta hutsegiteekin lotutako patroiak identifikatzeko gai delako.

Eredu honek erabaki-zuhaitz asko konbinatzen ditu, eta horri esker, hainbat aldagairen arteko erlazioak azter ditzake (tenperatura, bibrazioa...), guretzako hori oso garrantzitsua da mekinen hutsetigeK ez direlako beti aldagai bakar baten ondorioz izaten. Random Forest ereduak datu historikoetatik ikas dezake, baldin eta datu horiek behar bezala etiketatuta badaude. Horrela, aurretik gertatutako hutsegiteak eta funtzionamendu normaleko egoerak erabil ditzake ereduak egoera berriak sailkatzeko. Horrez gain, erlazio konplexuak ikasten ditu, hutsegiteak identifikatzeko, aldagaien arteko erlazio ez-linealak ikasi ditzake.


