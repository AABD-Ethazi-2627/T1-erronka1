
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

## Zergatik erabili da 0.15 atalasea
FAILURE_THRESHOLD = 0.15 hautatuko da, kostu ekonomiko txikiena duen atalasea baita.  Kostuen taula ofizialaren arabera, detektatu gabeko akats bat (5.000 €) alarma faltsu bat (200 €) baino 25 aldiz garestiagoa da. Horregatik, merezi du alarma faltsu gehiago onartzea, trukean matxura gehiago detektatzen badira. 0,15ekin 54 akatsetatik 48 detektatu genituen
### Kostuen taula ofiziala
Ereduaren emaitza bakoitzak batez besteko kostu bat du:
| Casua | Gertaera | Kostea |
|---|---|---:|
| FN (false negative) |Makina produkzioan hausten da: 3 h × 1.200 €/h + premiazko konponketa eta piezak. | 5.000 € |
| FP (false positive) | Makina geldirik dagoela, 45 minutuko alferrikako azterketa egitea. | 200 € |
| TP (true positive) | Mantentze-lan prebentiboa: hautsi baino lehen aldatzen da pieza. | 300 € |
| TN (true negatie) | Arazorik gabe funtzionatzen du | 0 € |

### Atalaseen konparaketa
0,15eko atalasea da kostu txikiena sortzen duena. 0,5eko atalasearekin alderatuta, 17.600 € aurrezten dira, eta 0,4ko atalasearekin alderatuta, berriz, 9.000 €. Baliozkotzea 1.600 makinaren erregistroekin egin da, benetako 54 hutsegite kontuan hartuta eta gure Random Forest eredua erabiliz.

| Atalasea | Detektatutakoak (TP) | Detektatu gabekoak (FN) | Alarma faltsuak (FP) | Recall | Doitasuna (Precision) | Kostu osoa |
|---|---:|---:|---:|---:|---:|---:|
| 0,5 (lehenetsia) | 42 | 12 | 4 | 0,78 | 0,91 | 73.400 € |
| 0,4 | 44 | 10 | 8 | 0,81 | 0,85 | 64.800 € |
| 0,3 | 44 | 10 | 14 | 0,81 | 0,76 | 66.000 € |
| 0,2 | 45 | 9 | 35 | 0,83 | 0,56 | 65.500 € |
| **0,15 (aukeratua)** | **48** | **6** | **57** | **0,89** | **0,46** | **55.800 €** |
| 0,1 | 49 | 5 | 93 | 0,91 | 0,35 | 58.300 € |

Matxura bat gehiago detektatzeak 4.700 € aurrezten ditu (5.000 € matxuragatik, 300 € pieza aldatzeagatik), eta aurrezki horrek 23 bat alarma faltsu ordaintzen ditu. Atalasea jaisteak konpentsatu egiten du, matxura bakoitzak 23 alarma faltsu baino gutxiago balio duen bitartean.

* **0,5etik 0,4ra:** 2 hutsegite gehiago detektatzen dira (+9.400 €), baina 4 alarma faltsu gehiago sortzen dira (−800 €). Beraz, aldaketa horrek merezi du.

* **0,4tik 0,2ra:** ia ez da hobekuntzarik lortzen. Recall-a ia konstante mantentzen da (≈ 0,82), 0,22 eta 0,45 arteko atalaseetan. 27 alarma faltsu gehiago sortzen dira, baina hutsegite bakarra gehiago detektatzen da. Horregatik, 0,2 eta 0,3 atalaseek 0,4k baino kostu handiagoa dute.

* **0,4tik 0,15era:** 4 hutsegite gehiago detektatzen dira (+18.800 €), baina 49 alarma faltsu gehiago sortzen dira (−9.800 €). Aldaketa horrek merezi du, guztira 9.000 € aurrezten direlako.

* **0,15etik 0,1era:** hutsegite bat gehiago detektatzen da (+4.700 €), baina 36 alarma faltsu gehiago sortzen dira (−7.200 €). Kasu honetan, aldaketak ez du merezi, kostu osoa handitu egiten delako.

Errore kopurua bakarrik kontuan hartuko bagenu, 0,4ko atalasea hobea dela pentsa genezake (18 errore, 63 errore baino gutxiago). Hala ere, errore guztiek ez dute kostu bera. Kostuak kontuan hartuta, 0,15eko atalasea merkeagoa da.

### Zergatik 0,15 eta ez kostu txikieneko balio zehatza?

Gure kalkuluetan, kosturik txikiena 0,16ko atalasean lortzen da (54.200 €). Hala ere, balio hori baliozkotze-datu zehatzetara gehiegi egokituta egon daiteke. 0,10 eta 0,16 arteko atalaseek antzeko kostuak dituzte (54.000–58.000 €). Horregatik, 0,15eko atalasea aukeratu dugu, aukera egokia eta zuhurra delako, balio zehatz bakar baten menpe egon gabe.
