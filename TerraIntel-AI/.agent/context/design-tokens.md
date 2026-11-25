```css
:root {
  --canvas:#F6F6F4; --surface:#FFFFFF; --surface-sunken:#EFEFEC;
  --border:#E1E1DC; --border-strong:#C9C9C2;
  --text:#1B1B18; --text-muted:#61615C; --text-faint:#8A8A84;
  --accent:#2E6B4F; --accent-hover:#245640;
  --danger:#B42318; --warning:#B54708; --ok:#067647;
  --s-1:4px; --s-2:8px; --s-3:12px; --s-4:16px;
  --s-5:24px; --s-6:32px; --s-7:48px;
  --r-sm:3px; --r-md:5px;
  --shadow-pop:0 1px 2px rgba(16,16,14,.06), 0 6px 16px rgba(16,16,14,.08);
}
```
Typography: Inter (UI), IBM Plex Mono (numerics/IDs). Weights 400/500/600 only.
Scale: 11/12/13/14/16/20/24/32. `tabular-nums` on all statistics. Max measure 72ch.
NDVI ramp: ColorBrewer **YlGn** 9-class, nodata = transparent + hatch.
Difference ramp: **RdBu** 11-class diverging, centred at 0, explicit numeric breakpoints.
Icons: Lucide, 1.5px stroke, 16/20px, one set only.
Focus: `outline: 2px solid var(--accent); outline-offset: 2px` on every interactive element.
