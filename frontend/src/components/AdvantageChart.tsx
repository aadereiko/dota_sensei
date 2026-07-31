import { useMemo, useRef, useState } from "react";

/**
 * Net advantage over time as a diverging signed area around zero.
 *
 * Form: the data's job is polarity (who is ahead, by how much), so this is a
 * diverging encoding — two opposed hues with a neutral zero baseline.
 *
 * Colour: Radiant blue / Dire red rather than Dota's green/red. Green vs red
 * measures ΔE 7.0 under deuteranopia, inside the fail band; blue vs red measures
 * 19.2 on this surface. Position above/below the baseline carries the meaning
 * anyway, so hue is redundant encoding rather than the only channel.
 *
 * Gold and XP get separate charts on purpose — one plot with two y-scales would
 * invent a correlation the data doesn't contain.
 */

const RADIANT = "#3987e5";
const DIRE = "#e66767";
const GRID = "#2c2c2a";
const BASELINE = "#383835";
const MUTED = "#898781";

interface Props {
  title: string;
  /** Per-minute radiant-minus-dire. Index is the minute. */
  series: number[];
  /** Formats a value for the axis and tooltip, e.g. "12.4k". */
  format?: (value: number) => string;
  /**
   * Smallest domain the chart will zoom to. Without a floor, a game that stayed
   * within a few hundred gold would be stretched into a dramatic mountain range.
   */
  minSpan?: number;
  height?: number;
}

const PAD = { top: 16, right: 12, bottom: 22, left: 46 };

export function AdvantageChart({
  title,
  series,
  format = compact,
  minSpan = 4000,
  height = 180,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const width = 640; // viewBox units; the SVG scales to its container

  const geom = useMemo(() => {
    const plotW = width - PAD.left - PAD.right;
    const plotH = height - PAD.top - PAD.bottom;

    // Fit the data but always include zero, so the baseline stays truthful while
    // the plot actually uses its canvas. A symmetric domain wasted half the
    // height on a one-sided stomp, which is most games.
    let top = Math.max(0, ...series);
    let bottom = Math.min(0, ...series);
    const shortfall = minSpan - (top - bottom);
    if (shortfall > 0) {
      top += shortfall / 2;
      bottom -= shortfall / 2;
    }

    const x = (i: number) =>
      PAD.left + (series.length <= 1 ? 0 : (i / (series.length - 1)) * plotW);
    const y = (v: number) => PAD.top + ((top - v) / (top - bottom)) * plotH;
    return { plotW, plotH, top, bottom, x, y, zeroY: PAD.top + (top / (top - bottom)) * plotH };
  }, [series, height, minSpan]);

  if (series.length === 0) return null;

  // Two clipped copies of one area path: above the baseline is Radiant, below
  // is Dire. Clipping keeps the crossings exact without hunting for roots.
  const areaPath = [
    `M ${geom.x(0)} ${geom.zeroY}`,
    ...series.map((v, i) => `L ${geom.x(i)} ${geom.y(v)}`),
    `L ${geom.x(series.length - 1)} ${geom.zeroY}`,
    "Z",
  ].join(" ");
  const linePath = series.map((v, i) => `${i ? "L" : "M"} ${geom.x(i)} ${geom.y(v)}`).join(" ");

  const uid = title.replace(/\W/g, "");
  const ticks = axisTicks(geom.bottom, geom.top);
  const last = series[series.length - 1] ?? 0;

  const onMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    const i = Math.round(ratio * width - PAD.left) / (geom.plotW / (series.length - 1));
    setHover(Math.max(0, Math.min(series.length - 1, Math.round(i))));
  };

  return (
    <figure className="rounded-lg border border-border-subtle bg-surface-raised p-4">
      <figcaption className="mb-1 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-200">{title}</h3>
        {/* Legend carries the direction too. Tick labels are magnitudes, so
            without this "20k" above and "20k" below reads as one scale twice —
            and putting the arrows inside the SVG collided with the 0 tick. */}
        <span className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-sm" style={{ background: RADIANT }} />
            <span className="text-slate-400">▲ Radiant</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-sm" style={{ background: DIRE }} />
            <span className="text-slate-400">▼ Dire</span>
          </span>
        </span>
      </figcaption>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full touch-none"
        role="img"
        aria-label={`${title}. Ends at ${format(Math.abs(last))} for ${
          last >= 0 ? "Radiant" : "Dire"
        }.`}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
      >
        <defs>
          <clipPath id={`above-${uid}`}>
            <rect x={0} y={0} width={width} height={geom.zeroY} />
          </clipPath>
          <clipPath id={`below-${uid}`}>
            <rect x={0} y={geom.zeroY} width={width} height={height - geom.zeroY} />
          </clipPath>
        </defs>

        {ticks.map((value) => (
          <g key={value}>
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={geom.y(value)}
              y2={geom.y(value)}
              stroke={value === 0 ? BASELINE : GRID}
              strokeWidth={value === 0 ? 1.5 : 1}
            />
            <text
              x={PAD.left - 6}
              y={geom.y(value) + 3}
              textAnchor="end"
              fontSize="9"
              fill={MUTED}
            >
              {value === 0 ? "0" : format(Math.abs(value))}
            </text>
          </g>
        ))}


        <path d={areaPath} fill={RADIANT} opacity={0.28} clipPath={`url(#above-${uid})`} />
        <path d={areaPath} fill={DIRE} opacity={0.28} clipPath={`url(#below-${uid})`} />
        <path
          d={linePath}
          fill="none"
          stroke={RADIANT}
          strokeWidth={2}
          clipPath={`url(#above-${uid})`}
        />
        <path
          d={linePath}
          fill="none"
          stroke={DIRE}
          strokeWidth={2}
          clipPath={`url(#below-${uid})`}
        />

        {[0, Math.floor(series.length / 2), series.length - 1].map((i) => (
          <text
            key={i}
            x={geom.x(i)}
            y={height - 6}
            textAnchor={i === 0 ? "start" : i === series.length - 1 ? "end" : "middle"}
            fontSize="9"
            fill={MUTED}
          >
            {i}:00
          </text>
        ))}

        {hover !== null && series[hover] !== undefined && (
          <g pointerEvents="none">
            <line
              x1={geom.x(hover)}
              x2={geom.x(hover)}
              y1={PAD.top}
              y2={height - PAD.bottom}
              stroke={MUTED}
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            <circle
              cx={geom.x(hover)}
              cy={geom.y(series[hover])}
              r={4}
              fill={series[hover] >= 0 ? RADIANT : DIRE}
              stroke="#1a2028"
              strokeWidth={2}
            />
          </g>
        )}
      </svg>

      <p className="mt-1 h-4 text-xs text-slate-400">
        {hover !== null && series[hover] !== undefined ? (
          <>
            <span className="font-mono text-slate-300">{hover}:00</span> —{" "}
            {series[hover] === 0 ? (
              "even"
            ) : (
              <>
                <span style={{ color: series[hover] > 0 ? RADIANT : DIRE }}>
                  {series[hover] > 0 ? "Radiant" : "Dire"}
                </span>{" "}
                ahead by{" "}
                <span className="font-mono text-slate-300">
                  {format(Math.abs(series[hover]))}
                </span>
              </>
            )}
          </>
        ) : (
          <span className="text-slate-500">Hover for the value at any minute.</span>
        )}
      </p>
    </figure>
  );
}

function compact(value: number): string {
  return Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(Math.round(value));
}

/** Zero plus a step or two inside the domain — a dense axis out-shouts the data. */
function axisTicks(bottom: number, top: number): number[] {
  const step = niceStep(Math.max(top, -bottom));
  const ticks = new Set([0]);
  for (let v = step; v <= top; v += step) ticks.add(v);
  for (let v = -step; v >= bottom; v -= step) ticks.add(v);
  return [...ticks].sort((a, b) => a - b);
}

function niceStep(reach: number): number {
  const raw = Math.max(1, reach / 2);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  return Math.max(1, Math.round(raw / magnitude) * magnitude);
}
