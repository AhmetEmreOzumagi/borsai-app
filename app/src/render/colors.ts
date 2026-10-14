// Model başına sabit renk (sütun ve eğri rengi aynı).
const COLORS: Record<string, string> = {
  v1_5_h99: "#1f5fbf",
  v1_6_h99: "#3d8bd9",
  v1_5_market20_v0: "#6a4fc2",
  pb_v0: "#0f8a6a",
  base_always_ceiling: "#8a8f99",
  base_train_median: "#9a7b4f",
  base_train_mean: "#b5894a",
  base_zero: "#707784",
  base_rate: "#8d6fa8",
  base_last10_rate: "#a0708f",
  ceiling_hazard_v0: "#c0392b",
  "ceiling_hazard_v0@INF": "#e0776b",
  pb_ceiling_v0: "#16a085",
  "pb_ceiling_v0@INF": "#62c4ae",
  ceiling_path_v0: "#7d3c98",
  "ceiling_path_v0@INF": "#af7ac5",
  pb_ceiling_path_v0: "#117864",
  base_km_expanding: "#d68910",
  base_km_last10: "#b7950b",
  // D1 sonrası güncelleme (EK 3 §6.5): ana modelden (ceiling_hazard_v0) ayrışsın diye koyu turuncu
  post_d1_hazard_v0: "#e67e22",
  ALWAYS_CEILING: "#9aa0aa",
};

export function colorOf(modelId: string): string {
  return COLORS[modelId] ?? "#6b7384";
}
