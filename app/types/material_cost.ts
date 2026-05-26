/**
 * MySifa — Calcul des coûts matières (schéma v78).
 * Types de référence pour l'UI / intégrations (stack principal : JS vanilla).
 * Tables SQLite préfixées mc_*
 */

export type MaterialCategoryCode =
  | "FRONTAL"
  | "ADHESIF"
  | "SILICONE"
  | "GLASSINE"
  | "AUTRE";

export type PriceCurrency = "EUR" | "USD";
export type PriceBasis = "PER_KG" | "PER_M2";

/** Clés mc_setting — paramètres globaux (singleton). */
export type McSettingKey =
  | "eur_usd_rate"
  | "default_container_cost_usd"
  | "default_container_kg"
  | "default_margin_eur_m2";

export const MC_SETTING_KEYS: readonly McSettingKey[] = [
  "eur_usd_rate",
  "default_container_cost_usd",
  "default_container_kg",
  "default_margin_eur_m2",
] as const;

export const MC_SETTING_DEFAULTS: Record<McSettingKey, number> = {
  eur_usd_rate: 0.85,
  default_container_cost_usd: 4000,
  default_container_kg: 26000,
  default_margin_eur_m2: 0.06,
};

/** Décimal métier : 12 chiffres max, 4 décimales (aligné validation Pydantic). */
export type McDecimal = number;

export interface McSetting {
  key: McSettingKey;
  value_decimal: McDecimal;
  updated_at?: string;
  updated_by?: number | null;
}

export interface McSupplier {
  id: number;
  name: string;
  country?: string | null;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface McMaterialCategory {
  id: number;
  code: MaterialCategoryCode;
  label: string;
  sort_order: number;
}

export interface McMaterial {
  id: number;
  name: string;
  appellation_code: string;
  category_id: number;
  supplier_id?: number | null;
  weight_per_m2: McDecimal;
  weight_gsm?: number | null;
  price_currency: PriceCurrency;
  unit_price: McDecimal;
  price_basis: PriceBasis;
  tax_incidence: McDecimal;
  is_imported: boolean;
  container_kg?: McDecimal | null;
  container_cost_usd?: McDecimal | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface McMaterialPriceHistory {
  id: number;
  material_id: number;
  unit_price: McDecimal;
  price_currency: PriceCurrency;
  tax_incidence: McDecimal;
  effective_date: string; // YYYY-MM-DD
  source?: string | null;
  created_by?: number | null;
  created_at: string;
}

export interface McProduct {
  id: number;
  code: string;
  name: string;
  frontal_id?: number | null;
  adhesif_id?: number | null;
  silicone_id?: number | null;
  glassine_id?: number | null;
  extra_material_ids?: number[];
  custom_margin_eur_m2?: McDecimal | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Liaison N-N produit ↔ matières « Autre ». */
export interface McProductExtraMaterial {
  product_id: number;
  material_id: number;
  sort_order: number;
}

export interface McProductCostBreakdown {
  product_id: number;
  product_code: string;
  margin_eur_m2: McDecimal;
  components_eur_m2: Record<string, McDecimal>;
  total_before_margin_eur_m2: McDecimal;
  total_eur_m2: McDecimal;
}
