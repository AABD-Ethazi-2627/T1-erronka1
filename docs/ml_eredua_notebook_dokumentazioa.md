
# CNC Guard - Hutsegiteen ereduaren entrenamendua

Random Forest bat entrenatzen dugu, CNC makina batek 6 sentsore irakurketatik aurrera huts egingo duen iragartzen duena. 0,15eko atalasearekin, balidazioko 54 akatsetatik 48 detektatzen ditu (recall 0,89), eta kalkulatutako kostua 55.800 €-tan uzten du; eredurik gabe, berriz, 270.000 €-tan.

## Random Forest modeloa aukeratzeko justifikazioa


## Kodean emandako pausoak
### 1. Beharrezko liburutegiak kargatu
Proiektu gustietan bezala , lehenik liburutegiak kargatuko ditugu. Huek diira erabilitakoak eta zertarko balio duen bakoitza:

* **pandas (pd)**: CSV fitxategiak irakurtzeko eta tablekin aln egiteko.
* **matplotlib.pyplot (plt)**:  preision/recall grafikoak margozteko.
*  **seaborn (sns)**: matplotlib sortutako grafikoak ikusgarriagoak egiteko.
*  **sklearn (scikit-learn)**: machine learning liburutegia.
    *  **RandomForestClassifier**: erabiltzen dugun modeloa.
    *   **train_test_split**: 
    
