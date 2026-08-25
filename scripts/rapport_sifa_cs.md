# Inventaire de la base HFSQL `sifa_cs`

Généré le 24/08/2026 15:54 — lecture seule.

Source : `provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;`

Objets vus par le schéma : 200 — inspectés ici : 29 (tables `_backup_` exclues : 17)

## Sommaire

| Table | Type | Lignes | Colonnes |
|---|---|---:|---:|
| [`cdi_comic`](#cdi-comic) | TABLE | 0 | 9 |
| [`cdi_comif`](#cdi-comif) | TABLE | 0 | 9 |
| [`cdi_entete`](#cdi-entete) | TABLE | 254 | 80 |
| [`cdi_ligne`](#cdi-ligne) | TABLE | 340 | 120 |
| [`cdi_res`](#cdi-res) | TABLE | 165 | 37 |
| [`gpr_art`](#gpr-art) | TABLE | 5 | 18 |
| [`gpr_ff`](#gpr-ff) | TABLE | 1583 | 302 |
| [`gpr_ff1`](#gpr-ff1) | TABLE | 2701 | 229 |
| [`gpr_ffcomic`](#gpr-ffcomic) | TABLE | 1093 | 11 |
| [`gpr_ffcomif`](#gpr-ffcomif) | TABLE | 3 | 11 |
| [`gpr_gpr`](#gpr-gpr) | TABLE | 2804 | 15 |
| [`gpr_gprcom`](#gpr-gprcom) | TABLE | 0 | 11 |
| [`gpr_mat`](#gpr-mat) | TABLE | 653 | 32 |
| [`gpr_sat`](#gpr-sat) | TABLE | 26 | 9 |
| [`mac_atps`](#mac-atps) | TABLE | 0 | 21 |
| [`mac_pro`](#mac-pro) | TABLE | 43 | 74 |
| [`mac_ptps`](#mac-ptps) | TABLE | 18 | 98 |
| [`mac_tra`](#mac-tra) | TABLE | 74 | 135 |
| [`mat_fmat`](#mat-fmat) | TABLE | 57 | 21 |
| [`mat_mat`](#mat-mat) | TABLE | 7521 | 483 |
| [`mat_matcom`](#mat-matcom) | TABLE | 79 | 11 |
| [`mat_matcomif`](#mat-matcomif) | TABLE | 6089 | 11 |
| [`mat_matcomir`](#mat-matcomir) | TABLE | 0 | 11 |
| [`mat_matcomis`](#mat-matcomis) | TABLE | 18 | 11 |
| [`mat_nomen`](#mat-nomen) | TABLE | 482 | 46 |
| [`vte_com`](#vte-com) | TABLE | 2172 | 9 |
| [`vte_comic`](#vte-comic) | TABLE | 20 | 9 |
| [`vte_entete`](#vte-entete) | TABLE | 63411 | 97 |
| [`vte_ligne`](#vte-ligne) | TABLE | 74190 | 58 |

## Détail des tables

### `cdi_comic`

Type : TABLE — lignes : 0 — colonnes : 9

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `typt` | octet |
| 5 | `com` | varchar(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `cdi_comif`

Type : TABLE — lignes : 0 — colonnes : 9

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `typt` | octet |
| 5 | `com` | varchar(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

### `cdi_entete`

Type : TABLE — lignes : 254 — colonnes : 80

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | réel4 |
| 3 | `salm` | entier2ns |
| 4 | `dtem` | horodatage |
| 5 | `numero` | entier8ns |
| 6 | `com` | octet |
| 7 | `com_2` | octet |
| 8 | `com_3` | octet |
| 9 | `com_4` | octet |
| 10 | `com_5` | octet |
| 11 | `com_6` | octet |
| 12 | `com_7` | octet |
| 13 | `com_8` | octet |
| 14 | `com_9` | octet |
| 15 | `com_10` | octet |
| 16 | `type` | entier2ns |
| 17 | `operateur` | entier2ns |
| 18 | `amjc` | date |
| 19 | `numclt` | entier4ns |
| 20 | `edi` | octet |
| 21 | `tdec` | entier4ns |
| 22 | `amjp` | horodatage |
| 23 | `amjr` | date |
| 24 | `pos` | octet |
| 25 | `ndec` | entier8ns |
| 26 | `code1m` | varchar(5) |
| 27 | `code2m` | varchar(20) |
| 28 | `code3m` | varchar(10) |
| 29 | `prio` | entier4ns |
| 30 | `mac1p` | varchar(10) |
| 31 | `tcdemar` | octet |
| 32 | `qte` | réel8 |
| 33 | `oftl` | réel8 |
| 34 | `ofta` | réel8 |
| 35 | `onbl` | entier4ns |
| 36 | `onba` | entier4ns |
| 37 | `typematbasebof` | octet |
| 38 | `laizem` | entier4ns |
| 39 | `nbcoul` | octet |
| 40 | `vit` | entier4ns |
| 41 | `machine` | varchar(10) |
| 42 | `machine_2` | varchar(10) |
| 43 | `machine_3` | varchar(10) |
| 44 | `machine_4` | varchar(10) |
| 45 | `machine_5` | varchar(10) |
| 46 | `travail` | entier4ns |
| 47 | `travail_2` | entier4ns |
| 48 | `travail_3` | entier4ns |
| 49 | `travail_4` | entier4ns |
| 50 | `travail_5` | entier4ns |
| 51 | `tpcm` | réel4 |
| 52 | `tpcm_2` | réel4 |
| 53 | `tpcm_3` | réel4 |
| 54 | `tpcm_4` | réel4 |
| 55 | `tpcm_5` | réel4 |
| 56 | `tpsm` | réel4 |
| 57 | `tpsm_2` | réel4 |
| 58 | `tpsm_3` | réel4 |
| 59 | `tpsm_4` | réel4 |
| 60 | `tpsm_5` | réel4 |
| 61 | `tpst` | réel4 |
| 62 | `tpst_2` | réel4 |
| 63 | `tpst_3` | réel4 |
| 64 | `tpst_4` | réel4 |
| 65 | `tpst_5` | réel4 |
| 66 | `cond` | varchar(10) |
| 67 | `tpcco` | réel4 |
| 68 | `tpsco` | réel4 |
| 69 | `pprio` | octet |
| 70 | `amjpi` | horodatage |
| 71 | `ptpsp` | réel4 |
| 72 | `ptpsc` | réel4 |
| 73 | `pcom` | varchar(30) |
| 74 | `amjpe` | date |
| 75 | `ncli` | entier4ns |
| 76 | `ntei` | entier4ns |
| 77 | `nrec` | entier4ns |
| 78 | `ama` | octet |
| 79 | `dosplavu` | octet |
| 80 | `imp` | octet |

Extrait :

| id | corbeille | salm | dtem | numero | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | type | operateur | amjc | numclt | edi | tdec | amjp | amjr | pos | ndec | code1m | code2m | code3m | prio | mac1p | tcdemar | qte | oftl | ofta | onbl | onba | typematbasebof | laizem | nbcoul | vit | machine | machine_2 | machine_3 | machine_4 | machine_5 | travail | travail_2 | travail_3 | travail_4 | travail_5 | tpcm | tpcm_2 | tpcm_3 | tpcm_4 | tpcm_5 | tpsm | tpsm_2 | tpsm_3 | tpsm_4 | tpsm_5 | tpst | tpst_2 | tpst_3 | tpst_4 | tpst_5 | cond | tpcco | tpsco | pprio | amjpi | ptpsp | ptpsc | pcom | amjpe | ncli | ntei | nrec | ama | dosplavu | imp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 9999 | 09/22/2022 19:42:54 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 04/27/2021 00:00:00 | 1050 | 0 | 2 | 04/27/2021 11:04:11 | 04/27/2021 00:00:00 | 4 | 1296 | 886 | 0002 |  | 5 |  | 1 | 1200000 | 0 | 0 | 0 | 0 | 1 | 267 | 0 | 0 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 5.04 | 0 | 0 | 0 | 0 | 5.04 | 0 | 0 | 0 | 0 | 1.54 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 11/30/1999 00:00:00 | 0 | 0 |  |  | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 1 | 1 | 04/27/2021 11:04:17 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 04/27/2021 00:00:00 | 1050 | 0 | 2 | 04/27/2021 11:04:11 | 04/27/2021 00:00:00 | 0 | 1296 | 886 | 0002 |  | 5 |  | 1 | 1200000 | 0 | 0 | 0 | 0 | 1 | 267 | 0 | 0 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 5.04 | 0 | 0 | 0 | 0 | 5.04 | 0 | 0 | 0 | 0 | 1.54 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 11/30/1999 00:00:00 | 0 | 0 |  |  | 0 | 0 | 0 | 1 | 0 | 0 |
| 80 | 11 | 907 | 01/23/2026 13:55:57 | 1018 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 9998 | 01/06/2026 00:00:00 | 470 | 0 | 2 | 01/06/2026 11:51:06 | 01/06/2026 00:00:00 | 3 | 1733 | 1 | 0008 |  | 5 |  | 1 | 384000 | 0 | 0 | 0 | 0 | 1 | 440 | 0 | 0 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 7.05 | 0 | 0 | 0 | 0 | 7.05 | 0 | 0 | 0 | 0 | 5.05 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 | 11/30/1999 00:00:00 | 0 | 0 |  |  | 0 | 0 | 0 | 1 | 0 | 0 |

### `cdi_ligne`

Type : TABLE — lignes : 340 — colonnes : 120

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | réel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `typematbasebof` | octet |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `lai` | entier4ns |
| 10 | `lai_2` | entier4ns |
| 11 | `lai_3` | entier4ns |
| 12 | `lai_4` | entier4ns |
| 13 | `lai_5` | entier4ns |
| 14 | `numero` | entier8ns |
| 15 | `ligne` | entier4ns |
| 16 | `numclt` | entier4ns |
| 17 | `nocde` | entier8ns |
| 18 | `lgcde` | entier4ns |
| 19 | `amjl` | date |
| 20 | `amje` | date |
| 21 | `lpos` | octet |
| 22 | `qte` | réel8 |
| 23 | `modliv` | entier2ns |
| 24 | `nbj` | entier4ns |
| 25 | `mach` | varchar(10) |
| 26 | `mach_2` | varchar(10) |
| 27 | `mach_3` | varchar(10) |
| 28 | `mach_4` | varchar(10) |
| 29 | `mach_5` | varchar(10) |
| 30 | `tra` | entier4ns |
| 31 | `tra_2` | entier4ns |
| 32 | `tra_3` | entier4ns |
| 33 | `tra_4` | entier4ns |
| 34 | `tra_5` | entier4ns |
| 35 | `tpsm` | réel4 |
| 36 | `tpsm_2` | réel4 |
| 37 | `tpsm_3` | réel4 |
| 38 | `tpsm_4` | réel4 |
| 39 | `tpsm_5` | réel4 |
| 40 | `tpst` | réel4 |
| 41 | `tpst_2` | réel4 |
| 42 | `tpst_3` | réel4 |
| 43 | `tpst_4` | réel4 |
| 44 | `tpst_5` | réel4 |
| 45 | `cond` | varchar(10) |
| 46 | `tpsco` | réel4 |
| 47 | `matcode1` | varchar(5) |
| 48 | `matcode1_2` | varchar(5) |
| 49 | `matcode1_3` | varchar(5) |
| 50 | `matcode1_4` | varchar(5) |
| 51 | `matcode1_5` | varchar(5) |
| 52 | `matcode2` | varchar(20) |
| 53 | `matcode2_2` | varchar(20) |
| 54 | `matcode2_3` | varchar(20) |
| 55 | `matcode2_4` | varchar(20) |
| 56 | `matcode2_5` | varchar(20) |
| 57 | `matcode3` | varchar(10) |
| 58 | `matcode3_2` | varchar(10) |
| 59 | `matcode3_3` | varchar(10) |
| 60 | `matcode3_4` | varchar(10) |
| 61 | `matcode3_5` | varchar(10) |
| 62 | `qtem` | réel8 |
| 63 | `qtem_2` | réel8 |
| 64 | `qtem_3` | réel8 |
| 65 | `qtem_4` | réel8 |
| 66 | `qtem_5` | réel8 |
| 67 | `qtemhg` | réel8 |
| 68 | `qtemhg_2` | réel8 |
| 69 | `qtemhg_3` | réel8 |
| 70 | `qtemhg_4` | réel8 |
| 71 | `qtemhg_5` | réel8 |
| 72 | `pcod1` | varchar(5) |
| 73 | `pcod2` | varchar(20) |
| 74 | `laipel` | entier4ns |
| 75 | `qtep` | réel8 |
| 76 | `dcod1` | varchar(5) |
| 77 | `dcod1_2` | varchar(5) |
| 78 | `dcod1_3` | varchar(5) |
| 79 | `dcod1_4` | varchar(5) |
| 80 | `dcod1_5` | varchar(5) |
| 81 | `dcod2` | varchar(20) |
| 82 | `dcod2_2` | varchar(20) |
| 83 | `dcod2_3` | varchar(20) |
| 84 | `dcod2_4` | varchar(20) |
| 85 | `dcod2_5` | varchar(20) |
| 86 | `laidor` | entier4ns |
| 87 | `laidor_2` | entier4ns |
| 88 | `laidor_3` | entier4ns |
| 89 | `laidor_4` | entier4ns |
| 90 | `laidor_5` | entier4ns |
| 91 | `qted` | réel8 |
| 92 | `qted_2` | réel8 |
| 93 | `qted_3` | réel8 |
| 94 | `qted_4` | réel8 |
| 95 | `qted_5` | réel8 |
| 96 | `vcod1` | varchar(5) |
| 97 | `vcod2` | varchar(20) |
| 98 | `qtev` | réel8 |
| 99 | `vbcod1` | varchar(5) |
| 100 | `vbcod2` | varchar(20) |
| 101 | `qtevb` | réel8 |
| 102 | `lab` | octet |
| 103 | `ncli` | entier4ns |
| 104 | `ntei` | entier4ns |
| 105 | `nrec` | entier4ns |
| 106 | `com` | octet |
| 107 | `com_2` | octet |
| 108 | `com_3` | octet |
| 109 | `com_4` | octet |
| 110 | `com_5` | octet |
| 111 | `com_6` | octet |
| 112 | `com_7` | octet |
| 113 | `com_8` | octet |
| 114 | `com_9` | octet |
| 115 | `com_10` | octet |
| 116 | `nbt` | entier4ns |
| 117 | `num1` | varchar(50) |
| 118 | `num2` | varchar(50) |
| 119 | `amapose` | entier4ns |
| 120 | `vcouv` | varchar(10) |

Extrait :

| id | corbeille | dtem | salm | typematbasebof | code1 | code2 | code3 | lai | lai_2 | lai_3 | lai_4 | lai_5 | numero | ligne | numclt | nocde | lgcde | amjl | amje | lpos | qte | modliv | nbj | mach | mach_2 | mach_3 | mach_4 | mach_5 | tra | tra_2 | tra_3 | tra_4 | tra_5 | tpsm | tpsm_2 | tpsm_3 | tpsm_4 | tpsm_5 | tpst | tpst_2 | tpst_3 | tpst_4 | tpst_5 | cond | tpsco | matcode1 | matcode1_2 | matcode1_3 | matcode1_4 | matcode1_5 | matcode2 | matcode2_2 | matcode2_3 | matcode2_4 | matcode2_5 | matcode3 | matcode3_2 | matcode3_3 | matcode3_4 | matcode3_5 | qtem | qtem_2 | qtem_3 | qtem_4 | qtem_5 | qtemhg | qtemhg_2 | qtemhg_3 | qtemhg_4 | qtemhg_5 | pcod1 | pcod2 | laipel | qtep | dcod1 | dcod1_2 | dcod1_3 | dcod1_4 | dcod1_5 | dcod2 | dcod2_2 | dcod2_3 | dcod2_4 | dcod2_5 | laidor | laidor_2 | laidor_3 | laidor_4 | laidor_5 | qted | qted_2 | qted_3 | qted_4 | qted_5 | vcod1 | vcod2 | qtev | vbcod1 | vbcod2 | qtevb | lab | ncli | ntei | nrec | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | nbt | num1 | num2 | amapose | vcouv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 09/22/2022 19:42:54 | 9999 | 1 | 1050 | 0001 |  | 267 | 0 | 0 | 0 | 0 | 1000 | 1 | 1050 | 9919715 | 1 | 11/18/2020 00:00:00 | 11/13/2020 00:00:00 | 4 | 1200000 | 1 | 5 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 5.04 | 0 | 0 | 0 | 0 | 1.54 | 0 | 0 | 0 | 0 |  | 0 | 886 |  |  |  |  | 0002 |  |  |  |  |  |  |  |  |  | 7219 | 7219 | 7219 | 7219 | 7219 | 5542 | 5542 | 5542 | 5542 | 5542 |  |  | 0 | 7219 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 7219 | 7219 | 0 | 0 | 0 |  |  | 0 |  |  | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  | 0 | -1 |
| 2 | 1 | 04/27/2021 11:04:14 | 1 | 1 | 1050 | 0001 |  | 267 | 0 | 0 | 0 | 0 | 1000 | 1 | 1050 | 9919715 | 1 | 11/18/2020 00:00:00 | 11/13/2020 00:00:00 | 0 | 1200000 | 1 | 5 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 | 886 |  |  |  |  | 0002 |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  | 0 | 0 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  | 0 |  |  | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  | 0 | -1 |
| 81 | 9 | 01/22/2026 19:56:12 | 907 | 1 | 470 | 0011 |  | 440 | 0 | 0 | 0 | 0 | 1018 | 1 | 470 | 9931044 | 2 | 02/02/2026 00:00:00 | 01/29/2026 00:00:00 | 3 | 384000 | 1 | 1 | 1 |  |  |  |  | 1 | 0 | 0 | 0 | 0 | 7.05 | 0 | 0 | 0 | 0 | 5.05 | 0 | 0 | 0 | 0 |  | 0 | 1 |  |  |  |  | 0008 |  |  |  |  |  |  |  |  |  | 25943 | 25943 | 25943 | 25943 | 25943 | 24232 | 24232 | 24232 | 24232 | 24232 |  |  | 0 | 25943 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 25943 | 25943 | 0 | 0 | 0 |  |  | 0 |  |  | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  | 0 | -1 |

### `cdi_res`

Type : TABLE — lignes : 165 — colonnes : 37

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | réel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `type` | entier4ns |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `lai` | entier4ns |
| 10 | `qtec` | réel8 |
| 11 | `qte` | réel8 |
| 12 | `qtes` | réel8 |
| 13 | `qtev` | réel8 |
| 14 | `qtehg` | réel8 |
| 15 | `m2qte` | réel8 |
| 16 | `m2pri` | numérique |
| 17 | `com` | octet |
| 18 | `com_2` | octet |
| 19 | `com_3` | octet |
| 20 | `com_4` | octet |
| 21 | `com_5` | octet |
| 22 | `com_6` | octet |
| 23 | `com_7` | octet |
| 24 | `com_8` | octet |
| 25 | `com_9` | octet |
| 26 | `com_10` | octet |
| 27 | `mataj` | octet |
| 28 | `numero` | entier8ns |
| 29 | `lpos` | octet |
| 30 | `composant` | octet |
| 31 | `compocode1nomen` | varchar(5) |
| 32 | `compocode2nomen` | varchar(20) |
| 33 | `compocode3nomen` | varchar(10) |
| 34 | `compotypenomen` | entier4ns |
| 35 | `compoqte` | réel8 |
| 36 | `compotypeqte` | octet |
| 37 | `ordre` | varchar(10) |

Extrait :

| id | corbeille | dtem | salm | type | code1 | code2 | code3 | lai | qtec | qte | qtes | qtev | qtehg | m2qte | m2pri | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | mataj | numero | lpos | composant | compocode1nomen | compocode2nomen | compocode3nomen | compotypenomen | compoqte | compotypeqte | ordre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 01/19/2026 16:44:48 | 9998 | 1 | 886 | 0002 |  | 267 | 7219 | 7219 | 0 | 14438 | 5542 | 1927.47 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1000 | 2 | 0 |  |  |  | 0 | 0 | 0 |  |
| 2 | 1 | 04/28/2021 12:04:33 | 9998 | 1 | 886 | 0002 |  | 267 | 7219 | 7219 | 0 | 7219 | 5542 | 1927.47 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1000 | 2 | 0 |  |  |  | 0 | 0 | 0 |  |
| 37 | 3 | 01/19/2026 16:44:31 | 9998 | 1 | 1 | 0008 |  | 440 | 25943 | 25943 | 0 | 5000 | 24232 | 11414.92 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1018 | 1 | 0 |  |  |  | 0 | 0 | 0 |  |

### `gpr_art`

Type : TABLE — lignes : 5 — colonnes : 18

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `mach` | varchar(10) |
| 10 | `dos` | entier8ns |
| 11 | `ligne` | entier4ns |
| 12 | `numclt` | entier4ns |
| 13 | `qtes` | entier8ns |
| 14 | `orig` | varchar(1) |
| 15 | `type` | entier4ns |
| 16 | `code1` | varchar(5) |
| 17 | `code2` | varchar(20) |
| 18 | `code3` | varchar(10) |

Extrait :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | mach | dos | ligne | numclt | qtes | orig | type | code1 | code2 | code3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 04/28/2021 12:07:35 | 9998 | 5 | 9998 | 04/28/2021 12:07:33 | 1 | 1000 | 1 | 1050 | 10000 |  | 1 | 1050 | 0001 |  |
| 2 | 0 | 1 | 04/28/2021 12:07:35 | 9998 | 5 | 9998 | 04/28/2021 12:07:33 | 1 | 1000 | 1 | 1050 | 10000 |  | 1 | 1050 | 0001 |  |
| 3 | 0 | 0 | 02/23/2022 15:33:17 | 9998 | 5 | 9998 | 02/23/2022 15:33:15 | 1 | 1009 | 1 | 24 | 1000 |  | 1 | 24 | 0012 |  |

### `gpr_ff`

Type : TABLE — lignes : 1583 — colonnes : 302

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `type` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `nmac1` | varchar(10) |
| 12 | `labftl` | réel8 |
| 13 | `nmac2` | varchar(10) |
| 14 | `nmac3` | varchar(10) |
| 15 | `nmac4` | varchar(10) |
| 16 | `nmac5` | varchar(10) |
| 17 | `typeff` | octet |
| 18 | `typefiniff` | octet |
| 19 | `nocond` | varchar(10) |
| 20 | `m1cod1` | varchar(5) |
| 21 | `m1cod2` | varchar(20) |
| 22 | `m1cod3` | varchar(10) |
| 23 | `m2cod1` | varchar(5) |
| 24 | `m2cod2` | varchar(20) |
| 25 | `m2cod3` | varchar(10) |
| 26 | `m3cod1` | varchar(5) |
| 27 | `m3cod2` | varchar(20) |
| 28 | `m3cod3` | varchar(10) |
| 29 | `m4cod1` | varchar(5) |
| 30 | `m4cod2` | varchar(20) |
| 31 | `m4cod3` | varchar(10) |
| 32 | `m5cod1` | varchar(5) |
| 33 | `m5cod2` | varchar(20) |
| 34 | `m5cod3` | varchar(10) |
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
| 45 | `laiout` | réel8 |
| 46 | `laimat` | réel8 |
| 47 | `laimat2` | réel8 |
| 48 | `laimat3` | réel8 |
| 49 | `laimat4` | réel8 |
| 50 | `laimat5` | réel8 |
| 51 | `cliche` | varchar(20) |
| 52 | `cliche1` | varchar(20) |
| 53 | `cliche2` | varchar(20) |
| 54 | `cliche3` | varchar(20) |
| 55 | `cliche4` | varchar(20) |
| 56 | `cliche5` | varchar(20) |
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
| 88 | `espacliche` | réel8 |
| 89 | `nbposacliche` | entier4ns |
| 90 | `nbdtcliche` | entier4ns |
| 91 | `espacliche1` | réel8 |
| 92 | `nbposacliche1` | entier4ns |
| 93 | `espacliche2` | réel8 |
| 94 | `nbposacliche2` | entier4ns |
| 95 | `espacliche3` | réel8 |
| 96 | `nbposacliche3` | entier4ns |
| 97 | `espacliche4` | réel8 |
| 98 | `nbposacliche4` | entier4ns |
| 99 | `espacliche5` | réel8 |
| 100 | `nbposacliche5` | entier4ns |
| 101 | `nbdtcliche1` | entier4ns |
| 102 | `nbdtcliche2` | entier4ns |
| 103 | `nbdtcliche3` | entier4ns |
| 104 | `nbdtcliche4` | entier4ns |
| 105 | `nbdtcliche5` | entier4ns |
| 106 | `typematbasebof` | octet |
| 107 | `pelcod1` | varchar(5) |
| 108 | `pelcod2` | varchar(20) |
| 109 | `laipel` | entier4ns |
| 110 | `dorcod1` | varchar(5) |
| 111 | `dorcod2` | varchar(20) |
| 112 | `laidor` | entier4ns |
| 113 | `magdor` | varchar(10) |
| 114 | `coudor` | varchar(10) |
| 115 | `vercod1` | varchar(5) |
| 116 | `vercod2` | varchar(20) |
| 117 | `vercouv` | varchar(10) |
| 118 | `verbcod1` | varchar(5) |
| 119 | `verbcod2` | varchar(20) |
| 120 | `verchab` | varchar(10) |
| 121 | `pelcod21` | varchar(5) |
| 122 | `pelcod22` | varchar(20) |
| 123 | `laipel2` | entier4ns |
| 124 | `dorcod21` | varchar(5) |
| 125 | `dorcod22` | varchar(20) |
| 126 | `laidor2` | entier4ns |
| 127 | `magdor2` | varchar(10) |
| 128 | `coudor2` | varchar(10) |
| 129 | `coul` | varchar(20) |
| 130 | `coul_2` | varchar(20) |
| 131 | `coul_3` | varchar(20) |
| 132 | `coul_4` | varchar(20) |
| 133 | `coul_5` | varchar(20) |
| 134 | `coul_6` | varchar(20) |
| 135 | `coul_7` | varchar(20) |
| 136 | `coul_8` | varchar(20) |
| 137 | `coul_9` | varchar(20) |
| 138 | `coul_10` | varchar(20) |
| 139 | `teint` | entier8ns |
| 140 | `teint_2` | entier8ns |
| 141 | `teint_3` | entier8ns |
| 142 | `teint_4` | entier8ns |
| 143 | `teint_5` | entier8ns |
| 144 | `teint_6` | entier8ns |
| 145 | `teint_7` | entier8ns |
| 146 | `teint_8` | entier8ns |
| 147 | `teint_9` | entier8ns |
| 148 | `teint_10` | entier8ns |
| 149 | `pms` | varchar(10) |
| 150 | `pms_2` | varchar(10) |
| 151 | `pms_3` | varchar(10) |
| 152 | `pms_4` | varchar(10) |
| 153 | `pms_5` | varchar(10) |
| 154 | `pms_6` | varchar(10) |
| 155 | `pms_7` | varchar(10) |
| 156 | `pms_8` | varchar(10) |
| 157 | `pms_9` | varchar(10) |
| 158 | `pms_10` | varchar(10) |
| 159 | `pencrt` | réel4 |
| 160 | `pencrt_2` | réel4 |
| 161 | `pencrt_3` | réel4 |
| 162 | `pencrt_4` | réel4 |
| 163 | `pencrt_5` | réel4 |
| 164 | `pencrt_6` | réel4 |
| 165 | `pencrt_7` | réel4 |
| 166 | `pencrt_8` | réel4 |
| 167 | `pencrt_9` | réel4 |
| 168 | `pencrt_10` | réel4 |
| 169 | `typimp` | octet |
| 170 | `typimp_2` | octet |
| 171 | `typimp_3` | octet |
| 172 | `typimp_4` | octet |
| 173 | `typimp_5` | octet |
| 174 | `typimp_6` | octet |
| 175 | `typimp_7` | octet |
| 176 | `typimp_8` | octet |
| 177 | `typimp_9` | octet |
| 178 | `typimp_10` | octet |
| 179 | `recver` | octet |
| 180 | `recver_2` | octet |
| 181 | `recver_3` | octet |
| 182 | `recver_4` | octet |
| 183 | `recver_5` | octet |
| 184 | `recver_6` | octet |
| 185 | `recver_7` | octet |
| 186 | `recver_8` | octet |
| 187 | `recver_9` | octet |
| 188 | `recver_10` | octet |
| 189 | `ngser` | octet |
| 190 | `seri` | varchar(10) |
| 191 | `seri_2` | varchar(10) |
| 192 | `seri_3` | varchar(10) |
| 193 | `seri_4` | varchar(10) |
| 194 | `seri_5` | varchar(10) |
| 195 | `chabser` | varchar(10) |
| 196 | `chabser_2` | varchar(10) |
| 197 | `chabser_3` | varchar(10) |
| 198 | `chabser_4` | varchar(10) |
| 199 | `chabser_5` | varchar(10) |
| 200 | `coulimpc` | varchar(10) |
| 201 | `coulspotdos` | varchar(10) |
| 202 | `com` | octet |
| 203 | `com_2` | octet |
| 204 | `com_3` | octet |
| 205 | `com_4` | octet |
| 206 | `com_5` | octet |
| 207 | `com_6` | octet |
| 208 | `com_7` | octet |
| 209 | `com_8` | octet |
| 210 | `com_9` | octet |
| 211 | `com_10` | octet |
| 212 | `labforme` | octet |
| 213 | `labfta` | réel8 |
| 214 | `labnbl` | entier4ns |
| 215 | `labnba` | entier4ns |
| 216 | `nbedit` | octet |
| 217 | `matcomtech` | octet |
| 218 | `indice` | varchar(10) |
| 219 | `matrefclt` | octet |
| 220 | `labcod1` | varchar(5) |
| 221 | `labcod2` | varchar(20) |
| 222 | `labcod3` | varchar(10) |
| 223 | `nbeflivret` | octet |
| 224 | `c1_ner` | entier8ns |
| 225 | `c1_dmax` | entier4ns |
| 226 | `c1_dman` | réel4 |
| 227 | `c1_nef` | entier4ns |
| 228 | `c1_mlr` | réel8 |
| 229 | `c1_lm` | réel8 |
| 230 | `c1_e1` | octet |
| 231 | `c1_e2` | octet |
| 232 | `c1_pose` | octet |
| 233 | `c1_film` | octet |
| 234 | `c1_emb` | octet |
| 235 | `c1_pds` | réel4 |
| 236 | `cartlarg` | entier2ns |
| 237 | `cartlong` | entier2ns |
| 238 | `carthaut` | entier2ns |
| 239 | `cartnbetiq` | entier8ns |
| 240 | `cartpds` | réel4 |
| 241 | `c2_nep` | entier8ns |
| 242 | `c2_nef` | entier4ns |
| 243 | `c2_lf` | entier4ns |
| 244 | `c2_com` | varchar(35) |
| 245 | `c2_pp` | varchar(8) |
| 246 | `c2_ref` | varchar(10) |
| 247 | `c2_nbp` | entier8ns |
| 248 | `c2_neb` | entier8ns |
| 249 | `c3_plc` | entier8ns |
| 250 | `c3_etiqp` | entier8ns |
| 251 | `c3_qcol` | entier8ns |
| 252 | `c3_pdspqt` | réel4 |
| 253 | `c3_pdscol` | réel4 |
| 254 | `c3_emb` | octet |
| 255 | `c3_typ` | octet |
| 256 | `c3_autre` | varchar(20) |
| 257 | `c4_pqt` | entier8ns |
| 258 | `c4_qcol` | entier8ns |
| 259 | `c4_carlar` | entier2ns |
| 260 | `c4_carlon` | entier2ns |
| 261 | `c4_carhau` | entier2ns |
| 262 | `c4_film` | octet |
| 263 | `c4_elas` | octet |
| 264 | `c4_emb` | octet |
| 265 | `c4_pdspqt` | réel4 |
| 266 | `c4_pdscol` | réel4 |
| 267 | `c4_pdscar` | réel4 |
| 268 | `veranil` | réel4 |
| 269 | `perf1` | varchar(10) |
| 270 | `perf2` | varchar(10) |
| 271 | `operateur` | entier2ns |
| 272 | `c1_amorce` | octet |
| 273 | `repiquage` | octet |
| 274 | `impdorsal` | octet |
| 275 | `poscharniere` | octet |
| 276 | `perfointer` | octet |
| 277 | `testcltdivers2` | octet |
| 278 | `blancsoutien` | octet |
| 279 | `cleartoner` | octet |
| 280 | `extracouleur` | octet |
| 281 | `echencomplexe` | octet |
| 282 | `noportelame` | entier4ns |
| 283 | `nbelame` | octet |
| 284 | `perfotls` | entier4 |
| 285 | `c1_eman` | réel4 |
| 286 | `cartcode1` | varchar(5) |
| 287 | `cartcode2` | varchar(20) |
| 288 | `cartcode3` | varchar(10) |
| 289 | `palcode1` | varchar(5) |
| 290 | `palcode2` | varchar(20) |
| 291 | `palcode3` | varchar(10) |
| 292 | `testcltdivers1` | octet |
| 293 | `testcltdivers3` | octet |
| 294 | `pallargeur` | entier2ns |
| 295 | `pallongueur` | entier2ns |
| 296 | `paltype` | octet |
| 297 | `palnbcart` | entier2ns |
| 298 | `palpds` | réel4 |
| 299 | `palnbcartsol` | entier2ns |
| 300 | `palnbetage` | entier2ns |
| 301 | `palhautmax` | entier2ns |
| 302 | `cartnbbob` | entier4 |

Extrait :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | amj | nmac1 | labftl | nmac2 | nmac3 | nmac4 | nmac5 | typeff | typefiniff | nocond | m1cod1 | m1cod2 | m1cod3 | m2cod1 | m2cod2 | m2cod3 | m3cod1 | m3cod2 | m3cod3 | m4cod1 | m4cod2 | m4cod3 | m5cod1 | m5cod2 | m5cod3 | tdec1 | ndec1 | tdec2 | ndec2 | tdec3 | ndec3 | tdec4 | ndec4 | tdec5 | ndec5 | laiout | laimat | laimat2 | laimat3 | laimat4 | laimat5 | cliche | cliche1 | cliche2 | cliche3 | cliche4 | cliche5 | quadri | nbcoul | encrserig | gauf | numerot | perfcaroll | embos | impc | spotdos | grat | verrel | verneut | verpo | ntramac1 | ntramac2 | ntramac3 | ntramac4 | ntramac5 | tvitmac1 | tvitmac2 | tvitmac3 | tvitmac4 | tvitmac5 | vitmac1 | vitmac2 | vitmac3 | vitmac4 | vitmac5 | tvitcond | vitcond | nbcliche | espacliche | nbposacliche | nbdtcliche | espacliche1 | nbposacliche1 | espacliche2 | nbposacliche2 | espacliche3 | nbposacliche3 | espacliche4 | nbposacliche4 | espacliche5 | nbposacliche5 | nbdtcliche1 | nbdtcliche2 | nbdtcliche3 | nbdtcliche4 | nbdtcliche5 | typematbasebof | pelcod1 | pelcod2 | laipel | dorcod1 | dorcod2 | laidor | magdor | coudor | vercod1 | vercod2 | vercouv | verbcod1 | verbcod2 | verchab | pelcod21 | pelcod22 | laipel2 | dorcod21 | dorcod22 | laidor2 | magdor2 | coudor2 | coul | coul_2 | coul_3 | coul_4 | coul_5 | coul_6 | coul_7 | coul_8 | coul_9 | coul_10 | teint | teint_2 | teint_3 | teint_4 | teint_5 | teint_6 | teint_7 | teint_8 | teint_9 | teint_10 | pms | pms_2 | pms_3 | pms_4 | pms_5 | pms_6 | pms_7 | pms_8 | pms_9 | pms_10 | pencrt | pencrt_2 | pencrt_3 | pencrt_4 | pencrt_5 | pencrt_6 | pencrt_7 | pencrt_8 | pencrt_9 | pencrt_10 | typimp | typimp_2 | typimp_3 | typimp_4 | typimp_5 | typimp_6 | typimp_7 | typimp_8 | typimp_9 | typimp_10 | recver | recver_2 | recver_3 | recver_4 | recver_5 | recver_6 | recver_7 | recver_8 | recver_9 | recver_10 | ngser | seri | seri_2 | seri_3 | seri_4 | seri_5 | chabser | chabser_2 | chabser_3 | chabser_4 | chabser_5 | coulimpc | coulspotdos | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | labforme | labfta | labnbl | labnba | nbedit | matcomtech | indice | matrefclt | labcod1 | labcod2 | labcod3 | nbeflivret | c1_ner | c1_dmax | c1_dman | c1_nef | c1_mlr | c1_lm | c1_e1 | c1_e2 | c1_pose | c1_film | c1_emb | c1_pds | cartlarg | cartlong | carthaut | cartnbetiq | cartpds | c2_nep | c2_nef | c2_lf | c2_com | c2_pp | c2_ref | c2_nbp | c2_neb | c3_plc | c3_etiqp | c3_qcol | c3_pdspqt | c3_pdscol | c3_emb | c3_typ | c3_autre | c4_pqt | c4_qcol | c4_carlar | c4_carlon | c4_carhau | c4_film | c4_elas | c4_emb | c4_pdspqt | c4_pdscol | c4_pdscar | veranil | perf1 | perf2 | operateur | c1_amorce | repiquage | impdorsal | poscharniere | perfointer | testcltdivers2 | blancsoutien | cleartoner | extracouleur | echencomplexe | noportelame | nbelame | perfotls | c1_eman | cartcode1 | cartcode2 | cartcode3 | palcode1 | palcode2 | palcode3 | testcltdivers1 | testcltdivers3 | pallargeur | pallongueur | paltype | palnbcart | palpds | palnbcartsol | palnbetage | palhautmax | cartnbbob |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 61 | 1 | 10 | 03/02/2021 14:23:58 | 1 | 923 | 0003 |  | 1 | 02/15/2021 09:49:21 |  | 0 |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 | 0 | 1 | 1 | 5 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  | 0 |  |  | 0 |  |  |  |  | -1 |  |  |  |  |  | 0 |  |  | 0 |  |  |  |  | 1 |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |  | 1 |  |  |  | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -11111111111 1 1 1 1 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |  | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 60 | 1 | 9 | 02/22/2021 09:40:25 | 7 | 923 | 0003 |  | 1 | 02/15/2021 09:49:21 |  | 0 |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 | 0 | 1 | 1 | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  | 0 |  |  | 0 |  |  |  |  | -1 |  |  |  |  |  | 0 |  |  | 0 |  |  |  |  | 1 |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |  | 1 |  |  |  | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -11111111111 1 1 1 1 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |  | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 59 | 1 | 8 | 02/15/2021 09:59:15 | 7 | 923 | 0003 |  | 1 | 02/15/2021 09:49:21 |  | 0 |  |  |  |  | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 1 | 0 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  | 0 |  |  | 0 |  |  |  |  | -1 |  |  |  |  |  | 0 |  |  | 0 |  |  |  |  | 1 |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |  | 1 |  |  |  | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -11111111111 1 1 1 1 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |  | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `gpr_ff1`

Type : TABLE — lignes : 2701 — colonnes : 229

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `type` | entier2ns |
| 10 | `coul` | varchar(20) |
| 11 | `coul_2` | varchar(20) |
| 12 | `coul_3` | varchar(20) |
| 13 | `coul_4` | varchar(20) |
| 14 | `coul_5` | varchar(20) |
| 15 | `coul_6` | varchar(20) |
| 16 | `coul_7` | varchar(20) |
| 17 | `coul_8` | varchar(20) |
| 18 | `coul_9` | varchar(20) |
| 19 | `coul_10` | varchar(20) |
| 20 | `coul_11` | varchar(20) |
| 21 | `coul_12` | varchar(20) |
| 22 | `coul_13` | varchar(20) |
| 23 | `coul_14` | varchar(20) |
| 24 | `coul_15` | varchar(20) |
| 25 | `coul_16` | varchar(20) |
| 26 | `coul_17` | varchar(20) |
| 27 | `coul_18` | varchar(20) |
| 28 | `coul_19` | varchar(20) |
| 29 | `coul_20` | varchar(20) |
| 30 | `teint` | entier8ns |
| 31 | `teint_2` | entier8ns |
| 32 | `teint_3` | entier8ns |
| 33 | `teint_4` | entier8ns |
| 34 | `teint_5` | entier8ns |
| 35 | `teint_6` | entier8ns |
| 36 | `teint_7` | entier8ns |
| 37 | `teint_8` | entier8ns |
| 38 | `teint_9` | entier8ns |
| 39 | `teint_10` | entier8ns |
| 40 | `teint_11` | entier8ns |
| 41 | `teint_12` | entier8ns |
| 42 | `teint_13` | entier8ns |
| 43 | `teint_14` | entier8ns |
| 44 | `teint_15` | entier8ns |
| 45 | `teint_16` | entier8ns |
| 46 | `teint_17` | entier8ns |
| 47 | `teint_18` | entier8ns |
| 48 | `teint_19` | entier8ns |
| 49 | `teint_20` | entier8ns |
| 50 | `pms` | varchar(10) |
| 51 | `pms_2` | varchar(10) |
| 52 | `pms_3` | varchar(10) |
| 53 | `pms_4` | varchar(10) |
| 54 | `pms_5` | varchar(10) |
| 55 | `pms_6` | varchar(10) |
| 56 | `pms_7` | varchar(10) |
| 57 | `pms_8` | varchar(10) |
| 58 | `pms_9` | varchar(10) |
| 59 | `pms_10` | varchar(10) |
| 60 | `pms_11` | varchar(10) |
| 61 | `pms_12` | varchar(10) |
| 62 | `pms_13` | varchar(10) |
| 63 | `pms_14` | varchar(10) |
| 64 | `pms_15` | varchar(10) |
| 65 | `pms_16` | varchar(10) |
| 66 | `pms_17` | varchar(10) |
| 67 | `pms_18` | varchar(10) |
| 68 | `pms_19` | varchar(10) |
| 69 | `pms_20` | varchar(10) |
| 70 | `pencrt` | réel4 |
| 71 | `pencrt_2` | réel4 |
| 72 | `pencrt_3` | réel4 |
| 73 | `pencrt_4` | réel4 |
| 74 | `pencrt_5` | réel4 |
| 75 | `pencrt_6` | réel4 |
| 76 | `pencrt_7` | réel4 |
| 77 | `pencrt_8` | réel4 |
| 78 | `pencrt_9` | réel4 |
| 79 | `pencrt_10` | réel4 |
| 80 | `pencrt_11` | réel4 |
| 81 | `pencrt_12` | réel4 |
| 82 | `pencrt_13` | réel4 |
| 83 | `pencrt_14` | réel4 |
| 84 | `pencrt_15` | réel4 |
| 85 | `pencrt_16` | réel4 |
| 86 | `pencrt_17` | réel4 |
| 87 | `pencrt_18` | réel4 |
| 88 | `pencrt_19` | réel4 |
| 89 | `pencrt_20` | réel4 |
| 90 | `recver` | octet |
| 91 | `recver_2` | octet |
| 92 | `recver_3` | octet |
| 93 | `recver_4` | octet |
| 94 | `recver_5` | octet |
| 95 | `recver_6` | octet |
| 96 | `recver_7` | octet |
| 97 | `recver_8` | octet |
| 98 | `recver_9` | octet |
| 99 | `recver_10` | octet |
| 100 | `recver_11` | octet |
| 101 | `recver_12` | octet |
| 102 | `recver_13` | octet |
| 103 | `recver_14` | octet |
| 104 | `recver_15` | octet |
| 105 | `recver_16` | octet |
| 106 | `recver_17` | octet |
| 107 | `recver_18` | octet |
| 108 | `recver_19` | octet |
| 109 | `recver_20` | octet |
| 110 | `typeimp` | octet |
| 111 | `typeimp_2` | octet |
| 112 | `typeimp_3` | octet |
| 113 | `typeimp_4` | octet |
| 114 | `typeimp_5` | octet |
| 115 | `typeimp_6` | octet |
| 116 | `typeimp_7` | octet |
| 117 | `typeimp_8` | octet |
| 118 | `typeimp_9` | octet |
| 119 | `typeimp_10` | octet |
| 120 | `typeimp_11` | octet |
| 121 | `typeimp_12` | octet |
| 122 | `typeimp_13` | octet |
| 123 | `typeimp_14` | octet |
| 124 | `typeimp_15` | octet |
| 125 | `typeimp_16` | octet |
| 126 | `typeimp_17` | octet |
| 127 | `typeimp_18` | octet |
| 128 | `typeimp_19` | octet |
| 129 | `typeimp_20` | octet |
| 130 | `descriptif` | varchar(15) |
| 131 | `descriptif_2` | varchar(15) |
| 132 | `descriptif_3` | varchar(15) |
| 133 | `descriptif_4` | varchar(15) |
| 134 | `descriptif_5` | varchar(15) |
| 135 | `descriptif_6` | varchar(15) |
| 136 | `descriptif_7` | varchar(15) |
| 137 | `descriptif_8` | varchar(15) |
| 138 | `descriptif_9` | varchar(15) |
| 139 | `descriptif_10` | varchar(15) |
| 140 | `descriptif_11` | varchar(15) |
| 141 | `descriptif_12` | varchar(15) |
| 142 | `descriptif_13` | varchar(15) |
| 143 | `descriptif_14` | varchar(15) |
| 144 | `descriptif_15` | varchar(15) |
| 145 | `descriptif_16` | varchar(15) |
| 146 | `descriptif_17` | varchar(15) |
| 147 | `descriptif_18` | varchar(15) |
| 148 | `descriptif_19` | varchar(15) |
| 149 | `descriptif_20` | varchar(15) |
| 150 | `cc` | varchar(15) |
| 151 | `cc_2` | varchar(15) |
| 152 | `cc_3` | varchar(15) |
| 153 | `cc_4` | varchar(15) |
| 154 | `cc_5` | varchar(15) |
| 155 | `cc_6` | varchar(15) |
| 156 | `cc_7` | varchar(15) |
| 157 | `cc_8` | varchar(15) |
| 158 | `cc_9` | varchar(15) |
| 159 | `cc_10` | varchar(15) |
| 160 | `cc_11` | varchar(15) |
| 161 | `cc_12` | varchar(15) |
| 162 | `cc_13` | varchar(15) |
| 163 | `cc_14` | varchar(15) |
| 164 | `cc_15` | varchar(15) |
| 165 | `cc_16` | varchar(15) |
| 166 | `cc_17` | varchar(15) |
| 167 | `cc_18` | varchar(15) |
| 168 | `cc_19` | varchar(15) |
| 169 | `cc_20` | varchar(15) |
| 170 | `afaire` | octet |
| 171 | `afaire_2` | octet |
| 172 | `afaire_3` | octet |
| 173 | `afaire_4` | octet |
| 174 | `afaire_5` | octet |
| 175 | `afaire_6` | octet |
| 176 | `afaire_7` | octet |
| 177 | `afaire_8` | octet |
| 178 | `afaire_9` | octet |
| 179 | `afaire_10` | octet |
| 180 | `afaire_11` | octet |
| 181 | `afaire_12` | octet |
| 182 | `afaire_13` | octet |
| 183 | `afaire_14` | octet |
| 184 | `afaire_15` | octet |
| 185 | `afaire_16` | octet |
| 186 | `afaire_17` | octet |
| 187 | `afaire_18` | octet |
| 188 | `afaire_19` | octet |
| 189 | `afaire_20` | octet |
| 190 | `ordremac` | octet |
| 191 | `ordremac_2` | octet |
| 192 | `ordremac_3` | octet |
| 193 | `ordremac_4` | octet |
| 194 | `ordremac_5` | octet |
| 195 | `ordremac_6` | octet |
| 196 | `ordremac_7` | octet |
| 197 | `ordremac_8` | octet |
| 198 | `ordremac_9` | octet |
| 199 | `ordremac_10` | octet |
| 200 | `ordremac_11` | octet |
| 201 | `ordremac_12` | octet |
| 202 | `ordremac_13` | octet |
| 203 | `ordremac_14` | octet |
| 204 | `ordremac_15` | octet |
| 205 | `ordremac_16` | octet |
| 206 | `ordremac_17` | octet |
| 207 | `ordremac_18` | octet |
| 208 | `ordremac_19` | octet |
| 209 | `ordremac_20` | octet |
| 210 | `anilox` | varchar(5) |
| 211 | `anilox_2` | varchar(5) |
| 212 | `anilox_3` | varchar(5) |
| 213 | `anilox_4` | varchar(5) |
| 214 | `anilox_5` | varchar(5) |
| 215 | `anilox_6` | varchar(5) |
| 216 | `anilox_7` | varchar(5) |
| 217 | `anilox_8` | varchar(5) |
| 218 | `anilox_9` | varchar(5) |
| 219 | `anilox_10` | varchar(5) |
| 220 | `anilox_11` | varchar(5) |
| 221 | `anilox_12` | varchar(5) |
| 222 | `anilox_13` | varchar(5) |
| 223 | `anilox_14` | varchar(5) |
| 224 | `anilox_15` | varchar(5) |
| 225 | `anilox_16` | varchar(5) |
| 226 | `anilox_17` | varchar(5) |
| 227 | `anilox_18` | varchar(5) |
| 228 | `anilox_19` | varchar(5) |
| 229 | `anilox_20` | varchar(5) |

Extrait :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | coul | coul_2 | coul_3 | coul_4 | coul_5 | coul_6 | coul_7 | coul_8 | coul_9 | coul_10 | coul_11 | coul_12 | coul_13 | coul_14 | coul_15 | coul_16 | coul_17 | coul_18 | coul_19 | coul_20 | teint | teint_2 | teint_3 | teint_4 | teint_5 | teint_6 | teint_7 | teint_8 | teint_9 | teint_10 | teint_11 | teint_12 | teint_13 | teint_14 | teint_15 | teint_16 | teint_17 | teint_18 | teint_19 | teint_20 | pms | pms_2 | pms_3 | pms_4 | pms_5 | pms_6 | pms_7 | pms_8 | pms_9 | pms_10 | pms_11 | pms_12 | pms_13 | pms_14 | pms_15 | pms_16 | pms_17 | pms_18 | pms_19 | pms_20 | pencrt | pencrt_2 | pencrt_3 | pencrt_4 | pencrt_5 | pencrt_6 | pencrt_7 | pencrt_8 | pencrt_9 | pencrt_10 | pencrt_11 | pencrt_12 | pencrt_13 | pencrt_14 | pencrt_15 | pencrt_16 | pencrt_17 | pencrt_18 | pencrt_19 | pencrt_20 | recver | recver_2 | recver_3 | recver_4 | recver_5 | recver_6 | recver_7 | recver_8 | recver_9 | recver_10 | recver_11 | recver_12 | recver_13 | recver_14 | recver_15 | recver_16 | recver_17 | recver_18 | recver_19 | recver_20 | typeimp | typeimp_2 | typeimp_3 | typeimp_4 | typeimp_5 | typeimp_6 | typeimp_7 | typeimp_8 | typeimp_9 | typeimp_10 | typeimp_11 | typeimp_12 | typeimp_13 | typeimp_14 | typeimp_15 | typeimp_16 | typeimp_17 | typeimp_18 | typeimp_19 | typeimp_20 | descriptif | descriptif_2 | descriptif_3 | descriptif_4 | descriptif_5 | descriptif_6 | descriptif_7 | descriptif_8 | descriptif_9 | descriptif_10 | descriptif_11 | descriptif_12 | descriptif_13 | descriptif_14 | descriptif_15 | descriptif_16 | descriptif_17 | descriptif_18 | descriptif_19 | descriptif_20 | cc | cc_2 | cc_3 | cc_4 | cc_5 | cc_6 | cc_7 | cc_8 | cc_9 | cc_10 | cc_11 | cc_12 | cc_13 | cc_14 | cc_15 | cc_16 | cc_17 | cc_18 | cc_19 | cc_20 | afaire | afaire_2 | afaire_3 | afaire_4 | afaire_5 | afaire_6 | afaire_7 | afaire_8 | afaire_9 | afaire_10 | afaire_11 | afaire_12 | afaire_13 | afaire_14 | afaire_15 | afaire_16 | afaire_17 | afaire_18 | afaire_19 | afaire_20 | ordremac | ordremac_2 | ordremac_3 | ordremac_4 | ordremac_5 | ordremac_6 | ordremac_7 | ordremac_8 | ordremac_9 | ordremac_10 | ordremac_11 | ordremac_12 | ordremac_13 | ordremac_14 | ordremac_15 | ordremac_16 | ordremac_17 | ordremac_18 | ordremac_19 | ordremac_20 | anilox | anilox_2 | anilox_3 | anilox_4 | anilox_5 | anilox_6 | anilox_7 | anilox_8 | anilox_9 | anilox_10 | anilox_11 | anilox_12 | anilox_13 | anilox_14 | anilox_15 | anilox_16 | anilox_17 | anilox_18 | anilox_19 | anilox_20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 49 | 1 | 4 | 02/15/2021 09:49:52 | 7 | 923 | 0003 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 48 | 1 | 3 | 02/15/2021 09:49:43 | 7 | 923 | 0003 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 25 | 1 | 1 | 02/08/2021 15:18:03 | 7 | 351 | 0038 |  | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### `gpr_ffcomic`

Type : TABLE — lignes : 1093 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `code1` | varchar(5) |
| 5 | `code2` | varchar(20) |
| 6 | `code3` | varchar(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | varchar(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Extrait :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 1 | 0 | 351 | 0031 |  | 1 | 1 |  | 11/30/2023 12:39:44 | 7 |
| 4 | 1 | 1 | 351 | 0031 |  | 1 | 1 | xxxxx | 11/30/2023 12:37:01 | 7 |
| 5 | 1 | 2 | 351 | 0031 |  | 1 | 1 |  | 11/30/2023 12:39:44 | 7 |

### `gpr_ffcomif`

Type : TABLE — lignes : 3 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `code1` | varchar(5) |
| 5 | `code2` | varchar(20) |
| 6 | `code3` | varchar(10) |
| 7 | `type` | entier2ns |
| 8 | `typt` | octet |
| 9 | `com` | varchar(750) |
| 10 | `dtem` | horodatage |
| 11 | `salm` | entier2ns |

Extrait :

| id | bloq | corbeille | code1 | code2 | code3 | type | typt | com | dtem | salm |
|---|---|---|---|---|---|---|---|---|---|---|
| 2642 | 1 | 0 | 1245 | 0005 |  | 1 | 2 |  | 03/16/2026 10:54:12 | 9998 |
| 2643 | 1 | 1 | 1245 | 0005 |  | 1 | 2 | Vérifier le diamètre bobine lors de la première levée (Maxi  | 03/16/2026 10:53:34 | 9998 |
| 2645 | 1 | 2 | 1245 | 0005 |  | 1 | 2 |  | 03/16/2026 10:54:12 | 9998 |

### `gpr_gpr`

Type : TABLE — lignes : 2804 — colonnes : 15

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `pt` | octet |
| 10 | `mach` | varchar(10) |
| 11 | `dos` | entier8ns |
| 12 | `ligne` | entier4ns |
| 13 | `numclt` | entier4ns |
| 14 | `qtef` | entier8ns |
| 15 | `orig` | varchar(1) |

Extrait :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | pt | mach | dos | ligne | numclt | qtef | orig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 195 | 0 | 0 | 01/21/2026 15:08:20 | 907 | 4 | 907 | 01/21/2026 15:08:20 | 1 | 1 | 1018 | 1 | 470 | 0 |  |
| 194 | 0 | 0 | 01/21/2026 15:08:19 | 907 | 4 | 907 | 01/21/2026 15:08:19 | 89 | 1 | 1018 | 1 | 470 | 1400000 |  |
| 212 | 0 | 0 | 01/21/2026 15:26:57 | 913 | 4 | 913 | 01/21/2026 15:26:57 | 1 | 2 | 1018 | 1 | 470 | 0 |  |

### `gpr_gprcom`

Type : TABLE — lignes : 0 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `typt` | octet |
| 5 | `com` | varchar(750) |
| 6 | `dtem` | horodatage |
| 7 | `salm` | entier2ns |
| 8 | `service` | octet |
| 9 | `operateur` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `pt` | octet |

### `gpr_mat`

Type : TABLE — lignes : 653 — colonnes : 32

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `service` | octet |
| 7 | `operateur` | entier2ns |
| 8 | `amj` | horodatage |
| 9 | `mach` | varchar(10) |
| 10 | `dos` | entier8ns |
| 11 | `ligne` | entier4ns |
| 12 | `numclt` | entier4ns |
| 13 | `qtes` | entier8ns |
| 14 | `orig` | varchar(1) |
| 15 | `reflot` | varchar(15) |
| 16 | `reflot_2` | varchar(15) |
| 17 | `reflot_3` | varchar(15) |
| 18 | `reflot_4` | varchar(15) |
| 19 | `reflot_5` | varchar(15) |
| 20 | `reflot_6` | varchar(15) |
| 21 | `reflot_7` | varchar(15) |
| 22 | `reflot_8` | varchar(15) |
| 23 | `reflot_9` | varchar(15) |
| 24 | `reflot_10` | varchar(15) |
| 25 | `type` | entier4ns |
| 26 | `code1` | varchar(5) |
| 27 | `code2` | varchar(20) |
| 28 | `code3` | varchar(10) |
| 29 | `lai` | entier4ns |
| 30 | `saipos` | varchar(25) |
| 31 | `lpos` | octet |
| 32 | `qtev` | entier8ns |

Extrait :

| id | bloq | corbeille | dtem | salm | service | operateur | amj | mach | dos | ligne | numclt | qtes | orig | reflot | reflot_2 | reflot_3 | reflot_4 | reflot_5 | reflot_6 | reflot_7 | reflot_8 | reflot_9 | reflot_10 | type | code1 | code2 | code3 | lai | saipos | lpos | qtev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 04/28/2021 12:04:33 | 9998 | 4 | 9998 | 04/28/2021 12:04:33 | 1 | 1000 | 1 | 1050 | 7219 |  |  |  |  |  |  |  |  |  |  |  | 1 | 886 | 0002 |  | 267 | P1 | 1 | 7219 |
| 2 | 0 | 1 | 04/28/2021 12:04:33 | 9998 | 4 | 9998 | 04/28/2021 12:04:33 | 1 | 1000 | 1 | 1050 | 7219 |  |  |  |  |  |  |  |  |  |  |  | 1 | 886 | 0002 |  | 267 | P1 | 1 | 7219 |
| 3 | 0 | 0 | 09/08/2021 10:06:11 | 9999 | 4 | 9999 | 09/08/2021 10:06:10 | 0 | 1000 | 1 | 1050 | 0 |  |  |  |  |  |  |  |  |  |  |  | 1 | 886 | 0002 |  | 267 | P1 | 1 | 0 |

### `gpr_sat`

Type : TABLE — lignes : 26 — colonnes : 9

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `numero` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `ini1` | octet |
| 7 | `ini2` | varchar(10) |
| 8 | `ini3` | octet |
| 9 | `ini4` | octet |

Extrait :

| id | numero | bloq | dtem | salm | ini1 | ini2 | ini3 | ini4 |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 04/28/2021 12:05:02 | 9998 | 5 | 1 | 0 | 0 |
| 2 | 2 | 1 | 09/10/2021 11:48:51 | 5 | 1 |  | 0 | 0 |
| 3 | 3 | 1 | 10/19/2021 15:44:08 | 6 | 1 |  | 0 | 0 |

### `mac_atps`

Type : TABLE — lignes : 0 — colonnes : 21

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | varchar(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | réel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `amja` | date |
| 9 | `tps` | réel4 |
| 10 | `hd` | heure |
| 11 | `hd_2` | heure |
| 12 | `hd_3` | heure |
| 13 | `hd_4` | heure |
| 14 | `hd_5` | heure |
| 15 | `hd_6` | heure |
| 16 | `hf` | heure |
| 17 | `hf_2` | heure |
| 18 | `hf_3` | heure |
| 19 | `hf_4` | heure |
| 20 | `hf_5` | heure |
| 21 | `hf_6` | heure |

### `mac_pro`

Type : TABLE — lignes : 43 — colonnes : 74

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | varchar(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | réel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `mon` | entier8ns |
| 8 | `type` | entier2ns |
| 9 | `tmac` | octet |
| 10 | `timp` | octet |
| 11 | `gene` | octet |
| 12 | `nom` | varchar(50) |
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
| 41 | `tht` | numérique |
| 42 | `thd` | numérique |
| 43 | `ths` | numérique |
| 44 | `cci` | numérique |
| 45 | `ccd` | numérique |
| 46 | `ccg` | numérique |
| 47 | `ce` | numérique |
| 48 | `pe` | réel4 |
| 49 | `cs` | numérique |
| 50 | `ps` | réel4 |
| 51 | `dev` | octet |
| 52 | `com` | octet |
| 53 | `com_2` | octet |
| 54 | `com_3` | octet |
| 55 | `com_4` | octet |
| 56 | `com_5` | octet |
| 57 | `com_6` | octet |
| 58 | `com_7` | octet |
| 59 | `com_8` | octet |
| 60 | `com_9` | octet |
| 61 | `com_10` | octet |
| 62 | `tva` | entier8ns |
| 63 | `export` | entier8ns |
| 64 | `exo` | entier8ns |
| 65 | `cee` | entier8ns |
| 66 | `dom` | entier8ns |
| 67 | `fmcal` | entier2ns |
| 68 | `mmim` | entier4ns |
| 69 | `tbob` | entier2ns |
| 70 | `tbobm` | entier2ns |
| 71 | `fcal` | numérique |
| 72 | `cbs` | numérique |
| 73 | `pbs` | réel4 |
| 74 | `codemachcond` | varchar(10) |

Extrait :

| id | code | bloq | corbeille | dtem | salm | mon | type | tmac | timp | gene | nom | lai | nbcoul | nbpap | nbout | tvit | vit | etiq | cond1 | carn | cond2 | coup | cond3 | plan | cond4 | cart | cond5 | pel | dor | ver | bra | ser | gser | num | per | gau | emb | livre | cond6 | tht | thd | ths | cci | ccd | ccg | ce | pe | cs | ps | dev | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | tva | export | exo | cee | dom | fmcal | mmim | tbob | tbobm | fcal | cbs | pbs | codemachcond |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 1 | 0 | 04/22/2026 14:13:13 | 9998 | 4710000000 | 1 | 2 | 1 | 2 | DSI | 333 | 0 | 1 | 2 | 1 | 50 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 55.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 |  |
| 2 | 6 | 1 | 1 | 11/06/2012 22:39:00 | 9999 | 4710000000 | 1 | 3 | 3 | 2 | DSI | 1000 | 8 | 4 | 4 | 1 | 100 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0.000000 | 0 | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 |  |
| 3 | 1 | 1 | 0 | 04/22/2026 14:13:13 | 9998 | 4710000000 | 1 | 2 | 3 | 2 | COHESIO 1 | 510 | 3 | 1 | 3 | 1 | 152 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 2 | 1 | 1 | 1 | 1 | 142.000000 | 0.000000 | 0.000000 | 53.000000 | 0.000000 | 0.000000 | 0.037000 | 50 | 0.000000 | 0 | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 |  |

### `mac_ptps`

Type : TABLE — lignes : 18 — colonnes : 98

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | varchar(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | réel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `j1` | réel4 |
| 9 | `j1hd` | heure |
| 10 | `j1hd_2` | heure |
| 11 | `j1hd_3` | heure |
| 12 | `j1hd_4` | heure |
| 13 | `j1hd_5` | heure |
| 14 | `j1hd_6` | heure |
| 15 | `j1hf` | heure |
| 16 | `j1hf_2` | heure |
| 17 | `j1hf_3` | heure |
| 18 | `j1hf_4` | heure |
| 19 | `j1hf_5` | heure |
| 20 | `j1hf_6` | heure |
| 21 | `j2` | octet |
| 22 | `j3` | octet |
| 23 | `j4` | octet |
| 24 | `j5` | octet |
| 25 | `j6` | octet |
| 26 | `j7` | octet |
| 27 | `j2hd` | heure |
| 28 | `j2hd_2` | heure |
| 29 | `j2hd_3` | heure |
| 30 | `j2hd_4` | heure |
| 31 | `j2hd_5` | heure |
| 32 | `j2hd_6` | heure |
| 33 | `j3hd` | heure |
| 34 | `j3hd_2` | heure |
| 35 | `j3hd_3` | heure |
| 36 | `j3hd_4` | heure |
| 37 | `j3hd_5` | heure |
| 38 | `j3hd_6` | heure |
| 39 | `j4hd` | heure |
| 40 | `j4hd_2` | heure |
| 41 | `j4hd_3` | heure |
| 42 | `j4hd_4` | heure |
| 43 | `j4hd_5` | heure |
| 44 | `j4hd_6` | heure |
| 45 | `j5hd` | heure |
| 46 | `j5hd_2` | heure |
| 47 | `j5hd_3` | heure |
| 48 | `j5hd_4` | heure |
| 49 | `j5hd_5` | heure |
| 50 | `j5hd_6` | heure |
| 51 | `j6hd` | heure |
| 52 | `j6hd_2` | heure |
| 53 | `j6hd_3` | heure |
| 54 | `j6hd_4` | heure |
| 55 | `j6hd_5` | heure |
| 56 | `j6hd_6` | heure |
| 57 | `j7hd` | heure |
| 58 | `j7hd_2` | heure |
| 59 | `j7hd_3` | heure |
| 60 | `j7hd_4` | heure |
| 61 | `j7hd_5` | heure |
| 62 | `j7hd_6` | heure |
| 63 | `j2hf` | heure |
| 64 | `j2hf_2` | heure |
| 65 | `j2hf_3` | heure |
| 66 | `j2hf_4` | heure |
| 67 | `j2hf_5` | heure |
| 68 | `j2hf_6` | heure |
| 69 | `j3hf` | heure |
| 70 | `j3hf_2` | heure |
| 71 | `j3hf_3` | heure |
| 72 | `j3hf_4` | heure |
| 73 | `j3hf_5` | heure |
| 74 | `j3hf_6` | heure |
| 75 | `j4hf` | heure |
| 76 | `j4hf_2` | heure |
| 77 | `j4hf_3` | heure |
| 78 | `j4hf_4` | heure |
| 79 | `j4hf_5` | heure |
| 80 | `j4hf_6` | heure |
| 81 | `j5hf` | heure |
| 82 | `j5hf_2` | heure |
| 83 | `j5hf_3` | heure |
| 84 | `j5hf_4` | heure |
| 85 | `j5hf_5` | heure |
| 86 | `j5hf_6` | heure |
| 87 | `j6hf` | heure |
| 88 | `j6hf_2` | heure |
| 89 | `j6hf_3` | heure |
| 90 | `j6hf_4` | heure |
| 91 | `j6hf_5` | heure |
| 92 | `j6hf_6` | heure |
| 93 | `j7hf` | heure |
| 94 | `j7hf_2` | heure |
| 95 | `j7hf_3` | heure |
| 96 | `j7hf_4` | heure |
| 97 | `j7hf_5` | heure |
| 98 | `j7hf_6` | heure |

Extrait :

| id | code | bloq | corbeille | dtem | salm | type | j1 | j1hd | j1hd_2 | j1hd_3 | j1hd_4 | j1hd_5 | j1hd_6 | j1hf | j1hf_2 | j1hf_3 | j1hf_4 | j1hf_5 | j1hf_6 | j2 | j3 | j4 | j5 | j6 | j7 | j2hd | j2hd_2 | j2hd_3 | j2hd_4 | j2hd_5 | j2hd_6 | j3hd | j3hd_2 | j3hd_3 | j3hd_4 | j3hd_5 | j3hd_6 | j4hd | j4hd_2 | j4hd_3 | j4hd_4 | j4hd_5 | j4hd_6 | j5hd | j5hd_2 | j5hd_3 | j5hd_4 | j5hd_5 | j5hd_6 | j6hd | j6hd_2 | j6hd_3 | j6hd_4 | j6hd_5 | j6hd_6 | j7hd | j7hd_2 | j7hd_3 | j7hd_4 | j7hd_5 | j7hd_6 | j2hf | j2hf_2 | j2hf_3 | j2hf_4 | j2hf_5 | j2hf_6 | j3hf | j3hf_2 | j3hf_3 | j3hf_4 | j3hf_5 | j3hf_6 | j4hf | j4hf_2 | j4hf_3 | j4hf_4 | j4hf_5 | j4hf_6 | j5hf | j5hf_2 | j5hf_3 | j5hf_4 | j5hf_5 | j5hf_6 | j6hf | j6hf_2 | j6hf_3 | j6hf_4 | j6hf_5 | j6hf_6 | j7hf | j7hf_2 | j7hf_3 | j7hf_4 | j7hf_5 | j7hf_6 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 1 | 2 | 04/02/2020 12:20:01 | 9998 | 1 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 2 | 6 | 1 | 1 | 11/06/2012 22:41:00 | 9999 | 1 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |
| 3 | 1 | 1 | 0 | 11/06/2012 22:41:00 | 9999 | 1 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 0 | 0 | 0 | 0 | 0 | 0 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 | 11/30/1999 00:00:00 |

### `mac_tra`

Type : TABLE — lignes : 74 — colonnes : 135

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `code` | varchar(10) |
| 3 | `bloq` | octet |
| 4 | `corbeille` | réel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `type` | entier2ns |
| 8 | `nom` | varchar(50) |
| 9 | `tra` | entier4ns |
| 10 | `ligne` | entier4ns |
| 11 | `typl` | entier2ns |
| 12 | `mfab` | octet |
| 13 | `noml` | varchar(50) |
| 14 | `ttps` | varchar(10) |
| 15 | `ttps_2` | varchar(10) |
| 16 | `ttps_3` | varchar(10) |
| 17 | `ttps_4` | varchar(10) |
| 18 | `ttps_5` | varchar(10) |
| 19 | `ttps_6` | varchar(10) |
| 20 | `ttps_7` | varchar(10) |
| 21 | `ttps_8` | varchar(10) |
| 22 | `ttps_9` | varchar(10) |
| 23 | `ttps_10` | varchar(10) |
| 24 | `ttps_11` | varchar(10) |
| 25 | `ttps_12` | varchar(10) |
| 26 | `tps` | réel4 |
| 27 | `tps_2` | réel4 |
| 28 | `tps_3` | réel4 |
| 29 | `tps_4` | réel4 |
| 30 | `tps_5` | réel4 |
| 31 | `tps_6` | réel4 |
| 32 | `tps_7` | réel4 |
| 33 | `tps_8` | réel4 |
| 34 | `tps_9` | réel4 |
| 35 | `tps_10` | réel4 |
| 36 | `tps_11` | réel4 |
| 37 | `tps_12` | réel4 |
| 38 | `tgac` | varchar(10) |
| 39 | `tgac_2` | varchar(10) |
| 40 | `tgac_3` | varchar(10) |
| 41 | `tgac_4` | varchar(10) |
| 42 | `tgac_5` | varchar(10) |
| 43 | `tgac_6` | varchar(10) |
| 44 | `tgac_7` | varchar(10) |
| 45 | `tgac_8` | varchar(10) |
| 46 | `tgac_9` | varchar(10) |
| 47 | `tgac_10` | varchar(10) |
| 48 | `tgac_11` | varchar(10) |
| 49 | `tgac_12` | varchar(10) |
| 50 | `pgac` | octet |
| 51 | `pgac_2` | octet |
| 52 | `pgac_3` | octet |
| 53 | `pgac_4` | octet |
| 54 | `pgac_5` | octet |
| 55 | `pgac_6` | octet |
| 56 | `pgac_7` | octet |
| 57 | `pgac_8` | octet |
| 58 | `pgac_9` | octet |
| 59 | `pgac_10` | octet |
| 60 | `pgac_11` | octet |
| 61 | `pgac_12` | octet |
| 62 | `gac` | réel4 |
| 63 | `gac_2` | réel4 |
| 64 | `gac_3` | réel4 |
| 65 | `gac_4` | réel4 |
| 66 | `gac_5` | réel4 |
| 67 | `gac_6` | réel4 |
| 68 | `gac_7` | réel4 |
| 69 | `gac_8` | réel4 |
| 70 | `gac_9` | réel4 |
| 71 | `gac_10` | réel4 |
| 72 | `gac_11` | réel4 |
| 73 | `gac_12` | réel4 |
| 74 | `tthc` | varchar(10) |
| 75 | `tthc_2` | varchar(10) |
| 76 | `tthc_3` | varchar(10) |
| 77 | `tthc_4` | varchar(10) |
| 78 | `tthc_5` | varchar(10) |
| 79 | `tthc_6` | varchar(10) |
| 80 | `tthc_7` | varchar(10) |
| 81 | `tthc_8` | varchar(10) |
| 82 | `tthc_9` | varchar(10) |
| 83 | `tthc_10` | varchar(10) |
| 84 | `tthc_11` | varchar(10) |
| 85 | `tthc_12` | varchar(10) |
| 86 | `pthc` | octet |
| 87 | `pthc_2` | octet |
| 88 | `pthc_3` | octet |
| 89 | `pthc_4` | octet |
| 90 | `pthc_5` | octet |
| 91 | `pthc_6` | octet |
| 92 | `pthc_7` | octet |
| 93 | `pthc_8` | octet |
| 94 | `pthc_9` | octet |
| 95 | `pthc_10` | octet |
| 96 | `pthc_11` | octet |
| 97 | `pthc_12` | octet |
| 98 | `thc` | réel4 |
| 99 | `thc_2` | réel4 |
| 100 | `thc_3` | réel4 |
| 101 | `thc_4` | réel4 |
| 102 | `thc_5` | réel4 |
| 103 | `thc_6` | réel4 |
| 104 | `thc_7` | réel4 |
| 105 | `thc_8` | réel4 |
| 106 | `thc_9` | réel4 |
| 107 | `thc_10` | réel4 |
| 108 | `thc_11` | réel4 |
| 109 | `thc_12` | réel4 |
| 110 | `pvit` | octet |
| 111 | `pvit_2` | octet |
| 112 | `pvit_3` | octet |
| 113 | `pvit_4` | octet |
| 114 | `pvit_5` | octet |
| 115 | `pvit_6` | octet |
| 116 | `pvit_7` | octet |
| 117 | `pvit_8` | octet |
| 118 | `pvit_9` | octet |
| 119 | `pvit_10` | octet |
| 120 | `pvit_11` | octet |
| 121 | `pvit_12` | octet |
| 122 | `vit` | réel4 |
| 123 | `vit_2` | réel4 |
| 124 | `vit_3` | réel4 |
| 125 | `vit_4` | réel4 |
| 126 | `vit_5` | réel4 |
| 127 | `vit_6` | réel4 |
| 128 | `vit_7` | réel4 |
| 129 | `vit_8` | réel4 |
| 130 | `vit_9` | réel4 |
| 131 | `vit_10` | réel4 |
| 132 | `vit_11` | réel4 |
| 133 | `vit_12` | réel4 |
| 134 | `point` | entier2ns |
| 135 | `tgcv` | octet |

Extrait :

| id | code | bloq | corbeille | dtem | salm | type | nom | tra | ligne | typl | mfab | noml | ttps | ttps_2 | ttps_3 | ttps_4 | ttps_5 | ttps_6 | ttps_7 | ttps_8 | ttps_9 | ttps_10 | ttps_11 | ttps_12 | tps | tps_2 | tps_3 | tps_4 | tps_5 | tps_6 | tps_7 | tps_8 | tps_9 | tps_10 | tps_11 | tps_12 | tgac | tgac_2 | tgac_3 | tgac_4 | tgac_5 | tgac_6 | tgac_7 | tgac_8 | tgac_9 | tgac_10 | tgac_11 | tgac_12 | pgac | pgac_2 | pgac_3 | pgac_4 | pgac_5 | pgac_6 | pgac_7 | pgac_8 | pgac_9 | pgac_10 | pgac_11 | pgac_12 | gac | gac_2 | gac_3 | gac_4 | gac_5 | gac_6 | gac_7 | gac_8 | gac_9 | gac_10 | gac_11 | gac_12 | tthc | tthc_2 | tthc_3 | tthc_4 | tthc_5 | tthc_6 | tthc_7 | tthc_8 | tthc_9 | tthc_10 | tthc_11 | tthc_12 | pthc | pthc_2 | pthc_3 | pthc_4 | pthc_5 | pthc_6 | pthc_7 | pthc_8 | pthc_9 | pthc_10 | pthc_11 | pthc_12 | thc | thc_2 | thc_3 | thc_4 | thc_5 | thc_6 | thc_7 | thc_8 | thc_9 | thc_10 | thc_11 | thc_12 | pvit | pvit_2 | pvit_3 | pvit_4 | pvit_5 | pvit_6 | pvit_7 | pvit_8 | pvit_9 | pvit_10 | pvit_11 | pvit_12 | vit | vit_2 | vit_3 | vit_4 | vit_5 | vit_6 | vit_7 | vit_8 | vit_9 | vit_10 | vit_11 | vit_12 | point | tgcv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 208 | 6 | 1 | 2.1 | 01/21/2026 11:16:06 | 9998 | 1 |  | 11 | 4 | 7 | 2 | Vernis | F | F | F | F | F | F | S | S | S | S | S | S | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0.17 | 0 | 0 | 0 | 0 | 0 | 0 | S | S | S | S | S | S | S | S | S | S | S | S | 1 | 1 | 1 | 1 | 1 | 1 | 255 | 255 | 255 | 255 | 255 | 255 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | S | S | S | S | S | S | S | S | S | S | S | S | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| 207 | 6 | 1 | 2.1 | 01/21/2026 11:16:01 | 9998 | 1 |  | 11 | 6 | 5 | 2 | Dorure | F | F | F | F | F | F | S | S | S | S | S | S | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0 | 0 | 0 | 0 | 0 | 0 | S | S | S | S | S | S | S | S | S | S | S | S | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | S | S | S | S | S | S | S | S | S | S | S | S | 1 | 1 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| 17 | 1 | 1 | 0 | 10/26/2020 11:43:37 | 9999 | 1 | Classique | 1 | 0 | 1 | 1 | Fabrication |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | F | F | F | F | S | S | S | S | S | S | S | S | 2 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 5 | 5 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | F | F | F | F | F | F | S | S | S | S | S | S | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 197 | 197 | 197 | 197 | 197 | 197 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 255 | 0 | 80 | 80 | 80 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

### `mat_fmat`

Type : TABLE — lignes : 57 — colonnes : 21

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `fam` | entier4ns |
| 3 | `bloq` | octet |
| 4 | `corbeille` | réel4 |
| 5 | `dtem` | horodatage |
| 6 | `salm` | entier2ns |
| 7 | `tva` | entier8ns |
| 8 | `exp` | entier8ns |
| 9 | `cee` | entier8ns |
| 10 | `exo` | entier8ns |
| 11 | `sfam` | entier4ns |
| 12 | `libfam` | varchar(50) |
| 13 | `atva` | entier8ns |
| 14 | `aimp` | entier8ns |
| 15 | `aexo` | entier8ns |
| 16 | `acee` | entier8ns |
| 17 | `adom` | entier8ns |
| 18 | `amon` | entier8ns |
| 19 | `dom` | entier8ns |
| 20 | `mon` | entier8ns |
| 21 | `libsfam` | varchar(50) |

Extrait :

| id | fam | bloq | corbeille | dtem | salm | tva | exp | cee | exo | sfam | libfam | atva | aimp | aexo | acee | adom | amon | dom | mon | libsfam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 138 | 2 | 1 | 0 | 11/13/2020 10:08:33 | 9998 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 6011100000 | 6011120000 | 4710000000 | 6011110000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | Papier |
| 139 | 2 | 1 | 1 | 04/08/2020 14:08:13 | 7 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | grade 127522 |
| 140 | 2 | 1 | 2.1 | 04/08/2020 14:16:36 | 7 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 1 |  | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | 4710000000 | grade 127522 |

### `mat_mat`

Type : TABLE — lignes : 7521 — colonnes : 483

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `type` | entier4ns |
| 10 | `stk` | octet |
| 11 | `sfam` | entier4ns |
| 12 | `libc1` | varchar(50) |
| 13 | `nomen` | octet |
| 14 | `amjf` | date |
| 15 | `amjf_2` | date |
| 16 | `amjf_3` | date |
| 17 | `amjf_4` | date |
| 18 | `amjf_5` | date |
| 19 | `amjf_6` | date |
| 20 | `amjf_7` | date |
| 21 | `amjf_8` | date |
| 22 | `amjf_9` | date |
| 23 | `amjf_10` | date |
| 24 | `libc2` | varchar(50) |
| 25 | `coul` | varchar(20) |
| 26 | `pds` | réel4 |
| 27 | `ctva` | varchar(5) |
| 28 | `pcpv` | réel4 |
| 29 | `remp1` | varchar(5) |
| 30 | `remp2` | varchar(20) |
| 31 | `remp3` | varchar(10) |
| 32 | `com` | octet |
| 33 | `com_2` | octet |
| 34 | `com_3` | octet |
| 35 | `com_4` | octet |
| 36 | `com_5` | octet |
| 37 | `com_6` | octet |
| 38 | `com_7` | octet |
| 39 | `com_8` | octet |
| 40 | `com_9` | octet |
| 41 | `com_10` | octet |
| 42 | `cua` | varchar(5) |
| 43 | `cua_2` | varchar(5) |
| 44 | `cua_3` | varchar(5) |
| 45 | `cua_4` | varchar(5) |
| 46 | `cua_5` | varchar(5) |
| 47 | `cua_6` | varchar(5) |
| 48 | `cua_7` | varchar(5) |
| 49 | `cua_8` | varchar(5) |
| 50 | `cua_9` | varchar(5) |
| 51 | `cua_10` | varchar(5) |
| 52 | `cuc` | varchar(5) |
| 53 | `cuc_2` | varchar(5) |
| 54 | `cuc_3` | varchar(5) |
| 55 | `cuc_4` | varchar(5) |
| 56 | `cuc_5` | varchar(5) |
| 57 | `cuc_6` | varchar(5) |
| 58 | `cuc_7` | varchar(5) |
| 59 | `cuc_8` | varchar(5) |
| 60 | `cuc_9` | varchar(5) |
| 61 | `cuc_10` | varchar(5) |
| 62 | `depot` | varchar(10) |
| 63 | `rang` | varchar(50) |
| 64 | `mini` | réel8 |
| 65 | `maxi` | réel8 |
| 66 | `libt1` | varchar(50) |
| 67 | `libt1_2` | varchar(50) |
| 68 | `libt1_3` | varchar(50) |
| 69 | `libt1_4` | varchar(50) |
| 70 | `libt1_5` | varchar(50) |
| 71 | `libt1_6` | varchar(50) |
| 72 | `libt1_7` | varchar(50) |
| 73 | `libt1_8` | varchar(50) |
| 74 | `libt1_9` | varchar(50) |
| 75 | `libt1_10` | varchar(50) |
| 76 | `pa` | numérique |
| 77 | `libt2` | varchar(50) |
| 78 | `libt2_2` | varchar(50) |
| 79 | `libt2_3` | varchar(50) |
| 80 | `libt2_4` | varchar(50) |
| 81 | `libt2_5` | varchar(50) |
| 82 | `libt2_6` | varchar(50) |
| 83 | `libt2_7` | varchar(50) |
| 84 | `libt2_8` | varchar(50) |
| 85 | `libt2_9` | varchar(50) |
| 86 | `libt2_10` | varchar(50) |
| 87 | `m1_lai` | entier2ns |
| 88 | `m1_lai_2` | entier2ns |
| 89 | `m1_lai_3` | entier2ns |
| 90 | `m1_lai_4` | entier2ns |
| 91 | `m1_lai_5` | entier2ns |
| 92 | `m1_lai_6` | entier2ns |
| 93 | `m1_lai_7` | entier2ns |
| 94 | `m1_lai_8` | entier2ns |
| 95 | `m1_lai_9` | entier2ns |
| 96 | `m1_lai_10` | entier2ns |
| 97 | `m1_lai_11` | entier2ns |
| 98 | `m1_lai_12` | entier2ns |
| 99 | `m1_lai_13` | entier2ns |
| 100 | `m1_lai_14` | entier2ns |
| 101 | `m1_lai_15` | entier2ns |
| 102 | `m1_lai_16` | entier2ns |
| 103 | `m1_lai_17` | entier2ns |
| 104 | `m1_lai_18` | entier2ns |
| 105 | `m1_lai_19` | entier2ns |
| 106 | `m1_lai_20` | entier2ns |
| 107 | `m1_lai_21` | entier2ns |
| 108 | `m1_lai_22` | entier2ns |
| 109 | `m1_lai_23` | entier2ns |
| 110 | `m1_lai_24` | entier2ns |
| 111 | `m1_lai_25` | entier2ns |
| 112 | `m1_lai_26` | entier2ns |
| 113 | `m1_lai_27` | entier2ns |
| 114 | `m1_lai_28` | entier2ns |
| 115 | `m1_lai_29` | entier2ns |
| 116 | `m1_lai_30` | entier2ns |
| 117 | `m1_syn` | octet |
| 118 | `m1_abs` | réel4 |
| 119 | `m1_film` | octet |
| 120 | `m1_epais` | réel4 |
| 121 | `m1_adh` | varchar(25) |
| 122 | `m1_adh_2` | varchar(25) |
| 123 | `m1_adh_3` | varchar(25) |
| 124 | `m1_adh_4` | varchar(25) |
| 125 | `m1_adh_5` | varchar(25) |
| 126 | `m1_adh_6` | varchar(25) |
| 127 | `m1_adh_7` | varchar(25) |
| 128 | `m1_adh_8` | varchar(25) |
| 129 | `m1_adh_9` | varchar(25) |
| 130 | `m1_adh_10` | varchar(25) |
| 131 | `m1_pro` | varchar(25) |
| 132 | `m1_pro_2` | varchar(25) |
| 133 | `m1_pro_3` | varchar(25) |
| 134 | `m1_pro_4` | varchar(25) |
| 135 | `m1_pro_5` | varchar(25) |
| 136 | `m1_pro_6` | varchar(25) |
| 137 | `m1_pro_7` | varchar(25) |
| 138 | `m1_pro_8` | varchar(25) |
| 139 | `m1_pro_9` | varchar(25) |
| 140 | `m1_pro_10` | varchar(25) |
| 141 | `m1_geslaize` | octet |
| 142 | `numfou` | entier4ns |
| 143 | `numfou_2` | entier4ns |
| 144 | `numfou_3` | entier4ns |
| 145 | `numfou_4` | entier4ns |
| 146 | `numfou_5` | entier4ns |
| 147 | `numfou_6` | entier4ns |
| 148 | `numfou_7` | entier4ns |
| 149 | `numfou_8` | entier4ns |
| 150 | `numfou_9` | entier4ns |
| 151 | `numfou_10` | entier4ns |
| 152 | `ref` | varchar(30) |
| 153 | `ref_2` | varchar(30) |
| 154 | `ref_3` | varchar(30) |
| 155 | `ref_4` | varchar(30) |
| 156 | `ref_5` | varchar(30) |
| 157 | `ref_6` | varchar(30) |
| 158 | `ref_7` | varchar(30) |
| 159 | `ref_8` | varchar(30) |
| 160 | `ref_9` | varchar(30) |
| 161 | `ref_10` | varchar(30) |
| 162 | `bar` | varchar(30) |
| 163 | `bar_2` | varchar(30) |
| 164 | `bar_3` | varchar(30) |
| 165 | `bar_4` | varchar(30) |
| 166 | `bar_5` | varchar(30) |
| 167 | `bar_6` | varchar(30) |
| 168 | `bar_7` | varchar(30) |
| 169 | `bar_8` | varchar(30) |
| 170 | `bar_9` | varchar(30) |
| 171 | `bar_10` | varchar(30) |
| 172 | `amjv` | date |
| 173 | `amjv_2` | date |
| 174 | `amjv_3` | date |
| 175 | `amjv_4` | date |
| 176 | `amjv_5` | date |
| 177 | `amjv_6` | date |
| 178 | `amjv_7` | date |
| 179 | `amjv_8` | date |
| 180 | `amjv_9` | date |
| 181 | `amjv_10` | date |
| 182 | `qtemin1` | réel8 |
| 183 | `qtemin1_2` | réel8 |
| 184 | `qtemin1_3` | réel8 |
| 185 | `qtemin1_4` | réel8 |
| 186 | `qtemin1_5` | réel8 |
| 187 | `qtemin1_6` | réel8 |
| 188 | `qtemin1_7` | réel8 |
| 189 | `qtemin1_8` | réel8 |
| 190 | `qtemin1_9` | réel8 |
| 191 | `qtemin1_10` | réel8 |
| 192 | `qtemax1` | réel8 |
| 193 | `qtemax1_2` | réel8 |
| 194 | `qtemax1_3` | réel8 |
| 195 | `qtemax1_4` | réel8 |
| 196 | `qtemax1_5` | réel8 |
| 197 | `qtemax1_6` | réel8 |
| 198 | `qtemax1_7` | réel8 |
| 199 | `qtemax1_8` | réel8 |
| 200 | `qtemax1_9` | réel8 |
| 201 | `qtemax1_10` | réel8 |
| 202 | `pafou1` | numérique |
| 203 | `pafou1_2` | numérique |
| 204 | `pafou1_3` | numérique |
| 205 | `pafou1_4` | numérique |
| 206 | `pafou1_5` | numérique |
| 207 | `pafou1_6` | numérique |
| 208 | `pafou1_7` | numérique |
| 209 | `pafou1_8` | numérique |
| 210 | `pafou1_9` | numérique |
| 211 | `pafou1_10` | numérique |
| 212 | `amj` | horodatage |
| 213 | `qtemin2` | réel8 |
| 214 | `qtemin2_2` | réel8 |
| 215 | `qtemin2_3` | réel8 |
| 216 | `qtemin2_4` | réel8 |
| 217 | `qtemin2_5` | réel8 |
| 218 | `qtemin2_6` | réel8 |
| 219 | `qtemin2_7` | réel8 |
| 220 | `qtemin2_8` | réel8 |
| 221 | `qtemin2_9` | réel8 |
| 222 | `qtemin2_10` | réel8 |
| 223 | `qtemax2` | réel8 |
| 224 | `qtemax2_2` | réel8 |
| 225 | `qtemax2_3` | réel8 |
| 226 | `qtemax2_4` | réel8 |
| 227 | `qtemax2_5` | réel8 |
| 228 | `qtemax2_6` | réel8 |
| 229 | `qtemax2_7` | réel8 |
| 230 | `qtemax2_8` | réel8 |
| 231 | `qtemax2_9` | réel8 |
| 232 | `qtemax2_10` | réel8 |
| 233 | `pafou2` | numérique |
| 234 | `pafou2_2` | numérique |
| 235 | `pafou2_3` | numérique |
| 236 | `pafou2_4` | numérique |
| 237 | `pafou2_5` | numérique |
| 238 | `pafou2_6` | numérique |
| 239 | `pafou2_7` | numérique |
| 240 | `pafou2_8` | numérique |
| 241 | `pafou2_9` | numérique |
| 242 | `pafou2_10` | numérique |
| 243 | `qtemin3` | réel8 |
| 244 | `qtemin3_2` | réel8 |
| 245 | `qtemin3_3` | réel8 |
| 246 | `qtemin3_4` | réel8 |
| 247 | `qtemin3_5` | réel8 |
| 248 | `qtemin3_6` | réel8 |
| 249 | `qtemin3_7` | réel8 |
| 250 | `qtemin3_8` | réel8 |
| 251 | `qtemin3_9` | réel8 |
| 252 | `qtemin3_10` | réel8 |
| 253 | `qtemax3` | réel8 |
| 254 | `qtemax3_2` | réel8 |
| 255 | `qtemax3_3` | réel8 |
| 256 | `qtemax3_4` | réel8 |
| 257 | `qtemax3_5` | réel8 |
| 258 | `qtemax3_6` | réel8 |
| 259 | `qtemax3_7` | réel8 |
| 260 | `qtemax3_8` | réel8 |
| 261 | `qtemax3_9` | réel8 |
| 262 | `qtemax3_10` | réel8 |
| 263 | `pafou3` | numérique |
| 264 | `pafou3_2` | numérique |
| 265 | `pafou3_3` | numérique |
| 266 | `pafou3_4` | numérique |
| 267 | `pafou3_5` | numérique |
| 268 | `pafou3_6` | numérique |
| 269 | `pafou3_7` | numérique |
| 270 | `pafou3_8` | numérique |
| 271 | `pafou3_9` | numérique |
| 272 | `pafou3_10` | numérique |
| 273 | `qtemin4` | réel8 |
| 274 | `qtemin4_2` | réel8 |
| 275 | `qtemin4_3` | réel8 |
| 276 | `qtemin4_4` | réel8 |
| 277 | `qtemin4_5` | réel8 |
| 278 | `qtemin4_6` | réel8 |
| 279 | `qtemin4_7` | réel8 |
| 280 | `qtemin4_8` | réel8 |
| 281 | `qtemin4_9` | réel8 |
| 282 | `qtemin4_10` | réel8 |
| 283 | `qtemax4` | réel8 |
| 284 | `qtemax4_2` | réel8 |
| 285 | `qtemax4_3` | réel8 |
| 286 | `qtemax4_4` | réel8 |
| 287 | `qtemax4_5` | réel8 |
| 288 | `qtemax4_6` | réel8 |
| 289 | `qtemax4_7` | réel8 |
| 290 | `qtemax4_8` | réel8 |
| 291 | `qtemax4_9` | réel8 |
| 292 | `qtemax4_10` | réel8 |
| 293 | `pafou4` | numérique |
| 294 | `pafou4_2` | numérique |
| 295 | `pafou4_3` | numérique |
| 296 | `pafou4_4` | numérique |
| 297 | `pafou4_5` | numérique |
| 298 | `pafou4_6` | numérique |
| 299 | `pafou4_7` | numérique |
| 300 | `pafou4_8` | numérique |
| 301 | `pafou4_9` | numérique |
| 302 | `pafou4_10` | numérique |
| 303 | `qtemin5` | réel8 |
| 304 | `qtemin5_2` | réel8 |
| 305 | `qtemin5_3` | réel8 |
| 306 | `qtemin5_4` | réel8 |
| 307 | `qtemin5_5` | réel8 |
| 308 | `qtemin5_6` | réel8 |
| 309 | `qtemin5_7` | réel8 |
| 310 | `qtemin5_8` | réel8 |
| 311 | `qtemin5_9` | réel8 |
| 312 | `qtemin5_10` | réel8 |
| 313 | `qtemax5` | réel8 |
| 314 | `qtemax5_2` | réel8 |
| 315 | `qtemax5_3` | réel8 |
| 316 | `qtemax5_4` | réel8 |
| 317 | `qtemax5_5` | réel8 |
| 318 | `qtemax5_6` | réel8 |
| 319 | `qtemax5_7` | réel8 |
| 320 | `qtemax5_8` | réel8 |
| 321 | `qtemax5_9` | réel8 |
| 322 | `qtemax5_10` | réel8 |
| 323 | `pafou5` | numérique |
| 324 | `pafou5_2` | numérique |
| 325 | `pafou5_3` | numérique |
| 326 | `pafou5_4` | numérique |
| 327 | `pafou5_5` | numérique |
| 328 | `pafou5_6` | numérique |
| 329 | `pafou5_7` | numérique |
| 330 | `pafou5_8` | numérique |
| 331 | `pafou5_9` | numérique |
| 332 | `pafou5_10` | numérique |
| 333 | `qtemin6` | réel8 |
| 334 | `qtemin6_2` | réel8 |
| 335 | `qtemin6_3` | réel8 |
| 336 | `qtemin6_4` | réel8 |
| 337 | `qtemin6_5` | réel8 |
| 338 | `qtemin6_6` | réel8 |
| 339 | `qtemin6_7` | réel8 |
| 340 | `qtemin6_8` | réel8 |
| 341 | `qtemin6_9` | réel8 |
| 342 | `qtemin6_10` | réel8 |
| 343 | `qtemax6` | réel8 |
| 344 | `qtemax6_2` | réel8 |
| 345 | `qtemax6_3` | réel8 |
| 346 | `qtemax6_4` | réel8 |
| 347 | `qtemax6_5` | réel8 |
| 348 | `qtemax6_6` | réel8 |
| 349 | `qtemax6_7` | réel8 |
| 350 | `qtemax6_8` | réel8 |
| 351 | `qtemax6_9` | réel8 |
| 352 | `qtemax6_10` | réel8 |
| 353 | `pafou6` | numérique |
| 354 | `pafou6_2` | numérique |
| 355 | `pafou6_3` | numérique |
| 356 | `pafou6_4` | numérique |
| 357 | `pafou6_5` | numérique |
| 358 | `pafou6_6` | numérique |
| 359 | `pafou6_7` | numérique |
| 360 | `pafou6_8` | numérique |
| 361 | `pafou6_9` | numérique |
| 362 | `pafou6_10` | numérique |
| 363 | `qtemin7` | réel8 |
| 364 | `qtemin7_2` | réel8 |
| 365 | `qtemin7_3` | réel8 |
| 366 | `qtemin7_4` | réel8 |
| 367 | `qtemin7_5` | réel8 |
| 368 | `qtemin7_6` | réel8 |
| 369 | `qtemin7_7` | réel8 |
| 370 | `qtemin7_8` | réel8 |
| 371 | `qtemin7_9` | réel8 |
| 372 | `qtemin7_10` | réel8 |
| 373 | `qtemax7` | réel8 |
| 374 | `qtemax7_2` | réel8 |
| 375 | `qtemax7_3` | réel8 |
| 376 | `qtemax7_4` | réel8 |
| 377 | `qtemax7_5` | réel8 |
| 378 | `qtemax7_6` | réel8 |
| 379 | `qtemax7_7` | réel8 |
| 380 | `qtemax7_8` | réel8 |
| 381 | `qtemax7_9` | réel8 |
| 382 | `qtemax7_10` | réel8 |
| 383 | `pafou7` | numérique |
| 384 | `pafou7_2` | numérique |
| 385 | `pafou7_3` | numérique |
| 386 | `pafou7_4` | numérique |
| 387 | `pafou7_5` | numérique |
| 388 | `pafou7_6` | numérique |
| 389 | `pafou7_7` | numérique |
| 390 | `pafou7_8` | numérique |
| 391 | `pafou7_9` | numérique |
| 392 | `pafou7_10` | numérique |
| 393 | `qtemin8` | réel8 |
| 394 | `qtemin8_2` | réel8 |
| 395 | `qtemin8_3` | réel8 |
| 396 | `qtemin8_4` | réel8 |
| 397 | `qtemin8_5` | réel8 |
| 398 | `qtemin8_6` | réel8 |
| 399 | `qtemin8_7` | réel8 |
| 400 | `qtemin8_8` | réel8 |
| 401 | `qtemin8_9` | réel8 |
| 402 | `qtemin8_10` | réel8 |
| 403 | `qtemax8` | réel8 |
| 404 | `qtemax8_2` | réel8 |
| 405 | `qtemax8_3` | réel8 |
| 406 | `qtemax8_4` | réel8 |
| 407 | `qtemax8_5` | réel8 |
| 408 | `qtemax8_6` | réel8 |
| 409 | `qtemax8_7` | réel8 |
| 410 | `qtemax8_8` | réel8 |
| 411 | `qtemax8_9` | réel8 |
| 412 | `qtemax8_10` | réel8 |
| 413 | `pafou8` | numérique |
| 414 | `pafou8_2` | numérique |
| 415 | `pafou8_3` | numérique |
| 416 | `pafou8_4` | numérique |
| 417 | `pafou8_5` | numérique |
| 418 | `pafou8_6` | numérique |
| 419 | `pafou8_7` | numérique |
| 420 | `pafou8_8` | numérique |
| 421 | `pafou8_9` | numérique |
| 422 | `pafou8_10` | numérique |
| 423 | `qtemin9` | réel8 |
| 424 | `qtemin9_2` | réel8 |
| 425 | `qtemin9_3` | réel8 |
| 426 | `qtemin9_4` | réel8 |
| 427 | `qtemin9_5` | réel8 |
| 428 | `qtemin9_6` | réel8 |
| 429 | `qtemin9_7` | réel8 |
| 430 | `qtemin9_8` | réel8 |
| 431 | `qtemin9_9` | réel8 |
| 432 | `qtemin9_10` | réel8 |
| 433 | `qtemax9` | réel8 |
| 434 | `qtemax9_2` | réel8 |
| 435 | `qtemax9_3` | réel8 |
| 436 | `qtemax9_4` | réel8 |
| 437 | `qtemax9_5` | réel8 |
| 438 | `qtemax9_6` | réel8 |
| 439 | `qtemax9_7` | réel8 |
| 440 | `qtemax9_8` | réel8 |
| 441 | `qtemax9_9` | réel8 |
| 442 | `qtemax9_10` | réel8 |
| 443 | `pafou9` | numérique |
| 444 | `pafou9_2` | numérique |
| 445 | `pafou9_3` | numérique |
| 446 | `pafou9_4` | numérique |
| 447 | `pafou9_5` | numérique |
| 448 | `pafou9_6` | numérique |
| 449 | `pafou9_7` | numérique |
| 450 | `pafou9_8` | numérique |
| 451 | `pafou9_9` | numérique |
| 452 | `pafou9_10` | numérique |
| 453 | `qtemin10` | réel8 |
| 454 | `qtemin10_2` | réel8 |
| 455 | `qtemin10_3` | réel8 |
| 456 | `qtemin10_4` | réel8 |
| 457 | `qtemin10_5` | réel8 |
| 458 | `qtemin10_6` | réel8 |
| 459 | `qtemin10_7` | réel8 |
| 460 | `qtemin10_8` | réel8 |
| 461 | `qtemin10_9` | réel8 |
| 462 | `qtemin10_10` | réel8 |
| 463 | `qtemax10` | réel8 |
| 464 | `qtemax10_2` | réel8 |
| 465 | `qtemax10_3` | réel8 |
| 466 | `qtemax10_4` | réel8 |
| 467 | `qtemax10_5` | réel8 |
| 468 | `qtemax10_6` | réel8 |
| 469 | `qtemax10_7` | réel8 |
| 470 | `qtemax10_8` | réel8 |
| 471 | `qtemax10_9` | réel8 |
| 472 | `qtemax10_10` | réel8 |
| 473 | `pafou10` | numérique |
| 474 | `pafou10_2` | numérique |
| 475 | `pafou10_3` | numérique |
| 476 | `pafou10_4` | numérique |
| 477 | `pafou10_5` | numérique |
| 478 | `pafou10_6` | numérique |
| 479 | `pafou10_7` | numérique |
| 480 | `pafou10_8` | numérique |
| 481 | `pafou10_9` | numérique |
| 482 | `pafou10_10` | numérique |
| 483 | `gener` | octet |

Extrait :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | stk | sfam | libc1 | nomen | amjf | amjf_2 | amjf_3 | amjf_4 | amjf_5 | amjf_6 | amjf_7 | amjf_8 | amjf_9 | amjf_10 | libc2 | coul | pds | ctva | pcpv | remp1 | remp2 | remp3 | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | cua | cua_2 | cua_3 | cua_4 | cua_5 | cua_6 | cua_7 | cua_8 | cua_9 | cua_10 | cuc | cuc_2 | cuc_3 | cuc_4 | cuc_5 | cuc_6 | cuc_7 | cuc_8 | cuc_9 | cuc_10 | depot | rang | mini | maxi | libt1 | libt1_2 | libt1_3 | libt1_4 | libt1_5 | libt1_6 | libt1_7 | libt1_8 | libt1_9 | libt1_10 | pa | libt2 | libt2_2 | libt2_3 | libt2_4 | libt2_5 | libt2_6 | libt2_7 | libt2_8 | libt2_9 | libt2_10 | m1_lai | m1_lai_2 | m1_lai_3 | m1_lai_4 | m1_lai_5 | m1_lai_6 | m1_lai_7 | m1_lai_8 | m1_lai_9 | m1_lai_10 | m1_lai_11 | m1_lai_12 | m1_lai_13 | m1_lai_14 | m1_lai_15 | m1_lai_16 | m1_lai_17 | m1_lai_18 | m1_lai_19 | m1_lai_20 | m1_lai_21 | m1_lai_22 | m1_lai_23 | m1_lai_24 | m1_lai_25 | m1_lai_26 | m1_lai_27 | m1_lai_28 | m1_lai_29 | m1_lai_30 | m1_syn | m1_abs | m1_film | m1_epais | m1_adh | m1_adh_2 | m1_adh_3 | m1_adh_4 | m1_adh_5 | m1_adh_6 | m1_adh_7 | m1_adh_8 | m1_adh_9 | m1_adh_10 | m1_pro | m1_pro_2 | m1_pro_3 | m1_pro_4 | m1_pro_5 | m1_pro_6 | m1_pro_7 | m1_pro_8 | m1_pro_9 | m1_pro_10 | m1_geslaize | numfou | numfou_2 | numfou_3 | numfou_4 | numfou_5 | numfou_6 | numfou_7 | numfou_8 | numfou_9 | numfou_10 | ref | ref_2 | ref_3 | ref_4 | ref_5 | ref_6 | ref_7 | ref_8 | ref_9 | ref_10 | bar | bar_2 | bar_3 | bar_4 | bar_5 | bar_6 | bar_7 | bar_8 | bar_9 | bar_10 | amjv | amjv_2 | amjv_3 | amjv_4 | amjv_5 | amjv_6 | amjv_7 | amjv_8 | amjv_9 | amjv_10 | qtemin1 | qtemin1_2 | qtemin1_3 | qtemin1_4 | qtemin1_5 | qtemin1_6 | qtemin1_7 | qtemin1_8 | qtemin1_9 | qtemin1_10 | qtemax1 | qtemax1_2 | qtemax1_3 | qtemax1_4 | qtemax1_5 | qtemax1_6 | qtemax1_7 | qtemax1_8 | qtemax1_9 | qtemax1_10 | pafou1 | pafou1_2 | pafou1_3 | pafou1_4 | pafou1_5 | pafou1_6 | pafou1_7 | pafou1_8 | pafou1_9 | pafou1_10 | amj | qtemin2 | qtemin2_2 | qtemin2_3 | qtemin2_4 | qtemin2_5 | qtemin2_6 | qtemin2_7 | qtemin2_8 | qtemin2_9 | qtemin2_10 | qtemax2 | qtemax2_2 | qtemax2_3 | qtemax2_4 | qtemax2_5 | qtemax2_6 | qtemax2_7 | qtemax2_8 | qtemax2_9 | qtemax2_10 | pafou2 | pafou2_2 | pafou2_3 | pafou2_4 | pafou2_5 | pafou2_6 | pafou2_7 | pafou2_8 | pafou2_9 | pafou2_10 | qtemin3 | qtemin3_2 | qtemin3_3 | qtemin3_4 | qtemin3_5 | qtemin3_6 | qtemin3_7 | qtemin3_8 | qtemin3_9 | qtemin3_10 | qtemax3 | qtemax3_2 | qtemax3_3 | qtemax3_4 | qtemax3_5 | qtemax3_6 | qtemax3_7 | qtemax3_8 | qtemax3_9 | qtemax3_10 | pafou3 | pafou3_2 | pafou3_3 | pafou3_4 | pafou3_5 | pafou3_6 | pafou3_7 | pafou3_8 | pafou3_9 | pafou3_10 | qtemin4 | qtemin4_2 | qtemin4_3 | qtemin4_4 | qtemin4_5 | qtemin4_6 | qtemin4_7 | qtemin4_8 | qtemin4_9 | qtemin4_10 | qtemax4 | qtemax4_2 | qtemax4_3 | qtemax4_4 | qtemax4_5 | qtemax4_6 | qtemax4_7 | qtemax4_8 | qtemax4_9 | qtemax4_10 | pafou4 | pafou4_2 | pafou4_3 | pafou4_4 | pafou4_5 | pafou4_6 | pafou4_7 | pafou4_8 | pafou4_9 | pafou4_10 | qtemin5 | qtemin5_2 | qtemin5_3 | qtemin5_4 | qtemin5_5 | qtemin5_6 | qtemin5_7 | qtemin5_8 | qtemin5_9 | qtemin5_10 | qtemax5 | qtemax5_2 | qtemax5_3 | qtemax5_4 | qtemax5_5 | qtemax5_6 | qtemax5_7 | qtemax5_8 | qtemax5_9 | qtemax5_10 | pafou5 | pafou5_2 | pafou5_3 | pafou5_4 | pafou5_5 | pafou5_6 | pafou5_7 | pafou5_8 | pafou5_9 | pafou5_10 | qtemin6 | qtemin6_2 | qtemin6_3 | qtemin6_4 | qtemin6_5 | qtemin6_6 | qtemin6_7 | qtemin6_8 | qtemin6_9 | qtemin6_10 | qtemax6 | qtemax6_2 | qtemax6_3 | qtemax6_4 | qtemax6_5 | qtemax6_6 | qtemax6_7 | qtemax6_8 | qtemax6_9 | qtemax6_10 | pafou6 | pafou6_2 | pafou6_3 | pafou6_4 | pafou6_5 | pafou6_6 | pafou6_7 | pafou6_8 | pafou6_9 | pafou6_10 | qtemin7 | qtemin7_2 | qtemin7_3 | qtemin7_4 | qtemin7_5 | qtemin7_6 | qtemin7_7 | qtemin7_8 | qtemin7_9 | qtemin7_10 | qtemax7 | qtemax7_2 | qtemax7_3 | qtemax7_4 | qtemax7_5 | qtemax7_6 | qtemax7_7 | qtemax7_8 | qtemax7_9 | qtemax7_10 | pafou7 | pafou7_2 | pafou7_3 | pafou7_4 | pafou7_5 | pafou7_6 | pafou7_7 | pafou7_8 | pafou7_9 | pafou7_10 | qtemin8 | qtemin8_2 | qtemin8_3 | qtemin8_4 | qtemin8_5 | qtemin8_6 | qtemin8_7 | qtemin8_8 | qtemin8_9 | qtemin8_10 | qtemax8 | qtemax8_2 | qtemax8_3 | qtemax8_4 | qtemax8_5 | qtemax8_6 | qtemax8_7 | qtemax8_8 | qtemax8_9 | qtemax8_10 | pafou8 | pafou8_2 | pafou8_3 | pafou8_4 | pafou8_5 | pafou8_6 | pafou8_7 | pafou8_8 | pafou8_9 | pafou8_10 | qtemin9 | qtemin9_2 | qtemin9_3 | qtemin9_4 | qtemin9_5 | qtemin9_6 | qtemin9_7 | qtemin9_8 | qtemin9_9 | qtemin9_10 | qtemax9 | qtemax9_2 | qtemax9_3 | qtemax9_4 | qtemax9_5 | qtemax9_6 | qtemax9_7 | qtemax9_8 | qtemax9_9 | qtemax9_10 | pafou9 | pafou9_2 | pafou9_3 | pafou9_4 | pafou9_5 | pafou9_6 | pafou9_7 | pafou9_8 | pafou9_9 | pafou9_10 | qtemin10 | qtemin10_2 | qtemin10_3 | qtemin10_4 | qtemin10_5 | qtemin10_6 | qtemin10_7 | qtemin10_8 | qtemin10_9 | qtemin10_10 | qtemax10 | qtemax10_2 | qtemax10_3 | qtemax10_4 | qtemax10_5 | qtemax10_6 | qtemax10_7 | qtemax10_8 | qtemax10_9 | qtemax10_10 | pafou10 | pafou10_2 | pafou10_3 | pafou10_4 | pafou10_5 | pafou10_6 | pafou10_7 | pafou10_8 | pafou10_9 | pafou10_10 | gener |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4753 | 1 | 13 | 09/15/2023 09:59:17 | 2 | 1091 | 0001 |  | 3 | 2 | 1 | Velin Mat Blanc | 1 | 09/06/2023 00:00:00 |  |  |  |  |  |  |  |  |  |  | Blanc | 70 | 1 | 0 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |  |  |  |  |  |  |  |  |  | 12 |  |  |  |  |  |  |  |  |  |  |  | 1 | 20 | Crown V challenger 68 g, FSC |  |  |  |  |  |  |  |  |  | 1005.000000 | Ø Bob.1.000 mm, Ø Mandrin 152 mm, Bob. 11.000 ml |  |  |  |  |  |  |  |  |  | 333 | 440 | 470 | 510 | 530 | 570 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 65535 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 267 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Crown V challenger |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12/31/2099 00:00:00 |  |  |  |  |  |  |  |  |  | 1 | 0.01 | 0.01 | 0.01 | 0.01 | 0 | 0 | 0 | 0 | 0 | 9999999999.99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.086220 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 10/08/2020 17:18:10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |
| 1114 | 1 | 18.2 | 03/04/2021 15:10:15 | 7 | 1101 | 0002 |  | 13 | 2 | 0 | Tube Ø 40 mm, Lg 1.500 mm, 4 mm, Pal. 736 tubes | 1 | 01/01/2021 00:00:00 | 02/08/2021 00:00:00 |  |  |  |  |  |  |  |  | Ø Int 40,9 mm, Ext 48,9 mm, Résistance 30 kg |  | 0 | 1 | 0 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 15 |  |  |  |  |  |  |  |  | 15 | 41 |  |  |  |  |  |  |  |  |  |  | 0 | 99999999999.99 | Tube Ø 40 mm, Lg 1.500 mm, 4 mm, Pal. 736 tubes | Mandrin carton Ø int 40,9 ext 48,9 Lg 1500 |  |  |  |  |  |  |  |  | 0.000000 | Ø Int 40,9 mm, Ext 48,9 mm, Résistance 30 kg | Brut/Neutre |  |  |  |  |  |  |  |  | 1500 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 1101 | 1101 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | SIFA Mandrin_1500x40_CA |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12/31/2021 00:00:00 | 12/31/2021 00:00:00 |  |  |  |  |  |  |  |  | 0.01 | 1 | 0.01 | 0.01 | 0.01 | 0 | 0 | 0 | 0 | 0 | 9999999999.99 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.740000 | 0.750000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 01/29/2021 15:58:42 | 0 | 10000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9999999999.99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |
| 1113 | 1 | 17.1 | 03/04/2021 15:09:56 | 7 | 1101 | 0002 |  | 13 | 2 | 0 | Tube Ø 40 mm, Lg 1.500 mm, 4 mm, Pal. 736 tubes | 1 | 01/01/2021 00:00:00 | 02/08/2021 00:00:00 |  |  |  |  |  |  |  |  | Ø Int 40,9 mm, Ext 48,9 mm, Résistance 30 kg |  | 0 | 1 | 0 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 15 |  |  |  |  |  |  |  |  | 15 | 41 |  |  |  |  |  |  |  |  |  |  | 0 | 99999999999.99 | Tube Ø 40 mm, Lg 1.500 mm, 4 mm, Pal. 736 tubes | Mandrin carton Ø int 40,9 ext 48,9 Lg 1500 |  |  |  |  |  |  |  |  | 0.000000 | Ø Int 40,9 mm, Ext 48,9 mm, Résistance 30 kg | Brut/Neutre |  |  |  |  |  |  |  |  | 1500 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 | 1101 | 1101 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  | SIFA Mandrin_1500x40_CA |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 12/31/2021 00:00:00 | 12/31/2021 00:00:00 |  |  |  |  |  |  |  |  | 0.01 | 1 | 0.01 | 0.01 | 0.01 | 0 | 0 | 0 | 0 | 0 | 9999999999.99 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.740000 | 0.750000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 01/29/2021 15:58:42 | 0 | 10000.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9999999999.99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |

### `mat_matcom`

Type : TABLE — lignes : 79 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | varchar(5) |
| 6 | `code2` | varchar(20) |
| 7 | `code3` | varchar(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | varchar(50) |
| 11 | `com` | varchar(750) |

Extrait :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 04/14/2020 11:05:01 | ENLEV | ADPS4007 |  | 7 | 1 | 7 | Ne laisse pas de trace Cohésio 2 fondoir 160° |
| 2 | 1 | 1 | 04/14/2020 11:05:01 | ENLEV | ADPS4007 |  | 7 | 1 | 7 | Ne laisse pas de trace Cohésio 2 fondoir 160° |
| 3 | 1 | 0 | 04/14/2020 11:52:00 | ENLEV | ADTLH2355 |  | 7 | 1 | 7 | Laisse une légère trace |

### `mat_matcomif`

Type : TABLE — lignes : 6089 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | varchar(5) |
| 6 | `code2` | varchar(20) |
| 7 | `code3` | varchar(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | varchar(50) |
| 11 | `com` | varchar(750) |

Extrait :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 02/07/2022 08:57:17 |  | 1089 |  | 0 | 9 | 7 | ~~ |
| 2 | 1 | 1 | 02/07/2022 08:57:17 |  | 1089 |  | 0 | 9 | 7 | ~~ |
| 3 | 1 | 0 | 10/09/2024 16:08:07 |  | 1091 |  | 0 | 9 | 901 | ~~R:\Matières\Emballage\Cartonnages du Nord~ |

### `mat_matcomir`

Type : TABLE — lignes : 0 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | varchar(5) |
| 6 | `code2` | varchar(20) |
| 7 | `code3` | varchar(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | varchar(50) |
| 11 | `com` | varchar(750) |

### `mat_matcomis`

Type : TABLE — lignes : 18 — colonnes : 11

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `code1` | varchar(5) |
| 6 | `code2` | varchar(20) |
| 7 | `code3` | varchar(10) |
| 8 | `type` | entier4ns |
| 9 | `typt` | octet |
| 10 | `salm` | varchar(50) |
| 11 | `com` | varchar(750) |

Extrait :

| id | bloq | corbeille | dtem | code1 | code2 | code3 | type | typt | salm | com |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 02/28/2023 20:05:15 | 1058 | 0005 |  | 17 | 1 | 6 | une partie dans l allée B et dans le batimment 2 |
| 2 | 1 | 1 | 02/28/2023 20:05:15 | 1058 | 0005 |  | 17 | 1 | 6 | une partie dans l allée B et dans le batimment 2 |
| 3 | 1 | 0 | 02/28/2023 20:06:19 | 1059 | 0021 |  | 17 | 1 | 6 | mit dans la  première allé du batiment 2 |

### `mat_nomen`

Type : TABLE — lignes : 482 — colonnes : 46

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `dtem` | horodatage |
| 5 | `salm` | entier2ns |
| 6 | `code1` | varchar(5) |
| 7 | `code2` | varchar(20) |
| 8 | `code3` | varchar(10) |
| 9 | `type` | entier2ns |
| 10 | `amj` | horodatage |
| 11 | `fam` | entier4ns |
| 12 | `sfam` | entier4ns |
| 13 | `gamme` | entier2ns |
| 14 | `cuv` | varchar(5) |
| 15 | `depot` | varchar(10) |
| 16 | `qte` | réel8 |
| 17 | `htn` | numérique |
| 18 | `pa` | numérique |
| 19 | `pub` | numérique |
| 20 | `pun` | numérique |
| 21 | `suv` | octet |
| 22 | `vuv` | numérique |
| 23 | `net` | octet |
| 24 | `trem` | octet |
| 25 | `rem` | numérique |
| 26 | `des1` | varchar(50) |
| 27 | `lignenomen` | entier4ns |
| 28 | `des2` | varchar(50) |
| 29 | `des3` | varchar(50) |
| 30 | `des4` | varchar(50) |
| 31 | `htb` | numérique |
| 32 | `com` | octet |
| 33 | `com_2` | octet |
| 34 | `com_3` | octet |
| 35 | `com_4` | octet |
| 36 | `com_5` | octet |
| 37 | `com_6` | octet |
| 38 | `com_7` | octet |
| 39 | `com_8` | octet |
| 40 | `com_9` | octet |
| 41 | `com_10` | octet |
| 42 | `lpos` | octet |
| 43 | `rtype` | octet |
| 44 | `rcod1` | varchar(5) |
| 45 | `rcod2` | varchar(20) |
| 46 | `rcod3` | varchar(10) |

Extrait :

| id | bloq | corbeille | dtem | salm | code1 | code2 | code3 | type | amj | fam | sfam | gamme | cuv | depot | qte | htn | pa | pub | pun | suv | vuv | net | trem | rem | des1 | lignenomen | des2 | des3 | des4 | htb | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | lpos | rtype | rcod1 | rcod2 | rcod3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 126 | 1 | -1 | 12/09/2025 17:16:07 | 9998 | 886 | 0001 |  | 1 | 11/30/1999 00:00:00 | 0 | 1 | 0 | 10 |  | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1.00000 | 0 | 1 | 0.000000 | Glassine Jaune Siliconée | 1 |  |  |  | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 0001 |  |
| 127 | 1 | 1 | 12/09/2025 17:16:07 | 9998 | 886 | 0001 |  | 1 | 11/30/1999 00:00:00 | 0 | 1 | 0 | 10 |  | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1.00000 | 0 | 1 | 0.000000 | Glassine Jaune Siliconée | 1 |  |  |  | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 0001 |  |
| 870 | 1 | 2 | 03/30/2026 13:59:19 | 9998 | 886 | 0037 |  | 1 | 11/30/1999 00:00:00 | 0 | 1 | 0 | 10 |  | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 2 | 1.00000 | 0 | 1 | 0.000000 | Thermique Pro 108g | 3 |  |  Thermique pro 108g |  | 0.000000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | 0007 |  |

### `vte_com`

Type : TABLE — lignes : 2172 — colonnes : 9

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `typt` | octet |
| 5 | `com` | varchar(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Extrait :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 2 | Erreur de tarif sur facture 15020042 | 15020098 | 1 | 02/26/2015 17:04:00 | 3 |
| 2 | 1 | 1 | 2 | Erreur de tarif sur facture 15020042 | 15020098 | 1 | 02/26/2015 17:04:00 | 3 |
| 3 | 1 | 0 | 2 | erreur tarif | 15020100 | 3 | 02/26/2015 17:11:00 | 3 |

### `vte_comic`

Type : TABLE — lignes : 20 — colonnes : 9

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `bloq` | octet |
| 3 | `corbeille` | réel4 |
| 4 | `typt` | octet |
| 5 | `com` | varchar(750) |
| 6 | `numpiece` | entier8ns |
| 7 | `numligne` | entier4ns |
| 8 | `dtem` | horodatage |
| 9 | `salm` | entier2ns |

Extrait :

| id | bloq | corbeille | typt | com | numpiece | numligne | dtem | salm |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 0 | 1 |   Avoir sur Facture 15030066 erreur de prix. | 15030091 | 0 | 03/17/2015 14:27:00 | 5 |
| 2 | 1 | 1 | 1 |   Avoir sur Facture 15030066 erreur de prix. | 15030091 | 0 | 03/17/2015 14:27:00 | 5 |
| 3 | 1 | 0 | 2 | AVOIR SUR FACTURE 15040058 DU 16 04 2015 ERREUR DE PRIX | 15060014 | 0 | 06/02/2015 17:40:00 | 5 |

### `vte_entete`

Type : TABLE — lignes : 63411 — colonnes : 97

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | réel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `fax` | varchar(20) |
| 6 | `numero` | entier8ns |
| 7 | `pays` | varchar(50) |
| 8 | `cpays` | varchar(5) |
| 9 | `type` | entier2ns |
| 10 | `operateur` | entier2ns |
| 11 | `amjf` | date |
| 12 | `numclt` | entier4ns |
| 13 | `rs` | varchar(50) |
| 14 | `groupeclt` | entier4ns |
| 15 | `cat1` | entier2ns |
| 16 | `cat2` | entier2ns |
| 17 | `cat3` | entier2ns |
| 18 | `cp` | varchar(10) |
| 19 | `htn` | numérique |
| 20 | `adr1` | varchar(50) |
| 21 | `adr2` | varchar(50) |
| 22 | `ville` | varchar(50) |
| 23 | `bp` | varchar(10) |
| 24 | `fis` | octet |
| 25 | `devise` | varchar(10) |
| 26 | `htb` | numérique |
| 27 | `escompte` | réel4 |
| 28 | `trem` | octet |
| 29 | `rem` | numérique |
| 30 | `tva` | numérique |
| 31 | `ttcn` | numérique |
| 32 | `franco` | numérique |
| 33 | `acompte` | numérique |
| 34 | `reg` | entier4ns |
| 35 | `del` | entier2ns |
| 36 | `de1` | octet |
| 37 | `de2` | octet |
| 38 | `htnb` | numérique |
| 39 | `htnb_2` | numérique |
| 40 | `htnb_3` | numérique |
| 41 | `htnb_4` | numérique |
| 42 | `htnb_5` | numérique |
| 43 | `htnb_6` | numérique |
| 44 | `htnb_7` | numérique |
| 45 | `htnb_8` | numérique |
| 46 | `htnb_9` | numérique |
| 47 | `tvab` | numérique |
| 48 | `tvab_2` | numérique |
| 49 | `tvab_3` | numérique |
| 50 | `tvab_4` | numérique |
| 51 | `tvab_5` | numérique |
| 52 | `tvab_6` | numérique |
| 53 | `tvab_7` | numérique |
| 54 | `tvab_8` | numérique |
| 55 | `tvab_9` | numérique |
| 56 | `civ` | octet |
| 57 | `interlocuteur` | varchar(50) |
| 58 | `tex` | varchar(10) |
| 59 | `mail` | varchar(128) |
| 60 | `com` | octet |
| 61 | `com_2` | octet |
| 62 | `com_3` | octet |
| 63 | `com_4` | octet |
| 64 | `com_5` | octet |
| 65 | `com_6` | octet |
| 66 | `com_7` | octet |
| 67 | `com_8` | octet |
| 68 | `com_9` | octet |
| 69 | `com_10` | octet |
| 70 | `numint` | entier4ns |
| 71 | `dest` | varchar(1) |
| 72 | `frs` | varchar(50) |
| 73 | `fadr1` | varchar(50) |
| 74 | `fadr2` | varchar(50) |
| 75 | `intclt` | entier4ns |
| 76 | `fcp` | varchar(10) |
| 77 | `fville` | varchar(50) |
| 78 | `fpays` | varchar(50) |
| 79 | `amje` | date |
| 80 | `fcpays` | varchar(5) |
| 81 | `pos` | octet |
| 82 | `rap` | octet |
| 83 | `sol` | octet |
| 84 | `numrep` | entier2ns |
| 85 | `cais` | octet |
| 86 | `tvade` | octet |
| 87 | `nfa` | entier8ns |
| 88 | `typa` | octet |
| 89 | `comavoir` | varchar(30) |
| 90 | `vref` | varchar(50) |
| 91 | `nref` | varchar(50) |
| 92 | `fbp` | varchar(10) |
| 93 | `fsiret` | varchar(30) |
| 94 | `fntva` | varchar(30) |
| 95 | `vteauto` | octet |
| 96 | `edi` | octet |
| 97 | `imp` | octet |

Extrait :

| id | corbeille | dtem | salm | fax | numero | pays | cpays | type | operateur | amjf | numclt | rs | groupeclt | cat1 | cat2 | cat3 | cp | htn | adr1 | adr2 | ville | bp | fis | devise | htb | escompte | trem | rem | tva | ttcn | franco | acompte | reg | del | de1 | de2 | htnb | htnb_2 | htnb_3 | htnb_4 | htnb_5 | htnb_6 | htnb_7 | htnb_8 | htnb_9 | tvab | tvab_2 | tvab_3 | tvab_4 | tvab_5 | tvab_6 | tvab_7 | tvab_8 | tvab_9 | civ | interlocuteur | tex | mail | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | numint | dest | frs | fadr1 | fadr2 | intclt | fcp | fville | fpays | amje | fcpays | pos | rap | sol | numrep | cais | tvade | nfa | typa | comavoir | vref | nref | fbp | fsiret | fntva | vteauto | edi | imp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 04/13/2021 11:37:18 | 7 |  | 15010001 | FRANCE | FR | 1 | 5 | 01/08/2015 00:00:00 | 26 | ALKOS COSMETIQUES S.A. | 26 | 0 | 0 | 0 | 62360 | 327.100000 | Zone Industrielle de LANDACRES |  | HESDIN L'ABBE |  | 1 | E | 327.100000 | 0 | 1 | 0.000000 | 65.420000 | 392.520000 | 0.000000 | 0.000000 | 5 | 45 | 4 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | ALKOS COSMETIQUES S.A. | Zone Industrielle de LANDACRES |  | 26 | 62360 | HESDIN L'ABBE | FRANCE | 03/17/2015 00:00:00 | FR | 2 | 0 | 2 | 1 | 0 | 1 | 0 | 0 |  |  |  |  |  | FR 06343967527 | 0 | 0 | 0 |
| 2 | 1 | 01/14/2015 10:42:00 | 5 |  | 15010001 | FRANCE | FR | 1 | 5 | 01/08/2015 00:00:00 | 26 | ALKOS COSMETIQUES S.A. | 26 | 0 | 0 | 0 | 62360 | 327.100000 | Zone Industrielle de LANDACRES |  | HESDIN L'ABBE |  | 1 | E | 327.100000 | 0 | 1 | 0.000000 | 65.420000 | 392.520000 | 0.000000 | 0.000000 | 5 | 45 | 4 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | ALKOS COSMETIQUES S.A. | Zone Industrielle de LANDACRES |  | 26 | 62360 | HESDIN L'ABBE | FRANCE | 03/17/2015 00:00:00 | FR | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |  |  |  |  |  | FR 06343967527 | 0 | 0 | 0 |
| 3 | 0 | 04/13/2021 11:37:18 | 7 |  | 15010002 | FRANCE | FR | 1 | 5 | 01/08/2015 00:00:00 | 26 | ALKOS COSMETIQUES S.A. | 26 | 0 | 0 | 0 | 62360 | 236.340000 | Zone Industrielle de LANDACRES |  | HESDIN L'ABBE |  | 1 | E | 236.340000 | 0 | 1 | 0.000000 | 47.270000 | 283.610000 | 0.000000 | 0.000000 | 5 | 45 | 4 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1 |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | ALKOS COSMETIQUES S.A. | Zone Industrielle de LANDACRES |  | 26 | 62360 | HESDIN L'ABBE | FRANCE | 03/17/2015 00:00:00 | FR | 2 | 0 | 2 | 1 | 0 | 1 | 0 | 0 |  |  |  |  |  | FR 06343967527 | 0 | 0 | 0 |

### `vte_ligne`

Type : TABLE — lignes : 74190 — colonnes : 58

| # | Colonne | Type |
|---:|---|---|
| 1 | `id` | entier8 |
| 2 | `corbeille` | réel4 |
| 3 | `dtem` | horodatage |
| 4 | `salm` | entier2ns |
| 5 | `vtva` | numérique |
| 6 | `numero` | entier8ns |
| 7 | `type` | entier2ns |
| 8 | `htn` | numérique |
| 9 | `htb` | numérique |
| 10 | `trem` | octet |
| 11 | `rem` | numérique |
| 12 | `tva` | numérique |
| 13 | `ttcn` | numérique |
| 14 | `com` | octet |
| 15 | `com_2` | octet |
| 16 | `com_3` | octet |
| 17 | `com_4` | octet |
| 18 | `com_5` | octet |
| 19 | `com_6` | octet |
| 20 | `com_7` | octet |
| 21 | `com_8` | octet |
| 22 | `com_9` | octet |
| 23 | `com_10` | octet |
| 24 | `ligne` | entier4ns |
| 25 | `code1` | varchar(5) |
| 26 | `code2` | varchar(20) |
| 27 | `code3` | varchar(10) |
| 28 | `des1` | varchar(50) |
| 29 | `fam` | octet |
| 30 | `sfam` | entier4ns |
| 31 | `gamme` | entier2ns |
| 32 | `qte` | réel8 |
| 33 | `des2` | varchar(50) |
| 34 | `des3` | varchar(50) |
| 35 | `des4` | varchar(50) |
| 36 | `suv` | octet |
| 37 | `vuv` | numérique |
| 38 | `pa` | numérique |
| 39 | `pub` | numérique |
| 40 | `pun` | numérique |
| 41 | `depot` | varchar(10) |
| 42 | `net` | octet |
| 43 | `ctva` | varchar(5) |
| 44 | `livno` | entier8ns |
| 45 | `livlg` | entier4ns |
| 46 | `livbl` | entier8ns |
| 47 | `cptva` | entier8ns |
| 48 | `cpexp` | entier8ns |
| 49 | `cpexo` | entier8ns |
| 50 | `cpcee` | entier8ns |
| 51 | `cpdom` | entier8ns |
| 52 | `cpmon` | entier8ns |
| 53 | `cuv` | varchar(5) |
| 54 | `vref` | varchar(50) |
| 55 | `nref` | varchar(50) |
| 56 | `pds` | réel4 |
| 57 | `comrep` | réel4 |
| 58 | `mach` | varchar(10) |

Extrait :

| id | corbeille | dtem | salm | vtva | numero | type | htn | htb | trem | rem | tva | ttcn | com | com_2 | com_3 | com_4 | com_5 | com_6 | com_7 | com_8 | com_9 | com_10 | ligne | code1 | code2 | code3 | des1 | fam | sfam | gamme | qte | des2 | des3 | des4 | suv | vuv | pa | pub | pun | depot | net | ctva | livno | livlg | livbl | cptva | cpexp | cpexo | cpcee | cpdom | cpmon | cuv | vref | nref | pds | comrep | mach |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 01/08/2015 17:11:00 | 9999 | 20.00 | 15010001 | 1 | 327.100000 | 327.100000 | 1 | 0.000000 | 65.420000 | 392.520000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 26 | 0702 |  | Etiquette 55 x 65 mm, Therm Eco Perm, Sl | 15 | 9999 | 0 | 27580 | it, Bob.1.000 étiq, M.40, Ext |  |  | 2 | 1000.00000 | 0.000000 | 11.860000 | 11.860000 |  | 0 | 1 | 9911600 | 1 | 9915303 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 049919 | S9911485 du 18/12/2014 | 0 | 0 | S/T |
| 2 | 1 | 01/08/2015 17:11:00 | 9999 | 20.00 | 15010001 | 1 | 327.100000 | 327.100000 | 1 | 0.000000 | 65.420000 | 392.520000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 26 | 0702 |  | Etiquette 55 x 65 mm, Therm Eco Perm, Sl | 15 | 9999 | 0 | 27580 | it, Bob.1.000 étiq, M.40, Ext |  |  | 2 | 1000.00000 | 0.000000 | 11.860000 | 11.860000 |  | 0 | 1 | 9911600 | 1 | 9915303 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 049919 | S9911485 du 18/12/2014 | 0 | 0 | S/T |
| 3 | 0 | 01/08/2015 17:11:00 | 9999 | 20.00 | 15010002 | 1 | 47.340000 | 47.340000 | 1 | 0.000000 | 9.470000 | 56.810000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 26 | 0024 |  | Etiq.12x14 mm,PE Transp Perm - 2 front, | 15 | 9999 | 0 | 18000 | Spot noir,Bob.18 000,Ext,M76 |  |  | 2 | 1000.00000 | 0.000000 | 2.630000 | 2.630000 |  | 0 | 1 | 9911610 | 1 | 9915308 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 050004 |  | 0 | 0 | S/T |
