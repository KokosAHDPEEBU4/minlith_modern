# parity_check — артефакты сверки с оригиналом MINLITH

Снимок данных для пообразцовой сверки (см. `../SAMPLE_PARITY_VERIFICATION.md`).

| Файл | Что это |
|------|---------|
| `source_petrochemistry.xlsx` | Исходный файл проб (9 листов-свит: входные оксиды + блоки `MINLITH`). |
| `input_85_samples.xlsx` | 85 образцов в формате шаблона загрузки (лист «Данные»), по которым считался exe. |
| `expected_original.csv` | Эталон: строка 287 **оригинального** MINLITH по 85 образцам (живой Excel). |
| `results_excel_exact_1to1.xlsx` | Результат режима **«Excel 1:1»** (`excel_exact`) из приложения/exe. |
| `results_excel_parity.xlsx` | Результат режима **«Excel (корректные округл.)»** (`excel_parity`) из приложения/exe. |

## Итог сверки (85 образцов)
- **`excel_exact` = оригинал 1:1**: max|Δ| = 0.0000, расхождений 0.
- **`excel_parity` = оригинал в пределах округления**: max|Δ| = 0.09, 8 значений >0.05 на
  3 патологических образцах (`7913`, `7930`, `7931`).
- **exe ≡ запуск из исходников** (`…python/src`) — различия только в округлении выгрузки (≤0.005).

## Как сравнивать
Загрузить `results_excel_*.xlsx` (лист `Results`) и сопоставить с `expected_original.csv`
по имени образца и минералу (`Ab, An, Or, Q, Mm, Ill, Chl, Gb, Kn, Ap, Cc, Dl, Ank, Rch,
Sd, Srp, Mst, Ht, Prl, Pr` ↔ `Ab, An, Orn, Qn, Mmn, Illn, Chln, Gbn, Knn, Apn, Ccn, Dln,
Ankn, Rchn, Sdn, Srpn, Mstn, Htn, Prln, Prn`).
