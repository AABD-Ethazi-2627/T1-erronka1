
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


## Kodean emandako pausoak
### 1. Beharrezko liburutegiak kargatu
Proiektu gustietan bezala , lehenik liburutegiak kargatuko ditugu. Huek diira erabilitakoak eta zertarko balio duen bakoitza:

* **joblib**: entrenatutako modeloa gordetzeko eta gero berriro kargatzeko.
* **pandas (pd)**: CSV fitxategiak irakurtzeko eta taulekin lan egiteko.
* **matplotlib.pyplot (plt)**: grafikoak sortzeko, adibidez, precision-recall grafikoak.
* **seaborn (sns)**: grafiko estatistikoak sortzeko eta datuak modu bisualagoan erakusteko.
* **sklearn (scikit-learn)**: machine learning ereduak sortzeko eta ebaluatzeko liburutegia.
    * **RandomForestClassifier**: erabiltzen dugun sailkapen-eredua sortzeko.
    * **train_test_split**: datuak entrenamendu- eta test-multzoetan banatzeko.
    * **ConfusionMatrixDisplay**: nahasmen-matrizea grafikoki erakusteko.
    * **confusion_matrix**: benetako emaitzak eta modeloaren predikzioak alderatzeko.
    * **classification_report**: precision, recall eta F1-score metrikak erakusteko.
    * **accuracy_score**: modeloaren predikzioetatik zenbat diren zuzenak kalkulatzeko.
    * **precision_score**: positibotzat sailkatutako kasuetatik zenbat diren benetan positiboak kalkulatzeko.
    * **recall_score**: benetako kasu positiboetatik zenbat detektatzen dituen kalkulatzeko.
    * **f1_score**: precision eta recall metrikak konbinatzeko.
    * **roc_auc_score**: modeloak bi klaseak bereizteko duen gaitasuna ebaluatzeko.
    * **precision_recall_curve**: threshold desberdinekin precision eta recall nola aldatzen diren aztertzeko.
    * **average_precision_score**: precision-recall kurbaren errendimendua laburbiltzeko.
* **cnc_ml.columns**: proiektuan erabiltzen diren zutabeak eta kategoriak definitzeko.
* **cnc_ml.pipeline**: machine learning prozesua prestatzeko.
    * **build_pipeline**: datuak prestatzeko eta modeloa entrenatzeko pipeline-a sortzeko.
* **app.services.model**: aplikazioaren modeloarekin eta predikzioekin lotutako funtzionalitateak kudeatzeko.
    * **FAILURE_THRESHOLD**: hutsegiteak detektatzeko erabiltzen den atalasea definitzeko.
* **importlib**: Python-en moduluak inportatzeko eta kargatzeko.
    * **importlib.reload(m)**: `app.services.model` modulua berriro kargatzeko, garapenean egindako aldaketak aplikatzeko.
    
