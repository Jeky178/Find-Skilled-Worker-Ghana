import {
  Wrench, Zap, Hammer, Paintbrush, Car, Snowflake, Refrigerator,
  LayoutGrid, Flame, House, Sparkles, Settings,
} from "lucide-react";

const ICONS = {
  wrench: Wrench, zap: Zap, hammer: Hammer, paintbrush: Paintbrush, car: Car,
  snowflake: Snowflake, refrigerator: Refrigerator, "layout-grid": LayoutGrid,
  flame: Flame, home: House, sparkles: Sparkles, settings: Settings,
};

export default function CategoryIcon({ name, ...props }) {
  const Icon = ICONS[name] || Wrench;
  return <Icon aria-hidden="true" {...props} />;
}
