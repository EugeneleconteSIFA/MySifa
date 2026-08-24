# Inventaire de la base RVGI (`sifa_cs`)

Genere le 24/08/2026 16:17 - lecture seule.

Source : `provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;`

Objets au schema : 200 - copies `_backup_` : 17 - inspectees : 183

Extraits : les 3 dernieres lignes (`TOP n + ORDER BY id DESC`), valeurs tronquees a 60 caracteres.

Deux vues des colonnes : **logique** (un tableau WinDev compte pour une colonne, c'est le modele de l'editeur) et **physique** (ce que renvoie `SELECT *`, tableaux depiles en `x`, `x_2`...). Un script de synchro lit la vue physique.

**Corbeille exclue** : comptages, dates et extraits ne portent que sur `corbeille = 0`. La colonne *Total* montre le volume brut, corbeille comprise, quand la table porte ce marqueur.

## Sommaire

| Table | Lignes vivantes | Total | Derniere activite | Col. logiques | Col. physiques |
|---|---:|---:|---|---:|---:|
| [`aof_com`](#aof-com) | 16 | 32 | 03/27/2025 14:49:41 | 9 | 9 |
| [`aof_comft`](#aof-comft) | 0 | 0 | - | 9 | 0 |
| [`aof_comif`](#aof-comif) | 0 | 0 | - | 9 | 0 |
| [`aof_comir`](#aof-comir) | 0 | 0 | - | 9 | 0 |
| [`aof_comis`](#aof-comis) | 0 | 0 | - | 9 | 0 |
| [`aof_entete`](#aof-entete) | 31 | 69 | 03/27/2025 14:54:38 | 62 | 87 |
| [`aof_ligne`](#aof-ligne) | 58 | 127 | 03/27/2025 14:54:21 | 54 | 63 |
| [`cde_com`](#cde-com) | 33 886 | 68 113 | 08/24/2026 15:05:58 | 9 | 9 |
| [`cde_comif`](#cde-comif) | 7 295 | 15 034 | 08/24/2026 15:05:58 | 9 | 9 |
| [`cde_comil`](#cde-comil) | 14 451 | 29 029 | 08/24/2026 15:05:58 | 9 | 9 |
| [`cde_comis`](#cde-comis) | 5 458 | 10 926 | 08/06/2026 15:26:11 | 9 | 9 |
| [`cde_comit`](#cde-comit) | 0 | 0 | - | 9 | 0 |
| [`cde_entete`](#cde-entete) | 19 846 | 43 164 | 08/24/2026 15:46:47 | 67 | 92 |
| [`cde_exped`](#cde-exped) | 4 450 | 7 477 | 08/24/2026 15:06:08 | 13 | 13 |
| [`cde_ligne`](#cde-ligne) | 34 942 | 84 867 | 08/24/2026 16:09:29 | 71 | 80 |
| [`cde_nomen`](#cde-nomen) | 0 | = | - | 33 | 0 |
| [`cdf_com`](#cdf-com) | 1 570 | 3 535 | 08/24/2026 16:00:06 | 9 | 9 |
| [`cdf_comif`](#cdf-comif) | 3 | 7 | 02/12/2025 14:38:17 | 9 | 9 |
| [`cdf_comir`](#cdf-comir) | 43 | 108 | 05/26/2026 16:46:46 | 9 | 9 |
| [`cdf_comis`](#cdf-comis) | 379 | 771 | 07/31/2026 09:55:38 | 9 | 9 |
| [`cdf_entete`](#cdf-entete) | 4 572 | 10 931 | 08/24/2026 16:03:22 | 62 | 87 |
| [`cdf_ligne`](#cdf-ligne) | 9 214 | 27 311 | 08/24/2026 15:59:59 | 53 | 62 |
| [`cdi_comic`](#cdi-comic) | 0 | 0 | - | 9 | 0 |
| [`cdi_comif`](#cdi-comif) | 0 | 0 | - | 9 | 0 |
| [`cdi_entete`](#cdi-entete) | 52 | 254 | 04/16/2026 08:59:42 | 51 | 80 |
| [`cdi_ligne`](#cdi-ligne) | 76 | 340 | 04/16/2026 08:59:42 | 55 | 120 |
| [`cdi_res`](#cdi-res) | 137 | 165 | 03/31/2026 14:22:05 | 28 | 37 |
| [`cdm_appel`](#cdm-appel) | 167 | 334 | 01/09/2024 10:56:46 | 24 | 33 |
| [`cdm_com`](#cdm-com) | 903 | 1 843 | 07/30/2026 15:54:43 | 10 | 10 |
| [`cdm_comif`](#cdm-comif) | 261 | 522 | 07/28/2026 14:28:42 | 10 | 10 |
| [`cdm_comil`](#cdm-comil) | 370 | 751 | 07/30/2026 15:54:43 | 10 | 10 |
| [`cdm_comis`](#cdm-comis) | 171 | 348 | 07/28/2026 14:31:29 | 10 | 10 |
| [`cdm_comit`](#cdm-comit) | 0 | 0 | - | 10 | 0 |
| [`cdm_entete`](#cdm-entete) | 727 | 1 560 | 07/30/2026 16:02:25 | 64 | 89 |
| [`cdm_ligne`](#cdm-ligne) | 1 087 | 2 799 | 08/06/2026 09:14:14 | 61 | 70 |
| [`col_ligne`](#col-ligne) | 257 | 514 | 02/25/2026 15:30:34 | 24 | 41 |
| [`com_entete`](#com-entete) | 0 | 0 | - | 28 | 0 |
| [`cpr_ax`](#cpr-ax) | 285 | = | 01/09/2026 15:31:09 | 30 | 39 |
| [`cpr_comct`](#cpr-comct) | 0 | = | - | 8 | 0 |
| [`cpr_comil`](#cpr-comil) | 0 | = | - | 8 | 0 |
| [`cpr_lab`](#cpr-lab) | 52 | = | 01/09/2026 15:31:07 | 30 | 39 |
| [`cpr_mat`](#cpr-mat) | 24 | = | 01/09/2026 15:31:09 | 34 | 43 |
| [`cpr_mo`](#cpr-mo) | 24 | = | 01/09/2026 15:31:08 | 33 | 42 |
| [`cpr_out`](#cpr-out) | 22 | = | 01/09/2026 15:31:08 | 28 | 37 |
| [`cpr_pre`](#cpr-pre) | 0 | = | - | 30 | 0 |
| [`cpr_pv`](#cpr-pv) | 35 | = | 07/17/2026 08:54:51 | 168 | 205 |
| [`cpr_st`](#cpr-st) | 13 | = | 01/09/2026 15:31:10 | 30 | 39 |
| [`cpr_tr`](#cpr-tr) | 47 | = | 01/09/2026 15:31:11 | 30 | 39 |
| [`dev_com`](#dev-com) | 1 433 | 2 982 | 07/21/2026 17:22:58 | 9 | 9 |
| [`dev_comft`](#dev-comft) | 0 | 0 | - | 9 | 0 |
| [`dev_comif`](#dev-comif) | 383 | 814 | 07/21/2026 17:22:58 | 9 | 9 |
| [`dev_comil`](#dev-comil) | 636 | 1 369 | 07/21/2026 17:22:58 | 9 | 9 |
| [`dev_comis`](#dev-comis) | 167 | 342 | 05/27/2026 16:07:29 | 9 | 9 |
| [`dev_comit`](#dev-comit) | 0 | 0 | - | 9 | 0 |
| [`dev_entete`](#dev-entete) | 865 | 1 903 | 07/21/2026 17:23:29 | 65 | 90 |
| [`dev_ligne`](#dev-ligne) | 1 341 | 3 218 | 07/24/2026 10:59:23 | 60 | 69 |
| [`dev_nomen`](#dev-nomen) | 0 | = | - | 32 | 0 |
| [`ecc_com`](#ecc-com) | 0 | 0 | - | 9 | 0 |
| [`ecc_comic`](#ecc-comic) | 0 | 0 | - | 9 | 0 |
| [`ecc_ech`](#ecc-ech) | 43 644 | 93 442 | 08/07/2026 17:21:12 | 27 | 36 |
| [`ecc_reg`](#ecc-reg) | 2 | 4 | 02/17/2015 18:12:00 | 24 | 33 |
| [`ecf_ech`](#ecf-ech) | 0 | 0 | - | 26 | 0 |
| [`ecf_reg`](#ecf-reg) | 0 | 0 | - | 23 | 0 |
| [`fic_art`](#fic-art) | 7 678 | 41 389 | 08/24/2026 15:46:32 | 95 | 122 |
| [`fic_arta`](#fic-arta) | 2 714 | 10 668 | 08/24/2026 15:44:38 | 22 | 109 |
| [`fic_artc`](#fic-artc) | 689 | 2 133 | 07/31/2026 13:38:16 | 20 | 107 |
| [`fic_artcomcde`](#fic-artcomcde) | 1 168 | 2 821 | 07/28/2026 10:36:28 | 11 | 11 |
| [`fic_artcomcdf`](#fic-artcomcdf) | 13 | 33 | 08/04/2026 17:13:21 | 11 | 11 |
| [`fic_artcomifcde`](#fic-artcomifcde) | 17 | 37 | 09/23/2025 15:32:43 | 11 | 11 |
| [`fic_artcomifcdf`](#fic-artcomifcdf) | 0 | 0 | - | 11 | 0 |
| [`fic_artcomilcde`](#fic-artcomilcde) | 68 | 164 | 03/03/2026 09:05:07 | 11 | 11 |
| [`fic_artcomircdf`](#fic-artcomircdf) | 2 | 5 | 02/03/2022 11:23:49 | 11 | 11 |
| [`fic_artcomiscde`](#fic-artcomiscde) | 292 | 3 318 | 05/27/2026 16:01:28 | 11 | 11 |
| [`fic_artcomiscdf`](#fic-artcomiscdf) | 7 | 15 | 11/20/2023 11:26:06 | 11 | 11 |
| [`fic_artv`](#fic-artv) | 3 184 | 10 872 | 08/24/2026 15:46:24 | 17 | 104 |
| [`fic_bqe`](#fic-bqe) | 1 | 2 | 02/17/2015 18:11:00 | 19 | 19 |
| [`fic_cha`](#fic-cha) | 171 | 423 | 07/27/2026 14:22:17 | 14 | 72 |
| [`fic_clt`](#fic-clt) | 1 264 | 6 939 | 08/06/2026 11:13:34 | 92 | 101 |
| [`fic_clta`](#fic-clta) | 6 186 | 18 210 | 08/24/2026 15:49:59 | 33 | 33 |
| [`fic_cltb`](#fic-cltb) | 5 | 10 | 04/01/2022 10:33:30 | 18 | 18 |
| [`fic_cltcom`](#fic-cltcom) | 203 | 585 | 07/28/2026 10:14:18 | 8 | 8 |
| [`fic_cltcomif`](#fic-cltcomif) | 80 | 200 | 07/29/2025 11:21:50 | 8 | 8 |
| [`fic_cltcomil`](#fic-cltcomil) | 184 | 565 | 07/29/2026 14:56:08 | 8 | 8 |
| [`fic_cltcomis`](#fic-cltcomis) | 2 | 6 | 05/07/2025 15:15:46 | 8 | 8 |
| [`fic_clti`](#fic-clti) | 2 926 | 8 298 | 08/07/2026 09:28:25 | 21 | 21 |
| [`fic_comqt`](#fic-comqt) | 49 | 98 | 07/04/2013 18:06:00 | 15 | 102 |
| [`fic_contact`](#fic-contact) | 1 | 2 | 01/29/2021 08:58:01 | 7 | 7 |
| [`fic_depot`](#fic-depot) | 1 | 2 | 12/03/2020 09:49:34 | 13 | 13 |
| [`fic_devise`](#fic-devise) | 3 | 7 | 02/10/2024 09:43:40 | 9 | 9 |
| [`fic_famqt`](#fic-famqt) | 243 | 486 | 07/04/2013 18:08:00 | 17 | 104 |
| [`fic_fart`](#fic-fart) | 64 | 331 | 04/27/2021 15:30:44 | 34 | 43 |
| [`fic_fclt`](#fic-fclt) | 8 | 16 | 04/17/2018 10:37:00 | 14 | 14 |
| [`fic_fcpt`](#fic-fcpt) | 9 | 20 | 11/04/2020 11:02:03 | 20 | 20 |
| [`fic_ffou`](#fic-ffou) | 1 | 4 | 01/19/2021 16:23:34 | 8 | 8 |
| [`fic_fou`](#fic-fou) | 1 217 | 6 075 | 06/23/2026 15:56:54 | 61 | 70 |
| [`fic_foub`](#fic-foub) | 10 | 20 | 02/26/2026 17:28:09 | 18 | 18 |
| [`fic_foucom`](#fic-foucom) | 19 | 46 | 05/25/2026 11:41:39 | 8 | 8 |
| [`fic_foucomif`](#fic-foucomif) | 0 | 0 | - | 8 | 0 |
| [`fic_foucomir`](#fic-foucomir) | 1 | 3 | 02/13/2026 08:53:20 | 8 | 8 |
| [`fic_foucomis`](#fic-foucomis) | 1 | 3 | 02/13/2026 08:53:20 | 8 | 8 |
| [`fic_foui`](#fic-foui) | 265 | 799 | 07/15/2026 10:20:31 | 18 | 18 |
| [`fic_gamme`](#fic-gamme) | 0 | 13 | - | 10 | 0 |
| [`fic_lang`](#fic-lang) | 0 | 0 | - | 7 | 0 |
| [`fic_lib`](#fic-lib) | 0 | 0 | - | 8 | 0 |
| [`fic_liv`](#fic-liv) | 39 | 90 | 06/04/2026 07:02:02 | 15 | 15 |
| [`fic_majdev`](#fic-majdev) | 2 | 4 | 05/07/2012 15:37:00 | 8 | 8 |
| [`fic_nomen`](#fic-nomen) | 1 | 2 | 03/07/2016 11:47:00 | 37 | 46 |
| [`fic_para`](#fic-para) | 1 401 | 4 601 | 08/11/2026 09:45:12 | 12 | 12 |
| [`fic_pays`](#fic-pays) | 241 | 482 | 09/01/2025 00:00:00 | 9 | 9 |
| [`fic_piece`](#fic-piece) | 24 | = | - | 5 | 17 |
| [`fic_point`](#fic-point) | 60 | 161 | 03/02/2026 14:11:46 | 9 | 9 |
| [`fic_prio`](#fic-prio) | 1 | 5 | 11/02/2012 18:33:00 | 7 | 7 |
| [`fic_reg`](#fic-reg) | 13 | 27 | 05/13/2025 10:14:30 | 14 | 14 |
| [`fic_rep`](#fic-rep) | 5 | 32 | 06/04/2025 08:50:15 | 18 | 117 |
| [`fic_tar`](#fic-tar) | 551 | 1 102 | 03/27/2013 15:31:00 | 17 | 104 |
| [`fic_texte`](#fic-texte) | 7 | 19 | 01/10/2024 15:13:05 | 10 | 10 |
| [`fic_tliv`](#fic-tliv) | 1 | 5 | 01/18/2021 16:08:18 | 11 | 11 |
| [`fic_tva`](#fic-tva) | 3 | 8 | 04/03/2023 11:03:04 | 12 | 12 |
| [`fic_ua`](#fic-ua) | 46 | 107 | 02/27/2026 16:32:42 | 10 | 10 |
| [`fic_uc`](#fic-uc) | 138 | 315 | 03/02/2026 10:27:33 | 10 | 10 |
| [`fic_uv`](#fic-uv) | 35 | 83 | 01/20/2026 08:36:29 | 11 | 11 |
| [`fic_ville`](#fic-ville) | 2 251 | 4 676 | 08/24/2026 15:13:41 | 7 | 7 |
| [`gen_arbo`](#gen-arbo) | 594 | 1 296 | 06/11/2026 14:15:01 | 9 | 9 |
| [`gen_bloq`](#gen-bloq) | 351 | = | - | 4 | 4 |
| [`gen_mdp`](#gen-mdp) | 68 | 135 | 11/23/2022 10:54:15 | 11 | 11 |
| [`gen_mdpsal`](#gen-mdpsal) | 12 310 | 46 425 | 07/29/2026 10:04:22 | 8 | 8 |
| [`gen_messa`](#gen-messa) | 24 | 48 | 04/08/2019 09:30:00 | 18 | 18 |
| [`gen_sala`](#gen-sala) | 34 | 347 | 07/28/2026 11:49:53 | 79 | 79 |
| [`gen_soc`](#gen-soc) | 17 | = | - | 16 | 16 |
| [`gpr_art`](#gpr-art) | 2 | 5 | 02/23/2022 15:33:17 | 18 | 18 |
| [`gpr_ff`](#gpr-ff) | 584 | 1 583 | 07/08/2026 17:07:24 | 231 | 302 |
| [`gpr_ff1`](#gpr-ff1) | 1 202 | 2 701 | 06/04/2026 15:15:43 | 20 | 229 |
| [`gpr_ffcomic`](#gpr-ffcomic) | 535 | 1 093 | 07/08/2026 17:07:24 | 11 | 11 |
| [`gpr_ffcomif`](#gpr-ffcomif) | 1 | 3 | 03/16/2026 10:54:12 | 11 | 11 |
| [`gpr_gpr`](#gpr-gpr) | 2 804 | 2 804 | 04/17/2026 15:01:58 | 15 | 15 |
| [`gpr_gprcom`](#gpr-gprcom) | 0 | 0 | - | 11 | 0 |
| [`gpr_mat`](#gpr-mat) | 243 | 653 | 04/10/2026 13:31:25 | 23 | 32 |
| [`gpr_sat`](#gpr-sat) | 26 | = | 03/27/2026 09:35:00 | 9 | 9 |
| [`lab_comit`](#lab-comit) | 0 | 0 | - | 9 | 0 |
| [`lab_entete`](#lab-entete) | 0 | 0 | - | 59 | 0 |
| [`lab_ligne`](#lab-ligne) | 0 | 0 | - | 58 | 0 |
| [`lif_com`](#lif-com) | 0 | 0 | - | 11 | 0 |
| [`lif_comis`](#lif-comis) | 0 | 0 | - | 11 | 0 |
| [`lif_ligne`](#lif-ligne) | 8 949 | 21 225 | 08/24/2026 14:45:04 | 23 | 32 |
| [`liv_com`](#liv-com) | 1 774 | 3 572 | 08/24/2026 15:12:44 | 10 | 10 |
| [`liv_comis`](#liv-comis) | 6 296 | 12 593 | 08/07/2026 14:07:12 | 10 | 10 |
| [`liv_entete`](#liv-entete) | 23 034 | 46 651 | 08/24/2026 16:10:50 | 41 | 41 |
| [`liv_ligne`](#liv-ligne) | 35 787 | 77 930 | 08/24/2026 16:09:29 | 25 | 34 |
| [`mac_atps`](#mac-atps) | 0 | 0 | - | 11 | 0 |
| [`mac_pro`](#mac-pro) | 10 | 43 | 04/22/2026 14:13:13 | 65 | 74 |
| [`mac_ptps`](#mac-ptps) | 8 | 18 | 01/21/2026 15:48:56 | 28 | 98 |
| [`mac_tra`](#mac-tra) | 16 | 74 | 01/21/2026 16:04:57 | 25 | 135 |
| [`mat_fmat`](#mat-fmat) | 25 | 57 | 07/02/2026 13:00:06 | 21 | 21 |
| [`mat_mat`](#mat-mat) | 1 536 | 7 521 | 08/07/2026 10:23:28 | 76 | 483 |
| [`mat_matcom`](#mat-matcom) | 36 | 79 | 05/28/2026 13:02:52 | 11 | 11 |
| [`mat_matcomif`](#mat-matcomif) | 1 682 | 6 089 | 08/07/2026 10:23:28 | 11 | 11 |
| [`mat_matcomir`](#mat-matcomir) | 0 | 0 | - | 11 | 0 |
| [`mat_matcomis`](#mat-matcomis) | 8 | 18 | 05/19/2026 11:46:47 | 11 | 11 |
| [`mat_nomen`](#mat-nomen) | 132 | 482 | 03/31/2026 11:09:20 | 37 | 46 |
| [`out_cyl`](#out-cyl) | 124 | 335 | 12/11/2025 15:47:15 | 26 | 98 |
| [`out_dec`](#out-dec) | 2 643 | 9 072 | 08/05/2026 15:11:24 | 59 | 116 |
| [`out_deca`](#out-deca) | 2 248 | 2 248 | 08/05/2026 15:01:11 | 13 | 13 |
| [`out_deccom`](#out-deccom) | 1 496 | 3 225 | 07/28/2026 18:16:41 | 9 | 9 |
| [`out_deccomif`](#out-deccomif) | 0 | 0 | - | 9 | 0 |
| [`out_deccomir`](#out-deccomir) | 2 649 | 8 111 | 08/05/2026 15:01:11 | 9 | 9 |
| [`out_deccomis`](#out-deccomis) | 1 974 | 4 155 | 07/20/2026 12:56:14 | 9 | 9 |
| [`pal_p1a`](#pal-p1a) | 0 | 0 | - | 10 | 0 |
| [`pro_pro`](#pro-pro) | 5 | 10 | 11/18/2021 10:47:14 | 43 | 52 |
| [`pro_procom`](#pro-procom) | 0 | 0 | - | 8 | 0 |
| [`pro_procomif`](#pro-procomif) | 0 | 0 | - | 8 | 0 |
| [`pro_procomil`](#pro-procomil) | 0 | 0 | - | 8 | 0 |
| [`pro_procomis`](#pro-procomis) | 0 | 0 | - | 8 | 0 |
| [`pro_proi`](#pro-proi) | 4 | 8 | 11/18/2021 10:48:12 | 17 | 17 |
| [`stk_hist`](#stk-hist) | 25 588 | = | 08/24/2026 16:09:30 | 21 | 21 |
| [`stm_hist`](#stm-hist) | 18 040 | = | 08/07/2026 10:27:57 | 21 | 21 |
| [`vte_com`](#vte-com) | 1 079 | 2 172 | 07/27/2026 15:42:55 | 9 | 9 |
| [`vte_comic`](#vte-comic) | 10 | 20 | 01/09/2024 12:04:35 | 9 | 9 |
| [`vte_entete`](#vte-entete) | 21 821 | 63 411 | 08/07/2026 17:21:27 | 72 | 97 |
| [`vte_ligne`](#vte-ligne) | 36 998 | 74 190 | 08/07/2026 14:03:38 | 49 | 58 |
| [`vtf_com`](#vtf-com) | 0 | 0 | - | 9 | 0 |
| [`vtf_comic`](#vtf-comic) | 0 | 0 | - | 9 | 0 |
| [`vtf_entete`](#vtf-entete) | 4 181 | 10 100 | 08/06/2026 17:33:44 | 62 | 87 |
| [`vtf_ligne`](#vtf-ligne) | 9 603 | 19 563 | 08/06/2026 12:12:42 | 44 | 53 |

## Detail des tables

### `aof_com`

Lignes : 16 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 32 - derniere activite (dtem) : 03/27/2025 14:49:41 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 41 | 1 | 0 | 2 | ATTENTION : PRODUCTION "ZERO DEFAULT" Ne pas livrer moins... | 2022035 | 0 | 03/27/2025 14:49:41 | 4 |
| 39 | 1 | 0 | 2 | ATTENTION : PRODUCTION "ZERO DEFAULT" Ne pas livrer moins... | 2022030 | 0 | 02/08/2024 09:43:58 | 4 |
| 36 | 1 | 0 | 2 | ATTENTION : PRODUCTION "ZERO DEFAULT" Ne pas livrer moins... | 2022029 | 0 | 02/07/2024 15:48:34 | 12 |

### `aof_comft`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt, corbeille - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `aof_comif`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt, corbeille - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `aof_comir`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `aof_comis`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `aof_entete`

Lignes : 31 - colonnes logiques : 62 - physiques : 87 - total corbeille comprise : 69 - derniere activite (dtem) : 03/27/2025 14:54:38 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numfou` sur numfou - `rs` sur rs - `groupefou` sur groupefou - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjc` | date |
| 12 | `numfou` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupefou` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `vref` | texte(50) |
| 42 | `nref` | texte(50) |
| 43 | `civ` | octet |
| 44 | `interlocuteur` | texte(50) |
| 45 | `tex` | texte(10) |
| 46 | `mail` | texte(128) |
| 47 | `com` | octet |
| 48 | `numint` | entier4ns |
| 49 | `dest` | texte(1) |
| 50 | `intfou` | entier4ns |
| 51 | `lrs` | texte(50) |
| 52 | `ladr1` | texte(50) |
| 53 | `ladr2` | texte(50) |
| 54 | `lcp` | texte(10) |
| 55 | `lville` | texte(50) |
| 56 | `lpays` | texte(50) |
| 57 | `modliv` | entier2ns |
| 58 | `amje` | date |
| 59 | `nbjliv` | entier2ns |
| 60 | `amjl` | date |
| 61 | `lcpays` | texte(5) |
| 62 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 87 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjc | numfou | rs | groupefou | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 86 | 0 | 03/27/2025 14:54:38 | 4 |  | 2022035 | FRANCE | FR | 0 | 4 | 03/27/2025 00:00:00 | 1092 | QRT Graphique | 1092 | 0 | 0 | 0 | 30520 | 0.000000 | Avenue Sainte Barbe | ZI de Saint Martin | SAINT MARTIN DE VALGALGUES |  | 1 | E | 0.000000 | 0 | 1 | 0.000000 | 0.000000 |
| 82 | 0 | 03/19/2025 16:26:23 | 12 |  | 2022034 | FRANCE | FR | 0 | 12 | 03/19/2025 00:00:00 | 1093 | GRAND OUEST ETIQUETTES | 1093 | 0 | 0 | 0 | 22400 | 0.000000 | Z.A.C. de Beausoleil |  | LAMBALLE |  | 1 | E | 0.000000 | 0 | 1 | 0.000000 | 0.000000 |
| 75 | 0 | 05/16/2024 06:39:09 | 1 |  | 2022032 | FRANCE | FR | 0 | 1 | 05/16/2024 00:00:00 | 1127 | BRENNTAG SA | 1127 | 0 | 0 | 0 | 69680 | 0.000000 | 90 avenue du Progrès |  | CHASSIEU |  | 1 | E | 0.000000 | 0 | 1 | 0.000000 | 0.000000 |

### `aof_ligne`

Lignes : 58 - colonnes logiques : 54 - physiques : 63 - total corbeille comprise : 127 - derniere activite (dtem) : 03/27/2025 14:54:21 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `rref` sur rref - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `vref` | texte(50) |
| 15 | `nref` | texte(50) |
| 16 | `com` | octet |
| 17 | `lrs` | texte(50) |
| 18 | `ladr1` | texte(50) |
| 19 | `ladr2` | texte(50) |
| 20 | `lcp` | texte(10) |
| 21 | `lville` | texte(50) |
| 22 | `lpays` | texte(50) |
| 23 | `modliv` | entier2ns |
| 24 | `amje` | date |
| 25 | `nbjliv` | entier2ns |
| 26 | `amjl` | date |
| 27 | `lcpays` | texte(5) |
| 28 | `ligne` | entier4ns |
| 29 | `lpos` | octet |
| 30 | `code1` | texte(5) |
| 31 | `code2` | texte(20) |
| 32 | `code3` | texte(10) |
| 33 | `des1` | texte(50) |
| 34 | `fam` | octet |
| 35 | `sfam` | entier4ns |
| 36 | `gamme` | entier2ns |
| 37 | `qte` | reel8 |
| 38 | `rref` | octet |
| 39 | `des2` | texte(50) |
| 40 | `des3` | texte(50) |
| 41 | `des4` | texte(50) |
| 42 | `pa` | numerique |
| 43 | `pub` | numerique |
| 44 | `pun` | numerique |
| 45 | `depot` | texte(10) |
| 46 | `cua` | texte(5) |
| 47 | `sua` | octet |
| 48 | `vua` | numerique |
| 49 | `net` | octet |
| 50 | `ctva` | texte(5) |
| 51 | `drref` | texte(50) |
| 52 | `docp` | octet |
| 53 | `qtb` | reel8 |
| 54 | `metb` | reel8 |

Dernieres lignes (les 30 premieres colonnes sur 63 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 161 | 0 | 03/27/2025 14:54:21 | 4 | 20.00 | 2022035 | 2 | 0.000000 | 0.000000 | 1 | 0.000000 | 0.000000 | 0.000000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 PT 62 ou 1 PT 13 |  |  | 0000 | A CONFIRMER |
| 159 | 0 | 03/19/2025 16:26:18 | 12 | 20.00 | 2022034 | 2 | 0.000000 | 0.000000 | 1 | 0.000000 | 0.000000 | 0.000000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SIFA | 45 rue Rollin |  | 59100 | ROUBAIX |
| 153 | 0 | 03/19/2025 16:24:37 | 12 | 20.00 | 2022034 | 2 | 0.000000 | 0.000000 | 1 | 0.000000 | 0.000000 | 0.000000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SIFA | 45 rue Rollin |  | 59100 | ROUBAIX |

### `cde_com`

Lignes : 33 886 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 68 113 - derniere activite (dtem) : 08/24/2026 15:05:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 72243 | 1 | 0 | 2 | Pour l’intégralité des dossiers XEROX il faut envoyer des... | 9932398 | 0 | 08/24/2026 15:05:58 | 4 |
| 72241 | 1 | 0 | 1 | Pour l'année 2025, ATTENTION SUR CHAQUE V/cde / factrure ... | 9932398 | 0 | 08/24/2026 15:05:58 | 4 |
| 72239 | 1 | 0 | 1 |  NE PAS METTRE D'ETIQUETTE SIFA SUR LES CARTONS UNIQUEMEN... | 9932396 | 0 | 08/06/2026 15:24:42 | 57 |

### `cde_comif`

Lignes : 7 295 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 15 034 - derniere activite (dtem) : 08/24/2026 15:05:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 17513 | 1 | 0 | 1 | Attention envoyer également une facture par mail à  Mr Kr... | 9932398 | 0 | 08/24/2026 15:05:58 | 4 |
| 17511 | 1 | 0 | 1 | IMPORTANT - Frais de port en sus  à facturer pour les sit... | 9932393 | 0 | 08/06/2026 13:19:27 | 57 |
| 17509 | 1 | 0 | 2 | CENTRE DE COUT (1107862) CODE FOURNISSEUR 1000020593 | 9932391 | 0 | 08/05/2026 15:19:24 | 57 |

### `cde_comil`

Lignes : 14 451 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 29 029 - derniere activite (dtem) : 08/24/2026 15:05:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 31912 | 1 | 0 | 1 | Expédition par DPD de 2 bobines/paravents à l'attention d... | 9932398 | 0 | 08/24/2026 15:05:58 | 4 |
| 31908 | 1 | 0 | 1 | Horaire de livraison: 7h - 14h RDV par mail si + de 3 pal... | 9932397 | 0 | 08/07/2026 08:57:52 | 57 |
| 31906 | 1 | 0 | 1 |   NE PAS METTRE D'ETIQUETTE SIFA SUR LES CARTONS UNIQUEME... | 9932396 | 0 | 08/06/2026 15:24:42 | 57 |

### `cde_comis`

Lignes : 5 458 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 10 926 - derniere activite (dtem) : 08/06/2026 15:26:11 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 10976 | 1 | 0 | 1 | D121 = 315 unités - Ok Laetitia 28/08 D151 = 500 unités -... | 9932396 | 1 | 08/06/2026 15:26:11 | 57 |
| 10974 | 1 | 0 | 1 | STD2 = 1 CARTON (DE 12 RLX)  C191 = 2 CARTONS B431 = 72.0... | 9932394 | 1 | 08/06/2026 13:33:48 | 57 |
| 10972 | 1 | 0 | 1 | C171 = 48.000 ETQ C241 = 336.000 ETQ = 42 Cartons  | 9932393 | 1 | 08/06/2026 13:21:26 | 57 |

### `cde_comit`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `cde_entete`

Lignes : 19 846 - colonnes logiques : 67 - physiques : 92 - total corbeille comprise : 43 164 - derniere activite (dtem) : 08/24/2026 15:46:47 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `operateur` sur operateur - `numero` sur numero - `cpays` sur cpays - `type` sur type - `amjc` sur amjc - `numclt` sur numclt - `rs` sur rs - `groupeclt` sur groupeclt - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `numrep` sur numrep - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `operateur` | entier2ns |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `fax` | texte(20) |
| 7 | `numero` | entier8ns |
| 8 | `pays` | texte(50) |
| 9 | `cpays` | texte(5) |
| 10 | `type` | entier2ns |
| 11 | `amjc` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `vref` | texte(50) |
| 42 | `nref` | texte(50) |
| 43 | `civ` | octet |
| 44 | `interlocuteur` | texte(50) |
| 45 | `tex` | texte(10) |
| 46 | `mail` | texte(128) |
| 47 | `com` | octet |
| 48 | `numint` | entier4ns |
| 49 | `dest` | texte(1) |
| 50 | `intclt` | entier4ns |
| 51 | `lrs` | texte(50) |
| 52 | `ladr1` | texte(50) |
| 53 | `ladr2` | texte(50) |
| 54 | `lcp` | texte(10) |
| 55 | `lville` | texte(50) |
| 56 | `lpays` | texte(50) |
| 57 | `modliv` | entier2ns |
| 58 | `amje` | date |
| 59 | `nbjliv` | entier2ns |
| 60 | `amjl` | date |
| 61 | `lcpays` | texte(5) |
| 62 | `posacompte` | texte(1) |
| 63 | `fchan` | octet |
| 64 | `numrep` | entier2ns |
| 65 | `exped` | octet |
| 66 | `adrf` | entier4 |
| 67 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 92 - tout est dans le JSON) :

| id | corbeille | operateur | dtem | salm | fax | numero | pays | cpays | type | amjc | numclt | rs | groupeclt | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 51959 | 0 | 4 | 08/24/2026 15:46:47 | 4 |  | 9932399 | FRANCE | FR | 1 | 08/24/2026 00:00:00 | 1352 | TARKETT SPORTS | 1352 | 0 | 0 | 0 | 92919 | 1660.000000 |  |  | PARIS LA DEFENSE |  | 1 | E | 1660.000000 | 0 | 1 | 0.000000 | 332.000000 |
| 51957 | 0 | 4 | 08/24/2026 15:14:57 | 4 |  | 9932398 | FRANCE | FR | 1 | 08/24/2026 00:00:00 | 912 | XEROX TECHNOLOGY SERVICES | 890 | 0 | 1 | 1 | 93420 | 450.000000 | Immeuble Rembrandt | 22 avenue des Nations | VILLEPINTE  |  | 1 | E | 450.000000 | 0 | 1 | 0.000000 | 90.000000 |
| 51949 | 0 | 57 | 08/07/2026 08:57:52 | 57 |  | 9932397 | FRANCE | FR | 1 | 08/06/2026 00:00:00 | 1340 | SONELOG FLEURY  | 1245 | 0 | 0 | 1 | 91700 | 2300.000000 | Z.I des Ciroliers | 13 rue Clément Ader  | FLEURY-MEROGIS  |  | 1 | E | 2300.000000 | 0 | 1 | 0.000000 | 460.000000 |

### `cde_exped`

Lignes : 4 450 - colonnes logiques : 13 - physiques : 13 - total corbeille comprise : 7 477 - derniere activite (dtem) : 08/24/2026 15:06:08 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `pays` | texte(50) |
| 7 | `adr1` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `adr2` | texte(50) |
| 10 | `ville` | texte(50) |
| 11 | `rs` | texte(50) |
| 12 | `cp` | texte(10) |
| 13 | `bp` | texte(10) |

Dernieres lignes :

| id | corbeille | dtem | salm | numero | pays | adr1 | cpays | adr2 | ville | rs | cp | bp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9126 | 0 | 08/24/2026 15:06:08 | 4 | 9932398 | FRANCE | Immeuble Rembrandt | FR | 22 avenue des Nations | VILLEPINTE  | XEROX TECHNOLOGY SERVICES | 93420 |  |
| 9124 | 0 | 08/04/2026 15:08:35 | 57 | 9932388 | FRANCE | 16 avenue du Québec | FR | Z.A. Courtaboeuf Bat Lys L1.2 | VILLEBON SUR YVETTE | VIDEOJET TECHNOLOGIES | 91140 |  |
| 9122 | 0 | 07/31/2026 15:44:43 | 4 | 9932379 | FRANCE | 1 rue Pablo PICASSO BAT L'imprimerie | FR |  | SAINT-ETIENNE | ALTAVIA AUVERGNE-RHONE-ALPES | 42000 |  |

### `cde_ligne`

Lignes : 34 942 - colonnes logiques : 71 - physiques : 80 - total corbeille comprise : 84 867 - derniere activite (dtem) : 08/24/2026 16:09:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `orig` sur orig - `prod` sur prod - `pcol` sur pcol - `mar` sur mar - `lmar` sur lmar - `amar` sur amar - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `vref` | texte(50) |
| 15 | `nref` | texte(50) |
| 16 | `com` | octet |
| 17 | `lrs` | texte(50) |
| 18 | `ladr1` | texte(50) |
| 19 | `ladr2` | texte(50) |
| 20 | `lcp` | texte(10) |
| 21 | `lville` | texte(50) |
| 22 | `lpays` | texte(50) |
| 23 | `modliv` | entier2ns |
| 24 | `amje` | date |
| 25 | `nbjliv` | entier2ns |
| 26 | `amjl` | date |
| 27 | `suv` | octet |
| 28 | `vuv` | numerique |
| 29 | `lcpays` | texte(5) |
| 30 | `ligne` | entier4ns |
| 31 | `lpos` | octet |
| 32 | `code1` | texte(5) |
| 33 | `code2` | texte(20) |
| 34 | `code3` | texte(10) |
| 35 | `des1` | texte(50) |
| 36 | `fam` | octet |
| 37 | `sfam` | entier4ns |
| 38 | `gamme` | entier2ns |
| 39 | `qte` | reel8 |
| 40 | `des2` | texte(50) |
| 41 | `des3` | texte(50) |
| 42 | `des4` | texte(50) |
| 43 | `pa` | numerique |
| 44 | `pub` | numerique |
| 45 | `pun` | numerique |
| 46 | `depot` | texte(10) |
| 47 | `net` | octet |
| 48 | `ctva` | texte(5) |
| 49 | `orig` | octet |
| 50 | `prod` | octet |
| 51 | `pcol` | octet |
| 52 | `mar` | entier8ns |
| 53 | `lmar` | entier4ns |
| 54 | `amar` | entier4ns |
| 55 | `cuv` | texte(5) |
| 56 | `npiec` | entier8ns |
| 57 | `lpiec` | entier4ns |
| 58 | `qtep` | reel8 |
| 59 | `eetiq` | octet |
| 60 | `typnf` | octet |
| 61 | `comnf` | texte(50) |
| 62 | `comrep` | reel4 |
| 63 | `num1` | texte(50) |
| 64 | `num2` | texte(50) |
| 65 | `fchan` | octet |
| 66 | `ofimp` | octet |
| 67 | `lab` | octet |
| 68 | `qtex` | octet |
| 69 | `punpct` | reel4 |
| 70 | `bat` | octet |
| 71 | `amjb` | date |

Dernieres lignes (les 30 premieres colonnes sur 80 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 140876 | 0 | 08/24/2026 15:46:43 | 4 | 20.00 | 9932399 | 1 | 1660.000000 | 1660.000000 | 1 | 0.000000 | 332.000000 | 1992.000000 | 52727 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | FIELDTURF TARKETT | 91 rue Chateaubriand |  | 62260 | AUCHEL |
| 140874 | 0 | 08/24/2026 15:14:52 | 4 | 20.00 | 9932398 | 1 | 450.000000 | 450.000000 | 1 | 0.000000 | 90.000000 | 540.000000 | 6000990497 - PO 5500007265 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | CARREFOUR SUPPLY CHAIN | Madame Delphine MERLE | ZAC de Sennecé  | 71000 | SENNECE LES MACAON  |
| 140827 | 0 | 08/07/2026 10:10:22 | 11 | 20.00 | 9932397 | 1 | 2300.000000 | 2300.000000 | 1 | 0.000000 | 460.000000 | 2760.000000 | CF26SLOG02782 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PLATEFORME SONEPAR FLEURY | Z.I des Ciroliers | 13 rue Clément Ader  | 91700 | FLEURY-MEROGIS  |

### `cde_nomen`

Lignes : 0 - colonnes logiques : 33 - physiques : 0

Cles : `id` sur id (primaire) - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `htn` sur htn - `numero` sur numero - `ligne` sur ligne - `des1` sur des1 - `lignenomen` sur lignenomen - `lpos` sur lpos - `clef` sur numero, ligne, lignenomen

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `fam` | octet |
| 10 | `sfam` | entier4ns |
| 11 | `gamme` | entier2ns |
| 12 | `cuv` | texte(5) |
| 13 | `depot` | texte(10) |
| 14 | `qte` | reel8 |
| 15 | `htn` | numerique |
| 16 | `pa` | numerique |
| 17 | `pub` | numerique |
| 18 | `pun` | numerique |
| 19 | `suv` | octet |
| 20 | `vuv` | numerique |
| 21 | `net` | octet |
| 22 | `trem` | octet |
| 23 | `rem` | numerique |
| 24 | `numero` | entier8ns |
| 25 | `ligne` | entier4ns |
| 26 | `des1` | texte(50) |
| 27 | `lignenomen` | entier4ns |
| 28 | `des2` | texte(50) |
| 29 | `des3` | texte(50) |
| 30 | `des4` | texte(50) |
| 31 | `htb` | numerique |
| 32 | `com` | octet |
| 33 | `lpos` | octet |

### `cdf_com`

Lignes : 1 570 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 3 535 - derniere activite (dtem) : 08/24/2026 16:00:06 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 4831 | 1 | 0 | 2 | ATTENTION : PRODUCTION "ZERO DEFAULT" Echantillons de cha... | 6013 | 0 | 08/24/2026 16:00:06 | 4 |
| 4829 | 1 | 0 | 1 |  Il est impératif de respecter la quantité commandée (Tol... | 6013 | 0 | 08/24/2026 16:00:06 | 4 |
| 4827 | 1 | 0 | 2 |  Conditionnement par numéro de référence article 1397065 ... | 6000 | 2 | 08/05/2026 09:59:28 | 57 |

### `cdf_comif`

Lignes : 3 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 7 - derniere activite (dtem) : 02/12/2025 14:38:17 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 7 | 1 | 0 | 1 | Attention @COMPTA: j'ai rajouté cette ligne de frais de p... | 4374 | 4 | 02/12/2025 14:38:17 | 12 |
| 3 | 1 | 0 | 2 | Attention Films destinés au repiquage | 1099 | 0 | 01/26/2021 14:57:47 | 1 |
| 1 | 1 | 0 | 1 | Attention Films destinés au repiquage | 1099 | 0 | 01/26/2021 14:57:47 | 1 |

### `cdf_comir`

Lignes : 43 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 108 - derniere activite (dtem) : 05/26/2026 16:46:46 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 140 | 1 | 0 | 2 | Livraison le 12/06 matin sur RDV au 03.21.60.43.46 | 5823 | 2 | 05/26/2026 16:46:46 | 12 |
| 137 | 1 | 0 | 2 | Livraison le 12/06 matin sur RDV au 03.21.60.43.46  | 5822 | 1 | 05/26/2026 16:46:22 | 12 |
| 134 | 1 | 0 | 2 |  ATTENTION : PRODUCTION "ZERO DEFAULT" Echantillons de ch... | 5510 | 0 | 02/13/2026 08:51:04 | 57 |

### `cdf_comis`

Lignes : 379 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 771 - derniere activite (dtem) : 07/31/2026 09:55:38 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt, corbeille - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 776 | 1 | 0 | 1 | mit dans la  première allé du batiment 2 | 5993 | 1 | 07/31/2026 09:55:38 | 901 |
| 774 | 1 | 0 | 1 |  | 5953 | 1 | 07/16/2026 14:36:45 | 905 |
| 772 | 1 | 0 | 1 | mit dans la  première allé du batiment 2 | 5924 | 1 | 07/03/2026 17:47:38 | 7 |

### `cdf_entete`

Lignes : 4 572 - colonnes logiques : 62 - physiques : 87 - total corbeille comprise : 10 931 - derniere activite (dtem) : 08/24/2026 16:03:22 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numfou` sur numfou - `rs` sur rs - `groupefou` sur groupefou - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjc` | date |
| 12 | `numfou` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupefou` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `vref` | texte(50) |
| 42 | `nref` | texte(50) |
| 43 | `civ` | octet |
| 44 | `interlocuteur` | texte(50) |
| 45 | `tex` | texte(10) |
| 46 | `mail` | texte(128) |
| 47 | `com` | octet |
| 48 | `numint` | entier4ns |
| 49 | `dest` | texte(1) |
| 50 | `intfou` | entier4ns |
| 51 | `lrs` | texte(50) |
| 52 | `ladr1` | texte(50) |
| 53 | `ladr2` | texte(50) |
| 54 | `lcp` | texte(10) |
| 55 | `lville` | texte(50) |
| 56 | `lpays` | texte(50) |
| 57 | `modliv` | entier2ns |
| 58 | `amje` | date |
| 59 | `nbjliv` | entier2ns |
| 60 | `amjl` | date |
| 61 | `lcpays` | texte(5) |
| 62 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 87 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjc | numfou | rs | groupefou | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 14407 | 0 | 08/24/2026 16:03:22 | 4 |  | 6013 | FRANCE | FR | 1 | 4 | 08/24/2026 00:00:00 | 1092 | QRT Graphique | 1092 | 0 | 0 | 0 | 30520 | 1138.000000 | Avenue Sainte Barbe | ZI de Saint Martin | SAINT MARTIN DE VALGALGUES |  | 1 | E | 1138.000000 | 0 | 1 | 0.000000 | 227.600000 |
| 14405 | 0 | 08/24/2026 15:18:53 | 4 |  | 6012 | FRANCE | FR | 1 | 4 | 08/24/2026 00:00:00 | 1092 | QRT Graphique | 1092 | 0 | 0 | 0 | 30520 | 374.100000 | Avenue Sainte Barbe | ZI de Saint Martin | SAINT MARTIN DE VALGALGUES |  | 1 | E | 374.100000 | 0 | 1 | 0.000000 | 74.820000 |
| 14403 | 0 | 08/07/2026 17:02:58 | 7 |  | 6011 | CHINE | CN | 1 | 7 | 08/07/2026 00:00:00 | 1055 | JAOUR | 1055 | 0 | 0 | 1 | RUGAO | 58200.000000 | 399 WEST QIFENG ROAD, HIGH-TECH DEVELOPPEMENT ZONE | RUGAO | JIANGSU |  | 3 | E | 58200.000000 | 0 | 1 | 0.000000 | 0.000000 |

### `cdf_ligne`

Lignes : 9 214 - colonnes logiques : 53 - physiques : 62 - total corbeille comprise : 27 311 - derniere activite (dtem) : 08/24/2026 15:59:59 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `vref` | texte(50) |
| 15 | `nref` | texte(50) |
| 16 | `com` | octet |
| 17 | `lrs` | texte(50) |
| 18 | `ladr1` | texte(50) |
| 19 | `ladr2` | texte(50) |
| 20 | `lcp` | texte(10) |
| 21 | `lville` | texte(50) |
| 22 | `lpays` | texte(50) |
| 23 | `modliv` | entier2ns |
| 24 | `amje` | date |
| 25 | `nbjliv` | entier2ns |
| 26 | `amjl` | date |
| 27 | `lcpays` | texte(5) |
| 28 | `ligne` | entier4ns |
| 29 | `lpos` | octet |
| 30 | `code1` | texte(5) |
| 31 | `code2` | texte(20) |
| 32 | `code3` | texte(10) |
| 33 | `des1` | texte(50) |
| 34 | `fam` | octet |
| 35 | `sfam` | entier4ns |
| 36 | `gamme` | entier2ns |
| 37 | `qte` | reel8 |
| 38 | `des2` | texte(50) |
| 39 | `des3` | texte(50) |
| 40 | `des4` | texte(50) |
| 41 | `pa` | numerique |
| 42 | `pub` | numerique |
| 43 | `pun` | numerique |
| 44 | `depot` | texte(10) |
| 45 | `cua` | texte(5) |
| 46 | `sua` | octet |
| 47 | `vua` | numerique |
| 48 | `net` | octet |
| 49 | `ctva` | texte(5) |
| 50 | `docp` | octet |
| 51 | `qtb` | reel8 |
| 52 | `metb` | reel8 |
| 53 | `dteconf` | octet |

Dernieres lignes (les 30 premieres colonnes sur 62 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 42772 | 0 | 08/24/2026 15:59:59 | 4 | 20.00 | 6013 | 1 | 1138.000000 | 1138.000000 | 1 | 0.000000 | 227.600000 | 1365.600000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | FIELDTURF TARKETT | 91 rue Chateaubriand |  | 62260 | AUCHEL |
| 42770 | 0 | 08/24/2026 15:17:37 | 4 | 20.00 | 6012 | 1 | 374.100000 | 374.100000 | 1 | 0.000000 | 74.820000 | 448.920000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | CARREFOUR SUPPLY CHAIN | Madame Delphine MERLE | ZAC de Sennecé  | 71000 | SENNECE LES MACAON  |
| 42757 | 0 | 08/07/2026 17:02:55 | 7 | 0.00 | 6011 | 9 | 3492.000000 | 3492.000000 | 1 | 0.000000 | 0.000000 | 3492.000000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SIFA | 45 rue Rollin |  | 59100 | ROUBAIX |

### `cdi_comic`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `cdi_comif`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `cdi_entete`

Lignes : 52 - colonnes logiques : 51 - physiques : 80 - total corbeille comprise : 254 - derniere activite (dtem) : 04/16/2026 08:59:42 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numclt` sur numclt - `edi` sur edi - `tdec` sur tdec - `amjp` sur amjp - `amjr` sur amjr - `pos` sur pos - `ndec` sur ndec - `code1m` sur code1m - `code2m` sur code2m - `code3m` sur code3m - `prio` sur prio - `mac1p` sur mac1p - `tcdemar` sur tcdemar - `dosplavu` sur dosplavu - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `salm` | entier2ns |
| 4 | `dtem` | horodatage |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `type` | entier2ns |
| 8 | `operateur` | entier2ns |
| 9 | `amjc` | date |
| 10 | `numclt` | entier4ns |
| 11 | `edi` | octet |
| 12 | `tdec` | entier4ns |
| 13 | `amjp` | horodatage |
| 14 | `amjr` | date |
| 15 | `pos` | octet |
| 16 | `ndec` | entier8ns |
| 17 | `code1m` | texte(5) |
| 18 | `code2m` | texte(20) |
| 19 | `code3m` | texte(10) |
| 20 | `prio` | entier4ns |
| 21 | `mac1p` | texte(10) |
| 22 | `tcdemar` | octet |
| 23 | `qte` | reel8 |
| 24 | `oftl` | reel8 |
| 25 | `ofta` | reel8 |
| 26 | `onbl` | entier4ns |
| 27 | `onba` | entier4ns |
| 28 | `typematbasebof` | octet |
| 29 | `laizem` | entier4ns |
| 30 | `nbcoul` | octet |
| 31 | `vit` | entier4ns |
| 32 | `machine` | texte(50) |
| 33 | `travail` | entier4ns |
| 34 | `tpcm` | reel4 |
| 35 | `tpsm` | reel4 |
| 36 | `tpst` | reel4 |
| 37 | `cond` | texte(10) |
| 38 | `tpcco` | reel4 |
| 39 | `tpsco` | reel4 |
| 40 | `pprio` | octet |
| 41 | `amjpi` | horodatage |
| 42 | `ptpsp` | reel4 |
| 43 | `ptpsc` | reel4 |
| 44 | `pcom` | texte(30) |
| 45 | `amjpe` | date |
| 46 | `ncli` | entier4ns |
| 47 | `ntei` | entier4ns |
| 48 | `nrec` | entier4ns |
| 49 | `ama` | octet |
| 50 | `dosplavu` | octet |
| 51 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 80 - tout est dans le JSON) :

| id | corbeille | salm | dtem | numero | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | type | operateur | amjc | numclt | edi | tdec | amjp | amjr | pos | ndec | code1m | code2m | code3m | prio | mac1p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 359 | 0 | 907 | 04/01/2026 18:44:30 | 1069 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 9998 | 03/31/2026 00:00:00 | 0 | 0 | 2 | 03/31/2026 14:07:07 | 03/31/2026 00:00:00 | 2 | 2590 |  |  |  | 5 |  |
| 357 | 0 | 912 | 04/01/2026 11:34:21 | 1068 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 9998 | 03/31/2026 00:00:00 | 0 | 0 | 2 | 03/31/2026 14:05:01 | 03/31/2026 00:00:00 | 2 | 2590 |  |  |  | 5 |  |
| 344 | 0 | 913 | 04/03/2026 12:45:39 | 1067 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 9998 | 03/31/2026 00:00:00 | 245 | 0 | 2 | 03/31/2026 11:12:03 | 03/31/2026 00:00:00 | 3 | 2793 | 886 | 0315 |  | 5 |  |

### `cdi_ligne`

Lignes : 76 - colonnes logiques : 55 - physiques : 120 - total corbeille comprise : 340 - derniere activite (dtem) : 04/16/2026 08:59:42 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `numero` sur numero - `ligne` sur ligne - `numclt` sur numclt - `nocde` sur nocde - `lgcde` sur lgcde - `amjl` sur amjl - `amje` sur amje - `lpos` sur lpos - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `typematbasebof` | octet |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `lai` | entier4ns |
| 10 | `numero` | entier8ns |
| 11 | `ligne` | entier4ns |
| 12 | `numclt` | entier4ns |
| 13 | `nocde` | entier8ns |
| 14 | `lgcde` | entier4ns |
| 15 | `amjl` | date |
| 16 | `amje` | date |
| 17 | `lpos` | octet |
| 18 | `qte` | reel8 |
| 19 | `modliv` | entier2ns |
| 20 | `nbj` | entier4ns |
| 21 | `mach` | texte(50) |
| 22 | `tra` | entier4ns |
| 23 | `tpsm` | reel4 |
| 24 | `tpst` | reel4 |
| 25 | `cond` | texte(10) |
| 26 | `tpsco` | reel4 |
| 27 | `matcode1` | texte(25) |
| 28 | `matcode2` | texte(100) |
| 29 | `matcode3` | texte(50) |
| 30 | `qtem` | reel8 |
| 31 | `qtemhg` | reel8 |
| 32 | `pcod1` | texte(5) |
| 33 | `pcod2` | texte(20) |
| 34 | `laipel` | entier4ns |
| 35 | `qtep` | reel8 |
| 36 | `dcod1` | texte(25) |
| 37 | `dcod2` | texte(100) |
| 38 | `laidor` | entier4ns |
| 39 | `qted` | reel8 |
| 40 | `vcod1` | texte(5) |
| 41 | `vcod2` | texte(20) |
| 42 | `qtev` | reel8 |
| 43 | `vbcod1` | texte(5) |
| 44 | `vbcod2` | texte(20) |
| 45 | `qtevb` | reel8 |
| 46 | `lab` | octet |
| 47 | `ncli` | entier4ns |
| 48 | `ntei` | entier4ns |
| 49 | `nrec` | entier4ns |
| 50 | `com` | octet |
| 51 | `nbt` | entier4ns |
| 52 | `num1` | texte(50) |
| 53 | `num2` | texte(50) |
| 54 | `amapose` | entier4ns |
| 55 | `vcouv` | texte(10) |

Dernieres lignes (les 30 premieres colonnes sur 120 - tout est dans le JSON) :

| id | corbeille | dtem | salm | typematbasebof | code1 | code2 | code3 | lai | lai_2 | lai_3 | lai_4 | lai_5 | numero | ligne | numclt | nocde | lgcde | amjl | amje | lpos | qte | modliv | nbj | mach | mach_2 | mach_3 | mach_4 | mach_5 | tra |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 435 | 0 | 03/31/2026 16:33:33 | 57 | 1 | 1183 | 0033 |  | 494 | 0 | 0 | 0 | 0 | 1069 | 4 | 1287 | 9931442 | 3 | 05/02/2026 00:00:00 | 04/30/2026 00:00:00 | 0 | 500000 | 1 | 2 | 1 |  |  |  |  | 1 |
| 433 | 0 | 03/31/2026 16:29:31 | 57 | 1 | 1183 | 0033 |  | 494 | 0 | 0 | 0 | 0 | 1069 | 3 | 1284 | 9931441 | 3 | 05/02/2026 00:00:00 | 04/30/2026 00:00:00 | 0 | 500000 | 1 | 2 | 1 |  |  |  |  | 1 |
| 431 | 0 | 03/31/2026 16:31:34 | 57 | 1 | 1183 | 0033 |  | 494 | 0 | 0 | 0 | 0 | 1069 | 2 | 1285 | 9931440 | 3 | 05/02/2026 00:00:00 | 04/30/2026 00:00:00 | 0 | 500000 | 1 | 2 | 1 |  |  |  |  | 1 |

### `cdi_res`

Lignes : 137 - colonnes logiques : 28 - physiques : 37 - total corbeille comprise : 165 - derniere activite (dtem) : 03/31/2026 14:22:05 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `type` sur type - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `lai` sur lai - `numero` sur numero - `ordre` sur ordre - `clef` sur numero, ordre, type, code1, code2, code3, lai - `clefcorbeille` sur numero, ordre, type, code1, code2, code3, lai, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `type` | entier4ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `lai` | entier4ns |
| 10 | `qtec` | reel8 |
| 11 | `qte` | reel8 |
| 12 | `qtes` | reel8 |
| 13 | `qtev` | reel8 |
| 14 | `qtehg` | reel8 |
| 15 | `m2qte` | reel8 |
| 16 | `m2pri` | numerique |
| 17 | `com` | octet |
| 18 | `mataj` | octet |
| 19 | `numero` | entier8ns |
| 20 | `lpos` | octet |
| 21 | `composant` | octet |
| 22 | `compocode1nomen` | texte(5) |
| 23 | `compocode2nomen` | texte(20) |
| 24 | `compocode3nomen` | texte(10) |
| 25 | `compotypenomen` | entier4ns |
| 26 | `compoqte` | reel8 |
| 27 | `compotypeqte` | octet |
| 28 | `ordre` | texte(10) |

Dernieres lignes (les 30 premieres colonnes sur 37 - tout est dans le JSON) :

| id | corbeille | dtem | salm | type | code1 | code2 | code3 | lai | qtec | qte | qtes | qtev | qtehg | m2qte | m2pri | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | mataj | numero | lpos | composant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 367 | 0 | 03/31/2026 14:20:19 | 9998 | 2 | 1183 | 0001 |  | 494 | 146521 | 146521 | 0 | 0 | 133349.997492 | 72381.37 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1069 | 0 | 1 |
| 366 | 0 | 03/31/2026 14:07:35 | 9998 | 7 | 1 | 0002 |  | 0 | 40.363905729 | 40.363905729 | 0 | 0 | 31.290576892 | 40.36 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1069 | 0 | 1 |
| 365 | 0 | 03/31/2026 14:20:19 | 9998 | 3 | 1 | 0003 |  | 494 | 146521 | 146521 | 0 | 0 | 133349.997492 | 72381.37 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1069 | 0 | 1 |

### `cdm_appel`

Lignes : 167 - colonnes logiques : 24 - physiques : 33 - total corbeille comprise : 334 - derniere activite (dtem) : 01/09/2024 10:56:46 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `amje` sur amje - `ligne` sur ligne - `amjl` sur amjl - `lpos` sur lpos - `qte` sur qte - `appel` sur appel - `clef` sur numero, ligne, appel - `clefcorbeille` sur numero, ligne, appel, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `amje` | date |
| 7 | `vref` | texte(50) |
| 8 | `nref` | texte(50) |
| 9 | `com` | octet |
| 10 | `lrs` | texte(50) |
| 11 | `ladr1` | texte(50) |
| 12 | `ladr2` | texte(50) |
| 13 | `lcp` | texte(10) |
| 14 | `lville` | texte(50) |
| 15 | `lpays` | texte(50) |
| 16 | `modliv` | entier2ns |
| 17 | `lcpays` | texte(5) |
| 18 | `ligne` | entier4ns |
| 19 | `amjl` | date |
| 20 | `lpos` | octet |
| 21 | `qte` | reel8 |
| 22 | `depot` | texte(10) |
| 23 | `appel` | entier4ns |
| 24 | `nbjliv` | entier2ns |

Dernieres lignes (les 30 premieres colonnes sur 33 - tout est dans le JSON) :

| id | corbeille | dtem | salm | numero | amje | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville | lpays | modliv | lcpays | ligne | amjl | lpos | qte |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 402 | 0 | 01/09/2024 10:56:46 | 12 | 576 | 01/09/2024 00:00:00 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 |  | 1 | 01/11/2024 00:00:00 | 0 | 600000 |
| 400 | 0 | 01/09/2024 10:54:37 | 12 | 576 | 01/09/2024 00:00:00 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 |  | 1 | 01/11/2024 00:00:00 | 0 | 600000 |
| 391 | 0 | 01/09/2024 10:53:10 | 12 | 576 | 05/13/2024 00:00:00 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 |  | 1 | 05/16/2024 00:00:00 | 0 | 300000 |

### `cdm_com`

Lignes : 903 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 1 843 - derniere activite (dtem) : 07/30/2026 15:54:43 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numappel` sur numappel - `clef` sur numpiece, numligne, numappel, typt - `clefcorbeille` sur numpiece, numligne, numappel, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `numappel` | entier4ns |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | numappel | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|
| 2002 | 1 | 0 | 1 | NE LIVRER QUE LA QUANTITE COMMANDEE TOLERANCE 0%  | 762 | 0 | 0 | 07/30/2026 15:54:43 | 4 |
| 2000 | 1 | 0 | 1 | IMPERATIF : Mettre 2 étiquettes identiques sur la petite ... | 760 | 1 | 0 | 07/28/2026 14:31:29 | 57 |
| 1998 | 1 | 0 | 1 |   | 760 | 0 | 0 | 07/28/2026 14:28:42 | 57 |

### `cdm_comif`

Lignes : 261 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 522 - derniere activite (dtem) : 07/28/2026 14:28:42 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numappel` sur numappel - `clef` sur numpiece, numligne, numappel, typt - `clefcorbeille` sur numpiece, numligne, numappel, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `numappel` | entier4ns |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | numappel | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|
| 611 | 1 | 0 | 1 | ATTENTION Adresse de facturation  | 760 | 0 | 0 | 07/28/2026 14:28:42 | 57 |
| 609 | 1 | 0 | 2 | CENTRE DE COUT (1107862) CODE FOURNISSEUR 1000020593 | 758 | 0 | 0 | 07/20/2026 16:36:17 | 4 |
| 607 | 1 | 0 | 1 | Envoyer par mail facture.h010.hsellier@hermes.com | 758 | 0 | 0 | 07/20/2026 16:36:17 | 4 |

### `cdm_comil`

Lignes : 370 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 751 - derniere activite (dtem) : 07/30/2026 15:54:43 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numappel` sur numappel - `clef` sur numpiece, numligne, numappel, typt - `clefcorbeille` sur numpiece, numligne, numappel, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `numappel` | entier4ns |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | numappel | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|
| 883 | 1 | 0 | 1 | NE LIVRER QUE LA QUANTITE COMMANDEE  TOLERANCE 0%  | 762 | 0 | 0 | 07/30/2026 15:54:43 | 4 |
| 881 | 1 | 0 | 1 |  EXPEDITION : Prise de RDV auprès de la cellule marchand ... | 760 | 0 | 0 | 07/28/2026 14:28:42 | 57 |
| 879 | 1 | 0 | 2 |   | 758 | 0 | 0 | 07/20/2026 16:36:17 | 4 |

### `cdm_comis`

Lignes : 171 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 348 - derniere activite (dtem) : 07/28/2026 14:31:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numappel` sur numappel - `clef` sur numpiece, numligne, numappel, typt - `clefcorbeille` sur numpiece, numligne, numappel, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `numappel` | entier4ns |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | numappel | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|
| 355 | 1 | 0 | 1 | C362 = 240.000 ETQ | 760 | 1 | 0 | 07/28/2026 14:31:29 | 57 |
| 353 | 1 | 0 | 1 | C111 = 600 000 ETIQ: (PRODUCTION 02/2022 - ETIQUETTE SUPP... | 754 | 1 | 0 | 07/20/2026 15:49:41 | 4 |
| 351 | 1 | 0 | 1 |   | 749 | 1 | 0 | 06/26/2026 10:13:53 | 57 |

### `cdm_comit`

Lignes : 0 - colonnes logiques : 10 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numappel` sur numappel - `clef` sur numpiece, numligne, numappel, typt - `clefcorbeille` sur numpiece, numligne, numappel, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `numappel` | entier4ns |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |

### `cdm_entete`

Lignes : 727 - colonnes logiques : 64 - physiques : 89 - total corbeille comprise : 1 560 - derniere activite (dtem) : 07/30/2026 16:02:25 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numclt` sur numclt - `rs` sur rs - `groupeclt` sur groupeclt - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `numrep` sur numrep - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjc` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `vref` | texte(50) |
| 42 | `nref` | texte(50) |
| 43 | `civ` | octet |
| 44 | `interlocuteur` | texte(50) |
| 45 | `tex` | texte(10) |
| 46 | `mail` | texte(128) |
| 47 | `com` | octet |
| 48 | `numint` | entier4ns |
| 49 | `dest` | texte(1) |
| 50 | `intclt` | entier4ns |
| 51 | `lrs` | texte(50) |
| 52 | `ladr1` | texte(50) |
| 53 | `ladr2` | texte(50) |
| 54 | `lcp` | texte(10) |
| 55 | `lville` | texte(50) |
| 56 | `lpays` | texte(50) |
| 57 | `modliv` | entier2ns |
| 58 | `amjo` | date |
| 59 | `amjf` | date |
| 60 | `lcpays` | texte(5) |
| 61 | `posacompte` | texte(1) |
| 62 | `numrep` | entier2ns |
| 63 | `adrf` | entier4 |
| 64 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 89 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjc | numclt | rs | groupeclt | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1862 | 0 | 07/30/2026 16:02:25 | 4 | 04.77.92.44.44 | 762 | FRANCE | FR | 1 | 4 | 07/30/2026 00:00:00 | 1033 | ALTAVIA AUVERGNE-RHONE-ALPES | 1004 | 0 | 0 | 1 | 42000 | 18957.000000 | 1 rue Pablo PICASSO BAT L'imprimerie |  | SAINT-ETIENNE |  | 1 | E | 18957.000000 | 0 | 1 | 0.000000 | 3791.400000 |
| 1860 | 0 | 07/30/2026 08:27:00 | 57 |  | 761 | FRANCE | FR | 1 | 57 | 07/30/2026 00:00:00 | 986 | BAILLINDUSTRIE | 986 | 0 | 0 | 3 | 66600 | 1530.340000 | 2 avenue Jacques Vaucanson |  | RIVESALTES |  | 1 | E | 1530.340000 | 0 | 1 | 0.000000 | 306.070000 |
| 1858 | 0 | 07/28/2026 14:31:34 | 57 |  | 760 | FRANCE | FR | 1 | 57 | 07/28/2026 00:00:00 | 382 | KIABI | 382 | 0 | 0 | 1 | 59260 | 19548.000000 | 4a rue du moulin de Lezennes |  | LEZENNES |  | 1 | E | 19548.000000 | 0 | 1 | 0.000000 | 3909.600000 |

### `cdm_ligne`

Lignes : 1 087 - colonnes logiques : 61 - physiques : 70 - total corbeille comprise : 2 799 - derniere activite (dtem) : 08/06/2026 09:14:14 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `lpos` sur lpos - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `orig` sur orig - `prod` sur prod - `pcol` sur pcol - `amjo` sur amjo - `amjf` sur amjf - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `vref` | texte(50) |
| 15 | `nref` | texte(50) |
| 16 | `com` | octet |
| 17 | `lrs` | texte(50) |
| 18 | `ladr1` | texte(50) |
| 19 | `ladr2` | texte(50) |
| 20 | `lcp` | texte(10) |
| 21 | `lville` | texte(50) |
| 22 | `lpays` | texte(50) |
| 23 | `modliv` | entier2ns |
| 24 | `suv` | octet |
| 25 | `vuv` | numerique |
| 26 | `lcpays` | texte(5) |
| 27 | `ligne` | entier4ns |
| 28 | `lpos` | octet |
| 29 | `code1` | texte(5) |
| 30 | `code2` | texte(20) |
| 31 | `code3` | texte(10) |
| 32 | `des1` | texte(50) |
| 33 | `fam` | octet |
| 34 | `sfam` | entier4ns |
| 35 | `gamme` | entier2ns |
| 36 | `qte` | reel8 |
| 37 | `des2` | texte(50) |
| 38 | `des3` | texte(50) |
| 39 | `des4` | texte(50) |
| 40 | `pa` | numerique |
| 41 | `pub` | numerique |
| 42 | `pun` | numerique |
| 43 | `depot` | texte(10) |
| 44 | `net` | octet |
| 45 | `ctva` | texte(5) |
| 46 | `orig` | octet |
| 47 | `prod` | octet |
| 48 | `pcol` | octet |
| 49 | `cuv` | texte(5) |
| 50 | `npiec` | entier8ns |
| 51 | `lpiec` | entier4ns |
| 52 | `qtep` | reel8 |
| 53 | `eetiq` | octet |
| 54 | `amjo` | date |
| 55 | `lab` | octet |
| 56 | `amjf` | date |
| 57 | `icdm` | entier4ns |
| 58 | `comrep` | reel4 |
| 59 | `nbeliv` | entier4 |
| 60 | `bat` | octet |
| 61 | `amjb` | date |

Dernieres lignes (les 30 premieres colonnes sur 70 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4854 | 0 | 07/30/2026 16:02:19 | 4 | 20.00 | 762 | 1 | 18957.000000 | 18957.000000 | 1 | 0.000000 | 3791.400000 | 22748.400000 | AC-SEB-13729/C002 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | A CONFIRMER |  |  | 00000 | A CONFIRMER -> 00000 |
| 4851 | 0 | 07/30/2026 08:26:51 | 57 | 20.00 | 761 | 1 | 1530.340000 | 1530.340000 | 1 | 0.000000 | 306.070000 | 1836.410000 | CF4883 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | BAILLINDUSTRIE | 2 avenue Jacques Vaucanson |  | 66000 | RIVESALTES |
| 4848 | 0 | 07/28/2026 14:31:29 | 57 | 20.00 | 760 | 1 | 19548.000000 | 19548.000000 | 1 | 0.000000 | 3909.600000 | 23457.600000 | STOCK 07-2026 |  | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | SIMASTOCK LAMBRES | SIMASTOCK pour KIABI logistique | 70 rue Simone des Forest | 59552 | LAMBRES LEZ DOUAI |

### `col_ligne`

Lignes : 257 - colonnes logiques : 24 - physiques : 41 - total corbeille comprise : 514 - derniere activite (dtem) : 02/25/2026 15:30:34 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `amjc` sur amjc - `ligne` sur ligne - `operateur` sur operateur - `numbl` sur numbl - `colis` sur colis - `numclt` sur numclt - `numpal` sur numpal - `numcde` sur numcde - `lignecde` sur lignecde - `clef` sur numero, ligne, colis - `clefcorbeille` sur numero, ligne, colis, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `amjc` | date |
| 8 | `ligne` | entier4ns |
| 9 | `operateur` | entier2ns |
| 10 | `numbl` | entier8ns |
| 11 | `num1` | texte(50) |
| 12 | `num2` | texte(50) |
| 13 | `colis` | entier4ns |
| 14 | `numclt` | entier4ns |
| 15 | `numpal` | entier4ns |
| 16 | `numcde` | entier8ns |
| 17 | `lignecde` | entier4ns |
| 18 | `typfp` | octet |
| 19 | `des1` | texte(50) |
| 20 | `nbprod` | numerique |
| 21 | `nbsprod` | numerique |
| 22 | `imp` | octet |
| 23 | `typp` | octet |
| 24 | `edi` | octet |

Dernieres lignes (les 30 premieres colonnes sur 41 - tout est dans le JSON) :

| id | corbeille | dtem | salm | numero | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | amjc | ligne | operateur | numbl | num1 | num2 | colis | numclt | numpal | numcde | lignecde | typfp | des1 | nbprod | nbprod_2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1003 | 0 | 02/25/2026 15:30:34 | 9999 | 9929841 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 02/25/2026 00:00:00 | 6 | 9999 | 0 |  |  | 4 | 1220 | 0 | 0 | 0 | 1 | 1220 0001 | 5.000 | 1.000 |
| 1001 | 0 | 02/25/2026 15:30:34 | 9999 | 9929841 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 02/25/2026 00:00:00 | 6 | 9999 | 0 |  |  | 3 | 1220 | 0 | 0 | 0 | 1 | 1220 0001 | 5.000 | 1.000 |
| 999 | 0 | 02/25/2026 15:30:34 | 9999 | 9929841 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 02/25/2026 00:00:00 | 6 | 9999 | 0 |  |  | 2 | 1220 | 0 | 0 | 0 | 1 | 1220 0001 | 5.000 | 1.000 |

### `com_entete`

Lignes : 0 - colonnes logiques : 28 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numclt` sur numclt - `cp` sur cp - `numrep` sur numrep - `typclt` sur typclt - `typep` sur typep - `amjp` sur amjp - `pos` sur pos - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `messa` | texte(1500) |
| 5 | `salm` | entier2ns |
| 6 | `numero` | entier8ns |
| 7 | `type` | texte(10) |
| 8 | `operateur` | entier2ns |
| 9 | `amjc` | horodatage |
| 10 | `numclt` | entier4ns |
| 11 | `cp` | texte(10) |
| 12 | `civ` | octet |
| 13 | `interlocuteur` | texte(50) |
| 14 | `numrep` | entier2ns |
| 15 | `typclt` | octet |
| 16 | `typep` | texte(10) |
| 17 | `amjp` | horodatage |
| 18 | `tel` | texte(20) |
| 19 | `civp` | octet |
| 20 | `interlocuteurp` | texte(50) |
| 21 | `telp` | texte(20) |
| 22 | `orpiece` | entier4ns |
| 23 | `nbpiece` | entier4ns |
| 24 | `piece` | texte(1024) |
| 25 | `amjm` | horodatage |
| 26 | `sal` | entier2ns |
| 27 | `pos` | octet |
| 28 | `ale` | octet |

### `cpr_ax`

Lignes : 285 - colonnes logiques : 30 - physiques : 39 - derniere activite (dtem) : 01/09/2026 15:31:09 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `fam` | octet |
| 16 | `sfam` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `qte` | reel8 |
| 19 | `des2` | texte(50) |
| 20 | `des3` | texte(50) |
| 21 | `des4` | texte(50) |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `cuv` | texte(5) |
| 25 | `nligne` | entier4ns |
| 26 | `pma` | reel4 |
| 27 | `pun` | numerique |
| 28 | `noye` | octet |
| 29 | `htfp` | numerique |
| 30 | `htnoy` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 39 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | fam | sfam | gamme | qte | des2 | des3 | des4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 293 | 01/09/2026 15:31:09 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |
| 292 | 01/09/2026 15:30:56 | 9998 | 0 | 3 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 0 |  | Emballage |  | Frais d'emballage | 0 | 0 | 0 | 0 |  |  |  |
| 291 | 01/09/2026 15:30:56 | 9998 | 0 | 3 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 0 |  | Grattable |  | Encre grattable | 0 | 0 | 0 | 0 |  |  |  |

### `cpr_comct`

Lignes : 0 - colonnes logiques : 8 - physiques : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `typt` | octet |
| 4 | `com` | texte(750) |
| 5 | `numpiece` | entier8ns |
| 6 | `numligne` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `cpr_comil`

Lignes : 0 - colonnes logiques : 8 - physiques : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `typt` | octet |
| 4 | `com` | texte(750) |
| 5 | `numpiece` | entier8ns |
| 6 | `numligne` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `cpr_lab`

Lignes : 52 - colonnes logiques : 30 - physiques : 39 - derniere activite (dtem) : 01/09/2026 15:31:07 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `fam` | octet |
| 16 | `sfam` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `qte` | reel8 |
| 19 | `des2` | texte(50) |
| 20 | `des3` | texte(50) |
| 21 | `des4` | texte(50) |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `cuv` | texte(5) |
| 25 | `nligne` | entier4ns |
| 26 | `pma` | reel4 |
| 27 | `pun` | numerique |
| 28 | `noye` | octet |
| 29 | `htfp` | numerique |
| 30 | `htnoy` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 39 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | fam | sfam | gamme | qte | des2 | des3 | des4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 106 | 01/09/2026 15:31:07 | 9998 | 2601003 | 0 | 212.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |
| 105 | 01/09/2026 15:31:07 | 9998 | 2601003 | 3 | 212.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 1 | FR | FRAIS_DE_CLICHE |  | Frais de cliché | 102 | 2 | 0 | 4 |  |  |  |
| 104 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |

### `cpr_mat`

Lignes : 24 - colonnes logiques : 34 - physiques : 43 - derniere activite (dtem) : 01/09/2026 15:31:09 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `qte` sur qte - `nligne` sur nligne - `typemat` sur typemat - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `qte` | reel8 |
| 16 | `des2` | texte(50) |
| 17 | `des3` | texte(50) |
| 18 | `des4` | texte(50) |
| 19 | `pa` | numerique |
| 20 | `pub` | numerique |
| 21 | `cuv` | texte(5) |
| 22 | `nligne` | entier4ns |
| 23 | `pma` | reel4 |
| 24 | `pun` | numerique |
| 25 | `noye` | octet |
| 26 | `htfp` | numerique |
| 27 | `htnoy` | numerique |
| 28 | `typemat` | entier4ns |
| 29 | `totmlhg` | entier8ns |
| 30 | `totmlag` | entier8ns |
| 31 | `totm2hg` | entier8ns |
| 32 | `totm2ag` | entier8ns |
| 33 | `machine` | texte(10) |
| 34 | `travail` | entier4ns |

Dernieres lignes (les 30 premieres colonnes sur 43 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | qte | des2 | des3 | des4 | pa | pub | cuv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24 | 01/09/2026 15:31:09 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 23 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 22 | 11/17/2025 11:35:05 | 9999 | 2511001 | 3 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1.00000 | 1 | 886 | 0003 | 510 | Couché Mat Blanc, Adh. Enlevable, Glassine Jaune | 0 | 80g Etigloss, 19g PS 4007, 60g G. release 127522 |  |  | 0.285000 | 0.285000 | M² |

### `cpr_mo`

Lignes : 24 - colonnes logiques : 33 - physiques : 42 - derniere activite (dtem) : 01/09/2026 15:31:08 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `qte` | reel8 |
| 16 | `des2` | texte(50) |
| 17 | `des3` | texte(50) |
| 18 | `des4` | texte(50) |
| 19 | `pa` | numerique |
| 20 | `pub` | numerique |
| 21 | `cuv` | texte(5) |
| 22 | `nligne` | entier4ns |
| 23 | `pma` | reel4 |
| 24 | `pun` | numerique |
| 25 | `noye` | octet |
| 26 | `htfp` | numerique |
| 27 | `htnoy` | numerique |
| 28 | `mtp` | numerique |
| 29 | `vit` | reel4 |
| 30 | `ner` | texte(50) |
| 31 | `dman` | reel4 |
| 32 | `dmax` | entier4ns |
| 33 | `eman` | reel4 |

Dernieres lignes (les 30 premieres colonnes sur 42 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | qte | des2 | des3 | des4 | pa | pub | cuv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 24 | 01/09/2026 15:31:08 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 23 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 22 | 11/17/2025 11:35:05 | 9999 | 2511001 | 3 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 1 | 4 | 1 | 1 | COHESIO 1 | 0 | Classique |  |  | 142.000000 | 142.000000 | U |

### `cpr_out`

Lignes : 22 - colonnes logiques : 28 - physiques : 37 - derniere activite (dtem) : 01/09/2026 15:31:08 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `qte` | reel8 |
| 16 | `des2` | texte(50) |
| 17 | `des3` | texte(50) |
| 18 | `des4` | texte(50) |
| 19 | `pa` | numerique |
| 20 | `pub` | numerique |
| 21 | `cuv` | texte(5) |
| 22 | `nligne` | entier4ns |
| 23 | `pma` | reel4 |
| 24 | `pun` | numerique |
| 25 | `noye` | octet |
| 26 | `htfp` | numerique |
| 27 | `htnoy` | numerique |
| 28 | `pap` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 37 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | qte | des2 | des3 | des4 | pa | pub | cuv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 01/09/2026 15:31:08 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 28 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 |  |  |  | 0.000000 | 0.000000 |  |
| 27 | 11/17/2025 11:35:05 | 9999 | 2511001 | 3 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 1 | 2 | 1897 |  | Ronde 40,000 L X 40,000 A | 1 | - Espaces : 3,000 L X 2,720 A | - Poses  : 11 L X 11 A | - Denture : 148 | 0.000000 | 0.000000 | U |

### `cpr_pre`

Lignes : 0 - colonnes logiques : 30 - physiques : 0

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `fam` | octet |
| 16 | `sfam` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `qte` | reel8 |
| 19 | `des2` | texte(50) |
| 20 | `des3` | texte(50) |
| 21 | `des4` | texte(50) |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `cuv` | texte(5) |
| 25 | `nligne` | entier4ns |
| 26 | `pma` | reel4 |
| 27 | `pun` | numerique |
| 28 | `noye` | octet |
| 29 | `htfp` | numerique |
| 30 | `htnoy` | numerique |

### `cpr_pv`

Lignes : 35 - colonnes logiques : 168 - physiques : 205 - derniere activite (dtem) : 07/17/2026 08:54:51 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `ligne` sur ligne - `clef` sur numero, ligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `cpays` | texte(5) |
| 6 | `operateur` | entier2ns |
| 7 | `amjd` | date |
| 8 | `numclt` | entier4ns |
| 9 | `groupeclt` | entier4ns |
| 10 | `cat1` | entier2ns |
| 11 | `cat2` | entier2ns |
| 12 | `cat3` | entier2ns |
| 13 | `fam` | octet |
| 14 | `cp` | texte(10) |
| 15 | `com` | octet |
| 16 | `numrep` | entier2ns |
| 17 | `typclt` | octet |
| 18 | `ligne` | entier4ns |
| 19 | `type` | entier2ns |
| 20 | `code3` | texte(10) |
| 21 | `code2` | texte(20) |
| 22 | `code1` | texte(5) |
| 23 | `sfam` | entier4ns |
| 24 | `gamme` | entier2ns |
| 25 | `pvu` | numerique |
| 26 | `pvt` | numerique |
| 27 | `typp` | octet |
| 28 | `forme` | octet |
| 29 | `typfp` | octet |
| 30 | `ftx` | numerique |
| 31 | `fty` | numerique |
| 32 | `qte` | reel8 |
| 33 | `nbfab` | entier4ns |
| 34 | `nbliv` | entier4ns |
| 35 | `nbcoul` | octet |
| 36 | `quadri` | octet |
| 37 | `nbserie` | entier4ns |
| 38 | `pencre` | entier4ns |
| 39 | `nbcclic` | entier4ns |
| 40 | `nbctein` | entier4ns |
| 41 | `nbrtein` | entier4ns |
| 42 | `nbpl` | entier4ns |
| 43 | `nbpa` | entier4ns |
| 44 | `espa` | reel4 |
| 45 | `espl` | reel4 |
| 46 | `eche` | reel8 |
| 47 | `laizetr` | entier4ns |
| 48 | `laizetp` | entier4ns |
| 49 | `laizets` | entier4ns |
| 50 | `dor` | octet |
| 51 | `pel` | octet |
| 52 | `ver` | octet |
| 53 | `verb` | octet |
| 54 | `seri` | octet |
| 55 | `gauf` | octet |
| 56 | `grat` | octet |
| 57 | `pgra` | entier4ns |
| 58 | `vers` | octet |
| 59 | `pver` | entier4ns |
| 60 | `pecrs` | entier4ns |
| 61 | `pvers` | entier4ns |
| 62 | `pverb` | entier4ns |
| 63 | `perf` | octet |
| 64 | `num` | octet |
| 65 | `faclab` | octet |
| 66 | `pa1lab` | numerique |
| 67 | `tpa1lab` | numerique |
| 68 | `ppr1lab` | reel4 |
| 69 | `pmnlab` | reel4 |
| 70 | `pa2lab` | numerique |
| 71 | `tpa2lab` | numerique |
| 72 | `ppr2lab` | reel4 |
| 73 | `fplab` | numerique |
| 74 | `noylab` | octet |
| 75 | `mglab` | octet |
| 76 | `pa1mo` | numerique |
| 77 | `tpa1mo` | numerique |
| 78 | `ppr1mo` | reel4 |
| 79 | `pmnmo` | reel4 |
| 80 | `pa2mo` | numerique |
| 81 | `tpa2mo` | numerique |
| 82 | `ppr2mo` | reel4 |
| 83 | `fpmo` | numerique |
| 84 | `noymo` | octet |
| 85 | `mgmo` | octet |
| 86 | `pa1out` | numerique |
| 87 | `tpa1out` | numerique |
| 88 | `ppr1out` | reel4 |
| 89 | `pmnout` | reel4 |
| 90 | `pa2out` | numerique |
| 91 | `tpa2out` | numerique |
| 92 | `ppr2out` | reel4 |
| 93 | `fpout` | numerique |
| 94 | `mgout` | octet |
| 95 | `pa1mat` | numerique |
| 96 | `tpa1mat` | numerique |
| 97 | `ppr1mat` | reel4 |
| 98 | `pmnmat` | reel4 |
| 99 | `pa2mat` | numerique |
| 100 | `tpa2mat` | numerique |
| 101 | `ppr2mat` | reel4 |
| 102 | `fpmat` | numerique |
| 103 | `mgmat` | octet |
| 104 | `pa1st` | numerique |
| 105 | `tpa1st` | numerique |
| 106 | `ppr1st` | reel4 |
| 107 | `pmnst` | reel4 |
| 108 | `pa2st` | numerique |
| 109 | `tpa2st` | numerique |
| 110 | `ppr2st` | reel4 |
| 111 | `fpst` | numerique |
| 112 | `noyst` | octet |
| 113 | `mgst` | octet |
| 114 | `pa1ax` | numerique |
| 115 | `tpa1ax` | numerique |
| 116 | `ppr1ax` | reel4 |
| 117 | `pmnax` | reel4 |
| 118 | `pa2ax` | numerique |
| 119 | `tpa2ax` | numerique |
| 120 | `ppr2ax` | reel4 |
| 121 | `fpax` | numerique |
| 122 | `noyax` | octet |
| 123 | `mgax` | octet |
| 124 | `pa1tr` | numerique |
| 125 | `tpa1tr` | numerique |
| 126 | `ppr1tr` | reel4 |
| 127 | `pmntr` | reel4 |
| 128 | `pa2tr` | numerique |
| 129 | `tpa2tr` | numerique |
| 130 | `ppr2tr` | reel4 |
| 131 | `fptr` | numerique |
| 132 | `noytr` | octet |
| 133 | `mgtr` | octet |
| 134 | `pa1pr` | numerique |
| 135 | `tpa1pr` | numerique |
| 136 | `pmnpr` | reel4 |
| 137 | `pa2pr` | numerique |
| 138 | `tpa2pr` | numerique |
| 139 | `fppr` | numerique |
| 140 | `pmnvpt` | reel4 |
| 141 | `pvut` | numerique |
| 142 | `pvtt` | numerique |
| 143 | `mnpvt` | numerique |
| 144 | `pmnpvct` | reel4 |
| 145 | `mbpvt` | numerique |
| 146 | `pmbpvt` | reel4 |
| 147 | `pmnpv` | reel4 |
| 148 | `mnpv` | numerique |
| 149 | `pmnpvc` | reel4 |
| 150 | `mbpv` | numerique |
| 151 | `pmbpv` | reel4 |
| 152 | `modliv` | entier2ns |
| 153 | `pdshg` | reel4 |
| 154 | `pdsag` | reel4 |
| 155 | `pdspal` | reel4 |
| 156 | `nbepal` | entier4ns |
| 157 | `noyout` | octet |
| 158 | `noymat` | octet |
| 159 | `pa1pp` | numerique |
| 160 | `tpa1pp` | numerique |
| 161 | `ppr1pp` | reel4 |
| 162 | `pmnpp` | reel4 |
| 163 | `pa2pp` | numerique |
| 164 | `tpa2pp` | numerique |
| 165 | `ppr2pp` | reel4 |
| 166 | `fppp` | numerique |
| 167 | `noypp` | octet |
| 168 | `mgpp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 205 - tout est dans le JSON) :

| id | dtem | salm | numero | cpays | operateur | amjd | numclt | groupeclt | cat1 | cat2 | cat3 | fam | cp | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | numrep | typclt | ligne | type | code3 | code2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 37 | 07/17/2026 08:54:51 | 4 | 2607003 |  | 12 |  | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |  | 0050 |
| 35 | 03/30/2026 11:42:14 | 12 | 2603009 |  | 12 |  | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |  |  |
| 34 | 01/09/2026 15:30:56 | 9998 | 2601003 |  | 9998 | 01/09/2026 00:00:00 | 1000 | 938 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 51 | 1 | 1 | 1 |  |  |

### `cpr_st`

Lignes : 13 - colonnes logiques : 30 - physiques : 39 - derniere activite (dtem) : 01/09/2026 15:31:10 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `fam` | octet |
| 16 | `sfam` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `qte` | reel8 |
| 19 | `des2` | texte(50) |
| 20 | `des3` | texte(50) |
| 21 | `des4` | texte(50) |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `cuv` | texte(5) |
| 25 | `nligne` | entier4ns |
| 26 | `pma` | reel4 |
| 27 | `pun` | numerique |
| 28 | `noye` | octet |
| 29 | `htfp` | numerique |
| 30 | `htnoy` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 39 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | fam | sfam | gamme | qte | des2 | des3 | des4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 01/09/2026 15:31:10 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |
| 12 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |
| 11 | 11/23/2023 10:57:42 | 9999 | 2311008 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |

### `cpr_tr`

Lignes : 47 - colonnes logiques : 30 - physiques : 39 - derniere activite (dtem) : 01/09/2026 15:31:11 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `nligne` sur nligne - `clef` sur numero, ligne, nligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `numero` | entier8ns |
| 5 | `type` | entier2ns |
| 6 | `htn` | numerique |
| 7 | `com` | octet |
| 8 | `suv` | octet |
| 9 | `vuv` | numerique |
| 10 | `ligne` | entier4ns |
| 11 | `code1` | texte(5) |
| 12 | `code2` | texte(20) |
| 13 | `code3` | texte(10) |
| 14 | `des1` | texte(50) |
| 15 | `fam` | octet |
| 16 | `sfam` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `qte` | reel8 |
| 19 | `des2` | texte(50) |
| 20 | `des3` | texte(50) |
| 21 | `des4` | texte(50) |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `cuv` | texte(5) |
| 25 | `nligne` | entier4ns |
| 26 | `pma` | reel4 |
| 27 | `pun` | numerique |
| 28 | `noye` | octet |
| 29 | `htfp` | numerique |
| 30 | `htnoy` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 39 - tout est dans le JSON) :

| id | dtem | salm | numero | type | htn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | suv | vuv | ligne | code1 | code2 | code3 | des1 | fam | sfam | gamme | qte | des2 | des3 | des4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 54 | 01/09/2026 15:31:11 | 9998 | 2601003 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |
| 53 | 01/09/2026 15:31:10 | 9998 | 2601003 | 2 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1.00000 | 1 | FR | FRAIS_DE_PORT |  | Frais de port | 102 | 1 | 0 | 1 |  |  |  |
| 52 | 11/17/2025 11:35:05 | 9999 | 2511001 | 0 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.00000 | 1 |  |  |  |  | 0 | 0 | 0 | 0 |  |  |  |

### `dev_com`

Lignes : 1 433 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 2 982 - derniere activite (dtem) : 07/21/2026 17:22:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 3963 | 1 | 0 | 1 | 1 bdc par lieu de livraison | 2607006 | 0 | 07/21/2026 17:22:58 | 1 |
| 3961 | 1 | 0 | 1 | Modification matière au 08/10/2018 | 2607005 | 1 | 07/20/2026 09:35:53 | 1 |
| 3958 | 1 | 0 | 1 | Commande pour FACILITY : fichiers raccourcis étiq à mettr... | 2607005 | 0 | 07/20/2026 09:34:53 | 1 |

### `dev_comft`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `dev_comif`

Lignes : 383 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 814 - derniere activite (dtem) : 07/21/2026 17:22:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 1392 | 1 | 0 | 1 | 1 facture par BL et par entité de lieu de  livraison | 2607006 | 0 | 07/21/2026 17:22:58 | 1 |
| 1389 | 1 | 0 | 1 | 1 facture par BL et par entité de lieu de  livraison | 2607001 | 0 | 07/02/2026 10:38:49 | 1 |
| 1386 | 1 | 0 | 1 | 1 facture par BL et par entité de lieu de  livraison | 2606002 | 0 | 06/15/2026 16:05:02 | 1 |

### `dev_comil`

Lignes : 636 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 1 369 - derniere activite (dtem) : 07/21/2026 17:22:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 2160 | 1 | 0 | 1 | 1 Bl par lieu de livraison | 2607006 | 0 | 07/21/2026 17:22:58 | 1 |
| 2157 | 1 | 0 | 1 | DISCRETION COMMERCIALE BL NEUTRE FOURNI PAR LE CLIENT COP... | 2607005 | 0 | 07/20/2026 09:34:53 | 1 |
| 2154 | 1 | 0 | 1 | 1 Bl par lieu de livraison | 2607001 | 0 | 07/02/2026 10:38:49 | 1 |

### `dev_comis`

Lignes : 167 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 342 - derniere activite (dtem) : 05/27/2026 16:07:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 353 | 1 | 0 | 1 | STB2 = 2.500 ETQ A122 = 297.000 ETQ A241 = 270.000 ETQ  A... | 2605009 | 4 | 05/27/2026 16:07:29 | 1 |
| 351 | 1 | 0 | 1 | STB2 = 2.500 ETQ A122 = 297.000 ETQ A241 = 270.000 ETQ  A... | 2605009 | 3 | 05/27/2026 16:06:15 | 1 |
| 349 | 1 | 0 | 1 | STB2 = 2.500 ETQ A122 = 297.000 ETQ A241 = 270.000 ETQ  A... | 2605009 | 2 | 05/27/2026 16:05:24 | 1 |

### `dev_comit`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `dev_entete`

Lignes : 865 - colonnes logiques : 65 - physiques : 90 - total corbeille comprise : 1 903 - derniere activite (dtem) : 07/21/2026 17:23:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjd` sur amjd - `numclt` sur numclt - `rs` sur rs - `groupeclt` sur groupeclt - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `numrep` sur numrep - `typclt` sur typclt - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjd` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `vref` | texte(50) |
| 42 | `nref` | texte(50) |
| 43 | `civ` | octet |
| 44 | `interlocuteur` | texte(50) |
| 45 | `tex` | texte(10) |
| 46 | `mail` | texte(128) |
| 47 | `com` | octet |
| 48 | `numint` | entier4ns |
| 49 | `dest` | texte(1) |
| 50 | `intclt` | entier4ns |
| 51 | `lrs` | texte(50) |
| 52 | `ladr1` | texte(50) |
| 53 | `ladr2` | texte(50) |
| 54 | `lcp` | texte(10) |
| 55 | `lville` | texte(50) |
| 56 | `lpays` | texte(50) |
| 57 | `modliv` | entier2ns |
| 58 | `amje` | date |
| 59 | `nbjliv` | entier2ns |
| 60 | `amjl` | date |
| 61 | `lcpays` | texte(5) |
| 62 | `numrep` | entier2ns |
| 63 | `typclt` | octet |
| 64 | `mqte` | octet |
| 65 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 90 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjd | numclt | rs | groupeclt | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2593 | 0 | 07/21/2026 17:23:29 | 1 | +33 3 20 87 50 06 | 2607006 | FRANCE | FR | 0 | 1 | 07/21/2026 00:00:00 | 95 | BOULANGER | 95 | 0 | 0 | 1 | 62971 | 1567.800000 | TSA 20814 |  | ARRAS CEDEX 9 |  | 1 | E | 1567.800000 | 0 | 1 | 0.000000 | 313.560000 |
| 2591 | 0 | 07/20/2026 09:36:41 | 1 |  | 2607005 | BELGIQUE | BE | 0 | 1 | 07/20/2026 00:00:00 | 245 | E&P CONSULT | 245 | 0 | 1 | 1 | 9570 | 2341.400000 | Groenstraat 1c |  | LIERDE - 9570 |  | 4 | E | 2341.400000 | 0 | 1 | 0.000000 | 0.000000 |
| 2589 | 0 | 07/17/2026 09:39:31 | 4 |  | 2607004 | FRANCE | FR | 0 | 4 | 07/17/2026 00:00:00 | 1061 | ID LOGISTICS Sélective 9 | 351 | 0 | 0 | 1 | 13600 | 2634.000000 | 55 chemin des Engranauds |  | ORGON |  | 1 | E | 2634.000000 | 0 | 1 | 0.000000 | 526.800000 |

### `dev_ligne`

Lignes : 1 341 - colonnes logiques : 60 - physiques : 69 - total corbeille comprise : 3 218 - derniere activite (dtem) : 07/24/2026 10:59:23 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `rref` sur rref - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `vref` | texte(50) |
| 15 | `nref` | texte(50) |
| 16 | `com` | octet |
| 17 | `lrs` | texte(50) |
| 18 | `ladr1` | texte(50) |
| 19 | `ladr2` | texte(50) |
| 20 | `lcp` | texte(10) |
| 21 | `lville` | texte(50) |
| 22 | `lpays` | texte(50) |
| 23 | `modliv` | entier2ns |
| 24 | `amje` | date |
| 25 | `nbjliv` | entier2ns |
| 26 | `amjl` | date |
| 27 | `suv` | octet |
| 28 | `vuv` | numerique |
| 29 | `lcpays` | texte(5) |
| 30 | `ligne` | entier4ns |
| 31 | `lpos` | octet |
| 32 | `code1` | texte(5) |
| 33 | `code2` | texte(20) |
| 34 | `code3` | texte(10) |
| 35 | `des1` | texte(50) |
| 36 | `fam` | octet |
| 37 | `sfam` | entier4ns |
| 38 | `gamme` | entier2ns |
| 39 | `qte` | reel8 |
| 40 | `rref` | octet |
| 41 | `des2` | texte(50) |
| 42 | `des3` | texte(50) |
| 43 | `des4` | texte(50) |
| 44 | `pa` | numerique |
| 45 | `pub` | numerique |
| 46 | `pun` | numerique |
| 47 | `depot` | texte(10) |
| 48 | `net` | octet |
| 49 | `ctva` | texte(5) |
| 50 | `drref` | texte(50) |
| 51 | `cuv` | texte(5) |
| 52 | `comrep` | reel4 |
| 53 | `nbeliv` | entier4 |
| 54 | `lab` | octet |
| 55 | `bat` | octet |
| 56 | `amjb` | date |
| 57 | `nbjval` | entier2ns |
| 58 | `amjv` | date |
| 59 | `orig` | octet |
| 60 | `puc` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 69 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | vref | nref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lrs | ladr1 | ladr2 | lcp | lville |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4560 | 0 | 07/24/2026 10:59:23 | 57 | 20.00 | 2607006 | 2 | 1567.800000 | 1567.800000 | 1 | 0.000000 | 313.560000 | 1881.360000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | BOULANGER | 256 Bld Eugène THOMAS | Parcolog 2 | 62110 | HENIN BEAUMONT |
| 4554 | 0 | 07/20/2026 09:39:19 | 1 | 0.00 | 2607005 | 2 | 305.400000 | 305.400000 | 1 | 0.000000 | 0.000000 | 305.400000 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | Adresse à confirmer |  | 00000 | A CONFIRMER -> 00000 |
| 4552 | 0 | 07/20/2026 09:38:54 | 1 | 0.00 | 2607005 | 2 | 2036.000000 | 2036.000000 | 1 | 0.000000 | 0.000000 | 2036.000000 |  |  | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | Adresse à confirmer |  | 00000 | A CONFIRMER -> 00000 |

### `dev_nomen`

Lignes : 0 - colonnes logiques : 32 - physiques : 0

Cles : `id` sur id (primaire) - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `htn` sur htn - `numero` sur numero - `ligne` sur ligne - `des1` sur des1 - `lignenomen` sur lignenomen - `clef` sur numero, ligne, lignenomen

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `fam` | octet |
| 10 | `sfam` | entier4ns |
| 11 | `gamme` | entier2ns |
| 12 | `cuv` | texte(5) |
| 13 | `depot` | texte(10) |
| 14 | `qte` | reel8 |
| 15 | `htn` | numerique |
| 16 | `pa` | numerique |
| 17 | `pub` | numerique |
| 18 | `pun` | numerique |
| 19 | `suv` | octet |
| 20 | `vuv` | numerique |
| 21 | `net` | octet |
| 22 | `trem` | octet |
| 23 | `rem` | numerique |
| 24 | `numero` | entier8ns |
| 25 | `ligne` | entier4ns |
| 26 | `des1` | texte(50) |
| 27 | `lignenomen` | entier4ns |
| 28 | `des2` | texte(50) |
| 29 | `des3` | texte(50) |
| 30 | `des4` | texte(50) |
| 31 | `htb` | numerique |
| 32 | `com` | octet |

### `ecc_com`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `ecc_comic`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `ecc_ech`

Lignes : 43 644 - colonnes logiques : 27 - physiques : 36 - total corbeille comprise : 93 442 - derniere activite (dtem) : 08/07/2026 17:21:12 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `nofac` sur nofac - `amje` sur amje - `ligneech` sur ligneech - `pos` sur pos - `sol` sur sol - `operateur` sur operateur - `nbech` sur nbech - `numclt` sur numclt - `numcltp` sur numcltp - `rs` sur rs - `ville` sur ville - `reg` sur reg - `bqei` sur bqei - `bqec` sur bqec - `cp` sur cp - `cpays` sur cpays - `numrep` sur numrep - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `rap` sur rap - `clef` sur nofac, ligneech - `clefcorbeille` sur nofac, ligneech, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `nofac` | entier8ns |
| 6 | `com` | octet |
| 7 | `amje` | date |
| 8 | `ligneech` | entier4ns |
| 9 | `pos` | octet |
| 10 | `sol` | octet |
| 11 | `operateur` | entier2ns |
| 12 | `nbech` | entier4ns |
| 13 | `numclt` | entier4ns |
| 14 | `numcltp` | entier4ns |
| 15 | `rs` | texte(50) |
| 16 | `ville` | texte(50) |
| 17 | `reg` | entier4ns |
| 18 | `bqei` | entier4ns |
| 19 | `bqec` | entier4ns |
| 20 | `cp` | texte(10) |
| 21 | `cpays` | texte(5) |
| 22 | `numrep` | entier2ns |
| 23 | `cat1` | entier2ns |
| 24 | `cat2` | entier2ns |
| 25 | `cat3` | entier2ns |
| 26 | `rap` | octet |
| 27 | `mt` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 36 - tout est dans le JSON) :

| id | corbeille | dtem | salm | nofac | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | amje | ligneech | pos | sol | operateur | nbech | numclt | numcltp | rs | ville | reg | bqei | bqec | cp | cpays |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 145916 | 0 | 08/07/2026 17:21:12 | 5 | 26080047 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10/15/2026 00:00:00 | 1 | 1 | 0 | 5 | 0 | 601 | 601 | ROQUETTE FRERES | LESTREM | 3 | 0 | 0 | 62136 | FR |
| 145914 | 0 | 08/07/2026 17:20:43 | 5 | 26080047 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10/15/2026 00:00:00 | 0 | 0 | 0 | 5 | 1 | 601 | 601 | ROQUETTE FRERES | LESTREM | 3 | 0 | 0 | 62136 | FR |
| 145912 | 0 | 08/07/2026 17:21:12 | 5 | 26070203 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 08/31/2026 00:00:00 | 1 | 1 | 0 | 5 | 0 | 122 | 122 | S.A CARREFOUR BELGIUM | ZAVENTEM | 3 | 0 | 0 | 1930 | BE |

### `ecc_reg`

Lignes : 2 - colonnes logiques : 24 - physiques : 33 - total corbeille comprise : 4 - derniere activite (dtem) : 02/17/2015 18:12:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `amje` sur amje - `ligne` sur ligne - `pos` sur pos - `operateur` sur operateur - `numclt` sur numclt - `numcltp` sur numcltp - `reg` sur reg - `bqe` sur bqe - `numfac` sur numfac - `lignefac` sur lignefac - `amj` sur amj - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `amje` | horodatage |
| 8 | `ligne` | entier4ns |
| 9 | `pos` | octet |
| 10 | `operateur` | entier2ns |
| 11 | `numclt` | entier4ns |
| 12 | `numcltp` | entier4ns |
| 13 | `reg` | entier4ns |
| 14 | `bqe` | entier4ns |
| 15 | `numfac` | entier8ns |
| 16 | `lignefac` | entier4ns |
| 17 | `amj` | date |
| 18 | `refbque` | texte(50) |
| 19 | `refreg` | texte(50) |
| 20 | `apay` | numerique |
| 21 | `pay` | numerique |
| 22 | `teca` | octet |
| 23 | `ecart` | numerique |
| 24 | `amjer` | date |

Dernieres lignes (les 30 premieres colonnes sur 33 - tout est dans le JSON) :

| id | corbeille | dtem | salm | numero | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | amje | ligne | pos | operateur | numclt | numcltp | reg | bqe | numfac | lignefac | amj | refbque | refreg | apay | pay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0 | 02/17/2015 18:12:00 | 9999 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 1 | 1 | 9999 | 601 | 601 | 1 | 1 | 15010034 | 1 | 02/17/2015 00:00:00 |  |  | 3924.520000 | 3924.520000 |
| 1 | 0 | 02/17/2015 18:12:00 | 9999 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 0 | 1 | 9999 | 601 | 601 | 1 | 1 | 0 | 0 | 02/17/2015 00:00:00 |  |  | 9513.520000 | 3924.520000 |

### `ecf_ech`

Lignes : 0 - colonnes logiques : 26 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `nofac` sur nofac - `amje` sur amje - `ligneech` sur ligneech - `pos` sur pos - `sol` sur sol - `operateur` sur operateur - `nbech` sur nbech - `numfou` sur numfou - `numfoup` sur numfoup - `rs` sur rs - `ville` sur ville - `reg` sur reg - `bqei` sur bqei - `bqec` sur bqec - `cp` sur cp - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cpays` sur cpays - `rap` sur rap - `clef` sur nofac, ligneech - `clefcorbeille` sur nofac, ligneech, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `nofac` | entier8ns |
| 6 | `com` | octet |
| 7 | `amje` | date |
| 8 | `ligneech` | entier4ns |
| 9 | `pos` | octet |
| 10 | `sol` | octet |
| 11 | `operateur` | entier2ns |
| 12 | `nbech` | entier4ns |
| 13 | `numfou` | entier4ns |
| 14 | `numfoup` | entier4ns |
| 15 | `rs` | texte(50) |
| 16 | `ville` | texte(50) |
| 17 | `reg` | entier4ns |
| 18 | `bqei` | entier4ns |
| 19 | `bqec` | entier4ns |
| 20 | `cp` | texte(10) |
| 21 | `cat1` | entier2ns |
| 22 | `cat2` | entier2ns |
| 23 | `cat3` | entier2ns |
| 24 | `cpays` | texte(5) |
| 25 | `rap` | octet |
| 26 | `mt` | numerique |

### `ecf_reg`

Lignes : 0 - colonnes logiques : 23 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `amje` sur amje - `ligne` sur ligne - `pos` sur pos - `operateur` sur operateur - `reg` sur reg - `numfou` sur numfou - `bqe` sur bqe - `numfoup` sur numfoup - `numfac` sur numfac - `lignefac` sur lignefac - `amj` sur amj - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `amje` | horodatage |
| 8 | `ligne` | entier4ns |
| 9 | `pos` | octet |
| 10 | `operateur` | entier2ns |
| 11 | `reg` | entier4ns |
| 12 | `numfou` | entier4ns |
| 13 | `bqe` | entier4ns |
| 14 | `numfoup` | entier4ns |
| 15 | `numfac` | entier8ns |
| 16 | `lignefac` | entier4ns |
| 17 | `amj` | date |
| 18 | `refbque` | texte(50) |
| 19 | `refreg` | texte(50) |
| 20 | `apay` | numerique |
| 21 | `pay` | numerique |
| 22 | `teca` | octet |
| 23 | `ecart` | numerique |

### `fic_art`

Lignes : 7 678 - colonnes logiques : 95 - physiques : 122 - total corbeille comprise : 41 389 - derniere activite (dtem) : 08/24/2026 15:46:32 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `operateur` sur operateur - `stk` sur stk - `fam` sur fam - `sfam` sur sfam - `numclt` sur numclt - `gamme` sur gamme - `cltc1` sur cltc1 - `cltc2` sur cltc2 - `cltc3` sur cltc3 - `libc1` sur libc1 - `cltd1` sur cltd1 - `bar1` sur bar1 - `bar2` sur bar2 - `bar3` sur bar3 - `bar4` sur bar4 - `bar5` sur bar5 - `cliche` sur cliche - `typlc` sur typlc - `ftl` sur ftl - `fth` sur fth - `nomen` sur nomen - `numart` sur numart - `catalog` sur catalog - `cltc2b` sur cltc2b - `cltc2c` sur cltc2c - `clef` sur type, code1, code2, code3 - `clefcorbeille` sur type, code1, code2, code3, corbeille (unique) - `numartcorbeille` sur numart, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `teco` | numerique |
| 10 | `type` | entier2ns |
| 11 | `amj` | horodatage |
| 12 | `operateur` | entier2ns |
| 13 | `stk` | octet |
| 14 | `fam` | octet |
| 15 | `sfam` | entier4ns |
| 16 | `numclt` | entier4ns |
| 17 | `gamme` | entier2ns |
| 18 | `cltc1` | texte(5) |
| 19 | `cltc2` | texte(20) |
| 20 | `cltc3` | texte(10) |
| 21 | `libc1` | texte(50) |
| 22 | `cltd1` | texte(50) |
| 23 | `bar1` | texte(30) |
| 24 | `bar2` | texte(30) |
| 25 | `bar3` | texte(30) |
| 26 | `bar4` | texte(30) |
| 27 | `bar5` | texte(30) |
| 28 | `cliche` | texte(20) |
| 29 | `typlc` | octet |
| 30 | `ftl` | reel8 |
| 31 | `fth` | numerique |
| 32 | `nomen` | octet |
| 33 | `numart` | entier4ns |
| 34 | `libc2` | texte(50) |
| 35 | `libc3` | texte(50) |
| 36 | `libc4` | texte(50) |
| 37 | `cltd2` | texte(50) |
| 38 | `cltd3` | texte(50) |
| 39 | `cltd4` | texte(50) |
| 40 | `coul` | texte(20) |
| 41 | `pdsn` | reel4 |
| 42 | `pdsb` | reel4 |
| 43 | `ctva` | texte(5) |
| 44 | `pcpv` | reel4 |
| 45 | `remp1` | texte(5) |
| 46 | `remp2` | texte(20) |
| 47 | `remp3` | texte(10) |
| 48 | `coma` | octet |
| 49 | `comv` | octet |
| 50 | `umasse` | octet |
| 51 | `cpesee` | octet |
| 52 | `fcpt` | entier4ns |
| 53 | `typtv` | octet |
| 54 | `typpb` | octet |
| 55 | `coefv` | reel4 |
| 56 | `taruni` | numerique |
| 57 | `interv` | octet |
| 58 | `catalog` | texte(15) |
| 59 | `comrep` | reel4 |
| 60 | `cua` | texte(5) |
| 61 | `cuv` | texte(5) |
| 62 | `cuc` | texte(5) |
| 63 | `douane` | texte(15) |
| 64 | `cat1` | octet |
| 65 | `cat2` | octet |
| 66 | `cat3` | octet |
| 67 | `depot` | texte(10) |
| 68 | `rang` | texte(50) |
| 69 | `mini` | reel8 |
| 70 | `maxi` | reel8 |
| 71 | `pstk` | numerique |
| 72 | `cuastk` | texte(5) |
| 73 | `cucstk` | texte(5) |
| 74 | `alcool1` | reel8 |
| 75 | `alcool2` | octet |
| 76 | `alcool3` | reel8 |
| 77 | `alcool4` | entier4ns |
| 78 | `imp_typ` | entier4ns |
| 79 | `imp_a1` | texte(40) |
| 80 | `imp_a2` | texte(40) |
| 81 | `imp_a3` | texte(40) |
| 82 | `imp_a4` | texte(40) |
| 83 | `imp_a5` | texte(40) |
| 84 | `imp_n1` | reel8 |
| 85 | `imp_n2` | reel8 |
| 86 | `imp_n3` | reel8 |
| 87 | `imp_n4` | reel8 |
| 88 | `imp_n5` | reel8 |
| 89 | `imp_n6` | reel8 |
| 90 | `imp_n7` | reel8 |
| 91 | `imp_n8` | reel8 |
| 92 | `imp_n9` | reel8 |
| 93 | `cltc2b` | texte(20) |
| 94 | `typcb` | octet |
| 95 | `cltc2c` | texte(20) |

Dernieres lignes (les 30 premieres colonnes sur 122 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | teco | type | amj | operateur | stk | fam | sfam | numclt | gamme | cltc1 | cltc2 | cltc3 | libc1 | cltd1 | bar1 | bar2 | bar3 | bar4 | bar5 | cliche | typlc | ftl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 41483 | 1 | 0 | 08/24/2026 15:14:27 | 4 | 890 | 0112 |  | 0.000000 | 1 | 08/24/2026 14:58:55 | 4 | 2 | 1 | 1 | 890 | 0 |  | Don Association |  | Etiquette 100 x 210 mm, 2 couleurs R° | Etiquette 100 x 210 mm, 2 couleurs R° |  |  |  |  |  |  | 1 | 100 |
| 41478 | 1 | 0 | 08/05/2026 08:41:45 | 57 | 621 | 0041 |  | 0.000000 | 1 | 08/05/2026 08:40:32 | 57 | 2 | 1 | 1 | 621 | 0 |  |  |  | Etiquette 98 x 198 mm. | Etiquette 98 x 198 mm. |  |  |  |  |  |  | 1 | 0 |
| 41474 | 1 | 0 | 08/03/2026 09:30:48 | 57 | 1326 | 0002 |  | 0.000000 | 1 | 08/03/2026 09:30:48 | 57 | 2 | 1 | 1 | 1326 | 0 |  |  |  | Etiquette 100 x 40 mm. | Etiquette 100 x 40 mm. |  |  |  |  |  |  | 1 | 100 |

### `fic_arta`

Lignes : 2 714 - colonnes logiques : 22 - physiques : 109 - total corbeille comprise : 10 668 - derniere activite (dtem) : 08/24/2026 15:44:38 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `numfou` sur numfou - `ref` sur ref - `def` sur def - `bar` sur bar - `clef` sur type, code1, code2, code3, numfou - `clefcorbeille` sur type, code1, code2, code3, numfou, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `numfou` | entier4ns |
| 11 | `cua` | texte(5) |
| 12 | `cuc` | texte(5) |
| 13 | `ref` | texte(30) |
| 14 | `def` | octet |
| 15 | `bar` | texte(30) |
| 16 | `libt1` | texte(50) |
| 17 | `libt2` | texte(50) |
| 18 | `amj` | date |
| 19 | `amjv` | date |
| 20 | `qtemin` | reel8 |
| 21 | `qtemax` | reel8 |
| 22 | `pa` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 109 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | numfou | cua | cuc | ref | def | bar | libt1 | libt2 | amj | amjv | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10932 | 1 | 0 | 08/24/2026 15:00:42 | 4 | 890 | 0112 |  | 1 | 1092 | 11 | 11 |  | 2 |  |  |  | 08/24/2026 00:00:00 | 12/31/2099 00:00:00 | 0.01 | 3000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10930 | 1 | 0 | 08/07/2026 10:23:28 | 7 | 629 | 0015 |  | 901 | 629 | 10 | 12 | PDT0018 | 2 |  | THERMAL ECO BPA FREE FSC™ / RF20 / YG60 | Roll lenght 4.000 ml | 08/07/2026 00:00:00 | 12/31/2026 00:00:00 | 2000 | 15000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10918 | 1 | 0 | 08/04/2026 17:14:41 | 7 | 1004 | 0215 |  | 1 | 1183 | ROLL | 15 |  | 2 |  | Label 15x10 mm, 80g coated paper/permanente adh/YG | 2cls (1 front/1 back), Box:15 rolls of 2000 labels | 08/04/2026 00:00:00 | 12/31/2099 00:00:00 | 0.01 | 66765.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_artc`

Lignes : 689 - colonnes logiques : 20 - physiques : 107 - total corbeille comprise : 2 133 - derniere activite (dtem) : 07/31/2026 13:38:16 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `numclt` sur numclt - `cltc1` sur cltc1 - `cltc2` sur cltc2 - `cltc3` sur cltc3 - `clef` sur type, code1, code2, code3, numclt - `clefcorbeille` sur type, code1, code2, code3, numclt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `numclt` | entier4ns |
| 11 | `qtemin` | reel8 |
| 12 | `qtemax` | reel8 |
| 13 | `amjv` | date |
| 14 | `pv` | numerique |
| 15 | `cltc1` | texte(5) |
| 16 | `cltc2` | texte(20) |
| 17 | `cltc3` | texte(10) |
| 18 | `libc1` | texte(50) |
| 19 | `libc2` | texte(50) |
| 20 | `amjd` | date |

Dernieres lignes (les 30 premieres colonnes sur 107 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | numclt | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 | qtemin_12 | qtemin_13 | qtemin_14 | qtemin_15 | qtemin_16 | qtemin_17 | qtemin_18 | qtemin_19 | qtemin_20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2154 | 1 | 0 | 07/31/2026 13:38:16 | 57 | 91 | 0003 |  | 1 | 178 | 1 | 2176000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2152 | 1 | 0 | 07/28/2026 12:16:06 | 57 | TT | FR152X450_OW |  | 1 | 1318 | 0.01 | 48.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2150 | 1 | 0 | 07/22/2026 09:50:38 | 12 | 1390 | 0001 |  | 1 | 1390 | 0.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_artcomcde`

Lignes : 1 168 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 2 821 - derniere activite (dtem) : 07/28/2026 10:36:28 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | texte(5) |
| 6 | `code2` | texte(20) |
| 7 | `code3` | texte(10) |
| 8 | `type` | entier2ns |
| 9 | `typt` | octet |
| 10 | `salm` | texte(50) |
| 11 | `com` | texte(750) |

Dernieres lignes :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 2825 | 1 | 0 | 07/01/2026 11:10:10 | 973 | 0040 |  | 1 | 2 | 57 | Paravent de 1.000 plis de 1 étiquette /  3000 plis maxi p... |
| 2823 | 1 | 0 | 06/02/2026 16:15:42 | 1289 | 0009 |  | 1 | 1 | 57 | Bien respecter 24 cartons par palette  |
| 2821 | 1 | 0 | 05/29/2026 10:41:35 | 1145 | 0048 |  | 1 | 1 | 57 | 30/04/24 Modification du visuel et de la teinte pantone |

### `fic_artcomcdf`

Lignes : 13 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 33 - derniere activite (dtem) : 08/04/2026 17:13:21 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `salm` | entier2ns |
| 11 | `dtem` | horodatage |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | salm | dtem |
|---|---|---|---|---|---|---|---|---|---|---|
| 32 | 1 | 0 | 1004 | 0128 |  | 1 | 1 | Tarif de 0,196 $ par bobine chez Likexin pour fabrication... | 7 | 08/04/2026 17:13:21 |
| 30 | 1 | 0 | 1004 | 0215 |  | 1 | 1 | Tarif de 0,196 $ par bobine chez Likexin pour fabrication... | 7 | 08/04/2026 17:11:08 |
| 21 | 1 | 0 | 941 | 0122 |  | 1 | 2 |  | 5 | 02/03/2022 11:23:24 |

### `fic_artcomifcde`

Lignes : 17 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 37 - derniere activite (dtem) : 09/23/2025 15:32:43 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 35 | 1 | 0 | 487 | 0006 |  | 1 | 1 | ATTENTION FRAIS DE PORT A AJOUTER | 09/23/2025 15:32:43 | 57 |
| 33 | 1 | 0 | 1313 | 0009 |  | 1 | 1 | Paragon mandrin 76 mm. Validé chez le client le 11/09/2024.  | 12/24/2024 08:42:38 | 12 |
| 31 | 1 | 0 | 1313 | 0008 |  | 1 | 1 | A modifier car ne fonctionne pas lors de l'essai chez le ... | 12/24/2024 08:40:39 | 12 |

### `fic_artcomifcdf`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `com` | texte(750) |
| 9 | `typt` | octet |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

### `fic_artcomilcde`

Lignes : 68 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 164 - derniere activite (dtem) : 03/03/2026 09:05:07 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 163 | 1 | 0 | 923 | 0012 |  | 1 | 2 | - Mettre des cornières sur les palettes | 03/03/2026 09:05:07 | 1 |
| 158 | 1 | 0 | 487 | 0006 |  | 1 | 1 | ATTENTION FRAIS DE PORT A AJOUTER | 09/23/2025 15:32:43 | 57 |
| 152 | 1 | 0 | 1153 | 0001 |  | 1 | 1 | Attention pour chaque ref = 1 palette Ne plus mettre plus... | 02/19/2025 16:38:53 | 4 |

### `fic_artcomircdf`

Lignes : 2 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 5 - derniere activite (dtem) : 02/03/2022 11:23:49 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 1 | 0 | 941 | 0122 |  | 1 | 2 |  | 02/03/2022 11:23:49 | 5 |
| 1 | 1 | 0 | 941 | 0121 |  | 1 | 2 | Prise de RDV 48H avant la livraison  Jérôme MESSAGER au 0... | 02/03/2022 11:07:25 | 5 |

### `fic_artcomiscde`

Lignes : 292 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 3 318 - derniere activite (dtem) : 05/27/2026 16:01:28 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 3717 | 1 | 0 | 963 | 0006 |  | 1 | 1 | STB2 = 2.500 ETQ A122 = 297.000 ETQ A241 = 270.000 ETQ  A... | 05/27/2026 16:01:28 | 1 |
| 3714 | 1 | 0 | 601 | 0195 |  | 1 | 1 | A 413 = 210.600 ETQ | 03/19/2026 08:26:14 | 57 |
| 3712 | 1 | 0 | 938 | 0051 |  | 1 | 1 | Prod de 02/2026 : 24 bobines en B161, vu Momo (RL18/02) | 02/18/2026 16:15:45 | 12 |

### `fic_artcomiscdf`

Lignes : 7 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 15 - derniere activite (dtem) : 11/20/2023 11:26:06 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 14 | 1 | 0 | 938 | 0041 |  | 1 | 1 | A163 = 576 B | 11/20/2023 11:26:06 | 4 |
| 12 | 1 | 0 | 938 | 0040 |  | 1 | 1 | A163 = 576 B | 09/22/2023 15:13:11 | 12 |
| 10 | 1 | 0 | 938 | 0039 |  | 1 | 1 | A163 = 576 B | 09/05/2023 11:58:36 | 4 |

### `fic_artv`

Lignes : 3 184 - colonnes logiques : 17 - physiques : 104 - total corbeille comprise : 10 872 - derniere activite (dtem) : 08/24/2026 15:46:24 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `grille` sur grille - `clef` sur type, code1, code2, code3, grille - `clefcorbeille` sur type, code1, code2, code3, grille, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `grille` | octet |
| 11 | `cuv` | texte(5) |
| 12 | `cuc` | texte(5) |
| 13 | `amj` | date |
| 14 | `amjv` | date |
| 15 | `qtemin` | reel8 |
| 16 | `qtemax` | reel8 |
| 17 | `pv` | numerique |

Dernieres lignes (les 30 premieres colonnes sur 104 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | grille | cuv | cuc | amj | amjv | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 | qtemin_12 | qtemin_13 | qtemin_14 | qtemin_15 | qtemin_16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10893 | 1 | 0 | 08/24/2026 15:00:55 | 4 | 890 | 0112 |  | 1 | 1 | 11 | 11 | 08/24/2026 00:00:00 | 09/24/2026 00:00:00 | 0.01 | 3000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10891 | 1 | 0 | 08/05/2026 08:41:14 | 57 | 621 | 0041 |  | 1 | 1 | 11 | 11 | 08/05/2026 00:00:00 | 12/31/2099 00:00:00 | 0.01 | 750000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10889 | 1 | 0 | 07/31/2026 15:52:32 | 4 | 1004 | 0128 |  | 1 | 1 | 11 | 11 | 07/31/2026 00:00:00 | 08/31/2026 00:00:00 | 0.01 | 70200000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_bqe`

Lignes : 1 - colonnes logiques : 19 - physiques : 19 - total corbeille comprise : 2 - derniere activite (dtem) : 02/17/2015 18:11:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numbqe` sur numbqe - `clefcorbeille` sur numbqe, corbeille

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numbqe` | entier4ns |
| 7 | `nombqe` | texte(50) |
| 8 | `lieubqe` | texte(50) |
| 9 | `cdebqe` | texte(10) |
| 10 | `guibqe` | texte(10) |
| 11 | `cptbqe` | texte(20) |
| 12 | `ribbqe` | texte(5) |
| 13 | `bic` | texte(15) |
| 14 | `iban` | texte(45) |
| 15 | `cpays` | texte(5) |
| 16 | `pays` | texte(50) |
| 17 | `cptjour` | texte(20) |
| 18 | `cptcpt` | entier8ns |
| 19 | `cpter` | entier8ns |

Dernieres lignes :

| id | bloq | corbeille | dtem | salm | numbqe | nombqe | lieubqe | cdebqe | guibqe | cptbqe | ribbqe | bic | iban | cpays | pays | cptjour | cptcpt | cpter |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 02/17/2015 18:11:00 | 9999 | 1 |  |  |  |  |  |  |  |  | FR | FRANCE |  | 4710000000 | 4710000000 |

### `fic_cha`

Lignes : 171 - colonnes logiques : 14 - physiques : 72 - total corbeille comprise : 423 - derniere activite (dtem) : 07/27/2026 14:22:17 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `codcha` sur codcha - `enre` sur enre - `page` sur page - `amj` sur amj - `clef` sur numero, codcha, enre, page - `clefcorbeille` sur numero, codcha, enre, page, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier2ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(2000) |
| 8 | `titre` | texte(50) |
| 9 | `codcha` | texte(42) |
| 10 | `enre` | entier4ns |
| 11 | `page` | entier2ns |
| 12 | `typ` | octet |
| 13 | `pj` | texte(500) |
| 14 | `amj` | horodatage |

Dernieres lignes (les 30 premieres colonnes sur 72 - tout est dans le JSON) :

| id | numero | bloq | corbeille | dtem | salm | lib | titre | codcha | enre | page | typ | typ_2 | typ_3 | typ_4 | typ_5 | typ_6 | typ_7 | typ_8 | typ_9 | typ_10 | typ_11 | typ_12 | typ_13 | typ_14 | typ_15 | typ_16 | typ_17 | typ_18 | typ_19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 428 | 1 | 1 | 0 | 07/27/2026 14:22:17 | 12 |  | Livrason entre 6h et 12h - sans rendez vous. | 1382~~ | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 426 | 1 | 1 | 0 | 07/23/2026 16:28:41 | 12 | rendez vous à prendre avec la réception de chaque site. R... | Prise de rendez vous livraison : | 1392~~ | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 424 | 1 | 1 | 0 | 07/23/2026 16:23:36 | 12 | Rendez vous à prendre avec la réception de chaque site. R... | Prise de rendez vous | 1391~~ | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_clt`

Lignes : 1 264 - colonnes logiques : 92 - physiques : 101 - total corbeille comprise : 6 939 - derniere activite (dtem) : 08/06/2026 11:13:34 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `amj` sur amj - `operateur` sur operateur - `code` sur code - `rs` sur rs - `tel` sur tel - `fax` sur fax - `numrep` sur numrep - `mail` sur mail - `cp` sur cp - `vil` sur vil - `cpays` sur cpays - `groupe` sur groupe - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `artv` sur artv - `bloq` sur bloq - `encompt` sur encompt - `ecmt` sur ecmt - `id` sur id (primaire) - `pays` sur pays - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier4ns |
| 2 | `amj` | horodatage |
| 3 | `operateur` | entier2ns |
| 4 | `code` | texte(30) |
| 5 | `rs` | texte(50) |
| 6 | `tel` | texte(20) |
| 7 | `fax` | texte(20) |
| 8 | `numrep` | entier2ns |
| 9 | `mail` | texte(128) |
| 10 | `cp` | texte(10) |
| 11 | `vil` | texte(50) |
| 12 | `cpays` | texte(5) |
| 13 | `groupe` | entier4ns |
| 14 | `cat1` | entier2ns |
| 15 | `cat2` | entier2ns |
| 16 | `cat3` | entier2ns |
| 17 | `artv` | entier2ns |
| 18 | `bloq` | octet |
| 19 | `encompt` | texte(1) |
| 20 | `ecmt` | numerique |
| 21 | `dtem` | horodatage |
| 22 | `salm` | entier2ns |
| 23 | `adr1` | texte(50) |
| 24 | `adr2` | texte(50) |
| 25 | `bp` | texte(10) |
| 26 | `siret` | texte(30) |
| 27 | `ntva` | texte(30) |
| 28 | `rcs` | texte(30) |
| 29 | `ean` | texte(30) |
| 30 | `http` | texte(50) |
| 31 | `ftp` | texte(50) |
| 32 | `ftpmdp` | texte(20) |
| 33 | `inftp` | texte(50) |
| 34 | `inftpmdp` | texte(20) |
| 35 | `inftpok` | octet |
| 36 | `modeliv` | entier2ns |
| 37 | `nbjliv` | entier2ns |
| 38 | `franco` | numerique |
| 39 | `remise` | reel4 |
| 40 | `escompte` | reel4 |
| 41 | `dart` | octet |
| 42 | `rgpbl` | octet |
| 43 | `adrbl` | octet |
| 44 | `nbdev` | octet |
| 45 | `nbarc` | octet |
| 46 | `nbfac` | octet |
| 47 | `lang` | texte(1) |
| 48 | `edspe1` | entier4ns |
| 49 | `edspe2` | entier4ns |
| 50 | `edspe3` | entier4ns |
| 51 | `edspe4` | entier4ns |
| 52 | `edspe5` | entier4ns |
| 53 | `dev` | texte(5) |
| 54 | `reg` | entier4ns |
| 55 | `del` | entier2ns |
| 56 | `de1` | octet |
| 57 | `de2` | octet |
| 58 | `tlcr` | octet |
| 59 | `fis` | octet |
| 60 | `cltcpt` | texte(20) |
| 61 | `fcpt` | entier4ns |
| 62 | `mdpbloq` | texte(10) |
| 63 | `codcpt` | texte(20) |
| 64 | `com` | octet |
| 65 | `texd` | octet |
| 66 | `texc` | octet |
| 67 | `texl` | octet |
| 68 | `texf` | octet |
| 69 | `ceco` | octet |
| 70 | `fraisadm` | octet |
| 71 | `facdroit` | octet |
| 72 | `detfrais` | octet |
| 73 | `adv` | entier2ns |
| 74 | `comrep` | reel4 |
| 75 | `adrliv` | entier2ns |
| 76 | `id` | entier8 |
| 77 | `pays` | texte(50) |
| 78 | `nbbl` | octet |
| 79 | `corbeille` | reel4 |
| 80 | `expdev` | octet |
| 81 | `exparc` | octet |
| 82 | `expbl` | octet |
| 83 | `expfac` | octet |
| 84 | `nif` | texte(30) |
| 85 | `explr` | octet |
| 86 | `expedit` | octet |
| 87 | `etiqtra` | octet |
| 88 | `edicde` | octet |
| 89 | `nbcol` | octet |
| 90 | `bat` | octet |
| 91 | `dmargen` | reel4 |
| 92 | `dmargeb` | reel4 |

Dernieres lignes (les 30 premieres colonnes sur 101 - tout est dans le JSON) :

| numero | amj | operateur | code | rs | tel | fax | numrep | mail | cp | vil | cpays | groupe | cat1 | cat2 | cat3 | artv | bloq | encompt | ecmt | dtem | salm | adr1 | adr2 | bp | siret | ntva | rcs | ean | http |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1397 | 07/31/2026 15:04:15 | 12 | CFR159 EUROFINS YVRY | CFR159 Eurofins Pathologie SELAS | 04.037.23.38.34 |  | 13 | FR_SupplierInvoice@eurofins.com | 44323 | NANTES CEDEX 3 | FR | 938 | 0 | 0 | 0 | 1 | 1 | 2 | 0.000000 | 07/31/2026 15:07:28 | 12 | Nantes Service Comptabilité Fournisseurs | Rue Pierre Adolphe Robierre  |  | 433 406 477 00052 | FR15 433 406 477 |  |  |  |
| 1396 | 07/27/2026 17:12:52 | 12 | CFR352 EUROFINS POITOU CHARENT | CFR352 EUROFINS POITOU CHARENTE LIMOUSIN |  |  | 1 |  | 86530 | NAINTRE | FR | 938 | 0 | 0 | 0 | 1 | 1 | 2 | 0.000000 | 07/27/2026 17:13:01 | 12 | 38 avenue Victor Hugo |  |  | 981 297 690 00068 |  |  |  |  |
| 1395 | 07/27/2026 17:11:20 | 12 | CFR352 EUROFINS POITOU CHARENT | CFR352 EUROFINS POITOU CHARENTE LIMOUSIN |  |  | 1 |  | 86000 | POITIERS  | FR | 938 | 0 | 0 | 0 | 1 | 1 | 2 | 0.000000 | 07/27/2026 17:11:20 | 12 | 5 boulevard René Cassin |  |  | 981 297 690 00076 |  |  |  |  |

### `fic_clta`

Lignes : 6 186 - colonnes logiques : 33 - physiques : 33 - total corbeille comprise : 18 210 - derniere activite (dtem) : 08/24/2026 15:49:59 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numclt` sur numclt - `numadr` sur numadr - `clef` sur numclt, numadr - `clefcorbeille` sur numclt, numadr, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numclt` | entier4ns |
| 7 | `numadr` | entier4ns |
| 8 | `rs` | texte(50) |
| 9 | `adr1` | texte(50) |
| 10 | `adr2` | texte(50) |
| 11 | `bp` | texte(10) |
| 12 | `cp` | texte(10) |
| 13 | `cpays` | texte(5) |
| 14 | `pays` | texte(50) |
| 15 | `siret` | texte(30) |
| 16 | `ntva` | texte(30) |
| 17 | `rcs` | texte(20) |
| 18 | `ean` | texte(20) |
| 19 | `tel` | texte(20) |
| 20 | `fax` | texte(20) |
| 21 | `mail` | texte(128) |
| 22 | `i_service` | octet |
| 23 | `i_civ` | octet |
| 24 | `i_pre` | texte(30) |
| 25 | `i_nom` | texte(30) |
| 26 | `i_tel` | texte(20) |
| 27 | `i_gsm` | texte(20) |
| 28 | `i_fax` | texte(20) |
| 29 | `i_mail` | texte(128) |
| 30 | `modliv` | entier2ns |
| 31 | `nbjliv` | entier2ns |
| 32 | `vil` | texte(50) |
| 33 | `typeadr` | octet |

Dernieres lignes (les 30 premieres colonnes sur 33 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | numclt | numadr | rs | adr1 | adr2 | bp | cp | cpays | pays | siret | ntva | rcs | ean | tel | fax | mail | i_service | i_civ | i_pre | i_nom | i_tel | i_gsm | i_fax | i_mail | modliv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 18209 | 1 | 0 | 08/24/2026 15:13:41 | 4 | 912 | 158 | CARREFOUR SUPPLY CHAIN | Madame Delphine MERLE | ZAC de Sennecé  |  | 71000 | FR | FRANCE |  |  |  |  |  |  |  | 1 | 2 |  |  |  |  |  |  | 1 |
| 18207 | 1 | 0 | 08/06/2026 13:33:13 | 57 | 961 | 16 | GROUPE CARSO - LSEHL  | 4 avenue Jean Moulin  | Bâtiment Hydrogène |  | 69200 | FR | FRANCE |  |  |  |  |  |  |  | 1 | 2 |  |  |  |  |  |  | 1 |
| 18203 | 1 | 0 | 08/05/2026 09:04:08 | 57 | 1375 | 3 | SCACHAP | A l'attention de Claude Platon | 785 rue André Bouyer |  | 16700 | FR | FRANCE |  |  |  |  |  |  |  | 1 | 2 |  |  |  |  |  |  | 1 |

### `fic_cltb`

Lignes : 5 - colonnes logiques : 18 - physiques : 18 - total corbeille comprise : 10 - derniere activite (dtem) : 04/01/2022 10:33:30 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numclt` sur numclt - `numbqe` sur numbqe - `def` sur def - `clef` sur numclt, numbqe - `clefcorbeille` sur numclt, numbqe, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numclt` | entier4ns |
| 7 | `numbqe` | entier4ns |
| 8 | `def` | octet |
| 9 | `nombqe` | texte(50) |
| 10 | `lieubqe` | texte(50) |
| 11 | `cdebqe` | texte(10) |
| 12 | `guibqe` | texte(10) |
| 13 | `cptbqe` | texte(20) |
| 14 | `ribbqe` | texte(5) |
| 15 | `bic` | texte(15) |
| 16 | `iban` | texte(45) |
| 17 | `cpays` | texte(5) |
| 18 | `pays` | texte(50) |

Dernieres lignes :

| id | bloq | corbeille | dtem | salm | numclt | numbqe | def | nombqe | lieubqe | cdebqe | guibqe | cptbqe | ribbqe | bic | iban | cpays | pays |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 1 | 0 | 04/01/2022 10:33:30 | 2 | 1132 | 1 | 2 | CDN |  |  |  |  |  |  | FR76 3007 6021 4710 0046 0020 072 | FR | FRANCE |
| 7 | 1 | 0 | 11/08/2016 14:58:00 | 5 | 908 | 0 | 2 | CREDIT DU NORD |  |  |  |  |  | NORDFRPP | FR7630076020631255280020044 | FR | FRANCE |
| 5 | 1 | 0 | 06/10/2015 09:44:00 | 4 | 758 | 1 | 2 | BNPPARIBAS |  |  |  |  |  | BNPAFRPPCRO | FR7630004002120002572973284 | FR | FRANCE |

### `fic_cltcom`

Lignes : 203 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 585 - derniere activite (dtem) : 07/28/2026 10:14:18 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numclt` sur numclt - `clef` sur numclt, typt - `clefcorbeille` sur numclt, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numclt` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numclt | dtem | salm |
|---|---|---|---|---|---|---|---|
| 584 | 1 | 0 | 1 | Prise de rdv à confirmer avec Mme Leveque Emilie : emilie... | 1393 | 07/28/2026 10:14:18 | 12 |
| 582 | 1 | 0 | 1 | Prise de rdv à confirmer avec Mr Sebastien Sibileau: seba... | 1392 | 07/28/2026 10:13:29 | 12 |
| 579 | 1 | 0 | 1 | Prise de rdv à confirmer avec Mr Sebastien Hamard: sebast... | 1390 | 07/28/2026 10:12:07 | 12 |

### `fic_cltcomif`

Lignes : 80 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 200 - derniere activite (dtem) : 07/29/2025 11:21:50 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numclt` sur numclt - `clef` sur numclt, typt - `clefcorbeille` sur numclt, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numclt` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numclt | dtem | salm |
|---|---|---|---|---|---|---|---|
| 196 | 1 | 0 | 1 | ATTENTION Adresse de facturation  | 382 | 07/29/2025 11:21:50 | 12 |
| 191 | 1 | 0 | 1 | ATTENTION : LIVER LA QUANTITE EXACTE COMMANDEE - N'ACCEPT... | 1113 | 01/04/2024 17:49:05 | 1 |
| 189 | 1 | 0 | 1 | Le retard de paiement des factures est lié au fait que la... | 621 | 01/03/2024 16:47:52 | 1 |

### `fic_cltcomil`

Lignes : 184 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 565 - derniere activite (dtem) : 07/29/2026 14:56:08 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numclt` sur numclt - `clef` sur numclt, typt - `clefcorbeille` sur numclt, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numclt` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numclt | dtem | salm |
|---|---|---|---|---|---|---|---|
| 562 | 1 | 0 | 1 | Prise de rendez-vous, si plus de 3 palettes  Contact pour... | 1389 | 07/17/2026 14:31:01 | 4 |
| 559 | 1 | 0 | 2 | Livraison : hayon obligatoire lundi au vendredi de 09h à 17h | 1374 | 06/19/2026 14:31:27 | 12 |
| 554 | 1 | 0 | 1 | ATTENTION, LIVRAISON A CONFIRMER : Au 45 rue Rollin 59100... | 1154 | 04/07/2026 16:53:52 | 12 |

### `fic_cltcomis`

Lignes : 2 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 6 - derniere activite (dtem) : 05/07/2025 15:15:46 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numclt` sur numclt - `clef` sur numclt, typt - `clefcorbeille` sur numclt, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numclt` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numclt | dtem | salm |
|---|---|---|---|---|---|---|---|
| 134 | 1 | 0 | 2 |    | 923 | 05/07/2025 15:15:46 | 12 |
| 132 | 1 | 0 | 1 |  Le 26/09/2024 : A partir du LUNDI 04/11/2024, une nouvel... | 923 | 10/11/2024 09:16:37 | 12 |

### `fic_clti`

Lignes : 2 926 - colonnes logiques : 21 - physiques : 21 - total corbeille comprise : 8 298 - derniere activite (dtem) : 08/07/2026 09:28:25 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numclt` sur numclt - `numint` sur numint - `def` sur def - `clef` sur numclt, numint - `clefcorbeille` sur numclt, numint, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `service` | octet |
| 5 | `civ` | octet |
| 6 | `nom` | texte(30) |
| 7 | `pre` | texte(30) |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `numclt` | entier4ns |
| 11 | `numint` | entier4ns |
| 12 | `tel` | texte(20) |
| 13 | `gsm` | texte(20) |
| 14 | `fax` | texte(20) |
| 15 | `mail` | texte(128) |
| 16 | `def` | octet |
| 17 | `maildev` | octet |
| 18 | `mailarc` | octet |
| 19 | `mailbl` | octet |
| 20 | `mailfac` | octet |
| 21 | `maillr` | octet |

Dernieres lignes :

| id | bloq | corbeille | service | civ | nom | pre | dtem | salm | numclt | numint | tel | gsm | fax | mail | def | maildev | mailarc | mailbl | mailfac | maillr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8300 | 1 | 0 | 5 | 2 | Relance |  | 08/07/2026 09:28:25 | 5 | 954 | 16 |  |  |  | compta-fournisseurs@nanotera.eu | 0 | 1 | 1 | 1 | 1 | 1 |
| 8298 | 1 | 0 | 3 | 3 | LUMEN | Céline  | 08/06/2026 15:53:59 | 57 | 1299 | 6 |  |  |  | celine.lumen@sonepar.fr | 0 | 1 | 1 | 1 | 1 | 1 |
| 8295 | 1 | 0 | 5 | 2 | factures |  | 08/04/2026 11:41:24 | 5 | 1380 | 5 |  |  |  | fr_supplierinvoices@sc.eurofinseu.com | 0 | 1 | 1 | 1 | 2 | 1 |

### `fic_comqt`

Lignes : 49 - colonnes logiques : 15 - physiques : 102 - total corbeille comprise : 98 - derniere activite (dtem) : 07/04/2013 18:06:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `clef` sur type, numero - `clefcorbeille` sur type, numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numero` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `cuv` | texte(5) |
| 9 | `cuc` | texte(5) |
| 10 | `amj` | date |
| 11 | `amjv` | date |
| 12 | `qtemin` | reel8 |
| 13 | `qtemax` | reel8 |
| 14 | `qtecom` | reel4 |
| 15 | `interv` | octet |

Dernieres lignes (les 30 premieres colonnes sur 102 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | numero | type | cuv | cuc | amj | amjv | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 | qtemin_12 | qtemin_13 | qtemin_14 | qtemin_15 | qtemin_16 | qtemin_17 | qtemin_18 | qtemin_19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 97 | 1 | 0 | 07/04/2013 18:06:00 | 9998 | 118 | 0 | U | U | 07/04/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 24999.99 | 25 | 25000 | 99999.99 | 15 | 100000 | 9999999999.99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 95 | 1 | 0 | 07/04/2013 18:05:00 | 9998 | 117 | 0 | U | U | 03/26/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 11999.99 | 25 | 12000 | 24999.99 | 25 | 25000 | 49999.99 | 15 | 50000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 93 | 1 | 0 | 03/26/2013 11:59:00 | 9998 | 116 | 0 | M | U | 03/26/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 11999.99 | 20 | 12000 | 24999.99 | 15 | 25000 | 49999.99 | 12 | 50000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_contact`

Lignes : 1 - colonnes logiques : 7 - physiques : 7 - total corbeille comprise : 2 - derniere activite (dtem) : 01/29/2021 08:58:01 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `lib` | texte(50) |
| 6 | `dtem` | horodatage |
| 7 | `salm` | entier2ns |

Dernieres lignes :

| id | code | bloq | corbeille | lib | dtem | salm |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 0 | Test | 01/29/2021 08:58:01 | 7 |

### `fic_depot`

Lignes : 1 - colonnes logiques : 13 - physiques : 13 - total corbeille comprise : 2 - derniere activite (dtem) : 12/03/2020 09:49:34 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lieu` | texte(50) |
| 8 | `adr1` | texte(50) |
| 9 | `adr2` | texte(50) |
| 10 | `cp` | texte(10) |
| 11 | `ville` | texte(50) |
| 12 | `cpays` | texte(5) |
| 13 | `pays` | texte(50) |

Dernieres lignes :

| id | code | bloq | corbeille | dtem | salm | lieu | adr1 | adr2 | cp | ville | cpays | pays |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | RBX | 1 | 0 | 12/03/2020 09:49:34 | 7 | Rue Rollin | 45 rue Rollin |  | 59100 | ROUBAIX | FR | FRANCE |

### `fic_devise`

Lignes : 3 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 7 - derniere activite (dtem) : 02/10/2024 09:43:40 - extrait : TOP n + ORDER BY id DESC

Cles : `code` sur code - `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `code` | texte(10) |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `lib` | texte(50) |
| 5 | `sym` | texte(10) |
| 6 | `arr` | octet |
| 7 | `id` | entier8 |
| 8 | `bloq` | octet |
| 9 | `corbeille` | reel4 |

Dernieres lignes :

| code | dtem | salm | lib | sym | arr | id | bloq | corbeille |
|---|---|---|---|---|---|---|---|---|
| L | 02/10/2024 09:43:40 | 1 | Livre anglaise | £ | 1 | 6 | 1 | 0 |
| E | 12/08/2020 17:47:27 | 9999 | Euro | € | 2 | 3 | 1 | 0 |
| DOL | 05/07/2012 15:36:00 | 9998 | Dollar | $ | 3 | 1 | 1 | 0 |

### `fic_famqt`

Lignes : 243 - colonnes logiques : 17 - physiques : 104 - total corbeille comprise : 486 - derniere activite (dtem) : 07/04/2013 18:08:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `sfam` sur sfam - `fam` sur fam - `clef` sur type, numero, fam, sfam - `clefcorbeille` sur type, numero, fam, sfam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numero` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `cuv` | texte(5) |
| 9 | `cuc` | texte(5) |
| 10 | `amj` | date |
| 11 | `amjv` | date |
| 12 | `qtemin` | reel8 |
| 13 | `qtemax` | reel8 |
| 14 | `interv` | octet |
| 15 | `sfam` | entier4ns |
| 16 | `fam` | octet |
| 17 | `qtecom` | reel4 |

Dernieres lignes (les 30 premieres colonnes sur 104 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | numero | type | cuv | cuc | amj | amjv | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 | qtemin_12 | qtemin_13 | qtemin_14 | qtemin_15 | qtemin_16 | qtemin_17 | qtemin_18 | qtemin_19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 485 | 1 | 0 | 07/04/2013 18:08:00 | 9998 | 118 | 0 | U | U | 07/04/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 99999.99 | 20 | 100000 | 9999999999.99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 483 | 1 | 0 | 03/26/2013 13:24:00 | 9998 | 117 | 0 | M | U | 03/26/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 11999.99 | 15 | 12000 | 24999.99 | 12 | 25000 | 49999.99 | 10 | 50000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 481 | 1 | 0 | 03/26/2013 13:24:00 | 9998 | 117 | 0 | M | U | 03/26/2013 00:00:00 | 12/31/9999 00:00:00 | 0.01 | 9999999999.99 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_fart`

Lignes : 64 - colonnes logiques : 34 - physiques : 43 - total corbeille comprise : 331 - derniere activite (dtem) : 04/27/2021 15:30:44 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `fam` sur fam - `bloq` sur bloq - `corbeille` sur corbeille - `sfam` sur sfam - `clef` sur fam, sfam - `clefcorbeille` sur fam, sfam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `tva` | entier8ns |
| 8 | `exp` | entier8ns |
| 9 | `cee` | entier8ns |
| 10 | `exo` | entier8ns |
| 11 | `sfam` | entier4ns |
| 12 | `libfam` | texte(50) |
| 13 | `atva` | entier8ns |
| 14 | `aimp` | entier8ns |
| 15 | `aexo` | entier8ns |
| 16 | `acee` | entier8ns |
| 17 | `adom` | entier8ns |
| 18 | `amon` | entier8ns |
| 19 | `dom` | entier8ns |
| 20 | `mon` | entier8ns |
| 21 | `coef` | reel4 |
| 22 | `rem` | octet |
| 23 | `tran` | texte(1) |
| 24 | `libsfam` | texte(50) |
| 25 | `invstk` | octet |
| 26 | `decimpa` | octet |
| 27 | `decimpv` | octet |
| 28 | `decimqa` | octet |
| 29 | `decimqv` | octet |
| 30 | `comrep` | reel4 |
| 31 | `typlc` | octet |
| 32 | `jdv` | entier2ns |
| 33 | `ajdv` | octet |
| 34 | `typtarvte` | octet |

Dernieres lignes (les 30 premieres colonnes sur 43 - tout est dans le JSON) :

| id | fam | bloq | corbeille | dtem | salm | tva | exp | cee | exo | sfam | libfam | atva | aimp | aexo | acee | adom | amon | dom | mon | coef | coef_2 | coef_3 | coef_4 | coef_5 | coef_6 | coef_7 | coef_8 | coef_9 | coef_10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 329 | 81 | 1 | 0 | 03/26/2021 10:57:55 | 5 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 | Pièces atelier | 6068200000 | 6068220000 | 4710000000 | 6068210000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 324 | 82 | 1 | 0 | 03/19/2021 16:42:05 | 7 | 7011000000 | 4710000000 | 7011910000 | 4710000000 | 1 | Silicone | 6011400000 | 6011420000 | 4710000000 | 6011410000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 321 | 80 | 1 | 0 | 03/19/2021 16:41:32 | 7 | 7011000000 | 4710000000 | 7011910000 | 4710000000 | 1 | Palettes | 6021300000 | 6021320000 | 4710000000 | 6021310000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

### `fic_fclt`

Lignes : 8 - colonnes logiques : 14 - physiques : 14 - total corbeille comprise : 16 - derniere activite (dtem) : 04/17/2018 10:37:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `fam` sur fam - `bloq` sur bloq - `corbeille` sur corbeille - `sfam` sur sfam - `clef` sur fam, sfam - `clefcorbeille` sur fam, sfam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `tva` | entier8ns |
| 8 | `exp` | entier8ns |
| 9 | `cee` | entier8ns |
| 10 | `exo` | entier8ns |
| 11 | `sfam` | entier4ns |
| 12 | `lib` | texte(50) |
| 13 | `dom` | entier8ns |
| 14 | `mon` | entier8ns |

Dernieres lignes :

| id | fam | bloq | corbeille | dtem | salm | tva | exp | cee | exo | sfam | lib | dom | mon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 3 | 1 | 0 | 04/17/2018 10:37:00 | 3 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 3 | CIC | 0 | 0 |
| 13 | 3 | 1 | 0 | 04/17/2018 10:37:00 | 3 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 2 | Caisse d'Epargne | 0 | 0 |
| 11 | 3 | 1 | 0 | 02/13/2015 15:52:00 | 9999 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 | Factor | 0 | 0 |

### `fic_fcpt`

Lignes : 9 - colonnes logiques : 20 - physiques : 20 - total corbeille comprise : 20 - derniere activite (dtem) : 11/04/2020 11:02:03 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `fam` sur fam - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur fam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `tva` | entier8ns |
| 8 | `exp` | entier8ns |
| 9 | `cee` | entier8ns |
| 10 | `exo` | entier8ns |
| 11 | `lib` | texte(50) |
| 12 | `dom` | entier8ns |
| 13 | `mon` | entier8ns |
| 14 | `atva` | entier8ns |
| 15 | `aimp` | entier8ns |
| 16 | `acee` | entier8ns |
| 17 | `aexo` | entier8ns |
| 18 | `adom` | entier8ns |
| 19 | `amon` | entier8ns |
| 20 | `groupe` | octet |

Dernieres lignes :

| id | fam | bloq | corbeille | dtem | salm | tva | exp | cee | exo | lib | dom | mon | atva | aimp | acee | aexo | adom | amon | groupe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 17 | 9 | 1 | 0 | 11/04/2020 11:01:37 | 3 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Prestation diverse | 4710000000 | 4710000000 | 6041000000 | 6041030000 | 6041020000 | 4710000000 | 4710000000 | 4710000000 | 1 |
| 15 | 8 | 1 | 0 | 11/04/2020 11:02:03 | 3 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Intervention | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |
| 13 | 7 | 1 | 0 | 05/28/2015 12:16:00 | 1 | 7011660000 | 7019116500 | 7011916000 | 7018100000 | Frais d'outils | 4710000000 | 4710000000 | 6011100000 | 6011140000 | 6011120000 | 6011180000 | 4710000000 | 4710000000 | 1 |

### `fic_ffou`

Lignes : 1 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 4 - derniere activite (dtem) : 01/19/2021 16:23:34 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `fam` sur fam - `bloq` sur bloq - `corbeille` sur corbeille - `sfam` sur sfam - `clef` sur fam, sfam - `clefcorbeille` sur fam, sfam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `sfam` | entier4ns |
| 8 | `lib` | texte(50) |

Dernieres lignes :

| id | fam | bloq | corbeille | dtem | salm | sfam | lib |
|---|---|---|---|---|---|---|---|
| 1 | 3 | 1 | 0 | 01/19/2021 16:23:34 | 9998 | 1 | Fournisseur adhésif |

### `fic_fou`

Lignes : 1 217 - colonnes logiques : 61 - physiques : 70 - total corbeille comprise : 6 075 - derniere activite (dtem) : 06/23/2026 15:56:54 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `amj` sur amj - `operateur` sur operateur - `code` sur code - `rs` sur rs - `tel` sur tel - `fax` sur fax - `mail` sur mail - `cp` sur cp - `vil` sur vil - `cpays` sur cpays - `groupe` sur groupe - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `artv` sur artv - `bloq` sur bloq - `ecmt` sur ecmt - `id` sur id (primaire) - `pays` sur pays - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier4ns |
| 2 | `amj` | horodatage |
| 3 | `operateur` | entier2ns |
| 4 | `code` | texte(30) |
| 5 | `rs` | texte(50) |
| 6 | `tel` | texte(20) |
| 7 | `fax` | texte(20) |
| 8 | `mail` | texte(128) |
| 9 | `cp` | texte(10) |
| 10 | `vil` | texte(50) |
| 11 | `cpays` | texte(5) |
| 12 | `groupe` | entier4ns |
| 13 | `cat1` | entier2ns |
| 14 | `cat2` | entier2ns |
| 15 | `cat3` | entier2ns |
| 16 | `artv` | entier2ns |
| 17 | `bloq` | octet |
| 18 | `ecmt` | numerique |
| 19 | `dtem` | horodatage |
| 20 | `salm` | entier2ns |
| 21 | `adr1` | texte(50) |
| 22 | `adr2` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `siret` | texte(30) |
| 25 | `ntva` | texte(30) |
| 26 | `rcs` | texte(30) |
| 27 | `ean` | texte(30) |
| 28 | `http` | texte(50) |
| 29 | `ftp` | texte(50) |
| 30 | `ftpmdp` | texte(20) |
| 31 | `inftp` | texte(50) |
| 32 | `inftpmdp` | texte(20) |
| 33 | `inftpok` | octet |
| 34 | `modeliv` | entier2ns |
| 35 | `nbjliv` | entier2ns |
| 36 | `franco` | numerique |
| 37 | `remise` | reel4 |
| 38 | `escompte` | reel4 |
| 39 | `lang` | texte(1) |
| 40 | `dev` | texte(5) |
| 41 | `reg` | entier4ns |
| 42 | `del` | entier2ns |
| 43 | `de1` | octet |
| 44 | `de2` | octet |
| 45 | `tlcr` | octet |
| 46 | `fis` | octet |
| 47 | `foucpt` | texte(20) |
| 48 | `typcpt` | entier2ns |
| 49 | `codcpt` | texte(20) |
| 50 | `com` | octet |
| 51 | `texc` | octet |
| 52 | `id` | entier8 |
| 53 | `pays` | texte(50) |
| 54 | `corbeille` | reel4 |
| 55 | `journal` | texte(10) |
| 56 | `nbaof` | octet |
| 57 | `nbcdf` | octet |
| 58 | `texa` | octet |
| 59 | `expaof` | octet |
| 60 | `expcdf` | octet |
| 61 | `nif` | texte(30) |

Dernieres lignes (les 30 premieres colonnes sur 70 - tout est dans le JSON) :

| numero | amj | operateur | code | rs | tel | fax | mail | cp | vil | cpays | groupe | cat1 | cat2 | cat3 | artv | bloq | ecmt | dtem | salm | adr1 | adr2 | bp | siret | ntva | rcs | ean | http | ftp | ftpmdp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1222 | 06/23/2026 15:56:54 | 1 | AIRMATTECHNOLOGY | AIRMAT TECHNOLOGY | +333 21 79 31 20 |  |  | 62300 | LENS | FR | 1222 | 0 | 0 | 0 | 0 | 1 | 0.000000 | 06/23/2026 15:56:54 | 1 | 21 rue Abbé Jerzy POPIELUSZKO | ZI de la Croisette |  |  |  |  |  |  |  |  |
| 1221 | 05/29/2026 14:22:19 | 905 | SD PACK | SD PACK | 04.69.96.10.99 |  | info@sdpack.fr | 01480 | JASSANS RIOTTIER | FR | 1221 | 0 | 0 | 0 | 0 | 1 | 0.000000 | 05/29/2026 14:22:19 | 905 | 249 rue de l'industrie  |  |  |  |  |  |  |  |  |  |
| 1220 | 05/22/2026 14:41:52 | 12 | REGMA TRANSFERT THERMIQUE | REGMA TRANSFERT THERMIQUE | 02 35 04 75 48 |  |  | 76880 | ARQUES-LA-BATAILLE | FR | 1220 | 0 | 0 | 0 | 0 | 1 | 0.000000 | 05/22/2026 14:50:07 | 12 | 6 rue Verdier Monetti  | BP 6 |  | 442 097 093 00029 | FR09442097093 |  |  |  |  |  |

### `fic_foub`

Lignes : 10 - colonnes logiques : 18 - physiques : 18 - total corbeille comprise : 20 - derniere activite (dtem) : 02/26/2026 17:28:09 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numbqe` sur numbqe - `def` sur def - `numfou` sur numfou - `clef` sur numfou, numbqe - `clefcorbeille` sur numfou, numbqe, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `numbqe` | entier4ns |
| 7 | `def` | octet |
| 8 | `nombqe` | texte(50) |
| 9 | `numfou` | entier4ns |
| 10 | `lieubqe` | texte(50) |
| 11 | `cdebqe` | texte(10) |
| 12 | `guibqe` | texte(10) |
| 13 | `cptbqe` | texte(20) |
| 14 | `ribbqe` | texte(5) |
| 15 | `bic` | texte(15) |
| 16 | `iban` | texte(45) |
| 17 | `cpays` | texte(5) |
| 18 | `pays` | texte(50) |

Dernieres lignes :

| id | bloq | corbeille | dtem | salm | numbqe | def | nombqe | numfou | lieubqe | cdebqe | guibqe | cptbqe | ribbqe | bic | iban | cpays | pays |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 19 | 1 | 0 | 02/26/2026 17:28:09 | 7 | 1 | 2 | CAIXABANK | 1216 | VALENCIA |  |  |  |  | CAIXESBBXXX | ES51 2100 0908 5402 0012 7215 | ES | ESPAGNE |
| 17 | 1 | 0 | 01/30/2025 14:19:54 | 5 | 1 | 1 | BNP PARIBAS | 1053 |  |  |  |  |  |  | NB02 2772 4887 | NL | PAYS-BAS |
| 15 | 1 | 0 | 03/31/2023 09:22:48 | 2 | 1 | 2 | CIC  | 1154 | Croix | 30027 | 17045 | 00020980102 | 48 | CMCIFRPP | FR7630027170450002098010248 | FR | FRANCE |

### `fic_foucom`

Lignes : 19 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 46 - derniere activite (dtem) : 05/25/2026 11:41:39 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numfou` sur numfou - `clef` sur numfou, typt - `clefcorbeille` sur numfou, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numfou` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numfou | dtem | salm |
|---|---|---|---|---|---|---|---|
| 44 | 1 | 0 | 1 | Mandrin de 152 mm n'est pas possible chez Lecta | 1216 | 04/08/2026 11:12:00 | 905 |
| 42 | 1 | 0 | 2 |  Il est impératif de respecter la quantité commandée (Tol... | 1093 | 01/29/2026 10:53:48 | 57 |
| 40 | 1 | 0 | 1 |  Il est impératif de respecter la quantité commandée (Tol... | 1093 | 01/29/2026 10:53:48 | 57 |

### `fic_foucomif`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numfou` sur numfou - `clef` sur numfou, typt - `clefcorbeille` sur numfou, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numfou` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `fic_foucomir`

Lignes : 1 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 3 - derniere activite (dtem) : 02/13/2026 08:53:20 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numfou` sur numfou - `clef` sur numfou, typt - `clefcorbeille` sur numfou, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numfou` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numfou | dtem | salm |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 2 |  | 1092 | 02/13/2026 08:53:20 | 57 |

### `fic_foucomis`

Lignes : 1 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 3 - derniere activite (dtem) : 02/13/2026 08:53:20 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numfou` sur numfou - `clef` sur numfou, typt - `clefcorbeille` sur numfou, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numfou` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numfou | dtem | salm |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 2 |  | 1092 | 02/13/2026 08:53:20 | 57 |

### `fic_foui`

Lignes : 265 - colonnes logiques : 18 - physiques : 18 - total corbeille comprise : 799 - derniere activite (dtem) : 07/15/2026 10:20:31 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numfou` sur numfou - `numint` sur numint - `def` sur def - `clef` sur numfou, numint - `clefcorbeille` sur numfou, numint, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `service` | octet |
| 5 | `civ` | octet |
| 6 | `nom` | texte(30) |
| 7 | `pre` | texte(30) |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `numfou` | entier4ns |
| 11 | `numint` | entier4ns |
| 12 | `tel` | texte(20) |
| 13 | `gsm` | texte(20) |
| 14 | `fax` | texte(20) |
| 15 | `mail` | texte(128) |
| 16 | `def` | octet |
| 17 | `mailaof` | octet |
| 18 | `mailcdf` | octet |

Dernieres lignes :

| id | bloq | corbeille | service | civ | nom | pre | dtem | salm | numfou | numint | tel | gsm | fax | mail | def | mailaof | mailcdf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 798 | 1 | 0 | 2 | 3 |  | Bonni | 07/15/2026 10:20:31 | 905 | 1183 | 4 | +8615180169737 |  |  | sales02@likexin.com | 0 | 2 | 2 |
| 796 | 1 | 0 | 2 | 3 | Chen | Susie | 07/15/2026 10:17:22 | 905 | 1183 | 3 | 86-755-81798130 | 86-755-27360113 |  | sales06@likexin.com | 0 | 2 | 2 |
| 791 | 1 | 0 | 2 | 2 | PLANQUE | Amandine | 06/23/2026 16:24:05 | 1 | 1222 | 1 |  |  |  | aplanque@airmat.com | 0 | 1 | 2 |

### `fic_gamme`

Lignes : 0 - colonnes logiques : 10 - physiques : 0 - total corbeille comprise : 13

Cles : `id` sur id (primaire) - `numclt` sur numclt - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `clef` sur numclt, numero - `clefcorbeille` sur numclt, numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numclt` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib1` | texte(50) |
| 8 | `lib2` | texte(50) |
| 9 | `numero` | entier2ns |
| 10 | `refcliche` | texte(20) |

### `fic_lang`

Lignes : 0 - colonnes logiques : 7 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier2ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(50) |

### `fic_lib`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(5) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib1` | texte(50) |
| 8 | `lib2` | texte(50) |

### `fic_liv`

Lignes : 39 - colonnes logiques : 15 - physiques : 15 - total corbeille comprise : 90 - derniere activite (dtem) : 06/04/2026 07:02:02 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(50) |
| 8 | `code1` | texte(5) |
| 9 | `code2` | texte(20) |
| 10 | `code3` | texte(10) |
| 11 | `kgmp` | numerique |
| 12 | `ctimb` | numerique |
| 13 | `psurt` | numerique |
| 14 | `scarb` | numerique |
| 15 | `teco` | numerique |

Dernieres lignes :

| id | numero | bloq | corbeille | dtem | salm | lib | code1 | code2 | code3 | kgmp | ctimb | psurt | scarb | teco |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 125 | 48 | 1 | 0 | 06/04/2026 07:02:02 | 57 | GONDRAND |  |  |  | 0.000 | 0.000000 | 0.000000 | 0.00 | 0.000000 |
| 123 | 9 | 1 | 0 | 04/24/2026 08:59:23 | 905 | Zipmend Express |  |  |  | 0.000 | 0.000000 | 0.000000 | 0.00 | 0.000000 |
| 121 | 8 | 1 | 0 | 02/02/2026 11:28:09 | 11 | Transports LEDY |  |  |  | 0.000 | 0.000000 | 0.000000 | 0.00 | 0.000000 |

### `fic_majdev`

Lignes : 2 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 4 - derniere activite (dtem) : 05/07/2012 15:37:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `amj` sur amj - `bloq` sur bloq - `corbeille` sur corbeille - `clef` sur code, amj - `clefcorbeille` sur code, amj, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `amj` | date |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `cour` | numerique |
| 7 | `bloq` | octet |
| 8 | `corbeille` | reel4 |

Dernieres lignes :

| id | code | amj | dtem | salm | cour | bloq | corbeille |
|---|---|---|---|---|---|---|---|
| 3 | E | 05/07/2012 00:00:00 | 05/07/2012 15:36:00 | 9998 | 1.000000 | 1 | 0 |
| 1 | DOL | 05/07/2012 00:00:00 | 05/07/2012 15:37:00 | 9998 | 1.305000 | 1 | 0 |

### `fic_nomen`

Lignes : 1 - colonnes logiques : 37 - physiques : 46 - total corbeille comprise : 2 - derniere activite (dtem) : 03/07/2016 11:47:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `libc1` sur libc1 - `qte` sur qte - `htn` sur htn - `lignenomen` sur lignenomen - `lpos` sur lpos - `rtype` sur rtype - `rcod1` sur rcod1 - `rcod2` sur rcod2 - `rcod3` sur rcod3 - `clef` sur type, code1, code2, code3, lignenomen - `clefcorbeille` sur type, code1, code2, code3, lignenomen, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `fam` | octet |
| 12 | `sfam` | entier4ns |
| 13 | `gamme` | entier2ns |
| 14 | `libc1` | texte(50) |
| 15 | `libc2` | texte(50) |
| 16 | `libc3` | texte(50) |
| 17 | `libc4` | texte(50) |
| 18 | `cuv` | texte(5) |
| 19 | `depot` | texte(10) |
| 20 | `qte` | reel8 |
| 21 | `htn` | numerique |
| 22 | `pa` | numerique |
| 23 | `pub` | numerique |
| 24 | `pun` | numerique |
| 25 | `suv` | octet |
| 26 | `vuv` | numerique |
| 27 | `net` | octet |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `lignenomen` | entier4ns |
| 31 | `lpos` | octet |
| 32 | `rtype` | octet |
| 33 | `rcod1` | texte(5) |
| 34 | `rcod2` | texte(20) |
| 35 | `rcod3` | texte(10) |
| 36 | `htb` | numerique |
| 37 | `com` | octet |

Dernieres lignes (les 30 premieres colonnes sur 46 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | amj | fam | sfam | gamme | libc1 | libc2 | libc3 | libc4 | cuv | depot | qte | htn | pa | pub | pun | suv | vuv | net | trem | rem | lignenomen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 03/07/2016 11:47:00 | 4 | 539 | 0010 |  | 1 | 11/30/1999 00:00:00 | 0 | 0 | 0 |  |  |  |  |  |  | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.00000 | 0 | 0 | 0.000000 | 0 |

### `fic_para`

Lignes : 1 401 - colonnes logiques : 12 - physiques : 12 - total corbeille comprise : 4 601 - derniere activite (dtem) : 08/11/2026 09:45:12 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `id` sur id (primaire) - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier4ns |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `des1` | texte(50) |
| 5 | `nom` | texte(1024) |
| 6 | `coe` | reel4 |
| 7 | `mt` | numerique |
| 8 | `qte` | reel8 |
| 9 | `num` | entier8 |
| 10 | `spe1` | texte(100) |
| 11 | `id` | entier8 |
| 12 | `corbeille` | reel4 |

Dernieres lignes :

| numero | dtem | salm | des1 | nom | coe | mt | qte | num | spe1 | id | corbeille |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 92608004 | 08/11/2026 09:45:12 | 9998 | Maj fic_reg Del/De1/De2 Labelys |  | 0 | 0.000 | 0 | 2 |  | 5470 | 0 |
| 92608003 | 08/11/2026 09:44:41 | 9998 | Maj fic_reg CodeLabelys |  | 0 | 0.000 | 0 | 2 |  | 5469 | 0 |
| 92608002 | 08/11/2026 09:44:07 | 9998 | Maj fic_uv CodeLabelys |  | 0 | 0.000 | 0 | 2 |  | 5468 | 0 |

### `fic_pays`

Lignes : 241 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 482 - derniere activite (dtem) : 09/01/2025 00:00:00 - extrait : TOP n + ORDER BY id DESC

Cles : `pays` sur pays - `code` sur code - `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur pays, corbeille

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `pays` | texte(50) |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code` | texte(2) |
| 5 | `id` | entier8 |
| 6 | `bloq` | octet |
| 7 | `corbeille` | reel4 |
| 8 | `code3` | texte(3) |
| 9 | `numero` | entier4ns |

Dernieres lignes :

| pays | dtem | salm | code | id | bloq | corbeille | code3 | numero |
|---|---|---|---|---|---|---|---|---|
| ZAMBIE | 09/01/2025 00:00:00 | 9998 | ZM | 949 | 1 | 0 | ZMB | 894 |
| SERBIE-ET-MONTENEGRO | 09/01/2025 00:00:00 | 9998 | CS | 947 | 1 | 0 | SCG | 891 |
| YEMEN | 09/01/2025 00:00:00 | 9998 | YE | 945 | 1 | 0 | YEM | 887 |

### `fic_piece`

Lignes : 24 - colonnes logiques : 5 - physiques : 17 - extrait : TOP n + ORDER BY id DESC

Cles : `gestion` sur gestion - `aa` sur aa - `id` sur id (primaire) - `clef` sur gestion, aa (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `gestion` | entier4ns |
| 2 | `aa` | entier2ns |
| 3 | `numero` | entier8ns |
| 4 | `id` | entier8 |
| 5 | `type` | octet |

Dernieres lignes :

| gestion | aa | numero | numero_2 | numero_3 | numero_4 | numero_5 | numero_6 | numero_7 | numero_8 | numero_9 | numero_10 | numero_11 | numero_12 | numero_13 | id | type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 2026 | 26010161 | 26020157 | 26030202 | 26040186 | 26050155 | 26060222 | 26070204 | 26080048 | 26090001 | 26100001 | 26110001 | 26120001 | 0 | 30 | 1 |
| 2 | 2026 | 2601012 | 2602003 | 2603014 | 2604008 | 2605010 | 2606005 | 2607007 | 2608001 | 2609001 | 2610001 | 2611001 | 2612001 | 0 | 29 | 1 |
| 2 | 2025 | 2501011 | 2502009 | 2503012 | 2504006 | 2505009 | 2506009 | 2507007 | 2508002 | 2509014 | 2510014 | 2511015 | 2512006 | 0 | 28 | 1 |

### `fic_point`

Lignes : 60 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 161 - derniere activite (dtem) : 03/02/2026 14:11:46 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `type` sur type - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `clefcorbeille` sur type, numero, corbeille (unique) - `clef` sur type, numero

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `type` | entier2ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(50) |
| 8 | `numero` | entier2ns |
| 9 | `Imputable` | octet |

Dernieres lignes :

| id | type | bloq | corbeille | dtem | salm | lib | numero | Imputable |
|---|---|---|---|---|---|---|---|---|
| 156 | 4 | 1 | 0 | 03/02/2026 14:11:46 | 9998 | Nettoyage Bunch (étiquettes collées entre plaques) | 77 | 1 |
| 154 | 4 | 1 | 0 | 03/02/2026 14:09:49 | 9998 | Retraction couteaux fin de bobine | 76 | 1 |
| 148 | 4 | 1 | 0 | 02/18/2026 08:51:56 | 9998 | Changement Cliché | 75 | 1 |

### `fic_prio`

Lignes : 1 - colonnes logiques : 7 - physiques : 7 - total corbeille comprise : 5 - derniere activite (dtem) : 11/02/2012 18:33:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(50) |

Dernieres lignes :

| id | numero | bloq | corbeille | dtem | salm | lib |
|---|---|---|---|---|---|---|
| 1 | 5 | 1 | 0 | 11/02/2012 18:33:00 | 9999 | Normal |

### `fic_reg`

Lignes : 13 - colonnes logiques : 14 - physiques : 14 - total corbeille comprise : 27 - derniere activite (dtem) : 05/13/2025 10:14:30 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib` | texte(50) |
| 8 | `mode` | octet |
| 9 | `er` | octet |
| 10 | `rgp` | octet |
| 11 | `codelabelys` | texte(50) |
| 12 | `de1labelys` | octet |
| 13 | `dellabelys` | entier2ns |
| 14 | `de2labelys` | octet |

Dernieres lignes :

| id | numero | bloq | corbeille | dtem | salm | lib | mode | er | rgp | codelabelys | de1labelys | dellabelys | de2labelys |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 26 | 13 | 1 | 0 | 05/13/2025 10:14:30 | 1 | Virement sur Proforma | 1 | 1 | 1 |  | 0 | 0 | 0 |
| 23 | 12 | 1 | 0 | 10/19/2021 06:41:48 | 9998 | Carte VISA | 1 | 1 | 1 |  | 0 | 0 | 0 |
| 21 | 11 | 1 | 0 | 12/30/2014 18:22:00 | 9999 | Chèque avec escompte 2% | 1 | 1 | 2 |  | 0 | 0 | 0 |

### `fic_rep`

Lignes : 5 - colonnes logiques : 18 - physiques : 117 - total corbeille comprise : 32 - derniere activite (dtem) : 06/04/2025 08:50:15 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `nom` sur nom - `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier2ns |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `nom` | texte(50) |
| 5 | `id` | entier8 |
| 6 | `bloq` | octet |
| 7 | `corbeille` | reel4 |
| 8 | `civ` | octet |
| 9 | `pca` | reel4 |
| 10 | `pma` | reel4 |
| 11 | `dep` | octet |
| 12 | `sal` | entier2ns |
| 13 | `adv` | entier2ns |
| 14 | `maildev` | octet |
| 15 | `mailarc` | octet |
| 16 | `mailbl` | octet |
| 17 | `mailvte` | octet |
| 18 | `mailecc` | octet |

Dernieres lignes (les 30 premieres colonnes sur 117 - tout est dans le JSON) :

| numero | dtem | salm | nom | id | bloq | corbeille | civ | pca | pma | dep | dep_2 | dep_3 | dep_4 | dep_5 | dep_6 | dep_7 | dep_8 | dep_9 | dep_10 | dep_11 | dep_12 | dep_13 | dep_14 | dep_15 | dep_16 | dep_17 | dep_18 | dep_19 | dep_20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 53 | 06/04/2025 08:50:15 | 12 | Christophe MOUCHERON | 27 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 13 | 03/28/2024 10:46:36 | 9998 | GRANGER Guillaume | 19 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 51 | 03/28/2024 10:45:50 | 9998 | GRANGER Patrice | 5 | 1 | 0 | 2 | 0.03 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_tar`

Lignes : 551 - colonnes logiques : 17 - physiques : 104 - total corbeille comprise : 1 102 - derniere activite (dtem) : 03/27/2013 15:31:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code` sur code - `type` sur type - `clef` sur type, code - `clefcorbeille` sur type, code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code` | texte(15) |
| 7 | `type` | entier2ns |
| 8 | `cuv` | texte(5) |
| 9 | `cuc` | texte(5) |
| 10 | `amj` | date |
| 11 | `amjv` | date |
| 12 | `qtemin` | reel8 |
| 13 | `qtemax` | reel8 |
| 14 | `pv` | numerique |
| 15 | `lib1` | texte(50) |
| 16 | `lib2` | texte(50) |
| 17 | `interv` | octet |

Dernieres lignes (les 30 premieres colonnes sur 104 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code | type | cuv | cuc | amj | amjv | qtemin | qtemin_2 | qtemin_3 | qtemin_4 | qtemin_5 | qtemin_6 | qtemin_7 | qtemin_8 | qtemin_9 | qtemin_10 | qtemin_11 | qtemin_12 | qtemin_13 | qtemin_14 | qtemin_15 | qtemin_16 | qtemin_17 | qtemin_18 | qtemin_19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1101 | 1 | 0 | 03/27/2013 12:06:00 | 9998 | YEK4 | 0 | M | U | 03/27/2013 00:00:00 |  | 0.01 | 999.99 | 0 | 1000 | 1999.99 | 76.3642 | 2000 | 2999.99 | 57.268 | 3000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1099 | 1 | 0 | 03/27/2013 12:06:00 | 9998 | YEK3 | 0 | M | U | 03/27/2013 00:00:00 |  | 0.01 | 999.99 | 0 | 1000 | 1999.99 | 93.0708 | 2000 | 2999.99 | 71.585 | 3000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1097 | 1 | 0 | 03/27/2013 12:06:00 | 9998 | YEK2 | 0 | M | U | 03/27/2013 00:00:00 |  | 0.01 | 999.99 | 0 | 1000 | 1999.99 | 103.8034 | 2000 | 2999.99 | 79.9486 | 3000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `fic_texte`

Lignes : 7 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 19 - derniere activite (dtem) : 01/10/2024 15:13:05 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `type` sur type - `bloq` sur bloq - `corbeille` sur corbeille - `codtxt` sur codtxt - `clef` sur type, codtxt - `clefcorbeille` sur type, codtxt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `type` | entier2ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `entete` | texte(1000) |
| 8 | `titre` | texte(50) |
| 9 | `codtxt` | texte(10) |
| 10 | `pied` | texte(1000) |

Dernieres lignes :

| id | type | bloq | corbeille | dtem | salm | entete | titre | codtxt | pied |
|---|---|---|---|---|---|---|---|---|---|
| 17 | 1 | 1 | 0 | 12/06/2022 12:45:15 | 9998 |  | Modification RIB Lidl | 3 | MODIFICATION DE RIB SUITE RETRAIT DU CM CIC FACTORING VIR... |
| 12 | 22 | 1 | 0 | 02/17/2021 17:12:53 | 9998 | Nous vous remercions pour votre demande de prix et vous p... | Test | TEST | Nos prix sont basés sur les coûts de production et matéri... |
| 9 | 22 | 1 | 0 | 12/21/2020 17:41:57 | 9998 | tryutryurtyu | tryurtyu | RTUYRTU | rtyurtyurtyu |

### `fic_tliv`

Lignes : 1 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 5 - derniere activite (dtem) : 01/18/2021 16:08:18 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero - `bloq` sur bloq - `corbeille` sur corbeille - `dep` sur dep - `pds` sur pds - `clef` sur numero, dep, pds - `clefcorbeille` sur numero, dep, pds, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `cout` | numerique |
| 8 | `dep` | entier2ns |
| 9 | `pds` | reel4 |
| 10 | `calc` | octet |
| 11 | `tran` | entier4ns |

Dernieres lignes :

| id | numero | bloq | corbeille | dtem | salm | cout | dep | pds | calc | tran |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 1 | 0 | 01/18/2021 16:08:18 | 9998 | 78.540000 | 75 | 600 | 2 | 200 |

### `fic_tva`

Lignes : 3 - colonnes logiques : 12 - physiques : 12 - total corbeille comprise : 8 - derniere activite (dtem) : 04/03/2023 11:03:04 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(5) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `valeur` | numerique |
| 8 | `ach` | entier8ns |
| 9 | `vte` | entier8ns |
| 10 | `amon` | entier8ns |
| 11 | `mon` | entier8ns |
| 12 | `codelabelys` | texte(10) |

Dernieres lignes :

| id | code | bloq | corbeille | dtem | salm | valeur | ach | vte | amon | mon | codelabelys |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 8 | 1 | 0 | 11/28/2020 10:24:08 | 3 | 0.00 | 4456600000 | 4457120100 | 4710000000 | 4710000000 |  |
| 3 | 9 | 1 | 0 | 03/13/2012 14:39:00 | 9999 | 0.00 | 4710000000 | 4710000000 | 0 | 0 |  |
| 1 | 1 | 1 | 0 | 04/03/2023 11:03:04 | 5 | 20.00 | 4456600000 | 4457120100 | 4710000000 | 4710000000 |  |

### `fic_ua`

Lignes : 46 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 107 - derniere activite (dtem) : 02/27/2026 16:32:42 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(5) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib1` | texte(10) |
| 8 | `nombre` | numerique |
| 9 | `sig` | octet |
| 10 | `lib2` | texte(50) |

Dernieres lignes :

| id | code | bloq | corbeille | dtem | salm | lib1 | nombre | sig | lib2 |
|---|---|---|---|---|---|---|---|---|---|
| 106 | 50 | 1 | 0 | 02/27/2026 16:32:42 | 1 | Rx500 | 500.00000 | 1 | Rx500 |
| 104 | BOB | 1 | 0 | 01/20/2026 08:34:46 | 1 | Bobine | 0.00000 | 1 | Bobine |
| 101 | ROLL | 1 | 0 | 04/23/2025 18:12:31 | 1 | Roll | 1.00000 | 1 | Price by Roll |

### `fic_uc`

Lignes : 138 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 315 - derniere activite (dtem) : 03/02/2026 10:27:33 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(5) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib1` | texte(10) |
| 8 | `nombre` | numerique |
| 9 | `sig` | octet |
| 10 | `lib2` | texte(50) |

Dernieres lignes :

| id | code | bloq | corbeille | dtem | salm | lib1 | nombre | sig | lib2 |
|---|---|---|---|---|---|---|---|---|---|
| 331 | B500 | 1 | 0 | 03/02/2026 10:27:33 | 9998 | Bobine 500 | 500.00000 | 0 | Bobine 500 étiquettes |
| 329 | BOB | 1 | 0 | 01/20/2026 08:36:01 | 1 | Bobine | 0.00000 | 0 | Bobine |
| 326 | ROLL | 1 | 0 | 09/11/2024 16:27:19 | 1 | Roll | 0.00000 | 0 | Roll |

### `fic_uv`

Lignes : 35 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 83 - derniere activite (dtem) : 01/20/2026 08:36:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(5) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `lib1` | texte(10) |
| 8 | `nombre` | numerique |
| 9 | `sig` | octet |
| 10 | `lib2` | texte(50) |
| 11 | `codelabelys` | texte(10) |

Dernieres lignes :

| id | code | bloq | corbeille | dtem | salm | lib1 | nombre | sig | lib2 | codelabelys |
|---|---|---|---|---|---|---|---|---|---|---|
| 82 | BOB | 1 | 0 | 01/20/2026 08:36:29 | 1 | Bobine | 0.00000 | 1 | Bobine |  |
| 80 | P | 1 | 0 | 01/19/2024 10:06:01 | 2 | Palette | 1.00000 | 2 | Prix à la palette |  |
| 67 | KG | 1 | 0 | 04/21/2021 12:11:36 | 7 | Kg | 1.00000 | 1 | Prix et Quantité au Kg |  |

### `fic_ville`

Lignes : 2 251 - colonnes logiques : 7 - physiques : 7 - total corbeille comprise : 4 676 - derniere activite (dtem) : 08/24/2026 15:13:41 - extrait : TOP n + ORDER BY id DESC

Cles : `ville` sur ville - `code` sur code - `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur code, ville, corbeille (unique) - `clef` sur code, ville

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `ville` | texte(50) |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code` | texte(10) |
| 5 | `id` | entier8 |
| 6 | `bloq` | octet |
| 7 | `corbeille` | reel4 |

Dernieres lignes :

| ville | dtem | salm | code | id | bloq | corbeille |
|---|---|---|---|---|---|---|
| SENNECE LES MACAON  | 08/24/2026 15:13:41 | 4 | 71000 | 4744 | 1 | 0 |
| POUPRY | 08/04/2026 11:28:34 | 57 | 28140 | 4742 | 1 | 0 |
| CABRIERES D’AVIGNON | 08/03/2026 09:41:16 | 57 | 84220 | 4740 | 1 | 0 |

### `gen_arbo`

Lignes : 594 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 1 296 - derniere activite (dtem) : 06/11/2026 14:15:01 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `nom` sur nom - `point` sur point - `titre` sur titre - `clefcorbeille` sur nom, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `nom` | texte(50) |
| 4 | `point` | texte(50) |
| 5 | `titre` | texte(50) |
| 6 | `vers` | texte(50) |
| 7 | `typchaine` | entier2ns |
| 8 | `salm` | entier2ns |
| 9 | `dtem` | horodatage |

Dernieres lignes :

| id | corbeille | nom | point | titre | vers | typchaine | salm | dtem |
|---|---|---|---|---|---|---|---|---|
| 1205 | 0 | ecf_reg.08 | 27.11.15.08 | Paramètres Décaissements fournisseurs | 4.00 | 3 | 5 | 09/24/2025 13:57:03 |
| 1203 | 0 | ecf_reg.07 | 27.11.15.07 | Utilitaires Décaissements fournisseurs | 4.00 | 3 | 5 | 09/24/2025 13:57:03 |
| 1201 | 0 | ecf_reg.06 | 27.11.15.06 | Divers Décaissements fournisseurs | 4.00 | 3 | 5 | 09/24/2025 13:57:03 |

### `gen_bloq`

Lignes : 351 - colonnes logiques : 4 - physiques : 4 - extrait : aucun (premieres lignes)

Cles : `nomfichier` sur nomfichier (primaire) - `numid` sur numid - `sal` sur sal - `clef` sur nomfichier, numid (primaire)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `nomfichier` | texte(50) |
| 2 | `numid` | entier8ns |
| 3 | `sal` | entier2ns |
| 4 | `pointmenu` | octet |

Dernieres lignes :

| nomfichier | numid | sal | pointmenu |
|---|---|---|---|
| fic_art | 11157 | 53 | 3 |
| fic_art | 6935 | 8 | 3 |
| fic_art | 24600 | 53 | 3 |

### `gen_mdp`

Lignes : 68 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 135 - derniere activite (dtem) : 11/23/2022 10:54:15 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `nom` sur nom - `clefcorbeille` sur nom, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `nom` | texte(50) |
| 5 | `salm` | entier2ns |
| 6 | `dtem` | horodatage |
| 7 | `mdp` | texte(20) |
| 8 | `tpsd1` | heure |
| 9 | `tpsf1` | heure |
| 10 | `tpsd2` | heure |
| 11 | `tpsf2` | heure |

Dernieres lignes :

| id | bloq | corbeille | nom | salm | dtem | mdp | tpsd1 | tpsf1 | tpsd2 | tpsf2 |
|---|---|---|---|---|---|---|---|---|---|---|
| 134 | 0 | 0 | fic_reg | 1 | 11/23/2022 10:54:15 |  | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 132 | 0 | 0 | out_cyl_04 | 9998 | 07/19/2022 12:38:30 |  | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 130 | 0 | 0 | fic_lang | 1 | 05/11/2022 13:52:28 |  | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |

### `gen_mdpsal`

Lignes : 12 310 - colonnes logiques : 8 - physiques : 8 - total corbeille comprise : 46 425 - derniere activite (dtem) : 07/29/2026 10:04:22 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `nom` sur nom - `sal` sur sal - `clefcorbeille` sur nom, sal, corbeille (unique) - `clef` sur nom, sal

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `nom` | texte(50) |
| 5 | `salm` | entier2ns |
| 6 | `dtem` | horodatage |
| 7 | `sal` | entier2ns |
| 8 | `autorisation` | octet |

Dernieres lignes :

| id | bloq | corbeille | nom | salm | dtem | sal | autorisation |
|---|---|---|---|---|---|---|---|
| 46434 | 0 | 0 | vtf_tdb.06 | 9998 | 11/17/2025 12:14:09 | 906 | 2 |
| 46432 | 0 | 0 | lif_tdb.06 | 9998 | 11/17/2025 12:14:09 | 906 | 2 |
| 46430 | 0 | 0 | cdf_tdb.06 | 9998 | 11/17/2025 12:14:09 | 906 | 2 |

### `gen_messa`

Lignes : 24 - colonnes logiques : 18 - physiques : 18 - total corbeille comprise : 48 - derniere activite (dtem) : 04/08/2019 09:30:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `destinataire` sur destinataire - `expediteur` sur expediteur - `amjm` sur amjm - `clef` sur destinataire, expediteur, amjm - `clefcorbeille` sur destinataire, expediteur, amjm, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `salm` | entier2ns |
| 5 | `dtem` | horodatage |
| 6 | `destinataire` | entier2ns |
| 7 | `expediteur` | entier2ns |
| 8 | `amjm` | horodatage |
| 9 | `messa` | texte(1500) |
| 10 | `pos` | texte(1) |
| 11 | `amjx` | horodatage |
| 12 | `amjy` | horodatage |
| 13 | `amjz` | horodatage |
| 14 | `amjw` | horodatage |
| 15 | `orpiece` | entier4ns |
| 16 | `nbpiece` | entier4ns |
| 17 | `piece` | texte(1024) |
| 18 | `typepj` | texte(10) |

Dernieres lignes :

| id | bloq | corbeille | salm | dtem | destinataire | expediteur | amjm | messa | pos | amjx | amjy | amjz | amjw | orpiece | nbpiece | piece | typepj |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 47 | 1 | 0 | 9999 | 12/17/2014 15:28:44 | 9999 | 9999 | 12/17/2014 15:28:44 | Message depuis Gestion des commandes. Une pièce jointe : ... | A | 12/17/2014 15:28:00 | 12/17/2014 15:28:00 | 12/17/2014 15:29:00 | 11/30/1999 00:00:00 | 24 | 1 | 9185 |  |
| 45 | 1 | 0 | 9998 | 05/29/2012 15:04:31 | 9998 | 9998 | 05/29/2012 15:04:31 | Message depuis Gestion des commandes. Une pièce jointe : ... | A | 05/29/2012 15:04:00 | 05/29/2012 15:06:00 | 05/29/2012 15:06:00 | 11/30/1999 00:00:00 | 24 | 1 | 7 |  |
| 43 | 1 | 0 | 9998 | 05/18/2012 15:12:48 | 9998 | 9998 | 05/18/2012 15:12:48 |   sdfghsfdg sdfgsdfg                            | A | 05/18/2012 15:13:00 | 05/18/2012 15:13:00 | 05/18/2012 15:13:00 | 11/30/1999 00:00:00 | 0 | 0 |  |  |

### `gen_sala`

Lignes : 34 - colonnes logiques : 79 - physiques : 79 - total corbeille comprise : 347 - derniere activite (dtem) : 07/28/2026 11:49:53 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `mdp` sur mdp - `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique) - `mdpcorbeille` sur mdp, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier4ns |
| 2 | `dtem` | horodatage |
| 3 | `service` | octet |
| 4 | `civ` | octet |
| 5 | `nom` | texte(30) |
| 6 | `pre` | texte(30) |
| 7 | `ad1` | texte(30) |
| 8 | `ad2` | texte(30) |
| 9 | `ad3` | texte(30) |
| 10 | `ad4` | texte(30) |
| 11 | `cp` | texte(10) |
| 12 | `vil` | texte(30) |
| 13 | `cpays` | texte(5) |
| 14 | `pays` | texte(50) |
| 15 | `telf` | texte(30) |
| 16 | `telp` | texte(30) |
| 17 | `mail` | texte(128) |
| 18 | `logmail` | texte(50) |
| 19 | `pasmail` | texte(50) |
| 20 | `arcmail` | octet |
| 21 | `copiemail` | octet |
| 22 | `corpsmail` | octet |
| 23 | `alias` | texte(10) |
| 24 | `mdp` | texte(20) |
| 25 | `th` | reel4 |
| 26 | `affsaisie` | octet |
| 27 | `Typeedition` | octet |
| 28 | `affhisto` | octet |
| 29 | `affliste` | octet |
| 30 | `graphe` | octet |
| 31 | `okp1` | octet |
| 32 | `okp2` | octet |
| 33 | `okp3` | octet |
| 34 | `okl1` | octet |
| 35 | `okl2` | octet |
| 36 | `fondecran` | texte(1024) |
| 37 | `salm` | entier2ns |
| 38 | `okl3` | octet |
| 39 | `oka1` | octet |
| 40 | `oka2` | octet |
| 41 | `oka3` | octet |
| 42 | `okh1` | octet |
| 43 | `okh2` | octet |
| 44 | `okh3` | octet |
| 45 | `oks1` | octet |
| 46 | `oks2` | octet |
| 47 | `oks3` | octet |
| 48 | `okpa` | octet |
| 49 | `signaturecc` | octet |
| 50 | `id` | entier8 |
| 51 | `bloq` | octet |
| 52 | `corbeille` | reel4 |
| 53 | `pagegarde` | octet |
| 54 | `okandroid` | octet |
| 55 | `okpv` | octet |
| 56 | `okregclt` | octet |
| 57 | `okcorbeille` | octet |
| 58 | `okrestaurhisto` | octet |
| 59 | `oksupport` | octet |
| 60 | `lectpdf` | octet |
| 61 | `idpointeuse` | texte(20) |
| 62 | `lsv` | octet |
| 63 | `actufen` | octet |
| 64 | `copmaildev` | octet |
| 65 | `copmailcde` | octet |
| 66 | `copmailliv` | octet |
| 67 | `copmailvte` | octet |
| 68 | `copmailecc` | octet |
| 69 | `copmailaof` | octet |
| 70 | `copmailcdf` | octet |
| 71 | `okregfou` | octet |
| 72 | `okaccordclt` | octet |
| 73 | `okaccordfou` | octet |
| 74 | `okcptclt` | octet |
| 75 | `okcptfou` | octet |
| 76 | `okbqeclt` | octet |
| 77 | `okbqefou` | octet |
| 78 | `okbloqclt` | octet |
| 79 | `okpctmargeclt` | octet |

Dernieres lignes (les 30 premieres colonnes sur 79 - tout est dans le JSON) :

| numero | dtem | service | civ | nom | pre | ad1 | ad2 | ad3 | ad4 | cp | vil | cpays | pays | telf | telp | mail | logmail | pasmail | arcmail | copiemail | corpsmail | alias | mdp | th | affsaisie | Typeedition | affhisto | affliste | graphe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 913 | 01/27/2026 13:34:40 | 4 | 2 | VERNISSE | Bastien |  |  |  |  | 03510 | CHASSENARD -> 03510 | FR | FRANCE |  |  |  |  |  | 1 | 2 | 1 |  | 6280Vern59 | 0 | 1 | 1 | 1 | 1 | 1 |
| 912 | 03/11/2026 14:57:23 | 4 | 2 | MAYEUR | Henri |  |  |  |  | 59493 | VILLENEUVE D'ASCQ   -> 59493 | FR | FRANCE |  |  |  |  |  | 1 | 2 | 1 |  | 6280maye59 | 0 | 1 | 1 | 1 | 1 | 1 |
| 911 | 01/27/2026 13:34:09 | 4 | 2 | ADYNS | Mickael |  |  |  |  | 59510 | HEM -> 59510 | FR | FRANCE |  |  |  |  |  | 1 | 2 | 1 |  | 6280Adyn59 | 0 | 1 | 1 | 1 | 1 | 1 |

### `gen_soc`

Lignes : 17 - colonnes logiques : 16 - physiques : 16 - extrait : TOP n + ORDER BY id DESC

Cles : `code` sur code (unique) - `id` sur id (primaire) - `libelle` sur libelle - `type` sur type - `bdd` sur bdd - `serveur` sur serveur - `port` sur port - `utilisateur` sur utilisateur - `mdp` sur mdp - `principale` sur principale

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `code` | texte(20) |
| 2 | `id` | entier8 |
| 3 | `libelle` | texte(50) |
| 4 | `type` | octet |
| 5 | `bdd` | texte(50) |
| 6 | `serveur` | texte(1024) |
| 7 | `port` | texte(10) |
| 8 | `compression` | octet |
| 9 | `cryptage` | octet |
| 10 | `utilisateur` | texte(50) |
| 11 | `mdp` | texte(50) |
| 12 | `acces` | octet |
| 13 | `infos` | texte(100) |
| 14 | `curseur` | texte(100) |
| 15 | `principale` | octet |
| 16 | `chemcomp` | texte(1024) |

Dernieres lignes :

| code | id | libelle | type | bdd | serveur | port | compression | cryptage | utilisateur | mdp | acces | infos | curseur | principale | chemcomp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TESTS | 60 | SIFA TESTS | 1 | sifatests_cs | 192.168.100.199 | 4949 | 0 | 0 | Admin | 4yCp8/Z9szQ | 0 |  |  | 1 |  |
| z~SIFA9016 | 58 |  | 0 |  |  |  | 0 | 0 | Admin |  | 0 | Format nom fichier outils | 2 | 0 |  |
| z~SIFA9015 | 56 |  | 0 |  |  |  | 0 | 0 | Admin |  | 0 | Option pdf outils | 1 | 0 |  |

### `gpr_art`

Lignes : 2 - colonnes logiques : 18 - physiques : 18 - total corbeille comprise : 5 - derniere activite (dtem) : 02/23/2022 15:33:17 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `service` sur service - `operateur` sur operateur - `amj` sur amj - `mach` sur mach - `dos` sur dos - `ligne` sur ligne - `numclt` sur numclt - `type` sur type - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `clef` sur type, code1, code2, code3, service, operateur, amj - `clefcorbeille` sur type, code1, code2, code3, service, operateur, amj, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `mach` | texte(10) |
| 10 | `dos` | entier8ns |
| 11 | `ligne` | entier4ns |
| 12 | `numclt` | entier4ns |
| 13 | `qtes` | entier8ns |
| 14 | `orig` | texte(1) |
| 15 | `type` | entier4ns |
| 16 | `code1` | texte(5) |
| 17 | `code2` | texte(20) |
| 18 | `code3` | texte(10) |

Dernieres lignes :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | mach | dos | ligne | numclt | qtes | orig | type | code1 | code2 | code3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0 | 0 | 02/23/2022 15:33:17 | 9998 | 5 | 9998 | 02/23/2022 15:33:15 | 1 | 1009 | 1 | 24 | 1000 |  | 1 | 24 | 0012 |  |
| 1 | 0 | 0 | 04/28/2021 12:07:35 | 9998 | 5 | 9998 | 04/28/2021 12:07:33 | 1 | 1000 | 1 | 1050 | 10000 |  | 1 | 1050 | 0001 |  |

### `gpr_ff`

Lignes : 584 - colonnes logiques : 231 - physiques : 302 - total corbeille comprise : 1 583 - derniere activite (dtem) : 07/08/2026 17:07:24 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `operateur` sur operateur - `clef` sur type, code1, code2, code3 - `clefcorbeille` sur type, code1, code2, code3, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `nmac1` | texte(10) |
| 12 | `labftl` | reel8 |
| 13 | `nmac2` | texte(10) |
| 14 | `nmac3` | texte(10) |
| 15 | `nmac4` | texte(10) |
| 16 | `nmac5` | texte(10) |
| 17 | `typeff` | octet |
| 18 | `typefiniff` | octet |
| 19 | `nocond` | texte(10) |
| 20 | `m1cod1` | texte(5) |
| 21 | `m1cod2` | texte(20) |
| 22 | `m1cod3` | texte(10) |
| 23 | `m2cod1` | texte(5) |
| 24 | `m2cod2` | texte(20) |
| 25 | `m2cod3` | texte(10) |
| 26 | `m3cod1` | texte(5) |
| 27 | `m3cod2` | texte(20) |
| 28 | `m3cod3` | texte(10) |
| 29 | `m4cod1` | texte(5) |
| 30 | `m4cod2` | texte(20) |
| 31 | `m4cod3` | texte(10) |
| 32 | `m5cod1` | texte(5) |
| 33 | `m5cod2` | texte(20) |
| 34 | `m5cod3` | texte(10) |
| 35 | `tdec1` | entier4ns |
| 36 | `ndec1` | entier8ns |
| 37 | `tdec2` | entier4ns |
| 38 | `ndec2` | entier8ns |
| 39 | `tdec3` | entier4ns |
| 40 | `ndec3` | entier8ns |
| 41 | `tdec4` | entier4ns |
| 42 | `ndec4` | entier8ns |
| 43 | `tdec5` | entier4ns |
| 44 | `ndec5` | entier8ns |
| 45 | `laiout` | reel8 |
| 46 | `laimat` | reel8 |
| 47 | `laimat2` | reel8 |
| 48 | `laimat3` | reel8 |
| 49 | `laimat4` | reel8 |
| 50 | `laimat5` | reel8 |
| 51 | `cliche` | texte(20) |
| 52 | `cliche1` | texte(20) |
| 53 | `cliche2` | texte(20) |
| 54 | `cliche3` | texte(20) |
| 55 | `cliche4` | texte(20) |
| 56 | `cliche5` | texte(20) |
| 57 | `quadri` | octet |
| 58 | `nbcoul` | octet |
| 59 | `encrserig` | octet |
| 60 | `gauf` | octet |
| 61 | `numerot` | octet |
| 62 | `perfcaroll` | octet |
| 63 | `embos` | octet |
| 64 | `impc` | octet |
| 65 | `spotdos` | octet |
| 66 | `grat` | octet |
| 67 | `verrel` | octet |
| 68 | `verneut` | octet |
| 69 | `verpo` | octet |
| 70 | `ntramac1` | entier4ns |
| 71 | `ntramac2` | entier4ns |
| 72 | `ntramac3` | entier4ns |
| 73 | `ntramac4` | entier4ns |
| 74 | `ntramac5` | entier4ns |
| 75 | `tvitmac1` | octet |
| 76 | `tvitmac2` | octet |
| 77 | `tvitmac3` | octet |
| 78 | `tvitmac4` | octet |
| 79 | `tvitmac5` | octet |
| 80 | `vitmac1` | entier4ns |
| 81 | `vitmac2` | entier4ns |
| 82 | `vitmac3` | entier4ns |
| 83 | `vitmac4` | entier4ns |
| 84 | `vitmac5` | entier4ns |
| 85 | `tvitcond` | octet |
| 86 | `vitcond` | entier4ns |
| 87 | `nbcliche` | octet |
| 88 | `espacliche` | reel8 |
| 89 | `nbposacliche` | entier4ns |
| 90 | `nbdtcliche` | entier4ns |
| 91 | `espacliche1` | reel8 |
| 92 | `nbposacliche1` | entier4ns |
| 93 | `espacliche2` | reel8 |
| 94 | `nbposacliche2` | entier4ns |
| 95 | `espacliche3` | reel8 |
| 96 | `nbposacliche3` | entier4ns |
| 97 | `espacliche4` | reel8 |
| 98 | `nbposacliche4` | entier4ns |
| 99 | `espacliche5` | reel8 |
| 100 | `nbposacliche5` | entier4ns |
| 101 | `nbdtcliche1` | entier4ns |
| 102 | `nbdtcliche2` | entier4ns |
| 103 | `nbdtcliche3` | entier4ns |
| 104 | `nbdtcliche4` | entier4ns |
| 105 | `nbdtcliche5` | entier4ns |
| 106 | `typematbasebof` | octet |
| 107 | `pelcod1` | texte(5) |
| 108 | `pelcod2` | texte(20) |
| 109 | `laipel` | entier4ns |
| 110 | `dorcod1` | texte(5) |
| 111 | `dorcod2` | texte(20) |
| 112 | `laidor` | entier4ns |
| 113 | `magdor` | texte(10) |
| 114 | `coudor` | texte(10) |
| 115 | `vercod1` | texte(5) |
| 116 | `vercod2` | texte(20) |
| 117 | `vercouv` | texte(10) |
| 118 | `verbcod1` | texte(5) |
| 119 | `verbcod2` | texte(20) |
| 120 | `verchab` | texte(10) |
| 121 | `pelcod21` | texte(5) |
| 122 | `pelcod22` | texte(20) |
| 123 | `laipel2` | entier4ns |
| 124 | `dorcod21` | texte(5) |
| 125 | `dorcod22` | texte(20) |
| 126 | `laidor2` | entier4ns |
| 127 | `magdor2` | texte(10) |
| 128 | `coudor2` | texte(10) |
| 129 | `coul` | texte(200) |
| 130 | `teint` | entier8ns |
| 131 | `pms` | texte(100) |
| 132 | `pencrt` | reel4 |
| 133 | `typimp` | octet |
| 134 | `recver` | octet |
| 135 | `ngser` | octet |
| 136 | `seri` | texte(50) |
| 137 | `chabser` | texte(50) |
| 138 | `coulimpc` | texte(10) |
| 139 | `coulspotdos` | texte(10) |
| 140 | `com` | octet |
| 141 | `labforme` | octet |
| 142 | `labfta` | reel8 |
| 143 | `labnbl` | entier4ns |
| 144 | `labnba` | entier4ns |
| 145 | `nbedit` | octet |
| 146 | `matcomtech` | octet |
| 147 | `indice` | texte(10) |
| 148 | `matrefclt` | octet |
| 149 | `labcod1` | texte(5) |
| 150 | `labcod2` | texte(20) |
| 151 | `labcod3` | texte(10) |
| 152 | `nbeflivret` | octet |
| 153 | `c1_ner` | entier8ns |
| 154 | `c1_dmax` | entier4ns |
| 155 | `c1_dman` | reel4 |
| 156 | `c1_nef` | entier4ns |
| 157 | `c1_mlr` | reel8 |
| 158 | `c1_lm` | reel8 |
| 159 | `c1_e1` | octet |
| 160 | `c1_e2` | octet |
| 161 | `c1_pose` | octet |
| 162 | `c1_film` | octet |
| 163 | `c1_emb` | octet |
| 164 | `c1_pds` | reel4 |
| 165 | `cartlarg` | entier2ns |
| 166 | `cartlong` | entier2ns |
| 167 | `carthaut` | entier2ns |
| 168 | `cartnbetiq` | entier8ns |
| 169 | `cartpds` | reel4 |
| 170 | `c2_nep` | entier8ns |
| 171 | `c2_nef` | entier4ns |
| 172 | `c2_lf` | entier4ns |
| 173 | `c2_com` | texte(35) |
| 174 | `c2_pp` | texte(8) |
| 175 | `c2_ref` | texte(10) |
| 176 | `c2_nbp` | entier8ns |
| 177 | `c2_neb` | entier8ns |
| 178 | `c3_plc` | entier8ns |
| 179 | `c3_etiqp` | entier8ns |
| 180 | `c3_qcol` | entier8ns |
| 181 | `c3_pdspqt` | reel4 |
| 182 | `c3_pdscol` | reel4 |
| 183 | `c3_emb` | octet |
| 184 | `c3_typ` | octet |
| 185 | `c3_autre` | texte(20) |
| 186 | `c4_pqt` | entier8ns |
| 187 | `c4_qcol` | entier8ns |
| 188 | `c4_carlar` | entier2ns |
| 189 | `c4_carlon` | entier2ns |
| 190 | `c4_carhau` | entier2ns |
| 191 | `c4_film` | octet |
| 192 | `c4_elas` | octet |
| 193 | `c4_emb` | octet |
| 194 | `c4_pdspqt` | reel4 |
| 195 | `c4_pdscol` | reel4 |
| 196 | `c4_pdscar` | reel4 |
| 197 | `veranil` | reel4 |
| 198 | `perf1` | texte(10) |
| 199 | `perf2` | texte(10) |
| 200 | `operateur` | entier2ns |
| 201 | `c1_amorce` | octet |
| 202 | `repiquage` | octet |
| 203 | `impdorsal` | octet |
| 204 | `poscharniere` | octet |
| 205 | `perfointer` | octet |
| 206 | `testcltdivers2` | octet |
| 207 | `blancsoutien` | octet |
| 208 | `cleartoner` | octet |
| 209 | `extracouleur` | octet |
| 210 | `echencomplexe` | octet |
| 211 | `noportelame` | entier4ns |
| 212 | `nbelame` | octet |
| 213 | `perfotls` | entier4 |
| 214 | `c1_eman` | reel4 |
| 215 | `cartcode1` | texte(5) |
| 216 | `cartcode2` | texte(20) |
| 217 | `cartcode3` | texte(10) |
| 218 | `palcode1` | texte(5) |
| 219 | `palcode2` | texte(20) |
| 220 | `palcode3` | texte(10) |
| 221 | `testcltdivers1` | octet |
| 222 | `testcltdivers3` | octet |
| 223 | `pallargeur` | entier2ns |
| 224 | `pallongueur` | entier2ns |
| 225 | `paltype` | octet |
| 226 | `palnbcart` | entier2ns |
| 227 | `palpds` | reel4 |
| 228 | `palnbcartsol` | entier2ns |
| 229 | `palnbetage` | entier2ns |
| 230 | `palhautmax` | entier2ns |
| 231 | `cartnbbob` | entier4 |

Dernieres lignes (les 30 premieres colonnes sur 302 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | amj | nmac1 | labftl | nmac2 | nmac3 | nmac4 | nmac5 | typeff | typefiniff | nocond | m1cod1 | m1cod2 | m1cod3 | m2cod1 | m2cod2 | m2cod3 | m3cod1 | m3cod2 | m3cod3 | m4cod1 | m4cod2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1647 | 1 | 0 | 07/08/2026 17:07:24 | 12 | 890 | 0111 |  | 1 | 07/08/2026 17:07:24 | 2 | 0 |  |  |  |  | 1 | 2 |  | 886 | 0302 |  |  |  |  |  |  |  |  |  |
| 1645 | 1 | 0 | 07/08/2026 17:03:01 | 12 | 890 | 0110 |  | 1 | 07/08/2026 17:03:01 | 2 | 0 |  |  |  |  | 1 | 2 |  | 886 | 0307 |  |  |  |  |  |  |  |  |  |
| 1643 | 1 | 0 | 06/29/2026 16:11:37 | 4 | 1183 | 0037 |  | 1 | 06/29/2026 16:11:37 | 1 | 0 |  |  |  |  | 1 | 1 |  | 886 | 0104 |  |  |  |  |  |  |  |  |  |

### `gpr_ff1`

Lignes : 1 202 - colonnes logiques : 20 - physiques : 229 - total corbeille comprise : 2 701 - derniere activite (dtem) : 06/04/2026 15:15:43 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `clef` sur type, code1, code2, code3 - `clefcorbeille` sur type, code1, code2, code3, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `coul` | texte(400) |
| 11 | `teint` | entier8ns |
| 12 | `pms` | texte(200) |
| 13 | `pencrt` | reel4 |
| 14 | `recver` | octet |
| 15 | `typeimp` | octet |
| 16 | `descriptif` | texte(300) |
| 17 | `cc` | texte(300) |
| 18 | `afaire` | octet |
| 19 | `ordremac` | octet |
| 20 | `anilox` | texte(100) |

Dernieres lignes (les 30 premieres colonnes sur 229 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | coul | coul_2 | coul_3 | coul_4 | coul_5 | coul_6 | coul_7 | coul_8 | coul_9 | coul_10 | coul_11 | coul_12 | coul_13 | coul_14 | coul_15 | coul_16 | coul_17 | coul_18 | coul_19 | coul_20 | teint |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2777 | 1 | 0 | 06/04/2026 15:15:43 | 4 | 1164 | 0064 |  | 1 | BLACK | VIOLET PASTEL | BLACK |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 88501045 |
| 2775 | 1 | 0 | 06/02/2026 11:14:21 | 4 | 1164 | 0063 |  | 1 | BLACK | VIOLET PASTEL | BLACK |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 88501045 |
| 2773 | 1 | 0 | 06/02/2026 11:11:13 | 4 | 1164 | 0062 |  | 1 | BLACK | VIOLET PASTEL | BLACK |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 88501045 |

### `gpr_ffcomic`

Lignes : 535 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 1 093 - derniere activite (dtem) : 07/08/2026 17:07:24 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 2010 | 0 | 0 | 890 | 0111 |  | 1 | 2 | RACCORDS INTERDITS DANS LES BOBINES POUR LE CLIENT. IMPER... | 07/08/2026 17:07:24 | 12 |
| 2008 | 0 | 0 | 890 | 0110 |  | 1 | 2 | Etiquette de contrôle à mettre à l''intérieur du mandrin:... | 07/08/2026 17:03:01 | 12 |
| 2006 | 0 | 0 | 1183 | 0037 |  | 1 | 2 |  | 06/29/2026 16:11:37 | 4 |

### `gpr_ffcomif`

Lignes : 1 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 3 - derniere activite (dtem) : 03/16/2026 10:54:12 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | texte(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 2642 | 1 | 0 | 1245 | 0005 |  | 1 | 2 |  | 03/16/2026 10:54:12 | 9998 |

### `gpr_gpr`

Lignes : 2 804 - colonnes logiques : 15 - physiques : 15 - total corbeille comprise : 2 804 - derniere activite (dtem) : 04/17/2026 15:01:58 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `service` sur service - `operateur` sur operateur - `amj` sur amj - `pt` sur pt - `mach` sur mach - `dos` sur dos - `ligne` sur ligne - `numclt` sur numclt - `clef` sur service, operateur, amj - `clefcorbeille` sur service, operateur, amj, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `pt` | octet |
| 10 | `mach` | texte(10) |
| 11 | `dos` | entier8ns |
| 12 | `ligne` | entier4ns |
| 13 | `numclt` | entier4ns |
| 14 | `qtef` | entier8ns |
| 15 | `orig` | texte(1) |

Dernieres lignes :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | pt | mach | dos | ligne | numclt | qtef | orig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3071 | 0 | 0 | 04/17/2026 15:01:58 | 913 | 4 | 913 | 04/17/2026 15:01:58 | 87 | 9999 | 0 | 0 | 0 | 0 |  |
| 3070 | 0 | 0 | 04/17/2026 15:01:57 | 913 | 4 | 913 | 04/17/2026 15:01:57 | 89 | 2 | 1045 | 1 | 912 | 1318250 |  |
| 3069 | 0 | 0 | 04/17/2026 14:57:12 | 913 | 4 | 913 | 04/17/2026 14:57:12 | 3 | 2 | 1045 | 1 | 912 | 0 |  |

### `gpr_gprcom`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `service` sur service - `operateur` sur operateur - `amj` sur amj - `pt` sur pt - `clef` sur service, operateur, amj, pt, typt - `clefcorbeille` sur service, operateur, amj, pt, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `dtem` | horodatage |
| 7 | `salm` | entier2ns |
| 8 | `service` | octet |
| 9 | `operateur` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `pt` | octet |

### `gpr_mat`

Lignes : 243 - colonnes logiques : 23 - physiques : 32 - total corbeille comprise : 653 - derniere activite (dtem) : 04/10/2026 13:31:25 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `service` sur service - `operateur` sur operateur - `amj` sur amj - `mach` sur mach - `dos` sur dos - `ligne` sur ligne - `numclt` sur numclt - `type` sur type - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `lai` sur lai - `saipos` sur saipos - `lpos` sur lpos - `clef` sur type, code1, code2, code3, lai, service, operateur, saipos, amj - `clefcorbeille` sur type, code1, code2, code3, lai, service, operateur, saipos, amj, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `mach` | texte(10) |
| 10 | `dos` | entier8ns |
| 11 | `ligne` | entier4ns |
| 12 | `numclt` | entier4ns |
| 13 | `qtes` | entier8ns |
| 14 | `orig` | texte(1) |
| 15 | `reflot` | texte(150) |
| 16 | `type` | entier4ns |
| 17 | `code1` | texte(5) |
| 18 | `code2` | texte(20) |
| 19 | `code3` | texte(10) |
| 20 | `lai` | entier4ns |
| 21 | `saipos` | texte(25) |
| 22 | `lpos` | octet |
| 23 | `qtev` | entier8ns |

Dernieres lignes (les 30 premieres colonnes sur 32 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | mach | dos | ligne | numclt | qtes | orig | reflot | reflot_2 | reflot_3 | reflot_4 | reflot_5 | reflot_6 | reflot_7 | reflot_8 | reflot_9 | reflot_10 | type | code1 | code2 | code3 | lai | saipos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 652 | 0 | 0 | 04/10/2026 13:31:25 | 913 | 4 | 913 | 04/10/2026 13:31:25 | 2 | 1061 | 1 | 225 | 15036 |  |  |  |  |  |  |  |  |  |  |  | 5 | 1 | 0007 |  | 470 | P1~323 |
| 650 | 0 | 0 | 04/10/2026 13:31:25 | 913 | 4 | 913 | 04/10/2026 13:31:25 | 2 | 1061 | 1 | 225 | 388 |  |  |  |  |  |  |  |  |  |  |  | 7 | 1055 | 0006 |  | 0 | P1~322 |
| 648 | 0 | 0 | 04/10/2026 13:31:25 | 913 | 4 | 913 | 04/10/2026 13:31:25 | 2 | 1061 | 1 | 225 | 15036 |  |  |  |  |  |  |  |  |  |  |  | 2 | 1183 | 0001 |  | 470 | P1~321 |

### `gpr_sat`

Lignes : 26 - colonnes logiques : 9 - physiques : 9 - derniere activite (dtem) : 03/27/2026 09:35:00 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `numero` sur numero (unique) - `bloq` sur bloq

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `ini1` | octet |
| 7 | `ini2` | texte(10) |
| 8 | `ini3` | octet |
| 9 | `ini4` | octet |

Dernieres lignes :

| id | numero | bloq | dtem | salm | ini1 | ini2 | ini3 | ini4 |
|---|---|---|---|---|---|---|---|---|
| 26 | 26 | 1 | 02/19/2026 13:52:35 | 907 | 1 |  | 0 | 0 |
| 25 | 25 | 1 | 02/17/2026 16:12:45 | 9998 | 5 | 0 | 0 | 0 |
| 24 | 24 | 1 | 01/23/2026 13:30:25 | 57 | 1 |  | 0 | 0 |

### `lab_comit`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `lab_entete`

Lignes : 0 - colonnes logiques : 59 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjc` sur amjc - `numclt` sur numclt - `rs` sur rs - `groupeclt` sur groupeclt - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `numrep` sur numrep - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjc` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `adr1` | texte(50) |
| 20 | `adr2` | texte(50) |
| 21 | `ville` | texte(50) |
| 22 | `bp` | texte(10) |
| 23 | `edi` | octet |
| 24 | `vref` | texte(50) |
| 25 | `nref` | texte(50) |
| 26 | `civ` | octet |
| 27 | `interlocuteur` | texte(50) |
| 28 | `tex` | texte(10) |
| 29 | `mail` | texte(128) |
| 30 | `com` | octet |
| 31 | `numint` | entier4ns |
| 32 | `dest` | texte(1) |
| 33 | `intclt` | entier4ns |
| 34 | `lrs` | texte(50) |
| 35 | `ladr1` | texte(50) |
| 36 | `ladr2` | texte(50) |
| 37 | `lcp` | texte(10) |
| 38 | `lville` | texte(50) |
| 39 | `lpays` | texte(50) |
| 40 | `amje` | date |
| 41 | `amjl` | date |
| 42 | `lcpays` | texte(5) |
| 43 | `numrep` | entier2ns |
| 44 | `exped` | texte(1) |
| 45 | `amjp` | horodatage |
| 46 | `fbat` | octet |
| 47 | `fcli` | octet |
| 48 | `typcli` | octet |
| 49 | `epreuve` | octet |
| 50 | `bimpose` | octet |
| 51 | `etude` | octet |
| 52 | `fichier` | octet |
| 53 | `modele` | octet |
| 54 | `retourclt` | octet |
| 55 | `fourni` | octet |
| 56 | `outil` | octet |
| 57 | `posi` | octet |
| 58 | `batn` | octet |
| 59 | `imp` | octet |

### `lab_ligne`

Lignes : 0 - colonnes logiques : 58 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `code1` sur code1 - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `type` | entier2ns |
| 7 | `vref` | texte(50) |
| 8 | `nref` | texte(50) |
| 9 | `code1` | texte(5) |
| 10 | `com` | octet |
| 11 | `lrs` | texte(50) |
| 12 | `ladr1` | texte(50) |
| 13 | `ladr2` | texte(50) |
| 14 | `lcp` | texte(10) |
| 15 | `lville` | texte(50) |
| 16 | `lpays` | texte(50) |
| 17 | `amje` | date |
| 18 | `amjl` | date |
| 19 | `lcpays` | texte(5) |
| 20 | `fbat` | octet |
| 21 | `fcli` | octet |
| 22 | `typcli` | octet |
| 23 | `epreuve` | octet |
| 24 | `bimpose` | octet |
| 25 | `etude` | octet |
| 26 | `fichier` | octet |
| 27 | `modele` | octet |
| 28 | `retourclt` | octet |
| 29 | `fourni` | octet |
| 30 | `outil` | octet |
| 31 | `posi` | octet |
| 32 | `ligne` | entier4ns |
| 33 | `lpos` | octet |
| 34 | `code2` | texte(20) |
| 35 | `code3` | texte(10) |
| 36 | `des1` | texte(50) |
| 37 | `fam` | octet |
| 38 | `sfam` | entier4ns |
| 39 | `gamme` | entier2ns |
| 40 | `des2` | texte(50) |
| 41 | `des3` | texte(50) |
| 42 | `des4` | texte(50) |
| 43 | `labo` | octet |
| 44 | `modliv` | entier2ns |
| 45 | `nbjliv` | entier2ns |
| 46 | `num1` | texte(50) |
| 47 | `num2` | texte(50) |
| 48 | `qte` | reel8 |
| 49 | `pub` | numerique |
| 50 | `comrep` | reel4 |
| 51 | `catalog` | texte(15) |
| 52 | `amjr` | date |
| 53 | `roper` | entier2ns |
| 54 | `trem` | octet |
| 55 | `rem` | numerique |
| 56 | `cuv` | texte(5) |
| 57 | `batn` | octet |
| 58 | `refetude` | texte(50) |

### `lif_com`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `ref` sur ref - `lot` sur lot - `clef` sur numpiece, numligne, ref, lot, typt - `clefcorbeille` sur numpiece, numligne, ref, lot, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `ref` | texte(30) |
| 11 | `lot` | texte(10) |

### `lif_comis`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `ref` sur ref - `lot` sur lot - `clef` sur numpiece, numligne, ref, lot, typt - `clefcorbeille` sur numpiece, numligne, ref, lot, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `ref` | texte(30) |
| 11 | `lot` | texte(10) |

### `lif_ligne`

Lignes : 8 949 - colonnes logiques : 23 - physiques : 32 - total corbeille comprise : 21 225 - derniere activite (dtem) : 08/24/2026 14:45:04 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `ref` sur ref - `amje` sur amje - `amjl` sur amjl - `ligne` sur ligne - `lpos` sur lpos - `lot` sur lot - `operateur` sur operateur - `clef` sur numero, ligne, ref, lot - `clefcorbeille` sur numero, ligne, ref, lot, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `ref` | texte(30) |
| 7 | `com` | octet |
| 8 | `amje` | date |
| 9 | `amjl` | date |
| 10 | `ligne` | entier4ns |
| 11 | `lpos` | octet |
| 12 | `qte` | reel8 |
| 13 | `depot` | texte(10) |
| 14 | `lot` | texte(10) |
| 15 | `operateur` | entier2ns |
| 16 | `rang` | texte(50) |
| 17 | `note` | texte(50) |
| 18 | `note2` | texte(50) |
| 19 | `fac_no` | entier8ns |
| 20 | `fac_lg` | entier4ns |
| 21 | `daa` | texte(15) |
| 22 | `typnf` | octet |
| 23 | `comnf` | texte(50) |

Dernieres lignes (les 30 premieres colonnes sur 32 - tout est dans le JSON) :

| id | corbeille | dtem | salm | numero | ref | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | amje | amjl | ligne | lpos | qte | depot | lot | operateur | rang | note | note2 | fac_no | fac_lg | daa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 28414 | 0 | 08/24/2026 14:45:04 | 12 | 5979 | BL137434 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | 08/24/2026 00:00:00 | 7 | 0 | 1 |  |  | 12 |  |  |  | 0 | 0 |  |
| 28412 | 0 | 08/24/2026 14:45:02 | 12 | 5979 | BL137434 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | 08/24/2026 00:00:00 | 6 | 0 | 50000 |  |  | 12 |  |  |  | 0 | 0 |  |
| 28410 | 0 | 08/24/2026 14:44:57 | 12 | 5979 | BL137434 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | 08/24/2026 00:00:00 | 5 | 0 | 95500 |  |  | 12 |  |  |  | 0 | 0 |  |

### `liv_com`

Lignes : 1 774 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 3 572 - derniere activite (dtem) : 08/24/2026 15:12:44 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numero` sur numero - `clef` sur numero, numpiece, numligne, typt - `clefcorbeille` sur numero, numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `numero` | entier8ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm | numero |
|---|---|---|---|---|---|---|---|---|---|
| 3630 | 1 | 0 | 2 | Date de traçabilité : 17/02/2026. | 9932277 | 1 | 08/24/2026 15:12:44 | 12 | 9938773 |
| 3628 | 1 | 0 | 2 |  Traçabilité : S16/07/2026 | 9932270 | 1 | 08/07/2026 14:07:12 | 57 | 9938768 |
| 3626 | 1 | 0 | 2 | Traçabilité : S16/07/2026  Suite à une gâche trop importa... | 9932243 | 1 | 08/07/2026 12:04:05 | 57 | 9938766 |

### `liv_comis`

Lignes : 6 296 - colonnes logiques : 10 - physiques : 10 - total corbeille comprise : 12 593 - derniere activite (dtem) : 08/07/2026 14:07:12 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `numero` sur numero - `clef` sur numero, numpiece, numligne, typt - `clefcorbeille` sur numero, numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |
| 10 | `numero` | entier8ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm | numero |
|---|---|---|---|---|---|---|---|---|---|
| 12603 | 1 | 0 | 1 |  | 9932270 | 1 | 08/07/2026 14:07:12 | 57 | 9938768 |
| 12601 | 1 | 0 | 1 |  | 9932243 | 1 | 08/07/2026 12:04:05 | 57 | 9938766 |
| 12599 | 1 | 0 | 1 |  | 9932394 | 1 | 08/07/2026 11:06:31 | 57 | 9938760 |

### `liv_entete`

Lignes : 23 034 - colonnes logiques : 41 - physiques : 41 - total corbeille comprise : 46 651 - derniere activite (dtem) : 08/24/2026 16:10:50 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `operateur` sur operateur - `amje` sur amje - `numclt` sur numclt - `pos` sur pos - `lcp` sur lcp - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `operateur` | entier2ns |
| 9 | `amje` | date |
| 10 | `numclt` | entier4ns |
| 11 | `civ` | octet |
| 12 | `interlocuteur` | texte(50) |
| 13 | `tex` | texte(10) |
| 14 | `mail` | texte(128) |
| 15 | `numint` | entier4ns |
| 16 | `dest` | texte(1) |
| 17 | `intclt` | entier4ns |
| 18 | `pos` | octet |
| 19 | `lrs` | texte(50) |
| 20 | `ladr1` | texte(50) |
| 21 | `ladr2` | texte(50) |
| 22 | `lcp` | texte(10) |
| 23 | `lville` | texte(50) |
| 24 | `lpays` | texte(50) |
| 25 | `lcpays` | texte(5) |
| 26 | `emb` | texte(30) |
| 27 | `col` | entier4ns |
| 28 | `pal` | entier4ns |
| 29 | `pds` | reel4 |
| 30 | `nrec` | texte(30) |
| 31 | `numcde` | entier8ns |
| 32 | `femb` | numerique |
| 33 | `fport` | numerique |
| 34 | `facemb` | octet |
| 35 | `facport` | octet |
| 36 | `ctvaport` | texte(5) |
| 37 | `vtvaport` | numerique |
| 38 | `modliv` | entier2ns |
| 39 | `nbj` | entier4ns |
| 40 | `edi` | octet |
| 41 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 41 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | type | operateur | amje | numclt | civ | interlocuteur | tex | mail | numint | dest | intclt | pos | lrs | ladr1 | ladr2 | lcp | lville | lpays | lcpays | emb | col | pal | pds | nrec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50577 | 0 | 08/24/2026 16:10:50 | 12 |  | 9938775 | 1 | 12 | 08/25/2026 00:00:00 | 966 | 1 |  | STD |  | 0 | 1 | 966 | 0 | SOBOX - Quai = P 2 [ CHEZ SODEBO ] | 1 porte de la Guyonnière | La Guyonnière | 85600 | MONTAIGU-VENDEE | FRANCE | FR |  | 2 | 2 | 1360 |  |
| 50574 | 0 | 08/24/2026 15:52:58 | 12 |  | 9938774 | 1 | 12 | 08/25/2026 00:00:00 | 968 | 1 |  | STD |  | 0 | 1 | 968 | 0 | GOODWICH 1 - Quai G6 [CHEZ SODEBO] | 1 porte de la Guyonnière | La Guyonnière | 85600 | MONTAIGU-VENDEE | FRANCE | FR |  | 1 | 1 | 680 |  |
| 50572 | 0 | 08/24/2026 15:11:17 | 12 | +33 3 21 63 38 52 | 9938773 | 1 | 12 | 08/25/2026 00:00:00 | 601 | 1 |  | STD |  | 0 | 1 | 601 | 0 | ROQUETTE LESTREM | Rue de la Haute Loge - Quai 5-201 |  | 62136 | LESTREM | FRANCE | FR |  | 10 | 1 | 75 |  |

### `liv_ligne`

Lignes : 35 787 - colonnes logiques : 25 - physiques : 34 - total corbeille comprise : 77 930 - derniere activite (dtem) : 08/24/2026 16:09:29 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `amje` sur amje - `amjl` sur amjl - `lpos` sur lpos - `operateur` sur operateur - `lignecde` sur lignecde - `numcde` sur numcde - `clef` sur numero, numcde, lignecde - `clefcorbeille` sur numero, numcde, lignecde, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `amje` | date |
| 8 | `amjl` | date |
| 9 | `lpos` | octet |
| 10 | `qte` | reel8 |
| 11 | `depot` | texte(10) |
| 12 | `operateur` | entier2ns |
| 13 | `rang` | texte(50) |
| 14 | `note` | texte(50) |
| 15 | `note2` | texte(50) |
| 16 | `fac_no` | entier8ns |
| 17 | `lignecde` | entier4ns |
| 18 | `fac_lg` | entier4ns |
| 19 | `typnf` | octet |
| 20 | `comnf` | texte(50) |
| 21 | `numcde` | entier8ns |
| 22 | `pds` | reel4 |
| 23 | `qtefac` | reel8 |
| 24 | `num1` | texte(50) |
| 25 | `num2` | texte(50) |

Dernieres lignes (les 30 premieres colonnes sur 34 - tout est dans le JSON) :

| id | corbeille | dtem | salm | numero | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | amje | amjl | lpos | qte | depot | operateur | rang | note | note2 | fac_no | lignecde | fac_lg | typnf | comnf | numcde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 98088 | 0 | 08/24/2026 16:09:29 | 12 | 9938775 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 08/24/2026 00:00:00 | 08/27/2026 00:00:00 | 0 | 976800 |  | 12 |  |  |  | 0 | 1 | 0 | 0 |  | 9932281 |
| 98086 | 0 | 08/24/2026 15:51:36 | 12 | 9938774 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 08/24/2026 00:00:00 | 08/27/2026 00:00:00 | 0 | 488400 |  | 12 |  |  |  | 0 | 1 | 0 | 0 |  | 9932280 |
| 98083 | 0 | 08/24/2026 15:12:44 | 12 | 9938773 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 08/25/2026 00:00:00 | 08/27/2026 00:00:00 | 0 | 40000 |  | 12 |  |  |  | 0 | 1 | 0 | 0 |  | 9932277 |

### `mac_atps`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `amja` sur amja - `clef` sur type, code, amja - `clefcorbeille` sur type, code, amja, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `amja` | date |
| 9 | `tps` | reel4 |
| 10 | `hd` | heure |
| 11 | `hf` | heure |

### `mac_pro`

Lignes : 10 - colonnes logiques : 65 - physiques : 74 - total corbeille comprise : 43 - derniere activite (dtem) : 04/22/2026 14:13:13 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `tmac` sur tmac - `timp` sur timp - `gene` sur gene - `clef` sur type, code - `clefcorbeille` sur type, code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `mon` | entier8ns |
| 8 | `type` | entier2ns |
| 9 | `tmac` | octet |
| 10 | `timp` | octet |
| 11 | `gene` | octet |
| 12 | `nom` | texte(50) |
| 13 | `lai` | entier4ns |
| 14 | `nbcoul` | octet |
| 15 | `nbpap` | octet |
| 16 | `nbout` | octet |
| 17 | `tvit` | octet |
| 18 | `vit` | entier4ns |
| 19 | `etiq` | octet |
| 20 | `cond1` | octet |
| 21 | `carn` | octet |
| 22 | `cond2` | octet |
| 23 | `coup` | octet |
| 24 | `cond3` | octet |
| 25 | `plan` | octet |
| 26 | `cond4` | octet |
| 27 | `cart` | octet |
| 28 | `cond5` | octet |
| 29 | `pel` | octet |
| 30 | `dor` | octet |
| 31 | `ver` | octet |
| 32 | `bra` | octet |
| 33 | `ser` | octet |
| 34 | `gser` | octet |
| 35 | `num` | octet |
| 36 | `per` | octet |
| 37 | `gau` | octet |
| 38 | `emb` | octet |
| 39 | `livre` | octet |
| 40 | `cond6` | octet |
| 41 | `tht` | numerique |
| 42 | `thd` | numerique |
| 43 | `ths` | numerique |
| 44 | `cci` | numerique |
| 45 | `ccd` | numerique |
| 46 | `ccg` | numerique |
| 47 | `ce` | numerique |
| 48 | `pe` | reel4 |
| 49 | `cs` | numerique |
| 50 | `ps` | reel4 |
| 51 | `dev` | octet |
| 52 | `com` | octet |
| 53 | `tva` | entier8ns |
| 54 | `export` | entier8ns |
| 55 | `exo` | entier8ns |
| 56 | `cee` | entier8ns |
| 57 | `dom` | entier8ns |
| 58 | `fmcal` | entier2ns |
| 59 | `mmim` | entier4ns |
| 60 | `tbob` | entier2ns |
| 61 | `tbobm` | entier2ns |
| 62 | `fcal` | numerique |
| 63 | `cbs` | numerique |
| 64 | `pbs` | reel4 |
| 65 | `codemachcond` | texte(10) |

Dernieres lignes (les 30 premieres colonnes sur 74 - tout est dans le JSON) :

| id | code | bloq | corbeille | dtem | salm | mon | type | tmac | timp | gene | nom | lai | nbcoul | nbpap | nbout | tvit | vit | etiq | cond1 | carn | cond2 | coup | cond3 | plan | cond4 | cart | cond5 | pel | dor |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 36 | 7 | 1 | 0 | 04/22/2026 14:13:13 | 9998 | 4710000000 | 2 | 1 | 1 | 1 | COHESIO 2 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 34 | 6 | 1 | 0 | 04/22/2026 14:13:13 | 9998 | 4710000000 | 2 | 1 | 1 | 1 | COHESIO 2 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 32 | 5 | 1 | 0 | 04/22/2026 14:13:13 | 9998 | 4710000000 | 2 | 1 | 1 | 1 | Cohesio 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

### `mac_ptps`

Lignes : 8 - colonnes logiques : 28 - physiques : 98 - total corbeille comprise : 18 - derniere activite (dtem) : 01/21/2026 15:48:56 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `clef` sur type, code - `clefcorbeille` sur type, code, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `j1` | reel4 |
| 9 | `j1hd` | heure |
| 10 | `j1hf` | heure |
| 11 | `j2` | octet |
| 12 | `j3` | octet |
| 13 | `j4` | octet |
| 14 | `j5` | octet |
| 15 | `j6` | octet |
| 16 | `j7` | octet |
| 17 | `j2hd` | heure |
| 18 | `j3hd` | heure |
| 19 | `j4hd` | heure |
| 20 | `j5hd` | heure |
| 21 | `j6hd` | heure |
| 22 | `j7hd` | heure |
| 23 | `j2hf` | heure |
| 24 | `j3hf` | heure |
| 25 | `j4hf` | heure |
| 26 | `j5hf` | heure |
| 27 | `j6hf` | heure |
| 28 | `j7hf` | heure |

Dernieres lignes (les 30 premieres colonnes sur 98 - tout est dans le JSON) :

| id | code | bloq | corbeille | dtem | salm | type | j1 | j1hd | j1hd_2 | j1hd_3 | j1hd_4 | j1hd_5 | j1hd_6 | j1hf | j1hf_2 | j1hf_3 | j1hf_4 | j1hf_5 | j1hf_6 | j2 | j3 | j4 | j5 | j6 | j7 | j2hd | j2hd_2 | j2hd_3 | j2hd_4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 19 | 7 | 0 | 0 | 01/21/2026 15:48:56 | 9998 | 2 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 17 | 6 | 0 | 0 | 01/21/2026 15:48:45 | 9998 | 2 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 15 | 5 | 0 | 0 | 01/21/2026 14:15:43 | 9998 | 2 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |

### `mac_tra`

Lignes : 16 - colonnes logiques : 25 - physiques : 135 - total corbeille comprise : 74 - derniere activite (dtem) : 01/21/2026 16:04:57 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code` sur code - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `tra` sur tra - `ligne` sur ligne - `clefcorbeille` sur type, code, tra, ligne, corbeille (unique) - `clef` sur type, code, tra, ligne

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | texte(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `nom` | texte(50) |
| 9 | `tra` | entier4ns |
| 10 | `ligne` | entier4ns |
| 11 | `typl` | entier2ns |
| 12 | `mfab` | octet |
| 13 | `noml` | texte(50) |
| 14 | `ttps` | texte(120) |
| 15 | `tps` | reel4 |
| 16 | `tgac` | texte(120) |
| 17 | `pgac` | octet |
| 18 | `gac` | reel4 |
| 19 | `tthc` | texte(120) |
| 20 | `pthc` | octet |
| 21 | `thc` | reel4 |
| 22 | `pvit` | octet |
| 23 | `vit` | reel4 |
| 24 | `point` | entier2ns |
| 25 | `tgcv` | octet |

Dernieres lignes (les 30 premieres colonnes sur 135 - tout est dans le JSON) :

| id | code | bloq | corbeille | dtem | salm | type | nom | tra | ligne | typl | mfab | noml | ttps | ttps_2 | ttps_3 | ttps_4 | ttps_5 | ttps_6 | ttps_7 | ttps_8 | ttps_9 | ttps_10 | ttps_11 | ttps_12 | tps | tps_2 | tps_3 | tps_4 | tps_5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 209 | 2 | 1 | 0 | 01/21/2026 16:04:57 | 9998 | 1 | Classique | 1 | 0 | 1 | 1 | Fabrication | S | S | S | S | S | S | S | S | S | S | S |  | 0 | 0 | 0 | 0 | 0 |
| 180 | 6 | 1 | 0 | 01/09/2026 15:56:40 | 9998 | 1 |  | 11 | 1 | 1 | 2 | Calage | F | F | F | F | F | F | S | S | S | S | S | S | 0.5 | 0.75 | 1 | 1.25 | 1.5 |
| 178 | 6 | 1 | 0 | 01/09/2026 15:57:07 | 9998 | 1 | Sauvegarde Classique | 11 | 0 | 1 | 1 | Fabrication |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 |

### `mat_fmat`

Lignes : 25 - colonnes logiques : 21 - physiques : 21 - total corbeille comprise : 57 - derniere activite (dtem) : 07/02/2026 13:00:06 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `fam` sur fam - `bloq` sur bloq - `corbeille` sur corbeille - `sfam` sur sfam - `clef` sur fam, sfam - `clefcorbeille` sur fam, sfam, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `tva` | entier8ns |
| 8 | `exp` | entier8ns |
| 9 | `cee` | entier8ns |
| 10 | `exo` | entier8ns |
| 11 | `sfam` | entier4ns |
| 12 | `libfam` | texte(50) |
| 13 | `atva` | entier8ns |
| 14 | `aimp` | entier8ns |
| 15 | `aexo` | entier8ns |
| 16 | `acee` | entier8ns |
| 17 | `adom` | entier8ns |
| 18 | `amon` | entier8ns |
| 19 | `dom` | entier8ns |
| 20 | `mon` | entier8ns |
| 21 | `libsfam` | texte(50) |

Dernieres lignes :

| id | fam | bloq | corbeille | dtem | salm | tva | exp | cee | exo | sfam | libfam | atva | aimp | aexo | acee | adom | amon | dom | mon | libsfam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 224 | 19 | 1 | 0 | 07/02/2026 13:00:06 | 905 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Pièce Cohésio |
| 218 | 18 | 1 | 0 | 09/25/2022 15:47:03 | 9999 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 6021200000 | 4710000000 | 4710000000 | 6021120000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Palette |
| 216 | 17 | 1 | 0 | 09/25/2022 15:46:40 | 9999 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 6021200000 | 4710000000 | 4710000000 | 6021120000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Carton |

### `mat_mat`

Lignes : 1 536 - colonnes logiques : 76 - physiques : 483 - total corbeille comprise : 7 521 - derniere activite (dtem) : 08/07/2026 10:23:28 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `stk` sur stk - `sfam` sur sfam - `libc1` sur libc1 - `nomen` sur nomen - `amj` sur amj - `clef` sur type, code1, code2, code3 - `clefcorbeille` sur type, code1, code2, code3, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier4ns |
| 10 | `stk` | octet |
| 11 | `sfam` | entier4ns |
| 12 | `libc1` | texte(50) |
| 13 | `nomen` | octet |
| 14 | `amjf` | date |
| 15 | `libc2` | texte(50) |
| 16 | `coul` | texte(20) |
| 17 | `pds` | reel4 |
| 18 | `ctva` | texte(5) |
| 19 | `pcpv` | reel4 |
| 20 | `remp1` | texte(5) |
| 21 | `remp2` | texte(20) |
| 22 | `remp3` | texte(10) |
| 23 | `com` | octet |
| 24 | `cua` | texte(50) |
| 25 | `cuc` | texte(50) |
| 26 | `depot` | texte(10) |
| 27 | `rang` | texte(50) |
| 28 | `mini` | reel8 |
| 29 | `maxi` | reel8 |
| 30 | `libt1` | texte(500) |
| 31 | `pa` | numerique |
| 32 | `libt2` | texte(500) |
| 33 | `m1_lai` | entier2ns |
| 34 | `m1_syn` | octet |
| 35 | `m1_abs` | reel4 |
| 36 | `m1_film` | octet |
| 37 | `m1_epais` | reel4 |
| 38 | `m1_adh` | texte(250) |
| 39 | `m1_pro` | texte(250) |
| 40 | `m1_geslaize` | octet |
| 41 | `numfou` | entier4ns |
| 42 | `ref` | texte(300) |
| 43 | `bar` | texte(300) |
| 44 | `amjv` | date |
| 45 | `qtemin1` | reel8 |
| 46 | `qtemax1` | reel8 |
| 47 | `pafou1` | numerique |
| 48 | `amj` | horodatage |
| 49 | `qtemin2` | reel8 |
| 50 | `qtemax2` | reel8 |
| 51 | `pafou2` | numerique |
| 52 | `qtemin3` | reel8 |
| 53 | `qtemax3` | reel8 |
| 54 | `pafou3` | numerique |
| 55 | `qtemin4` | reel8 |
| 56 | `qtemax4` | reel8 |
| 57 | `pafou4` | numerique |
| 58 | `qtemin5` | reel8 |
| 59 | `qtemax5` | reel8 |
| 60 | `pafou5` | numerique |
| 61 | `qtemin6` | reel8 |
| 62 | `qtemax6` | reel8 |
| 63 | `pafou6` | numerique |
| 64 | `qtemin7` | reel8 |
| 65 | `qtemax7` | reel8 |
| 66 | `pafou7` | numerique |
| 67 | `qtemin8` | reel8 |
| 68 | `qtemax8` | reel8 |
| 69 | `pafou8` | numerique |
| 70 | `qtemin9` | reel8 |
| 71 | `qtemax9` | reel8 |
| 72 | `pafou9` | numerique |
| 73 | `qtemin10` | reel8 |
| 74 | `qtemax10` | reel8 |
| 75 | `pafou10` | numerique |
| 76 | `gener` | octet |

Dernieres lignes (les 30 premieres colonnes sur 483 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | stk | sfam | libc1 | nomen | amjf | amjf_2 | amjf_3 | amjf_4 | amjf_5 | amjf_6 | amjf_7 | amjf_8 | amjf_9 | amjf_10 | libc2 | coul | pds | ctva | pcpv | remp1 | remp2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8804 | 1 | 0 | 08/07/2026 10:23:28 | 7 | 629 | 0015 |  | 1 | 2 | 1 | Thermique Eco Adhésif Enlevable | 1 | 08/07/2026 00:00:00 |  |  |  |  |  |  |  |  |  | Bobine de 4.000 ml | Blanc | 144 | 1 | 0 |  |  |
| 8790 | 1 | 0 | 08/03/2026 10:24:24 | 901 | 897 | 0287 |  | 9 | 2 | 4 | Ronds 40 mm pour produit 1041/0004, 1 coul., rouge | 1 | 02/28/2022 00:00:00 |  |  |  |  |  |  |  |  |  | 8 modèles | P.485C | 0 | 1 | 0 |  |  |
| 8786 | 1 | 0 | 07/20/2026 12:46:18 | 901 | 897 | 0286 |  | 9 | 2 | 4 | Cliché 59 x 50 mm, 2 couleurs, P.185 (2/2) | 1 | 05/04/2022 00:00:00 |  |  |  |  |  |  |  |  |  | Pour produit 748/0016 et 0017 | P. 185 | 0 | 1 | 0 |  |  |

### `mat_matcom`

Lignes : 36 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 79 - derniere activite (dtem) : 05/28/2026 13:02:52 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | texte(5) |
| 6 | `code2` | texte(20) |
| 7 | `code3` | texte(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | texte(50) |
| 11 | `com` | texte(750) |

Dernieres lignes :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 80 | 1 | 0 | 05/28/2026 13:02:52 | 107 | 0010 |  | 1 | 1 | 7 | Attention, la laize mère de ce complexe est de 1 500 mm.  |
| 77 | 1 | 0 | 03/27/2026 12:39:44 | 548 | 0194 |  | 9 | 1 | 901 | Impréssion contour de 7 mm au bord de l'étiquette. |
| 75 | 1 | 0 | 04/16/2026 12:41:08 | 1152 | 0001 |  | 2 | 1 | 7 | Lors du passage d'une commande, il faut ajouter une ligne... |

### `mat_matcomif`

Lignes : 1 682 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 6 089 - derniere activite (dtem) : 08/07/2026 10:23:28 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | texte(5) |
| 6 | `code2` | texte(20) |
| 7 | `code3` | texte(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | texte(50) |
| 11 | `com` | texte(750) |

Dernieres lignes :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 6355 | 1 | 0 | 08/07/2026 10:23:28 |  | 10930 |  | 0 | 9 | 7 | Enlevable~Gil. Sili. Jaune~~ |
| 6341 | 1 | 0 | 08/03/2026 10:24:24 |  | 10909 |  | 0 | 9 | 901 | ~~~ |
| 6337 | 1 | 0 | 07/20/2026 12:46:18 |  | 10897 |  | 0 | 9 | 901 | ~~~ |

### `mat_matcomir`

Lignes : 0 - colonnes logiques : 11 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | texte(5) |
| 6 | `code2` | texte(20) |
| 7 | `code3` | texte(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | texte(50) |
| 11 | `com` | texte(750) |

### `mat_matcomis`

Lignes : 8 - colonnes logiques : 11 - physiques : 11 - total corbeille comprise : 18 - derniere activite (dtem) : 05/19/2026 11:46:47 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `typt` sur typt - `clef` sur type, code1, code2, code3, typt - `clefcorbeille` sur type, code1, code2, code3, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | texte(5) |
| 6 | `code2` | texte(20) |
| 7 | `code3` | texte(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | texte(50) |
| 11 | `com` | texte(750) |

Dernieres lignes :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 16 | 1 | 0 | 05/19/2026 11:46:47 | 1062 | 0017 |  | 17 | 1 | 7 |  |
| 14 | 1 | 0 | 12/24/2025 09:27:34 | 1162 | 0016 |  | 17 | 1 | 9998 | mit dans la  première allé du batiment 2 |
| 12 | 1 | 0 | 12/24/2025 09:20:39 | 1162 | 0008 |  | 17 | 1 | 9998 | une partie dans l allée B et dans le batimment 2 |

### `mat_nomen`

Lignes : 132 - colonnes logiques : 37 - physiques : 46 - total corbeille comprise : 482 - derniere activite (dtem) : 03/31/2026 11:09:20 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `amj` sur amj - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `htn` sur htn - `des1` sur des1 - `lignenomen` sur lignenomen - `lpos` sur lpos - `rtype` sur rtype - `rcod1` sur rcod1 - `rcod2` sur rcod2 - `rcod3` sur rcod3 - `clef` sur type, code1, code2, code3, lignenomen - `clefcorbeille` sur type, code1, code2, code3, lignenomen, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | texte(5) |
| 7 | `code2` | texte(20) |
| 8 | `code3` | texte(10) |
| 9 | `type` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `fam` | entier4ns |
| 12 | `sfam` | entier4ns |
| 13 | `gamme` | entier2ns |
| 14 | `cuv` | texte(5) |
| 15 | `depot` | texte(10) |
| 16 | `qte` | reel8 |
| 17 | `htn` | numerique |
| 18 | `pa` | numerique |
| 19 | `pub` | numerique |
| 20 | `pun` | numerique |
| 21 | `suv` | octet |
| 22 | `vuv` | numerique |
| 23 | `net` | octet |
| 24 | `trem` | octet |
| 25 | `rem` | numerique |
| 26 | `des1` | texte(50) |
| 27 | `lignenomen` | entier4ns |
| 28 | `des2` | texte(50) |
| 29 | `des3` | texte(50) |
| 30 | `des4` | texte(50) |
| 31 | `htb` | numerique |
| 32 | `com` | octet |
| 33 | `lpos` | octet |
| 34 | `rtype` | octet |
| 35 | `rcod1` | texte(5) |
| 36 | `rcod2` | texte(20) |
| 37 | `rcod3` | texte(10) |

Dernieres lignes (les 30 premieres colonnes sur 46 - tout est dans le JSON) :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | amj | fam | sfam | gamme | cuv | depot | qte | htn | pa | pub | pun | suv | vuv | net | trem | rem | des1 | lignenomen | des2 | des3 | des4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 875 | 1 | 0 | 03/31/2026 11:09:12 | 9998 | 886 | 0315 |  | 1 | 11/30/1999 00:00:00 | 0 | 1 | 0 | 10 | 0,1000 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1.00000 | 0 | 1 | 0.000000 | Jaune 60g | 3 |  |  |  |
| 873 | 1 | 0 | 03/31/2026 11:09:20 | 9998 | 886 | 0315 |  | 1 | 11/30/1999 00:00:00 | 0 | 5 | 0 | KG |  | 30 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 | 1.00000 | 0 | 2 | 0.000000 | Congélation | 2 |  |  |  |
| 871 | 1 | 0 | 03/31/2026 11:09:11 | 9998 | 886 | 0315 |  | 1 | 11/30/1999 00:00:00 | 0 | 1 | 0 | 10 |  | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1.00000 | 0 | 1 | 0.000000 | Velin Mat 62g | 1 |  |  |  |

### `out_cyl`

Lignes : 124 - colonnes logiques : 26 - physiques : 98 - total corbeille comprise : 335 - derniere activite (dtem) : 12/11/2025 15:47:15 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `type` sur type - `nbd` sur nbd - `cle2` sur cle2 - `bloq` sur bloq - `corbeille` sur corbeille - `mach` sur mach - `clef` sur type, nbd, cle2, mach - `clefcorbeille` sur type, nbd, cle2, mach, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `type` | octet |
| 3 | `nbd` | entier4ns |
| 4 | `cle2` | octet |
| 5 | `bloq` | octet |
| 6 | `corbeille` | reel4 |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |
| 9 | `mach` | texte(10) |
| 10 | `dmax` | reel8 |
| 11 | `dor` | octet |
| 12 | `ser` | octet |
| 13 | `com` | texte(750) |
| 14 | `qte` | entier4ns |
| 15 | `tmac` | octet |
| 16 | `machine` | texte(250) |
| 17 | `qteflasque` | entier4ns |
| 18 | `code` | texte(10) |
| 19 | `numfou` | entier4ns |
| 20 | `creux` | entier2 |
| 21 | `creuxp` | entier2 |
| 22 | `creuxo` | entier2 |
| 23 | `coeana` | reel8 |
| 24 | `gmac` | octet |
| 25 | `hautp` | entier4ns |
| 26 | `Perftl` | reel8 |

Dernieres lignes (les 30 premieres colonnes sur 98 - tout est dans le JSON) :

| id | type | nbd | cle2 | bloq | corbeille | dtem | salm | mach | dmax | dor | ser | com | qte | tmac | tmac_2 | tmac_3 | tmac_4 | tmac_5 | tmac_6 | tmac_7 | tmac_8 | tmac_9 | tmac_10 | tmac_11 | tmac_12 | tmac_13 | tmac_14 | tmac_15 | tmac_16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 350 | 7 | 164 | 1 | 1 | 0 | 03/12/2024 15:19:18 | 7 | 2 | 520.7 | 0 | 0 |  | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 348 | 2 | 140 | 0 | 1 | 0 | 12/06/2023 12:35:07 | 7 | 2 | 444.5 | 0 | 0 |  | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 346 | 5 | 8 | 0 | 1 | 0 | 10/05/2022 12:30:44 | 7 | 2 | 0 | 0 | 0 | Attention, nous disposons d'un seul anilox 800 lignes pou... | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

### `out_dec`

Lignes : 2 643 - colonnes logiques : 59 - physiques : 116 - total corbeille comprise : 9 072 - derniere activite (dtem) : 08/05/2026 15:11:24 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `type` sur type - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `code` sur code - `operateur` sur operateur - `etat` sur etat - `nbd` sur nbd - `dev` sur dev - `ray` sur ray - `ftl` sur ftl - `fta` sur fta - `nbl` sur nbl - `nba` sur nba - `nbt` sur nbt - `lt` sur lt - `at` sur at - `ft` sur ft - `mat` sur mat - `met` sur met - `qm` sur qm - `fr` sur fr - `per` sur per - `stk` sur stk - `numclt` sur numclt - `forme` sur forme - `amj` sur amj - `clef` sur type, numero - `clefcorbeille` sur type, numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `type` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `numero` | entier4ns |
| 8 | `code` | texte(10) |
| 9 | `operateur` | entier2ns |
| 10 | `etat` | octet |
| 11 | `machine` | texte(250) |
| 12 | `tmac` | octet |
| 13 | `nbd` | entier4ns |
| 14 | `dev` | octet |
| 15 | `ray` | reel4 |
| 16 | `ftl` | reel8 |
| 17 | `fta` | reel8 |
| 18 | `nbl` | entier4ns |
| 19 | `nba` | entier4ns |
| 20 | `nbt` | entier4ns |
| 21 | `lt` | reel8 |
| 22 | `at` | reel8 |
| 23 | `ft` | reel8 |
| 24 | `mat` | octet |
| 25 | `met` | octet |
| 26 | `qm` | entier4ns |
| 27 | `fr` | octet |
| 28 | `per` | octet |
| 29 | `stk` | octet |
| 30 | `numclt` | entier4ns |
| 31 | `espl` | reel4 |
| 32 | `espa` | reel4 |
| 33 | `eche` | reel8 |
| 34 | `pac` | entier4ns |
| 35 | `di` | reel8 |
| 36 | `nbrl` | entier4ns |
| 37 | `nbra` | entier4ns |
| 38 | `frt` | reel8 |
| 39 | `nbpc` | entier4ns |
| 40 | `lpc` | reel8 |
| 41 | `ppc` | texte(5) |
| 42 | `typs` | octet |
| 43 | `eps` | entier4ns |
| 44 | `hcou1` | texte(15) |
| 45 | `hcou2` | texte(15) |
| 46 | `nbd2` | entier4ns |
| 47 | `nbcal` | entier4ns |
| 48 | `nbeti` | entier4ns |
| 49 | `cua` | texte(5) |
| 50 | `ctva` | texte(5) |
| 51 | `com` | octet |
| 52 | `rclt` | texte(20) |
| 53 | `depot` | texte(10) |
| 54 | `rang` | texte(50) |
| 55 | `pstk` | numerique |
| 56 | `forme` | octet |
| 57 | `espg` | reel4 |
| 58 | `guizmo` | octet |
| 59 | `amj` | horodatage |

Dernieres lignes (les 30 premieres colonnes sur 116 - tout est dans le JSON) :

| id | type | bloq | corbeille | dtem | salm | numero | code | operateur | etat | machine | machine_2 | machine_3 | machine_4 | machine_5 | machine_6 | machine_7 | machine_8 | machine_9 | machine_10 | machine_11 | machine_12 | machine_13 | machine_14 | machine_15 | machine_16 | machine_17 | machine_18 | machine_19 | machine_20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9114 | 2 | 1 | 0 | 07/30/2026 15:55:50 | 905 | 2872 |  | 905 | 1 | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 9105 | 2 | 1 | 0 | 07/28/2026 18:16:41 | 7 | 2871 |  | 7 | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 9099 | 2 | 1 | 0 | 07/31/2026 12:18:10 | 905 | 2870 |  | 901 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### `out_deca`

Lignes : 2 248 - colonnes logiques : 13 - physiques : 13 - total corbeille comprise : 2 248 - derniere activite (dtem) : 08/05/2026 15:01:11 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `type` sur type - `bloq` sur bloq - `corbeille` sur corbeille - `numero` sur numero - `numfou` sur numfou - `def` sur def - `ref` sur ref - `clef` sur type, numero, numfou - `clefcorbeille` sur type, numero, numfou, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `type` | octet |
| 3 | `bloq` | octet |
| 4 | `corbeille` | reel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `numero` | entier4ns |
| 8 | `numfou` | entier4ns |
| 9 | `def` | octet |
| 10 | `ref` | texte(30) |
| 11 | `amj` | date |
| 12 | `cua` | texte(5) |
| 13 | `pa` | numerique |

Dernieres lignes :

| id | type | bloq | corbeille | dtem | salm | numero | numfou | def | ref | amj | cua | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4050 | 2 | 0 | 0 | 07/30/2026 15:52:49 | 905 | 2872 | 0 | 0 |  |  | U | 0.000000 |
| 4049 | 2 | 0 | 0 | 07/28/2026 18:16:41 | 7 | 2871 | 0 | 0 |  |  | U | 0.000000 |
| 4048 | 2 | 0 | 0 | 07/24/2026 15:32:30 | 901 | 2870 | 0 | 0 |  |  | U | 0.000000 |

### `out_deccom`

Lignes : 1 496 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 3 225 - derniere activite (dtem) : 07/28/2026 18:16:41 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `typt` sur typt - `numero` sur numero - `clef` sur type, numero, typt - `clefcorbeille` sur type, numero, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `type` | octet |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |
| 9 | `numero` | entier4ns |

Dernieres lignes :

| id | bloq | corbeille | type | typt | com | dtem | salm | numero |
|---|---|---|---|---|---|---|---|---|
| 3230 | 1 | 0 | 2 | 1 | Anicenne plaque 2692 coupée de 8 en 5 de front.  | 07/28/2026 18:16:41 | 7 | 2871 |
| 3228 | 1 | 0 | 4 | 1 | Découpe de sécurité. Voir BAT (953/0010).  | 07/23/2026 09:36:19 | 905 | 2869 |
| 3226 | 1 | 0 | 4 | 1 | Plaque spéciale. Uniquement 1 filet de découpe vertical a... | 07/22/2026 11:52:28 | 7 | 1419 |

### `out_deccomif`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `typt` sur typt - `numero` sur numero - `clef` sur type, numero, typt - `clefcorbeille` sur type, numero, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `type` | octet |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |
| 9 | `numero` | entier4ns |

### `out_deccomir`

Lignes : 2 649 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 8 111 - derniere activite (dtem) : 08/05/2026 15:01:11 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `typt` sur typt - `numero` sur numero - `clef` sur type, numero, typt - `clefcorbeille` sur type, numero, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `type` | octet |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |
| 9 | `numero` | entier4ns |

Dernieres lignes :

| id | bloq | corbeille | type | typt | com | dtem | salm | numero |
|---|---|---|---|---|---|---|---|---|
| 8144 | 1 | 0 | 2 | 9 | 2837~0~0~1~0~6~0~0~0~0~1~0~0~0~0~1~0~0~1~0~0~1~0~0~1~0~0~... | 07/30/2026 15:52:49 | 905 | 2872 |
| 8136 | 1 | 0 | 2 | 9 | 0~0~0~1~0~1~0~0~0~80~1~0~0~0~0~1~0~0~1~0~0~1~0~0~1~0~0~1~... | 07/28/2026 18:16:41 | 7 | 2871 |
| 8133 | 1 | 0 | 2 | 9 | 0~0~0~1~0~6~0~0~0~0~1~0~0~0~0~1~0~0~1~0~0~1~0~0~1~0~0~1~0... | 07/24/2026 15:32:30 | 901 | 2870 |

### `out_deccomis`

Lignes : 1 974 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 4 155 - derniere activite (dtem) : 07/20/2026 12:56:14 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `type` sur type - `typt` sur typt - `numero` sur numero - `clef` sur type, numero, typt - `clefcorbeille` sur type, numero, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `type` | octet |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |
| 9 | `numero` | entier4ns |

Dernieres lignes :

| id | bloq | corbeille | type | typt | com | dtem | salm | numero |
|---|---|---|---|---|---|---|---|---|
| 4157 | 1 | 0 | 2 | 1 | Adhésif: Oui N° Magnétique: 192-P | 07/16/2026 14:35:51 | 905 | 2863 |
| 4146 | 2 | 0 | 2 | 1 | Adhésif : Avec N° Magnétique : 96/1 | 04/02/2026 14:19:50 | 905 | 1413 |
| 4143 | 1 | 0 | 2 | 1 | Adhésif : Avec N° Magnétique : 160-P | 03/27/2026 15:55:51 | 901 | 2836 |

### `pal_p1a`

Lignes : 0 - colonnes logiques : 10 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `ligneof` sur ligneof - `colis` sur colis - `numcde` sur numcde - `lignecde` sur lignecde - `numof` sur numof - `clef` sur numcde, lignecde, colis, numero, numof, ligneof - `clefcorbeille` sur numcde, lignecde, colis, numero, numof, ligneof, corbeille

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `salm` | entier2ns |
| 4 | `dtem` | horodatage |
| 5 | `numero` | entier8ns |
| 6 | `ligneof` | entier4ns |
| 7 | `colis` | entier4ns |
| 8 | `numcde` | entier8ns |
| 9 | `lignecde` | entier4ns |
| 10 | `numof` | entier8ns |

### `pro_pro`

Lignes : 5 - colonnes logiques : 43 - physiques : 52 - total corbeille comprise : 10 - derniere activite (dtem) : 11/18/2021 10:47:14 - extrait : TOP n + ORDER BY id DESC

Cles : `numero` sur numero - `amj` sur amj - `operateur` sur operateur - `code` sur code - `rs` sur rs - `tel` sur tel - `fax` sur fax - `numrep` sur numrep - `mail` sur mail - `cp` sur cp - `vil` sur vil - `cpays` sur cpays - `groupe` sur groupe - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `bloq` sur bloq - `id` sur id (primaire) - `pays` sur pays - `corbeille` sur corbeille - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `numero` | entier4ns |
| 2 | `amj` | horodatage |
| 3 | `operateur` | entier2ns |
| 4 | `code` | texte(30) |
| 5 | `rs` | texte(50) |
| 6 | `tel` | texte(20) |
| 7 | `fax` | texte(20) |
| 8 | `numrep` | entier2ns |
| 9 | `mail` | texte(128) |
| 10 | `cp` | texte(10) |
| 11 | `vil` | texte(50) |
| 12 | `cpays` | texte(5) |
| 13 | `groupe` | entier4ns |
| 14 | `cat1` | entier2ns |
| 15 | `cat2` | entier2ns |
| 16 | `cat3` | entier2ns |
| 17 | `bloq` | octet |
| 18 | `dtem` | horodatage |
| 19 | `salm` | entier2ns |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `bp` | texte(10) |
| 23 | `siret` | texte(30) |
| 24 | `ntva` | texte(30) |
| 25 | `rcs` | texte(30) |
| 26 | `ean` | texte(30) |
| 27 | `http` | texte(50) |
| 28 | `ftp` | texte(50) |
| 29 | `ftpmdp` | texte(20) |
| 30 | `inftp` | texte(50) |
| 31 | `inftpmdp` | texte(20) |
| 32 | `inftpok` | octet |
| 33 | `nbdev` | octet |
| 34 | `lang` | texte(1) |
| 35 | `dev` | texte(5) |
| 36 | `com` | octet |
| 37 | `texd` | octet |
| 38 | `adv` | entier2ns |
| 39 | `id` | entier8 |
| 40 | `pays` | texte(50) |
| 41 | `corbeille` | reel4 |
| 42 | `expdev` | octet |
| 43 | `nif` | texte(30) |

Dernieres lignes (les 30 premieres colonnes sur 52 - tout est dans le JSON) :

| numero | amj | operateur | code | rs | tel | fax | numrep | mail | cp | vil | cpays | groupe | cat1 | cat2 | cat3 | bloq | dtem | salm | adr1 | adr2 | bp | siret | ntva | rcs | ean | http | ftp | ftpmdp | inftp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 11/18/2021 10:47:14 | 0 | POLLET | ETSPOLLET | 03 28 41 89 91 | 03 28 40 06 36  | 1 |  | 59190 | MORBECQUE | FR | 5 | 0 | 0 | 0 | 1 | 11/18/2021 10:47:14 | 53 | 4, Route Nationale | Le Hasard |  | 477513154 | FR18477513154 |  |  |  |  |  | nIJ88YST63 |
| 4 | 09/27/2021 17:23:52 | 0 | THIIRIET | THIRIET  |  |  | 51 |  | 10430 | ROSIERES | FR | 4 | 0 | 0 | 0 | 1 | 09/27/2021 17:23:52 | 54 | 35, avenue Gabriel Deheurles  |  |  |  |  |  |  |  |  |  | FzM44Zak23 |
| 3 | 09/07/2021 12:16:15 | 0 | LAUWERS | Lauwers Emballages | 03 27 48 30 00 | 03 27 48 30 09 | 1 |  | 59178 | HASNON | FR | 3 | 0 | 0 | 0 | 1 | 09/07/2021 12:16:15 | 53 | 5, Rue Olivier Deguise |  |  | 30814779200011 |  |  |  |  |  |  | sIF02Yde55 |

### `pro_procom`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numpro` sur numpro - `typt` sur typt - `clef` sur numpro, typt - `clefcorbeille` sur numpro, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `numpro` | entier4ns |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `pro_procomif`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numpro` sur numpro - `typt` sur typt - `clef` sur numpro, typt - `clefcorbeille` sur numpro, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `numpro` | entier4ns |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `pro_procomil`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numpro` sur numpro - `typt` sur typt - `clef` sur numpro, typt - `clefcorbeille` sur numpro, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `numpro` | entier4ns |
| 5 | `typt` | octet |
| 6 | `com` | texte(750) |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `pro_procomis`

Lignes : 0 - colonnes logiques : 8 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpro` sur numpro - `clef` sur numpro, typt - `clefcorbeille` sur numpro, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpro` | entier4ns |
| 7 | `dtem` | horodatage |
| 8 | `salm` | entier2ns |

### `pro_proi`

Lignes : 4 - colonnes logiques : 17 - physiques : 17 - total corbeille comprise : 8 - derniere activite (dtem) : 11/18/2021 10:48:12 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `numpro` sur numpro - `numint` sur numint - `def` sur def - `clef` sur numpro, numint - `clefcorbeille` sur numpro, numint, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `service` | octet |
| 5 | `numpro` | entier4ns |
| 6 | `civ` | octet |
| 7 | `nom` | texte(30) |
| 8 | `pre` | texte(30) |
| 9 | `dtem` | horodatage |
| 10 | `salm` | entier2ns |
| 11 | `numint` | entier4ns |
| 12 | `tel` | texte(20) |
| 13 | `gsm` | texte(20) |
| 14 | `fax` | texte(20) |
| 15 | `mail` | texte(128) |
| 16 | `def` | octet |
| 17 | `maildev` | octet |

Dernieres lignes :

| id | bloq | corbeille | service | numpro | civ | nom | pre | dtem | salm | numint | tel | gsm | fax | mail | def | maildev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 7 | 1 | 0 | 2 | 5 | 3 | DELPORTE | Elodie | 11/18/2021 10:48:12 | 53 | 1 | 03 28 41 89 91 |  |  |  | 0 | 1 |
| 5 | 1 | 0 | 6 | 4 | 2 | Cuvilliez  | Florian | 09/27/2021 17:26:12 | 54 | 1 | 03 25 75 88 76 | 06 89 11 01 29 |  | f.cuvilliez@thiriet.com | 0 | 1 |
| 3 | 1 | 0 | 1 | 3 | 2 | Béra | Antoine | 09/07/2021 12:17:42 | 53 | 1 | 03 27 48 30 00 |  | 03 27 48 30 09 | antoine.bera@lauwers.emb.com | 0 | 1 |

### `stk_hist`

Lignes : 25 588 - colonnes logiques : 21 - physiques : 21 - derniere activite (dtem) : 08/24/2026 16:09:30 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `numfouclt` sur numfouclt - `amjh` sur amjh - `operateur` sur operateur - `mvt` sur mvt - `depot` sur depot - `rang` sur rang - `numcde` sur numcde - `ligne` sur ligne - `refbl` sur refbl - `clef` sur type, code1, code2, code3, amjh (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier2ns |
| 8 | `numfouclt` | entier4ns |
| 9 | `amjh` | horodatage |
| 10 | `operateur` | entier2ns |
| 11 | `mvt` | octet |
| 12 | `depot` | texte(10) |
| 13 | `rang` | texte(50) |
| 14 | `numcde` | entier8ns |
| 15 | `ligne` | entier4ns |
| 16 | `qte1` | reel8 |
| 17 | `qte2` | reel8 |
| 18 | `des1` | texte(50) |
| 19 | `des2` | texte(50) |
| 20 | `lot` | texte(10) |
| 21 | `refbl` | texte(30) |

Dernieres lignes :

| id | dtem | salm | code1 | code2 | code3 | type | numfouclt | amjh | operateur | mvt | depot | rang | numcde | ligne | qte1 | qte2 | des1 | des2 | lot | refbl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 38003 | 08/24/2026 16:09:30 | 12 | 965 | 0001 |  | 1 | 966 | 08/24/2026 16:09:30 | 12 | 5 |  |  | 9932281 | 1 | 976800 | -1428400 | Livraison du 24/08/2026 |  |  | 9938775 |
| 38002 | 08/24/2026 15:51:37 | 12 | 965 | 0001 |  | 1 | 968 | 08/24/2026 15:51:37 | 12 | 5 |  |  | 9932280 | 1 | 488400 | -451600 | Livraison du 24/08/2026 |  |  | 9938774 |
| 38001 | 08/24/2026 15:08:32 | 12 | 601 | 0018 |  | 1 | 601 | 08/24/2026 15:08:32 | 12 | 5 |  |  | 9932277 | 1 | 40000 | 160000 | Livraison du 25/08/2026 |  |  | 9938773 |

### `stm_hist`

Lignes : 18 040 - colonnes logiques : 21 - physiques : 21 - derniere activite (dtem) : 08/07/2026 10:27:57 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `type` sur type - `numfouclt` sur numfouclt - `amjh` sur amjh - `operateur` sur operateur - `mvt` sur mvt - `depot` sur depot - `rang` sur rang - `numcde` sur numcde - `ligne` sur ligne - `refbl` sur refbl - `clef` sur type, code1, code2, code3, amjh

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `dtem` | horodatage |
| 3 | `salm` | entier2ns |
| 4 | `code1` | texte(5) |
| 5 | `code2` | texte(20) |
| 6 | `code3` | texte(10) |
| 7 | `type` | entier4ns |
| 8 | `numfouclt` | entier4ns |
| 9 | `amjh` | horodatage |
| 10 | `operateur` | entier2ns |
| 11 | `mvt` | octet |
| 12 | `depot` | texte(10) |
| 13 | `rang` | texte(50) |
| 14 | `numcde` | entier8ns |
| 15 | `ligne` | entier4ns |
| 16 | `qte1` | reel8 |
| 17 | `qte2` | reel8 |
| 18 | `des1` | texte(50) |
| 19 | `des2` | texte(50) |
| 20 | `refbl` | texte(30) |
| 21 | `lot` | texte(10) |

Dernieres lignes :

| id | dtem | salm | code1 | code2 | code3 | type | numfouclt | amjh | operateur | mvt | depot | rang | numcde | ligne | qte1 | qte2 | des1 | des2 | refbl | lot |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 18454 | 08/07/2026 10:27:57 | 7 | 629 | 0015 | 470 | 1 | 629 | 08/07/2026 10:27:57 | 7 | 1 |  |  | 6009 | 1 | 0 | 0 | Création automatique Laize suite cde  fournisseur |  |  |  |
| 18453 | 08/07/2026 10:27:57 | 7 | 629 | 0015 | 470 | 1 | 0 | 12/30/1899 00:00:00 | 7 | 0 |  |  | 0 | 0 | 0 | 99999999999.99 |  |  | 0 |  |
| 18452 | 08/07/2026 10:23:28 | 7 | 629 | 0015 |  | 1 | 0 | 12/30/1899 00:00:00 | 7 | 0 |  |  | 0 | 0 | 0 | 99999999999.99 |  |  | 0 |  |

### `vte_com`

Lignes : 1 079 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 2 172 - derniere activite (dtem) : 07/27/2026 15:42:55 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 2206 | 1 | 0 | 2 | SUPPLIER CODE : 2140000470 | 26070141 | 2 | 07/27/2026 15:42:55 | 9998 |
| 2204 | 1 | 0 | 1 | SUPPLIER CODE : 2140000470 | 26070141 | 2 | 07/27/2026 15:42:55 | 9998 |
| 2202 | 1 | 0 | 2 | SUPPLIER CODE : 2140000470 | 26070141 | 1 | 07/27/2026 15:41:55 | 9998 |

### `vte_comic`

Lignes : 10 - colonnes logiques : 9 - physiques : 9 - total corbeille comprise : 20 - derniere activite (dtem) : 01/09/2024 12:04:35 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Dernieres lignes :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 23 | 1 | 0 | 2 | EORI EXPEDITEUR FR34088500300079 E MAIL : damien.huguet@h... | 24010066 | 0 | 01/09/2024 12:04:35 | 2 |
| 21 | 1 | 0 | 2 | N° IA : 63100250F001 | 23070053 | 0 | 07/11/2023 09:56:00 | 2 |
| 19 | 1 | 0 | 1 | N° IA : 63100250F001 | 23070053 | 0 | 07/11/2023 09:56:00 | 2 |

### `vte_entete`

Lignes : 21 821 - colonnes logiques : 72 - physiques : 97 - total corbeille comprise : 63 411 - derniere activite (dtem) : 08/07/2026 17:21:27 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjf` sur amjf - `numclt` sur numclt - `rs` sur rs - `groupeclt` sur groupeclt - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `reg` sur reg - `amje` sur amje - `pos` sur pos - `rap` sur rap - `sol` sur sol - `numrep` sur numrep - `cais` sur cais - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjf` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `htnb` | numerique |
| 39 | `tvab` | numerique |
| 40 | `civ` | octet |
| 41 | `interlocuteur` | texte(50) |
| 42 | `tex` | texte(10) |
| 43 | `mail` | texte(128) |
| 44 | `com` | octet |
| 45 | `numint` | entier4ns |
| 46 | `dest` | texte(1) |
| 47 | `frs` | texte(50) |
| 48 | `fadr1` | texte(50) |
| 49 | `fadr2` | texte(50) |
| 50 | `intclt` | entier4ns |
| 51 | `fcp` | texte(10) |
| 52 | `fville` | texte(50) |
| 53 | `fpays` | texte(50) |
| 54 | `amje` | date |
| 55 | `fcpays` | texte(5) |
| 56 | `pos` | octet |
| 57 | `rap` | octet |
| 58 | `sol` | octet |
| 59 | `numrep` | entier2ns |
| 60 | `cais` | octet |
| 61 | `tvade` | octet |
| 62 | `nfa` | entier8ns |
| 63 | `typa` | octet |
| 64 | `comavoir` | texte(30) |
| 65 | `vref` | texte(50) |
| 66 | `nref` | texte(50) |
| 67 | `fbp` | texte(10) |
| 68 | `fsiret` | texte(30) |
| 69 | `fntva` | texte(30) |
| 70 | `vteauto` | octet |
| 71 | `edi` | octet |
| 72 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 97 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjf | numclt | rs | groupeclt | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 93863 | 0 | 08/07/2026 17:21:27 | 5 |  | 26080047 | FRANCE | FR | 1 | 5 | 08/07/2026 00:00:00 | 601 | ROQUETTE FRERES | 601 | 0 | 0 | 1 | 62136 | 1827.960000 | Rue de la Haute Loge |  | LESTREM |  | 2 | E | 1827.960000 | 0 | 1 | 0.000000 | 0.000000 |
| 93861 | 0 | 08/07/2026 17:21:25 | 5 |  | 26070203 | BELGIQUE | BE | 1 | 5 | 07/02/2026 00:00:00 | 122 | S.A CARREFOUR BELGIUM | 122 | 0 | 0 | 1 | 1930 | 8091.060000 | Corporate Village | Leonardo Da Vincilaan 3 | ZAVENTEM |  | 4 | E | 8091.060000 | 0 | 1 | 0.000000 | 0.000000 |
| 93859 | 0 | 08/07/2026 17:21:27 | 5 |  | 26080046 | FRANCE | FR | 1 | 5 | 08/07/2026 00:00:00 | 748 | IMPRIMERIE LE REVEREND | 748 | 0 | 0 | 3 | 50700 | 0.000000 | Z.A. de la Tassinerie  | Route d'Huberville | VALOGNES |  | 1 | E | 0.000000 | 0 | 1 | 0.000000 | 0.000000 |

### `vte_ligne`

Lignes : 36 998 - colonnes logiques : 49 - physiques : 58 - total corbeille comprise : 74 190 - derniere activite (dtem) : 08/07/2026 14:03:38 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `livno` sur livno - `livlg` sur livlg - `livbl` sur livbl - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `com` | octet |
| 15 | `ligne` | entier4ns |
| 16 | `code1` | texte(5) |
| 17 | `code2` | texte(20) |
| 18 | `code3` | texte(10) |
| 19 | `des1` | texte(50) |
| 20 | `fam` | octet |
| 21 | `sfam` | entier4ns |
| 22 | `gamme` | entier2ns |
| 23 | `qte` | reel8 |
| 24 | `des2` | texte(50) |
| 25 | `des3` | texte(50) |
| 26 | `des4` | texte(50) |
| 27 | `suv` | octet |
| 28 | `vuv` | numerique |
| 29 | `pa` | numerique |
| 30 | `pub` | numerique |
| 31 | `pun` | numerique |
| 32 | `depot` | texte(10) |
| 33 | `net` | octet |
| 34 | `ctva` | texte(5) |
| 35 | `livno` | entier8ns |
| 36 | `livlg` | entier4ns |
| 37 | `livbl` | entier8ns |
| 38 | `cptva` | entier8ns |
| 39 | `cpexp` | entier8ns |
| 40 | `cpexo` | entier8ns |
| 41 | `cpcee` | entier8ns |
| 42 | `cpdom` | entier8ns |
| 43 | `cpmon` | entier8ns |
| 44 | `cuv` | texte(5) |
| 45 | `vref` | texte(50) |
| 46 | `nref` | texte(50) |
| 47 | `pds` | reel4 |
| 48 | `comrep` | reel4 |
| 49 | `mach` | texte(10) |

Dernieres lignes (les 30 premieres colonnes sur 58 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | ligne | code1 | code2 | code3 | des1 | fam | sfam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 75920 | 0 | 08/07/2026 14:03:38 | 5 | 0.00 | 26080047 | 1 | 1827.960000 | 1827.960000 | 1 | 0.000000 | 0.000000 | 1827.960000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 601 | 0161 |  | Etiquette 148 x 210 mm, | 1 | 1 |
| 75918 | 0 | 08/07/2026 14:02:13 | 5 | 0.00 | 26070203 | 1 | 2029.860000 | 2029.860000 | 1 | 0.000000 | 0.000000 | 2029.860000 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 122 | 0025 |  | Carton de 9.000 étiquettes | 2 | 1 |
| 75916 | 0 | 08/07/2026 14:02:08 | 5 | 0.00 | 26070203 | 1 | 6061.200000 | 6061.200000 | 1 | 0.000000 | 0.000000 | 6061.200000 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 122 | 0023 |  | C11.200/étiquettes, format 68x84 mm. | 2 | 1 |

### `vtf_com`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `vtf_comic`

Lignes : 0 - colonnes logiques : 9 - physiques : 0 - total corbeille comprise : 0

Cles : `id` sur id (primaire) - `bloq` sur bloq - `corbeille` sur corbeille - `typt` sur typt - `numpiece` sur numpiece - `numligne` sur numligne - `clef` sur numpiece, numligne, typt - `clefcorbeille` sur numpiece, numligne, typt, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | reel4 |
| 4 | `typt` | octet |
| 5 | `com` | texte(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `vtf_entete`

Lignes : 4 181 - colonnes logiques : 62 - physiques : 87 - total corbeille comprise : 10 100 - derniere activite (dtem) : 08/06/2026 17:33:44 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `cpays` sur cpays - `type` sur type - `operateur` sur operateur - `amjf` sur amjf - `numfou` sur numfou - `rs` sur rs - `groupefou` sur groupefou - `cat1` sur cat1 - `cat2` sur cat2 - `cat3` sur cat3 - `cp` sur cp - `htn` sur htn - `amje` sur amje - `facf` sur facf - `pos` sur pos - `rap` sur rap - `sol` sur sol - `clefcorbeille` sur numero, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | texte(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | texte(50) |
| 8 | `cpays` | texte(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjf` | date |
| 12 | `numfou` | entier4ns |
| 13 | `rs` | texte(50) |
| 14 | `groupefou` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | texte(10) |
| 19 | `htn` | numerique |
| 20 | `adr1` | texte(50) |
| 21 | `adr2` | texte(50) |
| 22 | `ville` | texte(50) |
| 23 | `bp` | texte(10) |
| 24 | `fis` | octet |
| 25 | `devise` | texte(10) |
| 26 | `htb` | numerique |
| 27 | `escompte` | reel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numerique |
| 30 | `tva` | numerique |
| 31 | `ttcn` | numerique |
| 32 | `franco` | numerique |
| 33 | `acompte` | numerique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `edi` | octet |
| 39 | `htnb` | numerique |
| 40 | `tvab` | numerique |
| 41 | `civ` | octet |
| 42 | `interlocuteur` | texte(50) |
| 43 | `tex` | texte(10) |
| 44 | `mail` | texte(128) |
| 45 | `com` | octet |
| 46 | `numint` | entier4ns |
| 47 | `dest` | texte(1) |
| 48 | `intfou` | entier4ns |
| 49 | `frs` | texte(50) |
| 50 | `fadr1` | texte(50) |
| 51 | `fadr2` | texte(50) |
| 52 | `fcp` | texte(10) |
| 53 | `fville` | texte(50) |
| 54 | `fpays` | texte(50) |
| 55 | `fcpays` | texte(5) |
| 56 | `amje` | date |
| 57 | `facf` | texte(20) |
| 58 | `pos` | octet |
| 59 | `rap` | octet |
| 60 | `sol` | octet |
| 61 | `tvacee` | numerique |
| 62 | `imp` | octet |

Dernieres lignes (les 30 premieres colonnes sur 87 - tout est dans le JSON) :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjf | numfou | rs | groupefou | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 13666 | 0 | 08/06/2026 17:33:44 | 5 |  | 4197 | FRANCE | FR | 1 | 905 | 08/06/2026 00:00:00 | 885 | SIEGWERK France SAS | 885 | 0 | 0 | 0 | 74105 | 106.740000 | Route de Taninges 13 | BP 506 | ANNEMASSE CEDEX |  | 1 | E | 106.740000 | 0 | 1 | 0.000000 | 21.350000 |
| 13664 | 0 | 08/06/2026 17:33:44 | 5 |  | 4196 | FRANCE | FR | 1 | 905 | 08/04/2026 00:00:00 | 1092 | QRT Graphique | 1092 | 0 | 0 | 0 | 30520 | 366.400000 | Avenue Sainte Barbe | ZI de Saint Martin | SAINT MARTIN DE VALGALGUES |  | 1 | E | 366.400000 | 0 | 1 | 0.000000 | 73.280000 |
| 13662 | 0 | 08/06/2026 17:33:44 | 5 |  | 4195 | FRANCE | FR | 1 | 905 | 08/04/2026 00:00:00 | 1092 | QRT Graphique | 1092 | 0 | 0 | 0 | 30520 | 1646.400000 | Avenue Sainte Barbe | ZI de Saint Martin | SAINT MARTIN DE VALGALGUES |  | 1 | E | 1646.400000 | 0 | 1 | 0.000000 | 329.280000 |

### `vtf_ligne`

Lignes : 9 603 - colonnes logiques : 44 - physiques : 53 - total corbeille comprise : 19 563 - derniere activite (dtem) : 08/06/2026 12:12:42 - extrait : TOP n + ORDER BY id DESC

Cles : `id` sur id (primaire) - `corbeille` sur corbeille - `numero` sur numero - `type` sur type - `htn` sur htn - `ligne` sur ligne - `code1` sur code1 - `code2` sur code2 - `code3` sur code3 - `des1` sur des1 - `fam` sur fam - `sfam` sur sfam - `gamme` sur gamme - `qte` sur qte - `livno` sur livno - `livlg` sur livlg - `livref` sur livref - `clef` sur numero, ligne - `clefcorbeille` sur numero, ligne, corbeille (unique)

| # | Colonne (logique) | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | reel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numerique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numerique |
| 9 | `htb` | numerique |
| 10 | `trem` | octet |
| 11 | `rem` | numerique |
| 12 | `tva` | numerique |
| 13 | `ttcn` | numerique |
| 14 | `com` | octet |
| 15 | `ligne` | entier4ns |
| 16 | `code1` | texte(5) |
| 17 | `code2` | texte(20) |
| 18 | `code3` | texte(10) |
| 19 | `des1` | texte(50) |
| 20 | `fam` | octet |
| 21 | `sfam` | entier4ns |
| 22 | `gamme` | entier2ns |
| 23 | `qte` | reel8 |
| 24 | `des2` | texte(50) |
| 25 | `des3` | texte(50) |
| 26 | `des4` | texte(50) |
| 27 | `pa` | numerique |
| 28 | `pub` | numerique |
| 29 | `pun` | numerique |
| 30 | `depot` | texte(10) |
| 31 | `cua` | texte(5) |
| 32 | `sua` | octet |
| 33 | `vua` | numerique |
| 34 | `net` | octet |
| 35 | `ctva` | texte(5) |
| 36 | `livno` | entier8ns |
| 37 | `livlg` | entier4ns |
| 38 | `livref` | texte(30) |
| 39 | `atva` | entier8ns |
| 40 | `aimp` | entier8ns |
| 41 | `aexo` | entier8ns |
| 42 | `acee` | entier8ns |
| 43 | `adom` | entier8ns |
| 44 | `amon` | entier8ns |

Dernieres lignes (les 30 premieres colonnes sur 53 - tout est dans le JSON) :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | ligne | code1 | code2 | code3 | des1 | fam | sfam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 21700 | 0 | 08/06/2026 12:12:42 | 905 | 20.00 | 4197 | 10 | 106.740000 | 106.740000 | 1 | 0.000000 | 21.350000 | 128.090000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 885 | 0031 |  | Nutri-ADD Photoinitiator E20 (2% du mélange encre) | 8 | 2 |
| 21698 | 0 | 08/06/2026 12:04:43 | 905 | 20.00 | 4196 | 1 | 366.400000 | 366.400000 | 1 | 0.000000 | 73.280000 | 439.680000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 890 | 0111 |  | Etiquette 148 x 210 mm, 2 coul. R° | 3 | 2 |
| 21696 | 0 | 08/06/2026 12:04:01 | 905 | 20.00 | 4195 | 1 | 1646.400000 | 1646.400000 | 1 | 0.000000 | 329.280000 | 1975.680000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 890 | 0085 |  | Etiquette 35 x 15 mm, 3 couleurs recto. | 4 | 1 |
