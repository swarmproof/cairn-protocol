# CAIRN Frontend Design Palette

## Color Rules

### Brand Colors (Use These)
- **Amber** (CAIRN brand): `amber-500`, `amber-600`, `amber-700`
- **Stone** (Neutral/UI): `stone-400`, `stone-500`, `stone-600`, `stone-700`, `stone-800`, `stone-900`, `stone-950`

### Semantic Colors (Only for specific meanings)
- **Red** (`red-700`): ONLY for failure states (FAILED task state)
- **Green**: NEVER use (no green in desert palette)
- **Blue**: NEVER use decoratively
- **Purple**: NEVER use

### What to Fix
1. Replace decorative `blue-*`, `green-*`, `emerald-*`, `purple-*` with `amber-*` or `stone-*`
2. Replace generic emoji icons (🚀, ✨, 💡) with geometric shapes or Lucide icons
3. Keep all animation components (BorderBeam, GlowCard, Spotlight, Radar) - just update their colors

### Animation Component Colors
- `BorderBeam`: colorFrom="#d97706" colorTo="#f59e0b" (amber)
- `GlowCard`: glowColor="rgba(217, 119, 6, 0.3)" (amber glow)
- `Spotlight`: fill="rgba(217, 119, 6, 0.1)" (amber tint)
- `Radar`: amber-500 sweep line, amber-tinted circles

### DO NOT
- Remove animation components
- Change layout or structure
- Remove features
- Change component architecture
