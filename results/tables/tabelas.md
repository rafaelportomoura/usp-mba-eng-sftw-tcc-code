# Tabelas descritivas (geradas por `python3 -m analysis.report`)

Fonte: `results.csv`, 18 execuções. Mediana, mínimo e máximo; sem teste de significância.

### descritiva por condicao

| condition | metrica | n | mediana | minimo | maximo |
|---|---|---|---|---|---|
| controle | auditability_total | 9 | 3 | 2 | 3 |
| controle | trace_code | 9 | 0 | 0 | 0 |
| controle | trace_tests | 9 | 0 | 0 | 1 |
| controle | assumptions | 9 | 0 | 0 | 0 |
| controle | risks | 9 | 0 | 0 | 0 |
| controle | rationale | 9 | 0 | 0 | 0 |
| controle | fidelity | 9 | 2 | 0 | 2 |
| controle | reproducibility | 9 | 1 | 1 | 1 |
| controle | ap_points | 9 | 1 | 0 | 6 |
| controle | rp_points | 9 | 0 | 0 | 0 |
| controle | output_words | 9 | 33 | 21 | 51 |
| controle | duration_s | 9 | 96.626 | 45.926 | 407.406 |
| controle | hidden_pass_rate | 9 | 1.0 | 1.0 | 1.0 |
| explicacao | auditability_total | 9 | 10 | 7 | 12 |
| explicacao | trace_code | 9 | 1 | 1 | 1 |
| explicacao | trace_tests | 9 | 2 | 1 | 2 |
| explicacao | assumptions | 9 | 1 | 0 | 2 |
| explicacao | risks | 9 | 1 | 0 | 2 |
| explicacao | rationale | 9 | 2 | 1 | 2 |
| explicacao | fidelity | 9 | 2 | 0 | 2 |
| explicacao | reproducibility | 9 | 2 | 2 | 2 |
| explicacao | ap_points | 9 | 4 | 0 | 7 |
| explicacao | rp_points | 9 | 9 | 6 | 11 |
| explicacao | output_words | 9 | 330 | 259 | 366 |
| explicacao | duration_s | 9 | 97.768 | 89.445 | 130.355 |
| explicacao | hidden_pass_rate | 9 | 1.0 | 1.0 | 1.0 |

### descritiva por tarefa e condicao

| task_id | condition | metrica | n | mediana | minimo | maximo |
|---|---|---|---|---|---|---|
| t1_shipping | controle | auditability_total | 3 | 3 | 3 | 3 |
| t1_shipping | controle | trace_code | 3 | 0 | 0 | 0 |
| t1_shipping | controle | trace_tests | 3 | 1 | 0 | 1 |
| t1_shipping | controle | assumptions | 3 | 0 | 0 | 0 |
| t1_shipping | controle | risks | 3 | 0 | 0 | 0 |
| t1_shipping | controle | rationale | 3 | 0 | 0 | 0 |
| t1_shipping | controle | fidelity | 3 | 1 | 1 | 2 |
| t1_shipping | controle | reproducibility | 3 | 1 | 1 | 1 |
| t1_shipping | controle | ap_points | 3 | 5 | 1 | 6 |
| t1_shipping | controle | rp_points | 3 | 0 | 0 | 0 |
| t1_shipping | controle | output_words | 3 | 32 | 21 | 44 |
| t1_shipping | controle | duration_s | 3 | 76.812 | 45.926 | 97.498 |
| t1_shipping | controle | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |
| t1_shipping | explicacao | auditability_total | 3 | 9 | 7 | 9 |
| t1_shipping | explicacao | trace_code | 3 | 1 | 1 | 1 |
| t1_shipping | explicacao | trace_tests | 3 | 1 | 1 | 1 |
| t1_shipping | explicacao | assumptions | 3 | 1 | 0 | 1 |
| t1_shipping | explicacao | risks | 3 | 0 | 0 | 1 |
| t1_shipping | explicacao | rationale | 3 | 1 | 1 | 2 |
| t1_shipping | explicacao | fidelity | 3 | 2 | 2 | 2 |
| t1_shipping | explicacao | reproducibility | 3 | 2 | 2 | 2 |
| t1_shipping | explicacao | ap_points | 3 | 6 | 6 | 7 |
| t1_shipping | explicacao | rp_points | 3 | 7 | 6 | 7 |
| t1_shipping | explicacao | output_words | 3 | 354 | 301 | 365 |
| t1_shipping | explicacao | duration_s | 3 | 92.105 | 89.445 | 97.578 |
| t1_shipping | explicacao | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |
| t2_order_pricing | controle | auditability_total | 3 | 3 | 3 | 3 |
| t2_order_pricing | controle | trace_code | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | trace_tests | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | assumptions | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | risks | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | rationale | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | fidelity | 3 | 2 | 2 | 2 |
| t2_order_pricing | controle | reproducibility | 3 | 1 | 1 | 1 |
| t2_order_pricing | controle | ap_points | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | rp_points | 3 | 0 | 0 | 0 |
| t2_order_pricing | controle | output_words | 3 | 48 | 32 | 51 |
| t2_order_pricing | controle | duration_s | 3 | 94.141 | 83.099 | 407.406 |
| t2_order_pricing | controle | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |
| t2_order_pricing | explicacao | auditability_total | 3 | 12 | 12 | 12 |
| t2_order_pricing | explicacao | trace_code | 3 | 1 | 1 | 1 |
| t2_order_pricing | explicacao | trace_tests | 3 | 2 | 2 | 2 |
| t2_order_pricing | explicacao | assumptions | 3 | 2 | 2 | 2 |
| t2_order_pricing | explicacao | risks | 3 | 1 | 1 | 1 |
| t2_order_pricing | explicacao | rationale | 3 | 2 | 2 | 2 |
| t2_order_pricing | explicacao | fidelity | 3 | 2 | 2 | 2 |
| t2_order_pricing | explicacao | reproducibility | 3 | 2 | 2 | 2 |
| t2_order_pricing | explicacao | ap_points | 3 | 4 | 4 | 5 |
| t2_order_pricing | explicacao | rp_points | 3 | 11 | 10 | 11 |
| t2_order_pricing | explicacao | output_words | 3 | 330 | 259 | 366 |
| t2_order_pricing | explicacao | duration_s | 3 | 120.918 | 117.999 | 130.355 |
| t2_order_pricing | explicacao | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |
| t3_inventory_reservation | controle | auditability_total | 3 | 3 | 2 | 3 |
| t3_inventory_reservation | controle | trace_code | 3 | 0 | 0 | 0 |
| t3_inventory_reservation | controle | trace_tests | 3 | 0 | 0 | 1 |
| t3_inventory_reservation | controle | assumptions | 3 | 0 | 0 | 0 |
| t3_inventory_reservation | controle | risks | 3 | 0 | 0 | 0 |
| t3_inventory_reservation | controle | rationale | 3 | 0 | 0 | 0 |
| t3_inventory_reservation | controle | fidelity | 3 | 2 | 0 | 2 |
| t3_inventory_reservation | controle | reproducibility | 3 | 1 | 1 | 1 |
| t3_inventory_reservation | controle | ap_points | 3 | 1 | 0 | 5 |
| t3_inventory_reservation | controle | rp_points | 3 | 0 | 0 | 0 |
| t3_inventory_reservation | controle | output_words | 3 | 33 | 29 | 46 |
| t3_inventory_reservation | controle | duration_s | 3 | 104.609 | 96.626 | 107.414 |
| t3_inventory_reservation | controle | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |
| t3_inventory_reservation | explicacao | auditability_total | 3 | 10 | 10 | 12 |
| t3_inventory_reservation | explicacao | trace_code | 3 | 1 | 1 | 1 |
| t3_inventory_reservation | explicacao | trace_tests | 3 | 2 | 2 | 2 |
| t3_inventory_reservation | explicacao | assumptions | 3 | 1 | 1 | 2 |
| t3_inventory_reservation | explicacao | risks | 3 | 2 | 1 | 2 |
| t3_inventory_reservation | explicacao | rationale | 3 | 1 | 1 | 2 |
| t3_inventory_reservation | explicacao | fidelity | 3 | 2 | 0 | 2 |
| t3_inventory_reservation | explicacao | reproducibility | 3 | 2 | 2 | 2 |
| t3_inventory_reservation | explicacao | ap_points | 3 | 0 | 0 | 1 |
| t3_inventory_reservation | explicacao | rp_points | 3 | 9 | 9 | 11 |
| t3_inventory_reservation | explicacao | output_words | 3 | 325 | 273 | 341 |
| t3_inventory_reservation | explicacao | duration_s | 3 | 97.768 | 94.067 | 117.814 |
| t3_inventory_reservation | explicacao | hidden_pass_rate | 3 | 1.0 | 1.0 | 1.0 |

### diferenca explicacao menos controle

| escopo | metrica | mediana_explicacao | mediana_controle | diferenca |
|---|---|---|---|---|
| todas | auditability_total | 10 | 3 | 7 |
| todas | trace_code | 1 | 0 | 1 |
| todas | trace_tests | 2 | 0 | 2 |
| todas | assumptions | 1 | 0 | 1 |
| todas | risks | 1 | 0 | 1 |
| todas | rationale | 2 | 0 | 2 |
| todas | fidelity | 2 | 2 | 0 |
| todas | reproducibility | 2 | 1 | 1 |
| todas | ap_points | 4 | 1 | 3 |
| todas | rp_points | 9 | 0 | 9 |
| todas | output_words | 330 | 33 | 297 |
| todas | duration_s | 97.768 | 96.626 | 1.142 |
| todas | hidden_pass_rate | 1.0 | 1.0 | 0.0 |

### diferenca por tarefa

| escopo | metrica | mediana_explicacao | mediana_controle | diferenca |
|---|---|---|---|---|
| t1_shipping | auditability_total | 9 | 3 | 6 |
| t1_shipping | trace_code | 1 | 0 | 1 |
| t1_shipping | trace_tests | 1 | 1 | 0 |
| t1_shipping | assumptions | 1 | 0 | 1 |
| t1_shipping | risks | 0 | 0 | 0 |
| t1_shipping | rationale | 1 | 0 | 1 |
| t1_shipping | fidelity | 2 | 1 | 1 |
| t1_shipping | reproducibility | 2 | 1 | 1 |
| t1_shipping | ap_points | 6 | 5 | 1 |
| t1_shipping | rp_points | 7 | 0 | 7 |
| t1_shipping | output_words | 354 | 32 | 322 |
| t1_shipping | duration_s | 92.105 | 76.812 | 15.293 |
| t1_shipping | hidden_pass_rate | 1.0 | 1.0 | 0.0 |
| t2_order_pricing | auditability_total | 12 | 3 | 9 |
| t2_order_pricing | trace_code | 1 | 0 | 1 |
| t2_order_pricing | trace_tests | 2 | 0 | 2 |
| t2_order_pricing | assumptions | 2 | 0 | 2 |
| t2_order_pricing | risks | 1 | 0 | 1 |
| t2_order_pricing | rationale | 2 | 0 | 2 |
| t2_order_pricing | fidelity | 2 | 2 | 0 |
| t2_order_pricing | reproducibility | 2 | 1 | 1 |
| t2_order_pricing | ap_points | 4 | 0 | 4 |
| t2_order_pricing | rp_points | 11 | 0 | 11 |
| t2_order_pricing | output_words | 330 | 48 | 282 |
| t2_order_pricing | duration_s | 120.918 | 94.141 | 26.777 |
| t2_order_pricing | hidden_pass_rate | 1.0 | 1.0 | 0.0 |
| t3_inventory_reservation | auditability_total | 10 | 3 | 7 |
| t3_inventory_reservation | trace_code | 1 | 0 | 1 |
| t3_inventory_reservation | trace_tests | 2 | 0 | 2 |
| t3_inventory_reservation | assumptions | 1 | 0 | 1 |
| t3_inventory_reservation | risks | 2 | 0 | 2 |
| t3_inventory_reservation | rationale | 1 | 0 | 1 |
| t3_inventory_reservation | fidelity | 2 | 2 | 0 |
| t3_inventory_reservation | reproducibility | 2 | 1 | 1 |
| t3_inventory_reservation | ap_points | 0 | 1 | -1 |
| t3_inventory_reservation | rp_points | 9 | 0 | 9 |
| t3_inventory_reservation | output_words | 325 | 33 | 292 |
| t3_inventory_reservation | duration_s | 97.768 | 104.609 | -6.841 |
| t3_inventory_reservation | hidden_pass_rate | 1.0 | 1.0 | 0.0 |

### sensibilidade c2 c6

| variante | cortes | mediana_controle | mediana_explicacao | diferenca | execucoes_com_total_alterado | direcao_de_H1_muda |
|---|---|---|---|---|---|---|
| oficial | oficiais | 3 | 10 | 7 | 0 | False |
| c2_high_70 | {"c2_high": 0.7} | 3 | 10 | 7 | 0 | False |
| c2_high_80 | {"c2_high": 0.8} | 3 | 10 | 7 | 0 | False |
| c2_low_40 | {"c2_low": 0.4} | 3 | 10 | 7 | 0 | False |
| c2_low_60 | {"c2_low": 0.6} | 3 | 10 | 7 | 0 | False |
| c6_min2_4 | {"c6_min2": 4} | 3 | 10 | 7 | 1 | False |
| c6_min2_6 | {"c6_min2": 6} | 3 | 10 | 7 | 0 | False |
| c6_min1_2 | {"c6_min1": 2} | 3 | 10 | 7 | 0 | False |
| c6_min1_4 | {"c6_min1": 4} | 3 | 10 | 7 | 1 | False |
