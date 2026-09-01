import React, { useState } from 'react';
import { TrendingUp, Calendar } from 'lucide-react';
import { Application } from '../../types';

interface ApplicationTrendChartProps {
  applications: Application[];
}

interface TrendPoint {
  label: string;
  rawDate: string;
  count: number;
}

export default function ApplicationTrendChart({ applications }: ApplicationTrendChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<TrendPoint | null>(null);

  // Group applications by month or date based on volume
  const dateMap: Record<string, { label: string; count: number; date: Date }> = {};

  applications.forEach((app) => {
    if (!app.application_date) return;
    const date = new Date(app.application_date);
    if (isNaN(date.getTime())) return;

    // Use "MMM YYYY" as aggregation bucket
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    const label = date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });

    if (!dateMap[key]) {
      dateMap[key] = { label, count: 0, date };
    }
    dateMap[key].count += 1;
  });

  // Sort chronological
  const points: TrendPoint[] = Object.keys(dateMap)
    .sort()
    .map((key) => ({
      label: dateMap[key].label,
      rawDate: key,
      count: dateMap[key].count,
    }));

  if (applications.length === 0 || points.length === 0) {
    return (
      <div className="glass-2 p-6 sm:p-7 rounded-2xl sm:rounded-3xl flex flex-col items-center justify-center text-center min-h-[280px]">
        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
          <Calendar size={22} />
        </div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">No Application Timeline Data</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs">
          Applications with valid submission dates will automatically populate this chronological activity chart.
        </p>
      </div>
    );
  }

  const maxCount = Math.max(...points.map((p) => p.count), 1);
  const totalInTimeline = points.reduce((acc, curr) => acc + curr.count, 0);

  // SVG dimensions
  const svgWidth = 600;
  const svgHeight = 180;
  const paddingX = 40;
  const paddingY = 25;
  const plotWidth = svgWidth - paddingX * 2;
  const plotHeight = svgHeight - paddingY * 2;

  // Compute coordinate points for line and area path
  const coords = points.map((p, idx) => {
    const x = points.length === 1 
      ? svgWidth / 2 
      : paddingX + (idx / (points.length - 1)) * plotWidth;
    const y = svgHeight - paddingY - (p.count / maxCount) * plotHeight;
    return { x, y, point: p };
  });

  // Build SVG Path
  const linePath = coords.reduce((acc, c, idx) => {
    if (idx === 0) return `M ${c.x} ${c.y}`;
    // Bezier curve smoothing
    const prev = coords[idx - 1];
    const cpX1 = prev.x + (c.x - prev.x) / 2;
    const cpY1 = prev.y;
    const cpX2 = prev.x + (c.x - prev.x) / 2;
    const cpY2 = c.y;
    return `${acc} C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${c.x} ${c.y}`;
  }, '');

  const areaPath = coords.length > 1 
    ? `${linePath} L ${coords[coords.length - 1].x} ${svgHeight - paddingY} L ${coords[0].x} ${svgHeight - paddingY} Z`
    : '';

  return (
    <div className="glass-2 p-4 sm:p-6 rounded-2xl sm:rounded-3xl space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-section-title flex items-center gap-2">
            <TrendingUp size={16} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            Application Activity Over Time
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Historical monthly volume of submitted job applications.
          </p>
        </div>
        <div className="text-right shrink-0">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Peak Month</span>
          <span className="text-sm sm:text-base font-black text-indigo-600 dark:text-indigo-400">
            {maxCount} {maxCount === 1 ? 'app' : 'apps'}
          </span>
        </div>
      </div>

      {/* SVG Time-Series Chart */}
      <div className="relative w-full overflow-hidden pt-2">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto max-h-52 overflow-visible"
          aria-label="Application Volume Timeline Chart"
        >
          <defs>
            <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Horizontal Grid lines */}
          <line
            x1={paddingX}
            y1={svgHeight - paddingY}
            x2={svgWidth - paddingX}
            y2={svgHeight - paddingY}
            className="stroke-slate-200 dark:stroke-white/[0.08]"
            strokeWidth="1"
          />
          <line
            x1={paddingX}
            y1={paddingY + plotHeight / 2}
            x2={svgWidth - paddingX}
            y2={paddingY + plotHeight / 2}
            className="stroke-slate-200/50 dark:stroke-white/[0.04]"
            strokeWidth="1"
            strokeDasharray="4 4"
          />

          {/* Area under curve */}
          {areaPath && (
            <path
              d={areaPath}
              fill="url(#trendGradient)"
              className="transition-all duration-500"
            />
          )}

          {/* Curve Line */}
          <path
            d={linePath}
            fill="none"
            stroke="#6366f1"
            strokeWidth="3"
            strokeLinecap="round"
            className="transition-all duration-500"
          />

          {/* Data Points */}
          {coords.map((c, idx) => {
            const isHovered = hoveredPoint?.rawDate === c.point.rawDate;
            return (
              <g key={idx} className="cursor-pointer">
                {/* Invisible hit box for easier hover/tap on mobile */}
                <circle
                  cx={c.x}
                  cy={c.y}
                  r="16"
                  fill="transparent"
                  onMouseEnter={() => setHoveredPoint(c.point)}
                  onMouseLeave={() => setHoveredPoint(null)}
                />
                {/* Visible Point */}
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={isHovered ? 6 : 4}
                  className="fill-indigo-600 dark:fill-indigo-400 stroke-white dark:stroke-[#0a0f1d] transition-all duration-200"
                  strokeWidth="2.5"
                  style={{
                    filter: isHovered ? 'drop-shadow(0 0 6px #6366f1)' : 'none',
                  }}
                />
              </g>
            );
          })}
        </svg>

        {/* X-Axis Labels */}
        <div className="flex justify-between items-center px-4 sm:px-6 pt-2 text-[10px] sm:text-xs font-semibold text-slate-400 dark:text-slate-500">
          {points.map((p, idx) => (
            <span
              key={p.rawDate}
              className={`transition-colors truncate max-w-[80px] ${
                hoveredPoint?.rawDate === p.rawDate
                  ? 'text-indigo-600 dark:text-indigo-400 font-bold'
                  : ''
              }`}
            >
              {p.label}
            </span>
          ))}
        </div>

        {/* Floating Tooltip Indicator */}
        {hoveredPoint && (
          <div className="mt-2 p-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 text-xs font-bold flex items-center justify-between shadow-lg animate-fade-in">
            <span>{hoveredPoint.label}</span>
            <span>
              {hoveredPoint.count} {hoveredPoint.count === 1 ? 'Application' : 'Applications'} (
              {((hoveredPoint.count / totalInTimeline) * 100).toFixed(1)}%)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
